# Research Report

Phase 1 implements the local ingestion observations used by the later RAG stack:

- Keep abstracts as atomic chunks.
- Preserve section hierarchy in chunk metadata.
- Store figures and tables as separate evidence units.
- Do not embed references as answer evidence; parse them later for citation graph
  expansion.
- Prefer local-first models and services so private paper folders remain local.

