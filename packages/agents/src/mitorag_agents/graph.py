"""Main StateGraph definition for Phase 4."""

from __future__ import annotations

import importlib
import json
import sqlite3
from collections.abc import Mapping as ABCMapping
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Sequence, Union, cast

from mitorag_agents.citation_auditor import citation_auditor_node
from mitorag_agents.config import DEFAULT_CHECKPOINT_PATH
from mitorag_agents.disease_therapeutics import disease_therapeutics_node
from mitorag_agents.entity_linker import entity_linker_node
from mitorag_agents.kg_cypher import kg_cypher_node
from mitorag_agents.local_rag import local_rag_node
from mitorag_agents.mitophysiology import mitophysiology_node
from mitorag_agents.planner import planner_node
from mitorag_agents.reranker_agent import reranker_node
from mitorag_agents.router import router_node
from mitorag_agents.state import MitoRAGState, StateUpdate
from mitorag_agents.synthesizer import synthesizer_node
from mitorag_agents.utils import merge_updates
from mitorag_agents.verifier import verifier_node
from mitorag_agents.web_rag import web_rag_node

Node = Callable[[MitoRAGState], StateUpdate]

NODE_ORDER = [
    "router",
    "planner",
    "local_rag",
    "web_rag",
    "kg_cypher",
    "entity_linker",
    "reranker",
    "mitophysiology",
    "disease_therapeutics",
    "verifier",
    "synthesizer",
    "citation_auditor",
]

NODES: Dict[str, Node] = {
    "router": router_node,
    "planner": planner_node,
    "local_rag": local_rag_node,
    "web_rag": web_rag_node,
    "kg_cypher": kg_cypher_node,
    "entity_linker": entity_linker_node,
    "reranker": reranker_node,
    "mitophysiology": mitophysiology_node,
    "disease_therapeutics": disease_therapeutics_node,
    "verifier": verifier_node,
    "synthesizer": synthesizer_node,
    "citation_auditor": citation_auditor_node,
}


