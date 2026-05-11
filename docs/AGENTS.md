# Agents

Phase 4 will wire twelve agents into a LangGraph `StateGraph`.

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

