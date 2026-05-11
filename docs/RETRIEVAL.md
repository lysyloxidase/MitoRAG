# Retrieval

Phase 2 will add hybrid retrieval:

- PubMedBERT biomedical dense embeddings
- `nomic-embed-text` local Ollama embeddings
- BM25 sparse retrieval
- Reciprocal Rank Fusion
- BGE cross-encoder reranking
- citation/reference traversal

Phase 1 chunks already carry `paper_id`, `section_path`, `chunk_type`, page, and
character offsets so retrieval can preserve scientific context.

