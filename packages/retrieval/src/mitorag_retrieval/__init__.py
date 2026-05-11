"""Hybrid retrieval package for MitoRAG Phase 2."""

from mitorag_retrieval.bm25_index import BM25Index
from mitorag_retrieval.citation_traversal import CitationPaper, CitationTraverser
from mitorag_retrieval.embedder import (
    DenseRetriever,
    DualEmbedder,
    HashingEmbeddingBackend,
    OllamaEmbeddingBackend,
    SentenceTransformerBackend,
)
from mitorag_retrieval.hybrid import HybridRetriever, reciprocal_rank_fusion
from mitorag_retrieval.models import RankedChunk, RetrievalDocument
from mitorag_retrieval.reranker import BGEReranker

__all__ = [
    "BGEReranker",
    "BM25Index",
    "CitationPaper",
    "CitationTraverser",
    "DenseRetriever",
    "DualEmbedder",
    "HashingEmbeddingBackend",
    "HybridRetriever",
    "OllamaEmbeddingBackend",
    "RankedChunk",
    "RetrievalDocument",
    "SentenceTransformerBackend",
    "__version__",
    "reciprocal_rank_fusion",
]

__version__ = "1.0.0"
