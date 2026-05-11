"""Smoke-test the Phase 4 MitoRAG agent graph."""

from __future__ import annotations

import argparse

from mitorag_agents import build_mitorag_graph


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="How many subunits does Complex I have?")
    parser.add_argument("--checkpoint", default="./data/checkpoints.db")
    args = parser.parse_args()

    graph = build_mitorag_graph(checkpoint_path=args.checkpoint)
    state = graph.invoke(
        {"query": args.query},
        config={"configurable": {"thread_id": "agents-smoke"}},
    )
    print(f"query_type={state['query_type']}")
    print(f"citations_valid={state['citations_valid']}")
    print(f"confidence={state['confidence']}")
    print("trace=" + " > ".join(state["agent_trace"]))
    print(state["answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