class SQLiteCheckpointStore:
    """Small SQLite checkpoint store used by the fallback graph."""

    def __init__(self, path: str = DEFAULT_CHECKPOINT_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, thread_id: str, state: MitoRAGState) -> None:
        payload = json.dumps(state.model_dump(), default=str, sort_keys=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO checkpoints(thread_id, payload)
                VALUES (?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET payload = excluded.payload
                """,
                (thread_id, payload),
            )
            connection.commit()

    def load_payload(self, thread_id: str) -> Optional[Mapping[str, object]]:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload FROM checkpoints WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        loaded: object = json.loads(str(row[0]))
        if isinstance(loaded, ABCMapping):
            return cast(Mapping[str, object], loaded)
        return None

    def _initialize(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints(
                    thread_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.commit()


class SimpleMitoRAGGraph:
    """LangGraph-compatible fallback with deterministic sequential execution."""

    def __init__(
        self,
        checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
        run_all_specialists: bool = True,
    ) -> None:
        self.checkpointer = SQLiteCheckpointStore(checkpoint_path)
        self.run_all_specialists = run_all_specialists

    def invoke(
        self,
        input_state: Union[Mapping[str, object], MitoRAGState],
        config: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, object]:
        state = coerce_state(input_state)
        thread_id = _thread_id(config)
        for node_name in ["router", "planner", "local_rag", "web_rag", "kg_cypher"]:
            state = _run_node(state, NODES[node_name])
        state = _run_node(state, entity_linker_node)
        state = _run_node(state, reranker_node)

        specialist_route = route_to_specialist(state)
        if self.run_all_specialists:
            state = _run_node(state, mitophysiology_node)
            state = _run_node(state, disease_therapeutics_node)
        elif specialist_route == "mitophysiology":
            state = _run_node(state, mitophysiology_node)
        elif specialist_route == "disease":
            state = _run_node(state, disease_therapeutics_node)

        state = _run_node(state, verifier_node)
        state = _run_node(state, synthesizer_node)
        state = _run_node(state, citation_auditor_node)
        retries = 0
        while check_citations(state) == "retry" and retries < 2:
            retries += 1
            state = _run_node(state, synthesizer_node)
            state = _run_node(state, citation_auditor_node)

        self.checkpointer.save(thread_id, state)
        return state.model_dump()


def build_mitorag_graph(
    checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
    prefer_langgraph: bool = True,
) -> object:
    """Build the 12-agent graph with LangGraph when installed, fallback otherwise."""

    if prefer_langgraph:
        graph = _try_build_langgraph(checkpoint_path)
        if graph is not None:
            return graph
    return SimpleMitoRAGGraph(checkpoint_path=checkpoint_path)


def route_to_specialist(state: MitoRAGState) -> str:
    """Route reranked evidence to the right specialist branch."""

    if state.query_type in {"disease", "therapeutics"}:
        return "disease"
    if state.query_type == "mechanistic":
        return "mitophysiology"
    return "direct"


def check_citations(state: MitoRAGState) -> str:
    """Return valid or retry for the citation-auditor conditional edge."""

    if state.citations_valid:
        return "valid"
    if state.invalid_citations and state.citation_retry_count < 2:
        return "retry"
    return "valid"


def coerce_state(input_state: Union[Mapping[str, object], MitoRAGState]) -> MitoRAGState:
    if isinstance(input_state, MitoRAGState):
        return input_state
    return MitoRAGState.model_validate(dict(input_state))


def _run_node(state: MitoRAGState, node: Node) -> MitoRAGState:
    return merge_updates(state, node(state))


def _thread_id(config: Optional[Mapping[str, object]]) -> str:
    if not config:
        return "default"
    configurable = config.get("configurable")
    if isinstance(configurable, ABCMapping):
        config_mapping = cast(Mapping[str, object], configurable)
        thread_id = config_mapping.get("thread_id")
        if isinstance(thread_id, str) and thread_id:
            return thread_id
    return "default"


def _try_build_langgraph(checkpoint_path: str) -> Optional[object]:
    try:
        graph_module = importlib.import_module("langgraph.graph")
    except Exception:
        return None

    state_graph_cls = getattr(graph_module, "StateGraph", None)
    end = getattr(graph_module, "END", "__end__")
    if state_graph_cls is None:
        return None

    graph = state_graph_cls(MitoRAGState)
    for node_name in NODE_ORDER:
        graph.add_node(node_name, _langgraph_node(NODES[node_name]))
    graph.set_entry_point("router")
    graph.add_edge("router", "planner")
    graph.add_edge("planner", "local_rag")
    graph.add_edge("planner", "web_rag")
    graph.add_edge("planner", "kg_cypher")
    graph.add_edge("local_rag", "entity_linker")
    graph.add_edge("web_rag", "entity_linker")
    graph.add_edge("kg_cypher", "entity_linker")
    graph.add_edge("entity_linker", "reranker")
    graph.add_conditional_edges(
        "reranker",
        _route_adapter,
        {
            "mitophysiology": "mitophysiology",
            "disease": "disease_therapeutics",
            "direct": "verifier",
        },
    )
    graph.add_edge("mitophysiology", "verifier")
    graph.add_edge("disease_therapeutics", "verifier")
    graph.add_edge("verifier", "synthesizer")
    graph.add_edge("synthesizer", "citation_auditor")
    graph.add_conditional_edges(
        "citation_auditor",
        _citation_adapter,
        {"valid": end, "retry": "synthesizer"},
    )

    checkpointer = _try_sqlite_saver(checkpoint_path)
    if checkpointer is None:
        return graph.compile()
    return graph.compile(checkpointer=checkpointer)


def _langgraph_node(node: Node) -> Callable[[object], StateUpdate]:
    def invoke(raw_state: object) -> StateUpdate:
        if isinstance(raw_state, MitoRAGState):
            state = raw_state
        elif isinstance(raw_state, ABCMapping):
            state = MitoRAGState.model_validate(dict(cast(Mapping[str, object], raw_state)))
        else:
            state = MitoRAGState.model_validate(raw_state)
        return node(state)

    return invoke


def _route_adapter(raw_state: object) -> str:
    return route_to_specialist(coerce_state_from_object(raw_state))


def _citation_adapter(raw_state: object) -> str:
    return check_citations(coerce_state_from_object(raw_state))


def coerce_state_from_object(raw_state: object) -> MitoRAGState:
    if isinstance(raw_state, MitoRAGState):
        return raw_state
    if isinstance(raw_state, ABCMapping):
        return MitoRAGState.model_validate(dict(cast(Mapping[str, object], raw_state)))
    return MitoRAGState.model_validate(raw_state)


def _try_sqlite_saver(checkpoint_path: str) -> Optional[object]:
    module_names: Sequence[str] = [
        "langgraph.checkpoint.sqlite",
        "langgraph.checkpoint.sqlite.aio",
    ]
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        saver_cls = getattr(module, "SqliteSaver", None)
        if saver_cls is None:
            continue
        from_conn_string = getattr(saver_cls, "from_conn_string", None)
        if callable(from_conn_string):
            return from_conn_string(checkpoint_path)
        try:
            return saver_cls(sqlite3.connect(checkpoint_path))
        except Exception:
            return None
    return None
