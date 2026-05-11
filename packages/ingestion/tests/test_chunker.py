from __future__ import annotations

from mitorag_ingest.chunker import chunk_paper
from mitorag_ingest.models import PaperMetadata, ParsedPaper, Section


def test_chunk_paper_keeps_abstract_atomic_and_splits_methods() -> None:
    methods_text = ("Mitochondrial isolation protocol sentence. " * 120).strip()
    paper = ParsedPaper(
        title="Chunking Test",
        abstract="This abstract must stay as a single evidence unit.",
        sections=[
            Section(
                heading="Methods",
                level=1,
                text=methods_text,
                page_number=2,
                char_start=100,
                char_end=100 + len(methods_text),
            )
        ],
        raw_text=f"Abstract\nThis abstract must stay as a single evidence unit.\n{methods_text}",
        metadata=PaperMetadata(doi="10.5555/chunk.1", journal="Test Journal", year=2026),
    )

    chunks = chunk_paper(paper, max_chars=800, overlap=100)

    abstract_chunks = [chunk for chunk in chunks if chunk.chunk_type.value == "abstract"]
    method_chunks = [chunk for chunk in chunks if chunk.section_path == "Methods"]
    assert len(abstract_chunks) == 1
    assert abstract_chunks[0].text == paper.abstract
    assert len(method_chunks) > 1
    assert all(chunk.metadata["doi"] == "10.5555/chunk.1" for chunk in method_chunks)


def test_chunk_paper_preserves_section_path_metadata() -> None:
    paper = ParsedPaper(
        title="Section Path Test",
        sections=[
            Section(
                heading="ETC Activity",
                level=2,
                parent_heading="Results",
                text="Complex I activity was reduced in mutant mitochondria.",
                page_number=5,
                char_start=200,
                char_end=253,
            )
        ],
        metadata=PaperMetadata(doi="10.5555/path.1"),
    )

    chunks = chunk_paper(paper)

    assert chunks[0].section_path == "Results > ETC Activity"
    assert chunks[0].metadata["section_path"] == "Results > ETC Activity"

