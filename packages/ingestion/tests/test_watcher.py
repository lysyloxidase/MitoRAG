from __future__ import annotations

from pathlib import Path
from typing import List

from mitorag_ingest.models import IngestionResult, ParsedPaper
from mitorag_ingest.watcher import PaperWatcher


class FakePipeline:
    def __init__(self) -> None:
        self.paths: List[Path] = []

    def ingest_pdf(self, path: Path) -> IngestionResult:
        self.paths.append(path)
        parsed = ParsedPaper(title=path.stem, source_path=str(path))
        return IngestionResult(
            paper_id=f"file:{path.stem}",
            source_path=str(path),
            title=path.stem,
            chunk_count=0,
            chunks=[],
            parsed=parsed,
        )


def test_watcher_poll_once_ingests_new_pdf(tmp_path: Path) -> None:
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    pdf_path = papers_dir / "new-paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    pipeline = FakePipeline()

    watcher = PaperWatcher(papers_dir, pipeline, settle_seconds=0)
    results = watcher.poll_once()

    assert [path.name for path in pipeline.paths] == ["new-paper.pdf"]
    assert len(results) == 1
    assert results[0].paper_id == "file:new-paper"

