# Agents

Phase 4 implements twelve agents with typed state, conditional routing, citation
retry logic, and SQLite checkpointing.

1. Router
2. Planner
3. Local-RAG
4. Web-RAG
5. KG-Cypher
6. Entity-Linker
7. Reranker
8. Verifier/CoVe
9. Synthesizer
10. Citation-Auditor
11. Mitophysiology Specialist L1-6
12. Disease/Therapeutics Specialist L7-10

Prompt placeholders live in `packages/agents/src/mitorag_agents/prompts/` so the
contracts can evolve alongside the graph implementation.

## State

`MitoRAGState` carries query classification, sub-queries, local/web/KG evidence,
linked entities, verified claims, contradictions, synthesized answer, citations,
agent trace, and per-agent latency.

## Graph Flow

The production graph uses LangGraph when `packages/agents[langgraph]` is
installed. Local tests use `SimpleMitoRAGGraph`, a deterministic compatibility
runner with the same `invoke()` shape and SQLite checkpointing.

Flow:

1. Router classifies the query.
2. Planner produces 3-5 sub-queries.
3. Local-RAG, Web-RAG, and KG-Cypher gather evidence.
4. Entity-Linker normalizes mentions to KG IDs.
5. Reranker fuses evidence and prepares the top set.
6. Specialist nodes add mitophysiology and disease/therapeutics context.
7. Verifier extracts claims and surfaces contradictions such as mPTP models.
8. Synthesizer writes cited prose.
9. Citation-Auditor validates PMID/DOI syntax and local cache support.
10. Invalid citations loop back to Synthesizer up to two times.

## Models

The `AGENT_MODEL_MAP` reserves Ollama models for production:

- router/entity linker: `llama3.2:3b-instruct-q4_K_M`
- planner/KG/synthesizer/specialists: `qwen2.5:14b-instruct-q4_K_M`
- verifier: `phi4:14b-q4_K_M`

Offline tests use deterministic heuristic nodes so CI does not require large
model downloads.
