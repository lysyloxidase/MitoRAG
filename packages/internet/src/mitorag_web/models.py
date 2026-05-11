"""Typed models for scientific web search results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence


def _empty_authors() -> List[str]:
    return []


def _empty_ids() -> Dict[str, str]:
    return {}


def _empty_embedding() -> List[float]:
    return []


def _empty_annotations() -> List[PubTatorAnnotation]:
    return []


@dataclass(frozen=True)
class PubMedResult:
    pmid: str
    title: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None


@dataclass(frozen=True)
class PubMedAbstract:
    pmid: str
    title: str
    abstract: str
    journal: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None
    authors: Sequence[str] = field(default_factory=_empty_authors)


@dataclass(frozen=True)
class S2Paper:
    paper_id: str
    title: str
    abstract: str = ""
    year: Optional[int] = None
    citation_count: int = 0
    doi: Optional[str] = None
    pmid: Optional[str] = None
    external_ids: Mapping[str, str] = field(default_factory=_empty_ids)
    embedding: Sequence[float] = field(default_factory=_empty_embedding)


@dataclass(frozen=True)
class EuropePMCResult:
    id: str
    source: str
    title: str
    abstract: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    journal: str = ""


@dataclass(frozen=True)
class BioRxivPreprint:
    doi: str
    title: str
    abstract: str
    date: str
    server: str
    category: str = ""
    authors: str = ""


@dataclass(frozen=True)
class PubTatorAnnotation:
    pmid: str
    text: str
    entity_type: str
    identifier: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None


@dataclass(frozen=True)
class WebChunk:
    id: str
    text: str
    source: str
    title: str
    score: float = 0.0
    pmid: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    citation: Optional[str] = None
    annotations: Sequence[PubTatorAnnotation] = field(default_factory=_empty_annotations)


def paper_key(doi: Optional[str], pmid: Optional[str], fallback: str) -> str:
    if doi:
        return f"doi:{doi.lower()}"
    if pmid:
        return f"pmid:{pmid}"
    return fallback

