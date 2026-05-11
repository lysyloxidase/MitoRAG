"""Filesystem watcher for the paper folder."""

from __future__ import annotations

import importlib
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, List, Optional, Protocol, Set, cast

from mitorag_ingest.chunker import chunk_paper
from mitorag_ingest.metadata_extractor import paper_id_from_metadata
from mitorag_ingest.models import IngestionResult
from mitorag_ingest.pdf_parser import parse_pdf

logger = logging.getLogger(__name__)


class IngestionPipeline(Protocol):
    """Protocol consumed by PaperWatcher."""

    def ingest_pdf(self, path: Path) -> IngestionResult:
        """Parse, chunk, embed, index, and link a PDF."""
        ...


class LocalIngestionPipeline:
    """Phase 1 local ingestion pipeline: parse and chunk only."""

    def __init__(self, on_result: Optional[Callable[[IngestionResult], None]] = None) -> None:
        self._on_result = on_result

    def ingest_pdf(self, path: Path) -> IngestionResult:
        parsed = parse_pdf(path)
        chunks = chunk_paper(parsed)
        paper_id = paper_id_from_metadata(parsed.metadata, path)
        result = IngestionResult(
            paper_id=paper_id,
            source_path=str(path),
            title=parsed.title,
            chunk_count=len(chunks),
            chunks=chunks,
            parsed=parsed,
        )
        if self._on_result:
            self._on_result(result)
        return result


class PaperWatcher:
    """Watch a paper folder and auto-ingest new PDFs."""

    def __init__(
        self,
        papers_dir: Path,
        pipeline: IngestionPipeline,
        settle_seconds: float = 0.5,
        poll_interval_seconds: float = 2.0,
        ingest_existing: bool = False,
    ) -> None:
        self.papers_dir = papers_dir.expanduser().resolve()
        self.pipeline = pipeline
        self.settle_seconds = settle_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self._seen: Set[Path] = set()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._observer: Optional[Any] = None
        self._ingest_existing = ingest_existing

    def start(self) -> None:
        """Start filesystem watching in the background."""

        self.papers_dir.mkdir(parents=True, exist_ok=True)
        if not self._ingest_existing:
            self._seen.update(self.papers_dir.glob("*.pdf"))
        if self._start_watchdog():
            return
        self._start_polling()

    def stop(self) -> None:
        """Stop any active watcher thread or watchdog observer."""

        self._stop_event.set()
        if self._observer is not None:
            stop = getattr(self._observer, "stop")
            join = getattr(self._observer, "join")
            stop()
            join(timeout=5)
            self._observer = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def poll_once(self) -> List[IngestionResult]:
        """Scan for unprocessed PDFs once; useful for tests and CLI runs."""

        self.papers_dir.mkdir(parents=True, exist_ok=True)
        results: List[IngestionResult] = []
        for path in sorted(self.papers_dir.glob("*.pdf")):
            if path in self._seen:
                continue
            result = self._ingest_path(path)
            if result is not None:
                results.append(result)
        return results

    def _start_watchdog(self) -> bool:
        try:
            events_module = importlib.import_module("watchdog.events")
            observers_module = importlib.import_module("watchdog.observers")
        except ImportError:
            return False

        handler_base = getattr(events_module, "FileSystemEventHandler")
        observer_cls = getattr(observers_module, "Observer")
        watcher = self

        class Handler(handler_base):  # type: ignore[misc, valid-type]
            def on_created(self, event: Any) -> None:
                if bool(getattr(event, "is_directory", False)):
                    return
                watcher._ingest_path(Path(str(getattr(event, "src_path"))))

            def on_moved(self, event: Any) -> None:
                if bool(getattr(event, "is_directory", False)):
                    return
                watcher._ingest_path(Path(str(getattr(event, "dest_path"))))

        observer = observer_cls()
        schedule = getattr(observer, "schedule")
        start = getattr(observer, "start")
        schedule(Handler(), str(self.papers_dir), recursive=False)
        start()
        self._observer = observer
        logger.info("Started watchdog observer for %s", self.papers_dir)
        return True

    def _start_polling(self) -> None:
        def loop() -> None:
            while not self._stop_event.is_set():
                self.poll_once()
                self._stop_event.wait(self.poll_interval_seconds)

        self._thread = threading.Thread(target=loop, name="mitorag-paper-watcher", daemon=True)
        self._thread.start()
        logger.info("Started polling paper watcher for %s", self.papers_dir)

    def _ingest_path(self, path: Path) -> Optional[IngestionResult]:
        path = path.expanduser().resolve()
        if path.suffix.lower() != ".pdf":
            return None
        with self._lock:
            if path in self._seen:
                return None
            self._seen.add(path)
        if not self._wait_until_stable(path):
            logger.warning("Skipping unstable or missing PDF: %s", path)
            return None
        try:
            result = self.pipeline.ingest_pdf(path)
        except Exception:
            with self._lock:
                self._seen.discard(path)
            logger.exception("Failed to ingest %s", path)
            raise
        logger.info("Ingested %s into %s chunks", path, result.chunk_count)
        return result

    def _wait_until_stable(self, path: Path) -> bool:
        if self.settle_seconds <= 0:
            return path.exists()
        try:
            first_size = path.stat().st_size
            time.sleep(self.settle_seconds)
            second_size = path.stat().st_size
        except FileNotFoundError:
            return False
        return first_size == second_size


def build_default_watcher(papers_dir: Path) -> PaperWatcher:
    """Create a Phase 1 watcher with the local parse/chunk pipeline."""

    return PaperWatcher(
        papers_dir=papers_dir,
        pipeline=cast(IngestionPipeline, LocalIngestionPipeline()),
    )
