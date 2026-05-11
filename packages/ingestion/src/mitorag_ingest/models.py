"""Pydantic models shared by the MitoRAG ingestion pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChunkType(str, Enum):
    """Evidence unit types that retrieval and citation auditing can reason over."""

    ABSTRACT = "abstract"
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"


class PaperMetadata(BaseModel):
    """Bibliographic and biomedical metadata extracted from a paper."""

    model_config = ConfigDict(extra="allow")

    doi: Optional[str] = None
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    journal: Optional[str] = None
    year: Optional[int] = None
    mesh_terms: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    def as_chunk_metadata(self) -> Dict[str, object]:
        """Return metadata fields that should travel with every chunk."""

        return {
            "doi": self.doi,
            "title": self.title,
            "authors": list(self.authors),
            "journal": self.journal,
            "year": self.year,
            "mesh_terms": list(self.mesh_terms),
            "keywords": list(self.keywords),
        }


class Section(BaseModel):
    """A parsed scientific section with heading hierarchy preserved."""

    heading: str
    level: int = Field(ge=1, le=6)
    text: str
    parent_heading: Optional[str] = None
    parent_headings: List[str] = Field(default_factory=list)
    page_number: int = Field(default=1, ge=1)
    char_start: int = Field(default=0, ge=0)
    char_end: int = Field(default=0, ge=0)

    @property
    def section_path(self) -> str:
        """Return a PaperQA-style heading path such as Results > ETC Activity."""

        parents = self.parent_headings
        if not parents and self.parent_heading:
            parents = [self.parent_heading]
        path_parts = [part.strip() for part in [*parents, self.heading] if part.strip()]
        return " > ".join(path_parts)


class FigureCaption(BaseModel):
    """A figure caption extracted from a paper."""

    label: str
    caption: str
    page_number: int = Field(default=1, ge=1)
    char_start: int = Field(default=0, ge=0)
    char_end: int = Field(default=0, ge=0)


class TableData(BaseModel):
    """A table text or markdown representation extracted from a paper."""

    label: str
    text: str
    page_number: int = Field(default=1, ge=1)
    char_start: int = Field(default=0, ge=0)
    char_end: int = Field(default=0, ge=0)


class EquationData(BaseModel):
    """A display equation extracted as text or markup."""

    label: Optional[str] = None
    text: str
    page_number: int = Field(default=1, ge=1)
    char_start: int = Field(default=0, ge=0)
    char_end: int = Field(default=0, ge=0)


def _section_list() -> List[Section]:
    return []


def _figure_list() -> List[FigureCaption]:
    return []


def _table_list() -> List[TableData]:
    return []


def _equation_list() -> List[EquationData]:
    return []


class ParsedPaper(BaseModel):
    """Structured representation of a scientific PDF."""

    title: str = ""
    abstract: str = ""
    sections: List[Section] = Field(default_factory=_section_list)
    figures: List[FigureCaption] = Field(default_factory=_figure_list)
    tables: List[TableData] = Field(default_factory=_table_list)
    equations: List[EquationData] = Field(default_factory=_equation_list)
    references: List[str] = Field(default_factory=list)
    raw_text: str = ""
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    source_path: Optional[str] = None
    page_count: int = Field(default=0, ge=0)


class Chunk(BaseModel):
    """A retrieval-ready scientific evidence chunk."""

    id: str
    text: str
    paper_id: str
    section_path: str
    chunk_type: ChunkType
    page_number: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    metadata: Dict[str, object] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    """Result emitted after a PDF is parsed and chunked."""

    paper_id: str
    source_path: str
    title: str
    chunk_count: int
    chunks: List[Chunk]
    parsed: ParsedPaper
