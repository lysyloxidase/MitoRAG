from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from mitorag_ingest.pdf_parser import parse_pdf


def test_parse_pdf_extracts_scientific_sections(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mitochondrial-paper.pdf"
    _write_sample_pdf(pdf_path)

    paper = parse_pdf(pdf_path)

    headings = {section.heading for section in paper.sections}
    assert paper.title == "Mitochondrial ETC Activity in Patient-Derived Fibroblasts"
    assert paper.metadata.doi == "10.1234/mito.2026.001"
    assert "mitochondria regulate oxidative phosphorylation" in paper.abstract.lower()
    expected_headings = {"Introduction", "Methods", "Mitochondrial Isolation", "Results"}
    assert expected_headings <= headings
    assert "ETC Activity" in headings
    assert any(section.section_path == "Results > ETC Activity" for section in paper.sections)
    assert paper.references


def _write_sample_pdf(path: Path) -> None:
    lines = [
        "Mitochondrial ETC Activity in Patient-Derived Fibroblasts",
        "Ada Lovelace, Grace Hopper",
        "Journal: Journal of Mitochondrial Systems",
        "DOI: 10.1234/mito.2026.001",
        "Abstract",
        "Mitochondria regulate oxidative phosphorylation in cells with inherited disease.",
        "Introduction",
        "Mitochondrial respiration depends on coordinated nuclear and mtDNA expression.",
        "Methods",
        "Mitochondrial Isolation",
        "Cells were homogenized and mitochondria were enriched by differential centrifugation.",
        "Results",
        "ETC Activity",
        "Complex I activity decreased while citrate synthase normalization preserved ratios.",
        "Discussion",
        "These data support respiratory chain remodeling in disease fibroblasts.",
        "References",
        "1. Example A. Mitochondrial biology. 2024.",
    ]
    pdf = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    del width
    y = height - 72
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 16
    pdf.save()
