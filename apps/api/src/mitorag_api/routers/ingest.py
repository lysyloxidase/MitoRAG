"""Paper upload and ingestion endpoints."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from typing_extensions import Annotated

from mitorag_ingest.watcher import LocalIngestionPipeline

router = APIRouter()


class IngestResponse(BaseModel):
    paper_id: str
    title: str
    chunk_count: int
    saved_to: str


class PaperSummary(BaseModel):
    filename: str
    size_bytes: int
    status: str = "available"


@router.post("/upload", response_model=IngestResponse)
async def upload_paper(file: Annotated[UploadFile, File(...)]) -> IngestResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf uploads are supported")

    papers_dir = Path(os.environ.get("PAPERS_DIR", "./data/papers"))
    papers_dir.mkdir(parents=True, exist_ok=True)
    target = papers_dir / Path(file.filename).name
    target.write_bytes(await file.read())

    result = LocalIngestionPipeline().ingest_pdf(target)
    return IngestResponse(
        paper_id=result.paper_id,
        title=result.title,
        chunk_count=result.chunk_count,
        saved_to=str(target),
    )


@router.get("/papers", response_model=List[PaperSummary])
def list_papers() -> List[PaperSummary]:
    papers_dir = Path(os.environ.get("PAPERS_DIR", "./data/papers"))
    papers_dir.mkdir(parents=True, exist_ok=True)
    return [
        PaperSummary(filename=path.name, size_bytes=path.stat().st_size)
        for path in sorted(papers_dir.glob("*.pdf"))
    ]
