from __future__ import annotations

from mitorag_kg.auto_construct import AutoKGConstructor, ExtractedTriple, triple_precision
from mitorag_kg.testing import InMemoryKG


def test_ner_extracts_mitochondrial_entities_from_abstract() -> None:
    constructor = AutoKGConstructor(InMemoryKG())
    abstract = "The m.3243A>G variant causes MELAS with Complex I deficiency."

    mentions = constructor.extract_entities(abstract)
    texts = {mention.text for mention in mentions}

    assert {"m.3243A>G", "MELAS", "Complex I"} <= texts


def test_entity_linking_maps_complex_i_to_complex_node() -> None:
    constructor = AutoKGConstructor(InMemoryKG())

    entity = constructor.normalize_entity("Complex I")

    assert entity is not None
    assert entity.label == "Complex"
    assert entity.key == "name"
    assert entity.key_value == "Complex I"


def test_relation_extraction_finds_nd4_subunit_triple() -> None:
    constructor = AutoKGConstructor(InMemoryKG())

    triples = constructor.extract_triples(
        "ND4 is a subunit of Complex I.",
        paper_doi="10.1234/nd4",
    )

    assert len(triples) == 1
    assert triples[0].subject_id == "MT-ND4"
    assert triples[0].predicate == "subunit_of"
    assert triples[0].object_id == "Complex I"


def test_triple_validation_rejects_non_biolink_predicate() -> None:
    constructor = AutoKGConstructor(InMemoryKG())
    triple = ExtractedTriple(
        subject_id="MT-ND4",
        subject_type="Gene",
        predicate="dances_with",
        object_id="Complex I",
        object_type="Complex",
        evidence_span="ND4 dances with Complex I.",
        confidence=0.95,
        paper_doi="10.1234/nope",
    )

    validation = constructor.validate_triple(triple)

    assert not validation.valid
    assert "predicate" in validation.reason


def test_neo4j_merge_adds_triple_with_provenance_metadata() -> None:
    graph = InMemoryKG()
    constructor = AutoKGConstructor(graph)
    triple = ExtractedTriple(
        subject_id="MT-ND4",
        subject_type="Gene",
        predicate="subunit_of",
        object_id="Complex I",
        object_type="Complex",
        evidence_span="ND4 is a subunit of Complex I.",
        confidence=0.91,
        paper_doi="10.1234/nd4",
    )

    result = constructor.merge_triple(triple)
    rel = graph.find_relationship(
        "Gene",
        "hgnc_symbol",
        "MT-ND4",
        "SUBUNIT_OF",
        "Complex",
        "name",
        "Complex I",
    )

    assert result.status == "merged"
    assert rel is not None
    assert rel.properties["paper_doi"] == "10.1234/nd4"
    assert rel.properties["evidence"] == "ND4 is a subunit of Complex I."
    assert rel.properties["confidence"] == 0.91
    assert rel.properties["evidence_count"] == 1


def test_contradiction_creates_contradiction_and_hypothesis_nodes() -> None:
    graph = InMemoryKG()
    constructor = AutoKGConstructor(graph)
    activates = ExtractedTriple(
        subject_id="PINK1",
        subject_type="Gene",
        predicate="activates",
        object_id="PRKN",
        object_type="Gene",
        evidence_span="PINK1 activates Parkin.",
        confidence=0.90,
        paper_doi="10.1234/activates",
    )
    inhibits = activates.model_copy(
        update={
            "predicate": "inhibits",
            "evidence_span": "PINK1 inhibits Parkin.",
            "paper_doi": "10.1234/inhibits",
        }
    )

    assert constructor.merge_triple(activates).status == "merged"
    result = constructor.merge_triple(inhibits)

    assert result.status == "contradiction"
    assert graph.count_nodes("Contradiction") == 1
    assert graph.count_relationships("CONTRADICTS") == 2


def test_same_triple_from_three_papers_increments_evidence_count() -> None:
    graph = InMemoryKG()
    constructor = AutoKGConstructor(graph)
    base = ExtractedTriple(
        subject_id="MT-ND4",
        subject_type="Gene",
        predicate="subunit_of",
        object_id="Complex I",
        object_type="Complex",
        evidence_span="ND4 is a subunit of Complex I.",
        confidence=0.91,
        paper_doi="10.1234/one",
    )

    for doi in ["10.1234/one", "10.1234/two", "10.1234/three"]:
        constructor.merge_triple(base.model_copy(update={"paper_doi": doi}))

    rel = graph.find_relationship(
        "Gene",
        "hgnc_symbol",
        "MT-ND4",
        "SUBUNIT_OF",
        "Complex",
        "name",
        "Complex I",
    )

    assert rel is not None
    assert rel.properties["evidence_count"] == 3
    assert rel.properties["evidence_papers"] == [
        "10.1234/one",
        "10.1234/two",
        "10.1234/three",
    ]


def test_construct_from_text_runs_end_to_end_and_precision_helper() -> None:
    graph = InMemoryKG()
    constructor = AutoKGConstructor(graph)
    result = constructor.construct_from_text(
        "ND4 is a subunit of Complex I. The m.3243A>G variant causes MELAS.",
        paper_doi="10.1234/paper",
    )

    assert result.triples_merged == 2
    assert result.triples_rejected == 0
    assert triple_precision(result.triples, result.triples) >= 0.70
