"""Dual embedding strategy: biomedical PubMedBERT + general Nomic/Ollama."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import urllib.request
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, cast

from mitorag_retrieval.models import RankedChunk, RetrievalDocument, tokenize
from mitorag_retrieval.vector_store import InMemoryVectorStore, Vector


class EmbeddingBackend(Protocol):
    """Text embedding backend used by dense retrievers."""

    name: str
    dimension: int

    def embed(self, texts: Sequence[str]) -> List[Vector]:
        """Embed one or more strings."""
        ...


class HashingEmbeddingBackend:
    """Deterministic 768-dim lexical embedding fallback.

    This is not a replacement for PubMedBERT or Nomic in production. It gives
    CI and local development a stable dense-retrieval path without downloading
    large models.
    """

    def __init__(self, name: str, dimension: int = 768, salt: str = "") -> None:
        self.name = name
        self.dimension = dimension
        self._salt = salt or name

    def embed(self, texts: Sequence[str]) -> List[Vector]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> Vector:
        vector = [0.0] * self.dimension
        tokens = tokenize(text)
        if not tokens:
            return vector

        terms = list(tokens)
        terms.extend(f"{left} {right}" for left, right in zip(tokens, tokens[1:]))
        for term in terms:
            digest = hashlib.sha256(f"{self._salt}:{term}".encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        return vector


class SentenceTransformerBackend:
    """sentence-transformers backend for PubMedBERT and BGE-style encoders."""

    def __init__(self, model_name: str, name: str = "pubmedbert", dimension: int = 768) -> None:
        module: Any = importlib.import_module("sentence_transformers")
        model_class: Any = getattr(module, "SentenceTransformer")
        self._model: Any = model_class(model_name)
        self.model_name = model_name
        self.name = name
        self.dimension = dimension

    def embed(self, texts: Sequence[str]) -> List[Vector]:
        encoded: object = self._model.encode(
            list(texts),
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return _coerce_vectors(encoded)


class OllamaEmbeddingBackend:
    """Ollama embedding backend for `nomic-embed-text`."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        host: Optional[str] = None,
        name: str = "nomic",
        dimension: int = 768,
        timeout_seconds: int = 120,
    ) -> None:
        self.model = model
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.name = name
        self.dimension = dimension
        self.timeout_seconds = timeout_seconds

    def embed(self, texts: Sequence[str]) -> List[Vector]:
        payload: Dict[str, object] = {"model": self.model, "input": list(texts)}
        try:
            response = self._post_json("/api/embed", payload)
            embeddings = response.get("embeddings")
            if embeddings is not None:
                return _coerce_vectors(embeddings)
        except Exception:
            return self._embed_with_legacy_endpoint(texts)

        return self._embed_with_legacy_endpoint(texts)

    def _embed_with_legacy_endpoint(self, texts: Sequence[str]) -> List[Vector]:
        vectors: List[Vector] = []
        for text in texts:
            response = self._post_json("/api/embeddings", {"model": self.model, "prompt": text})
            embedding = response.get("embedding")
            if embedding is None:
                raise RuntimeError("Ollama embedding response did not include an embedding")
            vectors.extend(_coerce_vectors([embedding]))
        return vectors

    def _post_json(self, endpoint: str, payload: Mapping[str, object]) -> Dict[str, object]:
        request = urllib.request.Request(
            f"{self.host}{endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            loaded: object = json.loads(response.read().decode("utf-8"))
        if not isinstance(loaded, dict):
            raise RuntimeError(f"Ollama returned non-object JSON from {endpoint}")
        return cast(Dict[str, object], loaded)


class DenseRetriever:
    """Dense retriever backed by an embedding model and vector store."""

    def __init__(
        self,
        backend: EmbeddingBackend,
        vector_store: Optional[InMemoryVectorStore] = None,
    ) -> None:
        self.backend = backend
        self.vector_store = vector_store or InMemoryVectorStore(backend.name)

    def index(self, documents: Iterable[RetrievalDocument], batch_size: int = 64) -> None:
        pending: List[RetrievalDocument] = []
        for document in documents:
            pending.append(document)
            if len(pending) >= batch_size:
                self._flush(pending)
                pending = []
        if pending:
            self._flush(pending)

    def search(self, query: str, top_k: int = 100) -> List[RankedChunk]:
        query_vectors = self.backend.embed([query])
        if not query_vectors:
            return []
        return self.vector_store.search(query_vectors[0], top_k=top_k)

    def _flush(self, documents: Sequence[RetrievalDocument]) -> None:
        vectors = self.backend.embed([document.text for document in documents])
        self.vector_store.add_many(documents, vectors)


class DualEmbedder:
    """Dual embedding strategy: biomedical + general.

    Primary (biomedical): NeuML/pubmedbert-base-embeddings via
    sentence-transformers. Secondary (general): nomic-embed-text via Ollama.
    At index time both vectors are computed per chunk; at query time both
    retrievers produce independent top-K lists for RRF fusion.
    """

    def __init__(
        self,
        bio_backend: Optional[EmbeddingBackend] = None,
        general_backend: Optional[EmbeddingBackend] = None,
    ) -> None:
        self.bio_embedder = DenseRetriever(
            bio_backend or HashingEmbeddingBackend("pubmedbert", salt="bio")
        )
        self.gen_embedder = DenseRetriever(
            general_backend or HashingEmbeddingBackend("nomic", salt="general")
        )

    @classmethod
    def from_production_models(cls, allow_fallback: bool = True) -> DualEmbedder:
        """Create production backends, optionally falling back when unavailable."""

        try:
            bio_backend: EmbeddingBackend = SentenceTransformerBackend(
                "NeuML/pubmedbert-base-embeddings",
                name="pubmedbert",
            )
        except Exception:
            if not allow_fallback:
                raise
            bio_backend = HashingEmbeddingBackend("pubmedbert", salt="bio")

        try:
            general_backend: EmbeddingBackend = OllamaEmbeddingBackend()
        except Exception:
            if not allow_fallback:
                raise
            general_backend = HashingEmbeddingBackend("nomic", salt="general")

        return cls(bio_backend=bio_backend, general_backend=general_backend)

    def index(self, documents: Iterable[RetrievalDocument]) -> None:
        materialized = list(documents)
        self.bio_embedder.index(materialized)
        self.gen_embedder.index(materialized)

    def search_biomedical(self, query: str, top_k: int = 100) -> List[RankedChunk]:
        return self.bio_embedder.search(query, top_k=top_k)

    def search_general(self, query: str, top_k: int = 100) -> List[RankedChunk]:
        return self.gen_embedder.search(query, top_k=top_k)


def _coerce_vectors(value: object) -> List[Vector]:
    if hasattr(value, "tolist"):
        value = cast(Any, value).tolist()
    if not isinstance(value, list):
        raise TypeError("Embedding backend returned a non-list value")
    if not value:
        return []
    outer = cast(List[object], value)
    if all(isinstance(item, (int, float)) for item in outer):
        return [_to_float_vector(outer)]

    vectors: List[Vector] = []
    for row in outer:
        if hasattr(row, "tolist"):
            row = cast(Any, row).tolist()
        if not isinstance(row, list):
            raise TypeError("Embedding backend returned a non-list vector")
        vectors.append(_to_float_vector(cast(List[object], row)))
    return vectors


def _to_float_vector(items: Sequence[object]) -> Vector:
    return [_coerce_float(item) for item in items]


def _coerce_float(value: object) -> float:
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"Expected numeric embedding value, got {type(value).__name__}")
