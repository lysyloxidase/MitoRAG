"""MitoRAG command-line interface."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, cast

from mitorag_agents.graph import SimpleMitoRAGGraph
from mitorag_agents.local_rag import local_fixture_chunks
from mitorag_agents.web_rag import web_fixture_chunks
from mitorag_ingest.watcher import LocalIngestionPipeline, PaperWatcher
from mitorag_kg import InMemoryKG, load_all_seeds
from mitorag_kg.graph_queries import MATRIX_LOCALIZATION_COUNT


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = str(getattr(args, "command", ""))

    if command == "ask":
        return ask(str(getattr(args, "question")), bool(getattr(args, "deep", False)))
    if command == "ingest":
        return ingest(Path(str(getattr(args, "path"))))
    if command == "ingest-once":
        return ingest(Path(str(getattr(args, "papers_dir"))))
    if command == "kg":
        return kg_command(args)
    if command == "search":
        return search(str(getattr(args, "query")))
    if command == "contradictions":
        return contradictions()

    parser.error(f"Unknown command: {command}")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mitorag")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ask_parser = subcommands.add_parser("ask", help="Ask a cited mitochondrial question")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--deep", action="store_true", help="Enable specialist debate trace")

    ingest_parser = subcommands.add_parser("ingest", help="Ingest a folder of PDFs")
    ingest_parser.add_argument("path")

    legacy_ingest = subcommands.add_parser("ingest-once", help="Parse PDFs in PAPERS_DIR once")
    legacy_ingest.add_argument(
        "--papers-dir",
        default=os.environ.get("PAPERS_DIR", "./data/papers"),
    )

    kg_parser = subcommands.add_parser("kg", help="Knowledge graph commands")
    kg_subcommands = kg_parser.add_subparsers(dest="kg_command", required=True)
    kg_subcommands.add_parser("stats", help="Show KG statistics")
    query_parser = kg_subcommands.add_parser("query", help="Run a Cypher query")
    query_parser.add_argument("cypher")
    level_parser = kg_subcommands.add_parser("level", help="Show a molecular KG level")
    level_parser.add_argument("level", type=int)

    search_parser = subcommands.add_parser("search", help="Search local and web fixtures")
    search_parser.add_argument("query")

    subcommands.add_parser("contradictions", help="List known contradictions")
    return parser


def ask(question: str, deep: bool = False) -> int:
    graph = SimpleMitoRAGGraph()
    state: Dict[str, object] = graph.invoke(
        {"query": question},
        config={"configurable": {"thread_id": "cli"}},
    )
    print(str(state.get("answer", "")))
    if deep:
        print("\nAgent trace:")
        latency_map = _mapping(state.get("latency_ms"))
        for agent in _sequence(state.get("agent_trace")):
            latency = _float(latency_map.get(str(agent)))
            print(f"- {agent}: {latency:.1f} ms")
    return 0


def ingest(path: Path) -> int:
    papers_dir = path.expanduser().resolve()
    watcher = PaperWatcher(
        papers_dir=papers_dir,
        pipeline=LocalIngestionPipeline(),
        settle_seconds=0,
        ingest_existing=True,
    )
    results = watcher.poll_once()
    if not results:
        print(f"No PDFs found in {papers_dir}")
        return 0
    for result in results:
        print(f"{result.paper_id}\t{result.chunk_count}\t{result.title}")
    return 0


def kg_command(args: argparse.Namespace) -> int:
    command = str(getattr(args, "kg_command", ""))
    graph = InMemoryKG()
    load_all_seeds(graph)

    if command == "stats":
        nodes = len(graph.nodes)
        edges = len(graph.relationships)
        print(f"nodes={nodes} edges={edges} papers={graph.count_nodes('Paper')}")
        return 0
    if command == "query":
        cypher = str(getattr(args, "cypher"))
        if "RETURN count(p)" in cypher:
            print(graph.run_scalar(MATRIX_LOCALIZATION_COUNT))
        else:
            print("Query accepted. Connect Neo4j for live row streaming.")
        return 0
    if command == "level":
        print(level_summary(int(getattr(args, "level"))))
        return 0
    raise ValueError(f"Unknown kg command: {command}")


def search(query: str) -> int:
    results = [*local_fixture_chunks(query), *web_fixture_chunks(query)]
    for result in results[:8]:
        citation = result.metadata.get("citation", "")
        print(f"{result.score:.2f}\t{citation}\t{result.text}")
    return 0


def contradictions() -> int:
    rows = [
        "mPTP composition: F-ATP synthase model vs ANT/non-ATP-synthase evidence",
        "Warburg effect: mitochondrial defect primary cause vs reverse Warburg support",
        "mtDNA-cGAS-STING: sterile inflammation driver vs bystander",
    ]
    for row in rows:
        print(row)
    return 0


def level_summary(level: int) -> str:
    summaries = {
        1: "Whole mitochondrion: OMM, IMM, IMS, matrix, localization edges",
        2: "OXPHOS: Complex I-V, CoQ10, cytochrome c, electron flow",
        3: "TCA cycle: citrate synthase through malate dehydrogenase",
        4: "Fatty acid beta-oxidation: CPT1/CPT2 to acetyl-CoA",
        5: "Dynamics: fusion, fission, mitophagy, biogenesis",
        6: "Import: TOM, TIM23, TIM22, SAM, MIA40/Erv1, MCU",
        7: "Apoptosis: BCL-2 family, MOMP, cytochrome c, mPTP hypotheses",
        8: "Diseases: MELAS, LHON, Leigh, MERRF, NARP variants",
        9: "Signaling: UPRmt, ROS, mitokines, ISR",
        10: "Therapeutics: Idebenone, CoQ10, MitoQ, Elamipretide, Urolithin A",
    }
    return summaries.get(level, "Unknown level. Choose 1-10.")


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, list):
        return cast(Sequence[object], value)
    return []


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _float(value: object) -> float:
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


if __name__ == "__main__":
    raise SystemExit(main())
