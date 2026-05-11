# Retrieval

Phase 2 implements hybrid retrieval:

1. BM25 sparse search over preserved biomedical tokens such as `MT-ND4`.
2. PubMedBERT dense search via `NeuML/pubmedbert-base-embeddings`.
3. General dense search via Ollama `nomic-embed-text`.
4. Reciprocal Rank Fusion with `k=60`, or `k=10` for corpora under 1000 chunks.
5. BGE cross-encoder reranking with `BAAI/bge-reranker-v2-m3`.

The production embedding and reranking models are optional at import time. Local
tests use deterministic 768-dim hashing embeddings and a lexical cross-encoder
fallback so CI stays fast and offline. Install `packages/retrieval[models]` and
set `MITORAG_LOAD_RERANKER_MODEL=1` to load the real BGE reranker.

## Pipeline

`HybridRetriever.retrieve(query, top_k=15)` runs:

- BM25 top-100
- PubMedBERT top-100
- Nomic top-100
- RRF candidate fusion
- top-50 candidate handoff
- cross-encoder reranking to top-15

Phase 1 chunks already carry `paper_id`, `section_path`, `chunk_type`, page, and
character offsets, and retrieval wraps them as `RetrievalDocument` values.
