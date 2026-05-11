"""Lightweight metadata extraction for scientific PDFs."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, List, Optional

from mitorag_ingest.models import PaperMetadata

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
JOURNAL_RE = re.compile(r"\b(?:journal|source)\s*[:\-]\s*(.+)$", re.IGNORECASE)
KEYWORDS_RE = re.compile(r"\bkeywords?\s*[:\-]\s*(.+)$", re.IGNORECASE)
MESH_RE = re.compile(r"\bMeSH(?:\s+terms?)?\s*[:\-]\s*(.+)$", re.IGNORECASE)


def extract_metadata(text: str, source_path: Optional[Path] = None) -> PaperMetadata:
    """Extract DOI, title, authors, journal, year, keywords, and MeSH terms.

    This is intentionally conservative. Phase 5 can enrich these fields through
    Crossref, PubMed, Europe PMC, or local reference managers.
    """

    lines = _meaningful_lines(text)
    doi = _extract_doi(text)
    title = _extract_title(lines, source_path)
    authors = _extract_authors(lines, title)
    journal = _first_regex_group(lines, JOURNAL_RE)
    year = _extract_year(text)
    keywords = _split_terms(_first_regex_group(lines, KEYWORDS_RE))
    mesh_terms = _split_terms(_first_regex_group(lines, MESH_RE))

    return PaperMetadata(
        doi=doi,
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        keywords=keywords,
        mesh_terms=mesh_terms,
    )


def paper_id_from_metadata(metadata: PaperMetadata, source_path: Optional[Path]) -> str:
    """Return DOI when present, otherwise a stable filename/title hash."""

    if metadata.doi:
        return metadata.doi.lower()
    basis = str(source_path.resolve()) if source_path else (metadata.title or "unknown-paper")
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"file:{digest}"


def _extract_doi(text: str) -> Optional[str]:
    match = DOI_RE.search(text)
    if not match:
        return None
    return match.group(0).rstrip(".,;)]}").lower()


def _meaningful_lines(text: str, limit: int = 80) -> List[str]:
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if line:
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _extract_title(lines: List[str], source_path: Optional[Path]) -> Optional[str]:
    for line in lines[:15]:
        lowered = line.lower()
        if lowered.startswith(("doi", "abstract", "keywords", "journal", "source")):
            continue
        if DOI_RE.search(line):
            continue
        if len(line) >= 8:
            return line
    return source_path.stem if source_path else None


def _extract_authors(lines: List[str], title: Optional[str]) -> List[str]:
    if not title:
        return []
    try:
        title_index = lines.index(title)
    except ValueError:
        return []
    if title_index + 1 >= len(lines):
        return []
    candidate = lines[title_index + 1]
    lowered = candidate.lower()
    if lowered.startswith(("abstract", "doi", "journal", "source")):
        return []
    if not any(separator in candidate for separator in [",", ";", " and "]):
        return []
    return [author for author in _split_terms(candidate) if len(author) > 1]


def _extract_year(text: str) -> Optional[int]:
    match = YEAR_RE.search(text)
    if not match:
        return None
    return int(match.group(1))


def _first_regex_group(lines: Iterable[str], pattern: re.Pattern[str]) -> Optional[str]:
    for line in lines:
        match = pattern.search(line)
        if match:
            return match.group(1).strip()
    return None


def _split_terms(value: Optional[str]) -> List[str]:
    if not value:
        return []
    terms = re.split(r"\s*[;,]\s*|\s+\|\s+", value)
    return [term.strip().rstrip(".") for term in terms if term.strip()]

