"""Twelve-agent orchestration package for MitoRAG Phase 4."""

from mitorag_agents.config import AGENT_MODEL_MAP
from mitorag_agents.graph import SimpleMitoRAGGraph, build_mitorag_graph
from mitorag_agents.state import (
    Citation,
    Claim,
    Contradiction,
    Entity,
    Evidence,
    KGSubgraph,
    MitoRAGState,
)

__all__ = [
    "AGENT_MODEL_MAP",
    "Citation",
    "Claim",
    "Contradiction",
    "Entity",
    "Evidence",
    "KGSubgraph",
    "MitoRAGState",
    "SimpleMitoRAGGraph",
    "__version__",
    "build_mitorag_graph",
]

__version__ = "1.0.0"
