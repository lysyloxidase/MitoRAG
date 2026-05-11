"""Model routing and runtime configuration for Phase 4 agents."""

from __future__ import annotations

AGENT_MODEL_MAP = {
    "router": "llama3.2:3b-instruct-q4_K_M",
    "planner": "qwen2.5:14b-instruct-q4_K_M",
    "kg_cypher": "qwen2.5:14b-instruct-q4_K_M",
    "entity_linker": "llama3.2:3b-instruct-q4_K_M",
    "verifier": "phi4:14b-q4_K_M",
    "synthesizer": "qwen2.5:14b-instruct-q4_K_M",
    "mitophysiology": "qwen2.5:14b-instruct-q4_K_M",
    "disease_therapeutics": "qwen2.5:14b-instruct-q4_K_M",
    "local_rag": None,
    "web_rag": None,
    "reranker": None,
    "citation_auditor": None,
}

DEFAULT_CHECKPOINT_PATH = "./data/checkpoints.db"

__all__ = ["AGENT_MODEL_MAP", "DEFAULT_CHECKPOINT_PATH"]
