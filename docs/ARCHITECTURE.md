# Architecture

MitoRAG is organized as a monorepo with independently installable Python
packages and app entrypoints.

## Runtime Services

- Ollama serves local LLMs and the Nomic embedding model.
- Neo4j stores curated and paper-derived mitochondrial knowledge graph facts.
- Redis is reserved for rate limiting, task status, and cache coordination.
- FastAPI exposes ingestion, query, KG, and health endpoints.

## Package Boundaries

- `packages/ingestion`: Phase 1 PDF parsing, metadata extraction, chunking, and
  filesystem watching.
- `packages/retrieval`: Phase 2 hybrid retrieval package boundary.
- `packages/knowledge_graph`: Phase 3 Neo4j schema, ontology seeds, and graph
  query helpers.
- `packages/agents`: Phase 4 LangGraph 12-agent orchestration boundary.
- `packages/internet`: Phase 5 scientific web API clients and rate limiting.
- `packages/ui`: Phase 7 frontend boundary.

The ingestion package is deliberately useful by itself: it returns structured
paper and chunk models that later phases can embed, index, and link into Neo4j.

