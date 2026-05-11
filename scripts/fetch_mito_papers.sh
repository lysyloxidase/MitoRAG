#!/usr/bin/env bash
# Bulk-download open-access mitochondrial research papers from Europe PMC.
#
# Usage:
#   ./scripts/fetch_mito_papers.sh [count] [query]
#
# Examples:
#   ./scripts/fetch_mito_papers.sh                              # default 50 papers
#   ./scripts/fetch_mito_papers.sh 200                          # 200 papers
#   ./scripts/fetch_mito_papers.sh 100 "PINK1 Parkin mitophagy" # topic-specific
#
# Files land in data/papers/ and are picked up automatically by the API watcher
# once you POST to /ingest/upload for each, OR re-run the API container so it
# re-indexes the watched folder.

set -euo pipefail

COUNT="${1:-50}"
QUERY="${2:-mitochondria}"
DEST="${PAPERS_DIR:-./data/papers}"
EPMC="https://www.ebi.ac.uk/europepmc/webservices/rest"

mkdir -p "$DEST"

echo "Fetching up to $COUNT open-access papers from Europe PMC matching: $QUERY"
echo "Destination: $DEST"
echo

# Europe PMC search filtered to open-access full-text articles.
ENCODED_QUERY=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "(${QUERY}) AND (HAS_PDF:Y AND OPEN_ACCESS:Y) AND mitochondri*")
SEARCH_URL="${EPMC}/search?query=${ENCODED_QUERY}&resultType=lite&pageSize=${COUNT}&format=json"

PAYLOAD=$(curl -fsSL "$SEARCH_URL")

# Iterate hits; pull PMCID + title, then fetch PDF from EPMC fulltext endpoint.
count=0
echo "$PAYLOAD" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for item in data.get("resultList", {}).get("result", []):
    pmcid = item.get("pmcid", "")
    title = item.get("title", "")
    if pmcid and title:
        clean = title.replace("\n", " ").replace("\r", " ").replace("|", "-")
        print(pmcid + "|" + clean[:140])
' | while IFS='|' read -r pmcid title; do
    safe_title=$(printf '%s' "$title" | tr -cd '[:alnum:][:space:]_-' | tr -s ' ' '_' | cut -c1-100)
    target="${DEST}/${pmcid}_${safe_title}.pdf"

    if [[ -f "$target" ]]; then
        printf "  [skip]    %s (already exists)\n" "$pmcid"
        continue
    fi

    pdf_url="${EPMC}/${pmcid}/fullTextXML"  # Some PMCs only have XML; try PDF first
    pdf_url="https://europepmc.org/articles/${pmcid}?pdf=render"

    if curl -fsSL -o "$target" "$pdf_url" 2>/dev/null && [[ -s "$target" ]]; then
        size=$(stat -f%z "$target" 2>/dev/null || stat -c%s "$target" 2>/dev/null || echo 0)
        if [[ "$size" -lt 4000 ]]; then
            rm -f "$target"
            printf "  [skip]    %s (no PDF available)\n" "$pmcid"
        else
            count=$((count + 1))
            printf "  [%3d]     %s — %s\n" "$count" "$pmcid" "${title:0:80}"
        fi
    else
        rm -f "$target"
        printf "  [fail]    %s\n" "$pmcid"
    fi
done

echo
echo "Done. Restart the API to pick up new PDFs, or upload through the UI to trigger immediate ingestion:"
echo "  docker compose restart api"
echo "  # OR for each PDF:"
echo "  curl -X POST -F file=@\${DEST}/<name>.pdf http://localhost:8000/ingest/upload"
