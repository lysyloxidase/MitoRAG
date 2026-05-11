"""Section-aware scientific chunking strategy."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, List, Tuple

from mitorag_ingest.metadata_extractor import paper_id_from_metadata
from mitorag_ingest.models import Chunk, ChunkType, ParsedPaper, Section


def chunk_paper(paper: ParsedPaper, max_chars: int = 1500, overlap: int = 200) -> List[Chunk]:
    """Chunk a parsed paper while preserving scientific structure."""

    if max_chars < 250:
        raise ValueError("max_chars must be at least 250")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    overlap = min(overlap, max_chars // 2)

    paper_id = paper_id_from_metadata(
        paper.metadata, Path(paper.source_path) if paper.source_path else None
    )
    chunks: List[Chunk] = []

    if paper.abstract.strip():
        chunks.append(
            _build_chunk(
                paper=paper,
                paper_id=paper_id,
                text=paper.abstract.strip(),
                section_path="Abstract",
                chunk_type=ChunkType.ABSTRACT,
                page_number=1,
                char_start=_safe_find(paper.raw_text, paper.abstract),
                char_end=_safe_find(paper.raw_text, paper.abstract) + len(paper.abstract.strip()),
            )
        )

    for section in paper.sections:
        chunks.extend(_chunk_section(paper, paper_id, section, max_chars, overlap))

    for figure in paper.figures:
        chunks.append(
            _build_chunk(
                paper=paper,
                paper_id=paper_id,
                text=figure.caption,
                section_path=figure.label,
                chunk_type=ChunkType.FIGURE,
                page_number=figure.page_number,
                char_start=figure.char_start,
                char_end=figure.char_end,
            )
        )

    for table in paper.tables:
        chunks.append(
            _build_chunk(
                paper=paper,
                paper_id=paper_id,
                text=table.text,
                section_path=table.label,
                chunk_type=ChunkType.TABLE,
                page_number=table.page_number,
                char_start=table.char_start,
                char_end=table.char_end,
            )
        )

    for equation in paper.equations:
        chunks.append(
            _build_chunk(
                paper=paper,
                paper_id=paper_id,
                text=equation.text,
                section_path=equation.label or "Equation",
                chunk_type=ChunkType.EQUATION,
                page_number=equation.page_number,
                char_start=equation.char_start,
                char_end=equation.char_end,
            )
        )

    return chunks


def _chunk_section(
    paper: ParsedPaper,
    paper_id: str,
    section: Section,
    max_chars: int,
    overlap: int,
) -> List[Chunk]:
    chunks: List[Chunk] = []
    for local_start, local_end, text in _split_text(section.text, max_chars, overlap):
        chunks.append(
            _build_chunk(
                paper=paper,
                paper_id=paper_id,
                text=text,
                section_path=section.section_path,
                chunk_type=ChunkType.TEXT,
                page_number=section.page_number,
                char_start=section.char_start + local_start,
                char_end=section.char_start + local_end,
            )
        )
    return chunks


def _split_text(text: str, max_chars: int, overlap: int) -> Iterable[Tuple[int, int, str]]:
    clean_text = text.strip()
    if not clean_text:
        return
    if len(clean_text) <= max_chars:
        yield 0, len(clean_text), clean_text
        return

    start = 0
    text_length = len(clean_text)
    while start < text_length:
        hard_end = min(start + max_chars, text_length)
        end = _best_break(clean_text, start, hard_end)
        piece = clean_text[start:end]
        leading_ws = len(piece) - len(piece.lstrip())
        trailing_ws = len(piece.rstrip())
        actual_start = start + leading_ws
        actual_end = start + trailing_ws
        chunk_text = clean_text[actual_start:actual_end]
        if chunk_text:
            yield actual_start, actual_end, chunk_text
        if end >= text_length:
            break
        start = max(actual_end - overlap, start + 1)


def _best_break(text: str, start: int, hard_end: int) -> int:
    if hard_end >= len(text):
        return len(text)
    window = text[start:hard_end]
    for separator in ["\n\n", "\n", ". ", "; ", ", "]:
        index = window.rfind(separator)
        if index >= max(80, len(window) // 2):
            return start + index + len(separator)
    return hard_end


def _build_chunk(
    paper: ParsedPaper,
    paper_id: str,
    text: str,
    section_path: str,
    chunk_type: ChunkType,
    page_number: int,
    char_start: int,
    char_end: int,
) -> Chunk:
    metadata = paper.metadata.as_chunk_metadata()
    metadata.update(
        {
            "paper_id": paper_id,
            "section_path": section_path,
            "chunk_type": chunk_type.value,
            "source_path": paper.source_path,
        }
    )
    chunk_id = _chunk_id(paper_id, section_path, chunk_type.value, char_start, char_end, text)
    return Chunk(
        id=chunk_id,
        text=text,
        paper_id=paper_id,
        section_path=section_path,
        chunk_type=chunk_type,
        page_number=page_number,
        char_start=char_start,
        char_end=char_end,
        metadata=metadata,
    )


def _chunk_id(
    paper_id: str,
    section_path: str,
    chunk_type: str,
    char_start: int,
    char_end: int,
    text: str,
) -> str:
    digest = hashlib.sha256(
        f"{paper_id}|{section_path}|{chunk_type}|{char_start}|{char_end}|{text}".encode()
    ).hexdigest()[:20]
    return f"chunk:{digest}"


def _safe_find(haystack: str, needle: str) -> int:
    index = haystack.find(needle.strip())
    return max(index, 0)
