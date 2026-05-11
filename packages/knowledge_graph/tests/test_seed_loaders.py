from __future__ import annotations

import pytest

from mitorag_kg import InMemoryKG, load_all_seeds
from mitorag_kg.graph_queries import MATRIX_LOCALIZATION_COUNT
from mitorag_kg.seeds.mitomap import CANONICAL_VARIANTS


@pytest.fixture()
def seeded_graph() -> InMemoryKG:
    graph = InMemoryKG()
    load_all_seeds(graph)
    return graph


def test_mitocarta_loads_1136_gene_nodes(seeded_graph: InMemoryKG) -> None:
    assert seeded_graph.count_nodes("Gene") == 1136
    assert seeded_graph.count_nodes("Protein") == 1136
    assert seeded_graph.count_nodes("Pathway") >= 149


def test_reactome_merge_adds_ids_to_at_least_500_mitocarta_proteins(
    seeded_graph: InMemoryKG,
) -> None:
    merged = seeded_graph.count_nodes_with_properties("Protein", ["mitocarta_id", "reactome_id"])
    assert merged >= 500


def test_mitomap_canonical_variants_and_heteroplasmy_thresholds(
    seeded_graph: InMemoryKG,
) -> None:
    assert seeded_graph.count_nodes("Variant") == 5
    expected = {str(row["hgvs"]): row["heteroplasmy_threshold"] for row in CANONICAL_VARIANTS}
    for hgvs, threshold in expected.items():
        node = seeded_graph.get_node("Variant", "hgvs", hgvs)
        assert node is not None
        assert node.properties["heteroplasmy_threshold"] == threshold


def test_kg_traversal_from_m3243_to_complex_i_oxphos(seeded_graph: InMemoryKG) -> None:
    assert seeded_graph.has_mitomap_path(
        "m.3243A>G",
        "MT-TL1",
        "Complex I",
        "Oxidative phosphorylation",
    )


def test_drug_nodes_have_target_edges(seeded_graph: InMemoryKG) -> None:
    assert seeded_graph.count_nodes("Drug") == 10
    assert seeded_graph.count_relationships("INHIBITS") >= 10


def test_mptp_controversy_has_contradicting_hypotheses(seeded_graph: InMemoryKG) -> None:
    assert seeded_graph.count_nodes("Hypothesis") >= 2
    assert seeded_graph.count_relationships("CONTRADICTS") >= 2


def test_matrix_localization_cypher_query_returns_expected_count(
    seeded_graph: InMemoryKG,
) -> None:
    assert seeded_graph.run_scalar(MATRIX_LOCALIZATION_COUNT) == 525

