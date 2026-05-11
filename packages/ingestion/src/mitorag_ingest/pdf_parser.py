"""Scientific PDF parser using marker-pdf with pdfplumber fallback.

marker-pdf:
  - Handles scientific layouts (2-column, equations, figures)
  - Outputs structured markdown with heading hierarchy

Fallback: pdfplumber for born-digital PDFs (fast and deterministic for tests).
"""

from __future__ import annotations

import importlib
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, cast

from mitorag_ingest.metadata_extractor import extract_metadata
from mitorag_ingest.models import FigureCaption, PaperMetadata, ParsedPaper, Section, TableData


class PdfParserError(RuntimeError):
    """Raised when a PDF cannot be parsed by any configured backend."""


class MarkerUnavailable(RuntimeError):
    """Raised internally when marker-pdf is not importable."""


@dataclass(frozen=True)
class _Heading:
    heading: str
    level: int
    start: int
    body_start: int
    page_number: int
    parent_heading: Optional[str]
    parent_headings: List[str]


_MAIN_HEADINGS = {
    "abstract",
    "summary",
    "introduction",
    "background",
    "materials and methods",
    "methods",
    "method",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "acknowledgements",
    "acknowledgments",
    "references",
    "bibliography",
}

_REFERENCE_HEADINGS = {"references", "bibliography"}
_ABSTRACT_HEADINGS = {"abstract", "summary"}


def parse_pdf(path: Path) -> ParsedPaper:
    """Parse a scientific PDF to a structured representation."""

    pdf_path = path.expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got {pdf_path}")

    marker_error: Optional[Exception] = None
    try:
        return _parse_with_marker(pdf_path)
    except (MarkerUnavailable, ImportError, AttributeError, TypeError, RuntimeError) as exc:
        marker_error = exc

    try:
        return _parse_with_pdfplumber(pdf_path)
    except Exception as exc:  # pragma: no cover - defensive context for real PDFs
        raise PdfParserError(
            f"Failed to parse {pdf_path} with marker-pdf and pdfplumber. "
            f"Marker error: {marker_error!r}; pdfplumber error: {exc!r}"
        ) from exc


def _parse_with_marker(path: Path) -> ParsedPaper:
    converter_module_spec = importlib.util.find_spec("marker.converters.pdf")
    models_module_spec = importlib.util.find_spec("marker.models")
    if converter_module_spec is None or models_module_spec is None:
        raise MarkerUnavailable("marker-pdf is not installed")

    converter_module = importlib.import_module("marker.converters.pdf")
    models_module = importlib.import_module("marker.models")
    converter_cls = getattr(converter_module, "PdfConverter", None)
    create_model_dict = getattr(models_module, "create_model_dict", None)
    if converter_cls is None or create_model_dict is None:
        raise MarkerUnavailable("marker-pdf API is not compatible")

    artifact_dict = create_model_dict()
    converter = converter_cls(artifact_dict=artifact_dict)
    rendered = converter(str(path))
    markdown = getattr(rendered, "markdown", None)
    if not isinstance(markdown, str) or not markdown.strip():
        markdown = str(rendered)
    if not markdown.strip():
        raise RuntimeError("marker-pdf returned empty output")
    return _paper_from_markdown(markdown, path)


def _parse_with_pdfplumber(path: Path) -> ParsedPaper:
    pdfplumber = importlib.import_module("pdfplumber")
    page_texts: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        pages = cast(Sequence[Any], getattr(pdf, "pages", []))
        for page in pages:
            raw_text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            page_texts.append(_normalize_text(raw_text))

    raw_text, page_spans = _join_pages(page_texts)
    metadata = extract_metadata(raw_text, path)
    parsed = _paper_from_text(raw_text, metadata, path, page_spans)
    return parsed.model_copy(update={"page_count": len(page_texts)})


