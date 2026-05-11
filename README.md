# MitoRAG

MitoRAG is a local-first mitochondrial research assistant scaffold. Phase 1
establishes the monorepo, Ollama/Neo4j/Redis compose stack, and a scientific PDF
ingestion package that parses papers, extracts metadata, chunks sections, and
watches a local paper folder.

## Quickstart

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e "packages/ingestion[dev]" -e "apps/api[dev]" -e "apps/cli[dev]"
ruff check .
pyright
pytest
```

Start infrastructure:

```bash
docker compose up --build
```

Pull and smoke-test the configured reasoning model when you are ready for the
multi-GB download:

```bash
python scripts/ollama_smoke.py
```

Drop PDFs into `data/papers/` to ingest them through the watcher or POST them to
`/ingest/upload` once the API is running.

## Phase Map

- Phase 1: monorepo, Ollama model setup, PDF parsing/chunking/watcher
- Phase 2: hybrid retrieval with PubMedBERT, Nomic, BM25, RRF, and reranking
- Phase 3: Neo4j mitochondrial knowledge graph and ontology seeds
- Phase 4: 12-agent LangGraph orchestration
- Phase 5: scientific web search integrations
- Phase 6: automatic KG construction from papers
- Phase 7: web frontend

