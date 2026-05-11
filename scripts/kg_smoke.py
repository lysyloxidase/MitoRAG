"""Smoke-test the Phase 3 KG seed loaders with the in-memory graph."""

from __future__ import annotations

from mitorag_kg import InMemoryKG, load_all_seeds
from mitorag_kg.graph_queries import MATRIX_LOCALIZATION_COUNT


def main() -> int:
    graph = InMemoryKG()
    results = load_all_seeds(graph)
    print("loaders=" + ",".join(result.loader for result in results))
    print(f"genes={graph.count_nodes('Gene')}")
    print(f"proteins={graph.count_nodes('Protein')}")
    print(f"matrix_localized={graph.run_scalar(MATRIX_LOCALIZATION_COUNT)}")
    print(
        "m3243_path="
        + str(
            graph.has_mitomap_path(
                "m.3243A>G",
                "MT-TL1",
                "Complex I",
                "Oxidative phosphorylation",
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