def _paper_from_markdown(markdown: str, source_path: Path) -> ParsedPaper:
    lines: List[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        lines.append(line)
    raw_text = "\n".join(lines)
    page_spans = [(0, len(raw_text), 1)]
    metadata = extract_metadata(raw_text, source_path)
    return _paper_from_text(raw_text, metadata, source_path, page_spans)


def _paper_from_text(
    raw_text: str,
    metadata: PaperMetadata,
    source_path: Path,
    page_spans: Sequence[Tuple[int, int, int]],
) -> ParsedPaper:
    headings = _detect_headings(raw_text, page_spans)
    sections: List[Section] = []
    abstract = ""
    references: List[str] = []

    for index, heading in enumerate(headings):
        body_end = headings[index + 1].start if index + 1 < len(headings) else len(raw_text)
        body = raw_text[heading.body_start : body_end].strip()
        normalized = _normalize_heading_key(heading.heading)
        if normalized in _ABSTRACT_HEADINGS:
            abstract = body
            continue
        if normalized in _REFERENCE_HEADINGS:
            references = _split_references(body)
            continue
        sections.append(
            Section(
                heading=heading.heading,
                level=heading.level,
                text=body,
                parent_heading=heading.parent_heading,
                parent_headings=heading.parent_headings,
                page_number=heading.page_number,
                char_start=heading.body_start,
                char_end=body_end,
            )
        )

    if not sections and raw_text.strip():
        sections.append(
            Section(
                heading="Full Text",
                level=1,
                text=raw_text.strip(),
                page_number=1,
                char_start=0,
                char_end=len(raw_text),
            )
        )

    figures = _extract_figure_captions(raw_text, page_spans)
    tables = _extract_tables(raw_text, page_spans)
    title = metadata.title or source_path.stem
    metadata = metadata.model_copy(update={"title": title})
    return ParsedPaper(
        title=title,
        abstract=abstract,
        sections=sections,
        figures=figures,
        tables=tables,
        references=references,
        raw_text=raw_text,
        metadata=metadata,
        source_path=str(source_path),
        page_count=max((span[2] for span in page_spans), default=0),
    )


def _normalize_text(text: str) -> str:
    normalized_lines: List[str] = []
    for line in text.replace("\x00", "").splitlines():
        normalized_lines.append(" ".join(line.split()))
    return "\n".join(normalized_lines).strip()


def _join_pages(page_texts: Sequence[str]) -> Tuple[str, List[Tuple[int, int, int]]]:
    parts: List[str] = []
    spans: List[Tuple[int, int, int]] = []
    cursor = 0
    for index, page_text in enumerate(page_texts):
        if index > 0:
            parts.append("\n\n")
            cursor += 2
        start = cursor
        parts.append(page_text)
        cursor += len(page_text)
        spans.append((start, cursor, index + 1))
    return "".join(parts), spans


def _detect_headings(raw_text: str, page_spans: Sequence[Tuple[int, int, int]]) -> List[_Heading]:
    headings: List[_Heading] = []
    stack: List[Tuple[int, str]] = []
    cursor = 0
    for raw_line in raw_text.splitlines(keepends=True):
        stripped = raw_line.strip()
        if not stripped:
            cursor += len(raw_line)
            continue
        line_start = cursor + raw_line.find(stripped)
        line_end = line_start + len(stripped)
        parsed = _parse_heading(stripped, stack)
        if parsed is None:
            cursor += len(raw_line)
            continue
        heading, level = parsed
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent_headings = [item[1] for item in stack]
        parent_heading = parent_headings[-1] if parent_headings else None
        headings.append(
            _Heading(
                heading=heading,
                level=level,
                start=line_start,
                body_start=line_end,
                page_number=_page_for_offset(line_start, page_spans),
                parent_heading=parent_heading,
                parent_headings=parent_headings,
            )
        )
        normalized = _normalize_heading_key(heading)
        if normalized not in _REFERENCE_HEADINGS:
            stack.append((level, heading))
        cursor += len(raw_line)
    return headings


def _parse_heading(line: str, stack: Sequence[Tuple[int, str]]) -> Optional[Tuple[str, int]]:
    without_trailing = line.rstrip(":").strip()
    numbered = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(.+)$", without_trailing)
    if numbered:
        level = min(numbered.group(1).count(".") + 1, 6)
        heading = numbered.group(2).strip().rstrip(":")
        if _looks_like_heading_text(heading):
            return heading, level

    normalized = _normalize_heading_key(without_trailing)
    if normalized in _MAIN_HEADINGS:
        return without_trailing, 1

    if stack and _looks_like_subheading(without_trailing):
        parent_level = stack[-1][0]
        return without_trailing, min(parent_level + 1, 6)
    return None


def _looks_like_heading_text(value: str) -> bool:
    words = value.split()
    return 0 < len(words) <= 14 and not value.endswith(".")


def _looks_like_subheading(value: str) -> bool:
    if not _looks_like_heading_text(value):
        return False
    lowered = value.lower()
    if lowered.startswith(("doi", "figure", "fig.", "table", "journal", "keywords")):
        return False
    if any(character in value for character in [";", ",", "=", "±"]):
        return False
    words = value.split()
    capitalized = sum(1 for word in words if word[:1].isupper())
    return capitalized >= max(1, len(words) // 2)


def _normalize_heading_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip(":")).lower()


def _page_for_offset(offset: int, page_spans: Sequence[Tuple[int, int, int]]) -> int:
    for start, end, page_number in page_spans:
        if start <= offset <= end:
            return page_number
    return page_spans[-1][2] if page_spans else 1


def _split_references(text: str) -> List[str]:
    references: List[str] = []
    current: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^(\[\d+\]|\d+\.|\d+\))\s+", line) and current:
            references.append(" ".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        references.append(" ".join(current).strip())
    return references


def _extract_figure_captions(
    raw_text: str, page_spans: Sequence[Tuple[int, int, int]]
) -> List[FigureCaption]:
    figures: List[FigureCaption] = []
    pattern = re.compile(r"\b(Fig(?:ure)?\.?\s*\d+[A-Za-z]?)[:.\s]+(.+)", re.IGNORECASE)
    for match in pattern.finditer(raw_text):
        caption = match.group(2).strip()
        if len(caption) < 8:
            continue
        figures.append(
            FigureCaption(
                label=match.group(1).strip(),
                caption=caption,
                page_number=_page_for_offset(match.start(), page_spans),
                char_start=match.start(),
                char_end=match.end(),
            )
        )
    return figures


def _extract_tables(raw_text: str, page_spans: Sequence[Tuple[int, int, int]]) -> List[TableData]:
    tables: List[TableData] = []
    pattern = re.compile(r"\b(Table\s*\d+[A-Za-z]?)[:.\s]+(.+)", re.IGNORECASE)
    for match in pattern.finditer(raw_text):
        text = match.group(2).strip()
        if len(text) < 8:
            continue
        tables.append(
            TableData(
                label=match.group(1).strip(),
                text=text,
                page_number=_page_for_offset(match.start(), page_spans),
                char_start=match.start(),
                char_end=match.end(),
            )
        )
    return tables
