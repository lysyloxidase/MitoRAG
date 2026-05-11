from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from mitorag_agents.graph import NODE_ORDER, SimpleMitoRAGGraph, build_mitorag_graph


def test_full_pipeline_returns_answer_under_120s_and_logs_all_agents(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "checkpoints.db"
    graph = build_mitorag_graph(
        checkpoint_path=str(checkpoint_path),
        prefer_langgraph=False,
    )

    start = time.perf_counter()
    state = graph.invoke(
        {"query": "How many subunits does Complex I have?"},
        config={"configurable": {"thread_id": "full-pipeline"}},
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 120
    assert state["answer"]
    assert state["citations_valid"] is True
    assert state["agent_trace"] == NODE_ORDER
    assert set(state["latency_ms"]) == set(NODE_ORDER)


def test_fallback_graph_writes_sqlite_checkpoint(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "checkpoints.db"
    graph = SimpleMitoRAGGraph(checkpoint_path=str(checkpoint_path))

    graph.invoke(
        {"query": "What causes MELAS?"},
        config={"configurable": {"thread_id": "melas-thread"}},
    )

    with sqlite3.connect(checkpoint_path) as connection:
        row = connection.execute(
            "SELECT payload FROM checkpoints WHERE thread_id = ?",
            ("melas-thread",),
        ).fetchone()

    assert row is not None
    assert "MELAS" in str(row[0])

