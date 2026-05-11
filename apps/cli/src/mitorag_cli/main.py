"""MitoRAG command-line interface."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional, Sequence

from mitorag_ingest.watcher import LocalIngestionPipeline, PaperWatcher


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mitorag")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest = subcommands.add_parser("ingest-once", help="Parse and chunk PDFs in PAPERS_DIR once")
    ingest.add_argument("--papers-dir", default=os.environ.get("PAPERS_DIR", "./data/papers"))

    args = parser.parse_args(argv)
    if args.command == "ingest-once":
        watcher = PaperWatcher(
            papers_dir=Path(args.papers_dir),
            pipeline=LocalIngestionPipeline(),
            settle_seconds=0,
            ingest_existing=True,
        )
        results = watcher.poll_once()
        for result in results:
            print(f"{result.paper_id}\t{result.chunk_count}\t{result.title}")
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
