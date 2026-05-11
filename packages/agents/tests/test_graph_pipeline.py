from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from mitorag_agents.graph import (
    NODE_ORDER,
    SimpleMitoRAGGraph,
    SQLiteCheckpointStore,
    _citation_adapter,
    _langgraph_node,
    _route_adapter,
    _thread_id,
    _try_sqlite_saver,
    build_mitorag_graph,
    check_citations,
    coerce_state,
    coerce_state_from_object,
    route_to_specialist,
)
from mitorag_agents.state import MitoRAGState


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


def test_checkpoint_store_loads_saved_payload(tmp_path: Path) -> None:
    store = SQLiteCheckpointStore(str(tmp_path / "checkpoints.db"))
    store.save("thread-a", MitoRAGState(query="Complex I"))

    payload = store.load_payload("thread-a")
    missing = store.load_payload("missing")

    assert payload is not None
    assert payload["query"] == "Complex I"
    assert missing is None


def test_graph_routing_helpers_cover_specialist_and_retry_paths() -> None:
    disease = MitoRAGState(query="MELAS", query_type="disease")
    therapy = MitoRAGState(query="Idebenone", query_type="therapeutics")
    mechanism = MitoRAGState(query="PINK1", query_type="mechanistic")
    factual = MitoRAGState(query="Complex I", query_type="factual")

    assert route_to_specialist(disease) == "disease"
    assert route_to_specialist(therapy) == "disease"
    assert route_to_specialist(mechanism) == "mitophysiology"
    assert route_to_specialist(factual) == "direct"

    assert check_citations(MitoRAGState(query="ok", citations_valid=True)) == "valid"
    assert (
        check_citations(
            MitoRAGState(query="bad", invalid_citations=["[PMID:99999999]"], citation_retry_count=0)
        )
        == "retry"
    )
    assert (
        check_citations(
            MitoRAGState(query="bad", invalid_citations=["[PMID:99999999]"], citation_retry_count=2)
        )
        == "valid"
    )


def test_state_coercion_and_langgraph_adapters() -> None:
    state = MitoRAGState(query="Complex I", query_type="mechanistic")
    mapped = {"query": "MELAS", "query_type": "disease"}

    assert coerce_state(state) is state
    assert coerce_state(mapped).query == "MELAS"
    assert coerce_state_from_object(state) is state
    assert coerce_state_from_object(mapped).query_type == "disease"
    assert _route_adapter(mapped) == "disease"
    assert _citation_adapter({"query": "ok", "citations_valid": True}) == "valid"

    wrapped = _langgraph_node(lambda current: {"answer": current.query})
    assert wrapped(state) == {"answer": "Complex I"}
    assert wrapped(mapped) == {"answer": "MELAS"}


def test_thread_id_and_langgraph_fallback_helpers(tmp_path: Path) -> None:
    assert _thread_id(None) == "default"
    assert _thread_id({}) == "default"
    assert _thread_id({"configurable": {"thread_id": "abc"}}) == "abc"
    assert _thread_id({"configurable": {"thread_id": ""}}) == "default"
    assert _thread_id({"configurable": {"thread_id": 3}}) == "default"

    graph = build_mitorag_graph(str(tmp_path / "fallback.db"), prefer_langgraph=True)
    assert hasattr(graph, "invoke")
    assert _try_sqlite_saver(str(tmp_path / "missing.db")) is None


def test_fallback_graph_can_route_single_specialist_branch(tmp_path: Path) -> None:
    graph = SimpleMitoRAGGraph(
        checkpoint_path=str(tmp_path / "single-specialist.db"),
        run_all_specialists=False,
    )

    state = graph.invoke({"query": "How does PINK1/Parkin mitophagy work?"})

    assert "mitophysiology" in state["agent_trace"]
    assert "disease_therapeutics" not in state["agent_trace"]
