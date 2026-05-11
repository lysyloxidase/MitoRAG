"""PDF ingestion pipeline for local mitochondrial papers."""

from mitorag_ingest.chunker import chunk_paper
from mitorag_ingest.models import (
    Chunk,
    EquationData,
    FigureCaption,
    IngestionResult,
    PaperMetadata,
    ParsedPaper,
    Section,
    TableData,
)
from mitorag_ingest.pdf_parser import parse_pdf
from mitorag_ingest.watcher import LocalIngestionPipeline, PaperWatcher

__all__ = [
    "Chunk",
    "EquationData",
    "FigureCaption",
    "IngestionResult",
    "LocalIngestionPipeline",
    "PaperMetadata",
    "PaperWatcher",
    "ParsedPaper",
    "Section",
    "TableData",
    "chunk_paper",
    "parse_pdf",
]

__version__ = "1.0.0"

