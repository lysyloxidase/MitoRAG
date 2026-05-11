from __future__ import annotations

from mitorag_ingest.metadata_extractor import extract_metadata


def test_extract_metadata_finds_doi_authors_journal_year_and_terms() -> None:
    metadata = extract_metadata(
        "\n".join(
            [
                "Mitochondrial Proteostasis in Disease",
                "Jane Doe, John Smith",
                "Journal: Cell Metabolism",
                "DOI: 10.1016/j.cmet.2025.01.001",
                "Keywords: mitochondria; proteostasis; mitophagy",
                "MeSH Terms: Mitochondria; Oxidative Phosphorylation",
            ]
        )
    )

    assert metadata.title == "Mitochondrial Proteostasis in Disease"
    assert metadata.authors == ["Jane Doe", "John Smith"]
    assert metadata.journal == "Cell Metabolism"
    assert metadata.year == 2025
    assert metadata.doi == "10.1016/j.cmet.2025.01.001"
    assert "mitophagy" in metadata.keywords
    assert "Mitochondria" in metadata.mesh_terms

