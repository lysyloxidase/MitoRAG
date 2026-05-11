"""Live smoke test for Phase 5 scientific web search clients."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in [
    ROOT / "packages" / "agents" / "src",
    ROOT / "packages" / "retrieval" / "src",
    ROOT / "packages" / "internet" / "src",
]:
    sys.path.insert(0, str(path))

from mitorag_agents.web_rag import WebRAGAgent  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test Phase 5 web search.")
    parser.add_argument("query", nargs="?", default="Complex I cryo-EM")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    chunks = await WebRAGAgent().search(args.query)
    for rank, chunk in enumerate(chunks[: args.top_k], start=1):
        citation = chunk.citation or chunk.pmid or chunk.doi or "uncited"
        print(f"{rank}. {citation} {chunk.title} [{chunk.source}] score={chunk.score:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
