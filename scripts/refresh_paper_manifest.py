#!/usr/bin/env python3
"""Refresh data/seeds/recent_papers.json with the newest mitochondrial papers.

Queries Europe PMC for the most recent open-access mitochondrial publications
and writes a deterministic JSON manifest. Run daily by .github/workflows/auto-update.yml
- only commits when the manifest content actually changes.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
QUERY = "(mitochondri*) AND (OPEN_ACCESS:Y) AND (HAS_ABSTRACT:Y)"
PAGE_SIZE = 50
TIMEOUT_SECONDS = 30
MANIFEST_PATH = Path("data/seeds/recent_papers.json")


def fetch_results() -> List[Dict[str, Any]]:
    params = {
        "query": QUERY,
        "format": "json",
        "pageSize": PAGE_SIZE,
        "sort": "P_PDATE_D desc",
        "resultType": "lite",
    }
    url = f"{EPMC_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "MitoRAG-daily/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        payload = json.loads(resp.read())
    return payload.get("resultList", {}).get("result", [])


def normalize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pmid": item.get("pmid") or None,
        "pmcid": item.get("pmcid") or None,
        "doi": item.get("doi") or None,
        "title": (item.get("title") or "").strip().rstrip("."),
        "year": item.get("pubYear") or None,
        "journal": item.get("journalTitle") or None,
        "first_author": (item.get("authorString") or "").split(",")[0].strip() or None,
        "source": item.get("source") or None,
    }


def main() -> int:
    try:
        results = fetch_results()
    except Exception as exc:
        print(f"Failed to fetch Europe PMC results: {exc}", file=sys.stderr)
        return 1

    papers = [normalize(item) for item in results]
    # Deterministic order so commits only happen on real content change.
    papers.sort(key=lambda p: (p.get("pmid") or "", p.get("doi") or "", p.get("title") or ""))

    manifest = {
        "query": QUERY,
        "count": len(papers),
        "papers": papers,
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"

    previous = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else ""
    if previous == serialized:
        print(f"No change ({len(papers)} papers).")
        return 0

    MANIFEST_PATH.write_text(serialized, encoding="utf-8")
    print(f"Wrote {len(papers)} papers to {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
