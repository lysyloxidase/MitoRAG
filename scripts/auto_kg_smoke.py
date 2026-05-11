"""Offline smoke test for Phase 6 auto-KG construction."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in [
    ROOT / "packages" / "knowledge_graph" / "src",
]:
    sys.path.insert(0, str(path))

from mitorag_kg import AutoKGConstructor, InMemoryKG  # noqa: E402


def main() -> None:
    graph = InMemoryKG()
    constructor = AutoKGConstructor(graph)
    result = constructor.construct_from_text(
        "ND4 is a subunit of Complex I. The m.3243A>G variant causes MELAS.",
        paper_doi="10.1234/auto-kg-smoke",
        title="Auto-KG smoke paper",
    )
    print(
        "Auto-KG:",
        f"+{result.triples_merged} triples,",
        f"+{result.new_entities} new entities,",
        f"{result.contradictions_detected} contradictions",
    )


if __name__ == "__main__":
    main()
