# MitoRAG

MitoRAG is a local-first mitochondrial research assistant scaffold. Phase 1
established PDF ingestion, Phase 2 added hybrid retrieval, Phase 3 added a
Neo4j mitochondrial knowledge graph, Phase 4 added the 12-agent orchestration
layer, Phase 5 added scientific web search clients, and Phase 6 adds automatic
paper-derived KG construction.

## Quickstart

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e "packages/ingestion[dev]" -e "packages/retrieval[dev]" -e "packages/knowledge_graph[dev]" -e "packages/internet[dev]" -e "packages/agents[dev]" -e "apps/api[dev]" -e "apps/cli[dev]"
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

Run a local retrieval latency smoke test:

```bash
python scripts/retrieval_smoke.py
```

Smoke-test the Phase 3 seed graph in memory:

```bash
python - <<'PY'
from mitorag_kg import InMemoryKG, load_all_seeds
from mitorag_kg.graph_queries import MATRIX_LOCALIZATION_COUNT

graph = InMemoryKG()
load_all_seeds(graph)
print(graph.count_nodes("Gene"), graph.run_scalar(MATRIX_LOCALIZATION_COUNT))
PY
```

Smoke-test the Phase 4 agent graph:

```bash
python scripts/agents_smoke.py "How many subunits does Complex I have?"
```

Smoke-test Phase 5 scientific web search:

```bash
python scripts/web_search_smoke.py "Complex I cryo-EM"
MITORAG_ENABLE_LIVE_WEB=1 python scripts/agents_smoke.py "Find recent papers on PINK1 mitophagy"
```

Smoke-test Phase 6 auto-KG construction:

```bash
python scripts/auto_kg_smoke.py
```

Production retrieval models are optional because they are large. Install and
load them explicitly when you want the real PubMedBERT/BGE path:

```bash
python -m pip install -e "packages/retrieval[models]"
MITORAG_LOAD_RERANKER_MODEL=1 python scripts/retrieval_smoke.py --load-reranker
ollama pull nomic-embed-text
```

Production agent orchestration uses optional LangGraph/LangChain Ollama
dependencies:

```bash
python -m pip install -e "packages/agents[langgraph]"
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
