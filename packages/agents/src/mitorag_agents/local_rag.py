"""Agent 3: local RAG retrieval node.

Scans the ingested PDF library (PAPERS_DIR), parses + chunks each file once
(cached by mtime), and scores chunks against the query with lightweight token
overlap. Returns top-K ranked chunks for downstream agents.

If the library is empty, returns no chunks — that way the verifier and
synthesizer aren't tricked by hardcoded controversy snippets when there are no
real PDFs to ground against.
"""

from __future__ import annotations

import logging
import math
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mitorag_agents.state import MitoRAGState, StateUpdate
from mitorag_agents.utils import ranked_chunk, timed_node
from mitorag_retrieval.models import RankedChunk

logger = logging.getLogger(__name__)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
STOPWORDS = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "has", "have", "had", "but", "not", "into", "than", "between", "which",
    "what", "how", "why", "when", "where", "who", "does", "did", "can", "could",
    "would", "should", "may", "might", "will", "shall", "their", "there", "these",
    "those", "such", "also", "been", "being", "about", "more", "most",
})


@dataclass(frozen=True)
class _CachedChunk:
    text: str
    paper_id: str
    section_path: str
    source_path: str


_cache_lock = threading.Lock()
_chunk_cache: Dict[str, Tuple[float, List[_CachedChunk]]] = {}


def local_rag_node(state: MitoRAGState) -> StateUpdate:
    """Retrieve local paper chunks from the ingested PDF library."""

    with timed_node(state, "local_rag") as update:
        if state.local_chunks:
            update["local_chunks"] = state.local_chunks
        else:
            update["local_chunks"] = scan_and_rank(state.query)
        return update


def scan_and_rank(query: str, top_k: int = 8) -> List[RankedChunk]:
    """Parse the PAPERS_DIR library (cached) and return top-k relevant chunks."""
    papers_dir = Path(os.environ.get("PAPERS_DIR", "./data/papers"))
    if not papers_dir.exists():
        return []

    pdfs = sorted(papers_dir.glob("*.pdf"))
    if not pdfs:
        return []

    all_chunks: List[_CachedChunk] = []
    for pdf in pdfs:
        try:
            chunks = _chunks_for(pdf)
        except Exception as exc:
            logger.warning("local_rag: failed to parse %s: %s", pdf.name, exc)
            continue
        all_chunks.extend(chunks)

    if not all_chunks:
        return []

    return _rank_chunks(query, all_chunks, top_k)


def _chunks_for(pdf_path: Path) -> List[_CachedChunk]:
    key = str(pdf_path)
    mtime = pdf_path.stat().st_mtime
    with _cache_lock:
        cached = _chunk_cache.get(key)
        if cached and cached[0] == mtime:
            return cached[1]

    chunks = _parse_pdf_safely(pdf_path)
    with _cache_lock:
        _chunk_cache[key] = (mtime, chunks)
    return chunks


def _parse_pdf_safely(pdf_path: Path) -> List[_CachedChunk]:
    try:
        from mitorag_ingest.chunker import chunk_paper
        from mitorag_ingest.pdf_parser import parse_pdf
    except ImportError:
        return []

    parsed = parse_pdf(pdf_path)
    chunked = chunk_paper(parsed)
    paper_id = _paper_id_from_filename(pdf_path) or (
        chunked[0].paper_id if chunked else pdf_path.stem
    )
    return [
        _CachedChunk(
            text=chunk.text,
            paper_id=paper_id,
            section_path=chunk.section_path or "Body",
            source_path=str(pdf_path),
        )
        for chunk in chunked
        if chunk.text and len(chunk.text) > 80
    ]


def _paper_id_from_filename(path: Path) -> Optional[str]:
    name = path.stem
    pmc_match = re.match(r"(PMC\d+)", name)
    if pmc_match:
        return pmc_match.group(1)
    pmid_match = re.match(r"PMID[_-]?(\d+)", name, flags=re.IGNORECASE)
    if pmid_match:
        return f"PMID:{pmid_match.group(1)}"
    return None


def _tokenize(text: str) -> List[str]:
    return [tok.lower() for tok in WORD_RE.findall(text) if tok.lower() not in STOPWORDS]


def _rank_chunks(query: str, chunks: List[_CachedChunk], top_k: int) -> List[RankedChunk]:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    q_set = set(q_tokens)

    scored: List[Tuple[float, _CachedChunk]] = []
    for chunk in chunks:
        c_tokens = _tokenize(chunk.text)
        if not c_tokens:
            continue
        c_set = set(c_tokens)
        overlap = len(q_set & c_set)
        if overlap == 0:
            continue
        score = overlap * math.log(1 + len(q_set)) / math.log(2 + len(c_tokens))
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    ranked: List[RankedChunk] = []
    for rank, (score, chunk) in enumerate(top, start=1):
        citation = _citation_for(chunk.paper_id)
        ranked.append(
            ranked_chunk(
                f"local-{rank}-{chunk.paper_id}",
                chunk.text[:1200],
                chunk.paper_id,
                chunk.section_path,
                float(score),
                rank,
                "local_rag",
                citation,
            )
        )
    return ranked


def _citation_for(paper_id: str) -> str:
    if not paper_id:
        return "[local]"
    if paper_id.startswith("PMID:"):
        return f"[{paper_id}]"
    if paper_id.startswith("PMC"):
        return f"[{paper_id}]"
    if paper_id.startswith("10."):
        return f"[doi:{paper_id}]"
    return f"[{paper_id}]"


def local_fixture_chunks(query: str) -> List[RankedChunk]:
    """Deterministic fixture chunks used by unit tests only.

    Production code path (``local_rag_node``) does *not* call this function;
    it scans the real PDF library instead. These fixtures intentionally cover
    Complex I, MELAS, and the mPTP controversy so verifier/synthesizer tests
    have predictable evidence to assert against.
    """
    del query
    return [
        ranked_chunk(
            "local-complex-i",
            "Complex I contains 45 subunits, including seven mtDNA-encoded ND subunits.",
            "PMID:33174596",
            "Results > Complex I",
            0.97,
            1,
            "local_rag",
            "[PMID:33174596]",
        ),
        ranked_chunk(
            "local-melas",
            "The m.3243A>G variant in MT-TL1 is a canonical cause of MELAS syndrome.",
            "PMID:25613900",
            "Disease > MELAS",
            0.92,
            2,
            "local_rag",
            "[PMID:25613900]",
        ),
        ranked_chunk(
            "local-mptp-atp",
            "One disputed model proposes the mPTP is formed by ATP synthase dimers.",
            "PMID:37336870",
            "Discussion > mPTP",
            0.88,
            3,
            "local_rag",
            "[PMID:37336870]",
        ),
        ranked_chunk(
            "local-mptp-ant",
            "Contradictory synthase-null evidence supports non-ATP-synthase mPTP opening.",
            "PMID:37607939",
            "Discussion > mPTP",
            0.87,
            4,
            "local_rag",
            "[PMID:37607939]",
        ),
        ranked_chunk(
            "local-methods",
            "Mitochondrial isolation uses differential centrifugation and purity controls.",
            "PMID:30000001",
            "Methods > Isolation",
            0.74,
            5,
            "local_rag",
            "[PMID:30000001]",
        ),
    ]
