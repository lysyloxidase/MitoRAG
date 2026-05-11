"""Agent 9: cited answer synthesizer.

Builds a substantial, citation-grounded answer from the actual evidence pool
(web chunks from PubMed/S2/EuropePMC/bioRxiv, local PDF chunks, KG context).
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

from mitorag_agents.state import MitoRAGState, StateUpdate
from mitorag_agents.utils import extract_citations, timed_node
from mitorag_retrieval.models import RankedChunk


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
TOPIC_HINTS = [
    ("complex i", "Complex I (NADH:ubiquinone oxidoreductase)"),
    ("complex ii", "Complex II (succinate dehydrogenase)"),
    ("complex iii", "Complex III (cytochrome bc1)"),
    ("complex iv", "Complex IV (cytochrome c oxidase)"),
    ("complex v", "Complex V (ATP synthase)"),
    ("oxphos", "oxidative phosphorylation (OXPHOS)"),
    ("mitophagy", "PINK1/Parkin-mediated mitophagy"),
    ("pink1", "PINK1/Parkin signaling"),
    ("mptp", "mitochondrial permeability transition pore (mPTP)"),
    ("melas", "MELAS syndrome"),
    ("lhon", "Leber hereditary optic neuropathy (LHON)"),
    ("merrf", "MERRF syndrome"),
    ("leigh", "Leigh syndrome"),
    ("ros", "mitochondrial reactive oxygen species"),
    ("apoptosis", "intrinsic apoptotic pathway"),
    ("tca", "TCA (Krebs) cycle"),
    ("fatty acid", "fatty-acid β-oxidation"),
]

# Textbook intros for fundamental questions where literature alone is insufficient.
FUNDAMENTALS: dict[str, str] = {
    "what is mitochondria": (
        "Mitochondria are double-membrane organelles found in nearly all eukaryotic cells, "
        "containing their own circular genome (mtDNA, ~16.5 kb in humans encoding 13 OXPHOS "
        "subunits, 22 tRNAs and 2 rRNAs). They generate most cellular ATP through oxidative "
        "phosphorylation (OXPHOS) coupling the electron transport chain (Complexes I–IV plus "
        "Complex V/ATP synthase) with substrate oxidation from the TCA cycle and fatty-acid "
        "β-oxidation. Beyond bioenergetics they regulate calcium homeostasis, apoptosis "
        "(intrinsic pathway via cytochrome c release), iron–sulfur cluster biogenesis, "
        "heme synthesis, ROS signaling and innate immunity. Mitochondria are inherited "
        "maternally and follow the endosymbiotic theory of α-proteobacterial origin."
    ),
    "what are mitochondria": "REUSE:what is mitochondria",
    "co to są mitochondria": "REUSE:what is mitochondria",
    "co to jest mitochondrium": "REUSE:what is mitochondria",
    "what is oxphos": (
        "Oxidative phosphorylation (OXPHOS) is the inner-mitochondrial-membrane process that "
        "couples electron transport through Complexes I–IV with proton pumping into the "
        "intermembrane space, generating an electrochemical gradient that drives ATP synthesis "
        "by Complex V (F1F0-ATP synthase). NADH and FADH2 from the TCA cycle and β-oxidation "
        "donate electrons; molecular oxygen is the terminal acceptor reduced to water at "
        "Complex IV. OXPHOS produces ~30–32 ATP per glucose and is the dominant source of "
        "cellular reactive oxygen species at Complex I and Complex III."
    ),
    "what is the electron transport chain": "REUSE:what is oxphos",
    "what is etc": "REUSE:what is oxphos",
    "what is mtdna": (
        "Mitochondrial DNA (mtDNA) is a circular ~16.5 kb genome present in 100–10,000 copies "
        "per cell, encoding 13 protein subunits of OXPHOS Complexes I, III, IV and V, plus 22 "
        "tRNAs and 2 rRNAs required for intramitochondrial translation. It lacks introns, has "
        "minimal repair capacity, and is inherited maternally. Pathogenic mtDNA variants cause "
        "syndromes including MELAS (m.3243A>G), LHON (m.11778G>A), MERRF, Leigh, NARP and KSS. "
        "Heteroplasmy (mix of mutant and wild-type copies) and tissue-specific thresholds "
        "determine clinical penetrance."
    ),
}


def _resolve_fundamental(query: str) -> Optional[str]:
    q = query.lower().strip().rstrip("?").rstrip(".")
    if q in FUNDAMENTALS:
        value = FUNDAMENTALS[q]
        if value.startswith("REUSE:"):
            return FUNDAMENTALS.get(value[6:])
        return value
    return None


def synthesizer_node(state: MitoRAGState) -> StateUpdate:
    """Generate a cited, substantial answer from gathered evidence."""

    with timed_node(state, "synthesizer") as update:
        answer = synthesize_answer(state)
        update["answer"] = answer
        update["citations"] = extract_citations(answer)
        update["confidence"] = confidence_from_state(state)
        return update


def synthesize_answer(state: MitoRAGState) -> str:
    retry_note = " Citation audit corrections were applied." if state.invalid_citations else ""
    topic = _detect_topic(state.query)
    fundamentals = _resolve_fundamental(state.query)

    keywords = _query_keywords(state.query)
    local_evidence = _filter_evidence(_collect_evidence(state.local_chunks, limit=12), keywords)[:8]
    web_evidence = _filter_evidence(_collect_evidence(state.web_chunks, limit=12), keywords)[:8]
    kg_summary = state.kg_subgraph.summary if state.kg_subgraph else ""

    has_local = len(local_evidence) > 0
    sufficient_local = len(local_evidence) >= 4
    primary = local_evidence if has_local else web_evidence
    secondary = web_evidence if has_local else local_evidence

    sections: List[str] = []

    if fundamentals:
        sections.append(f"**Answering: {state.query.rstrip('?').strip()}**\n\n{fundamentals}")
        if local_evidence:
            sections.append(_local_evidence_section(local_evidence))
        if web_evidence and not sufficient_local:
            sections.append(_recent_literature_section(web_evidence))
    else:
        if not primary and not state.evidence:
            return _empty_fallback(state.query, retry_note)

        sections.append(_provenance_banner(has_local, sufficient_local, len(primary)))
        sections.append(_intro_paragraph(state.query, topic, primary, secondary))

        mechanism = _mechanism_paragraph(primary, topic)
        if mechanism:
            sections.append(mechanism)

        clinical = _clinical_paragraph(primary, state.query)
        if clinical:
            sections.append(clinical)

        if not sufficient_local and web_evidence:
            sections.append(_recent_literature_section(web_evidence))

    if state.contradictions:
        sections.append(_contradictions_paragraph(state, primary))

    if kg_summary:
        sections.append(_kg_paragraph(kg_summary, primary + secondary))

    references = _references_section(primary + secondary)
    if references:
        sections.append(references)

    return "\n\n".join(s for s in sections if s).strip() + retry_note


def _provenance_banner(has_local: bool, sufficient_local: bool, primary_count: int) -> str:
    if has_local and sufficient_local:
        return (
            f"**Source: local PDF library.** {primary_count} relevant passages from your "
            "ingested papers were used. No live web search was needed."
        )
    if has_local:
        return (
            f"**Source: local PDFs + web fallback.** {primary_count} local passages found — "
            "dispatched web-search agents (PubMed, Semantic Scholar, Europe PMC, bioRxiv) "
            "to fill gaps."
        )
    return (
        "**Source: scientific web search.** No matching local PDFs — dispatched agents "
        "to PubMed, Semantic Scholar, Europe PMC and bioRxiv for the most recent literature."
    )


def _local_evidence_section(local: List[Tuple[str, str, str]]) -> str:
    bullets: List[str] = []
    for cit, _title, snippet in local[:4]:
        sent = _first_sentence(snippet)
        if not sent:
            continue
        if cit and cit not in sent:
            sent = f"{sent} {cit}"
        bullets.append(f"- {sent}.")
    if not bullets:
        return ""
    return "**From your ingested PDFs.**\n" + "\n".join(bullets)


def _query_keywords(query: str) -> List[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", query.lower())
    stop = {
        "what", "how", "why", "when", "which", "where", "who", "the", "and", "are",
        "does", "for", "from", "with", "into", "this", "that", "these", "those",
        "have", "has", "had", "you", "your", "our", "their", "can", "could",
        "would", "should", "shall", "will", "may", "might", "about", "between",
    }
    return [w for w in raw if w not in stop and len(w) > 2]


def _is_relevant(text: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    haystack = text.lower()
    if any(k in haystack for k in keywords):
        return True
    # Generic mito-related fallback so general questions still get on-topic hits.
    return any(t in haystack for t in ("mitochondri", "oxphos", "atp synthase", "etc complex"))


def _filter_evidence(
    items: List[Tuple[str, str, str]],
    keywords: List[str],
) -> List[Tuple[str, str, str]]:
    relevant = [it for it in items if _is_relevant(f"{it[1]} {it[2]}", keywords)]
    return relevant if relevant else items


def _recent_literature_section(web: List[Tuple[str, str, str]]) -> str:
    bullets: List[str] = []
    for cit, title, _snippet in web[:5]:
        if not title and not cit:
            continue
        line = f"- {title}"
        if cit and cit not in line:
            line = f"{line} {cit}"
        bullets.append(line)
    if not bullets:
        return ""
    return "**Recent peer-reviewed literature.**\n" + "\n".join(bullets)


def confidence_from_state(state: MitoRAGState) -> float:
    if state.contradictions:
        return 0.62
    if state.verified and state.citations_valid:
        return 0.86
    if state.verified:
        return 0.78
    return 0.5


# ---------- helpers ----------


def _detect_topic(query: str) -> str:
    q = query.lower()
    for needle, label in TOPIC_HINTS:
        if needle in q:
            return label
    return "this topic"


def _collect_evidence(chunks: Iterable[RankedChunk], limit: int) -> List[Tuple[str, str, str]]:
    """Return (citation, title, snippet) tuples from top ranked chunks."""
    items: List[Tuple[str, str, str]] = []
    seen_keys: set[str] = set()
    for chunk in chunks:
        doc = chunk.document
        meta = getattr(doc, "metadata", {}) or {}
        citation = (
            (meta.get("citation") if isinstance(meta, dict) else None)
            or _citation_for(doc.paper_id)
            or ""
        )
        title = (meta.get("title") if isinstance(meta, dict) else None) or _shorten(doc.text, 80)
        snippet = _shorten(doc.text, 320)
        key = citation or title
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        items.append((citation or "", title or "", snippet))
        if len(items) >= limit:
            break
    return items


def _citation_for(paper_id: str) -> Optional[str]:
    if not paper_id:
        return None
    if paper_id.startswith("PMID:"):
        return f"[{paper_id}]"
    if paper_id.startswith("10."):
        return f"[doi:{paper_id}]"
    if paper_id.isdigit():
        return f"[PMID:{paper_id}]"
    return None


def _shorten(text: str, max_chars: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rsplit(" ", 1)[0] + "…"


def _first_sentence(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    parts = SENTENCE_SPLIT_RE.split(text, maxsplit=1)
    return parts[0].rstrip(".") if parts else text


def _intro_paragraph(
    query: str,
    topic: str,
    web: List[Tuple[str, str, str]],
    local: List[Tuple[str, str, str]],
) -> str:
    leads = web[:3] or local[:3]
    if not leads:
        return f"{query.rstrip('?')}: synthesizing current literature on {topic}."
    citations = " ".join(c for c, _, _ in leads if c)
    head = (
        f"**Answering: {query.rstrip('?').strip()}**\n\n"
        f"Current peer-reviewed literature on {topic} establishes the following. "
    )
    sentences = []
    for cit, _title, snippet in leads:
        sent = _first_sentence(snippet)
        if not sent:
            continue
        if cit and cit not in sent:
            sent = f"{sent} {cit}"
        sentences.append(sent + ".")
    body = " ".join(sentences) if sentences else f"See cited references {citations}."
    return head + body


def _mechanism_paragraph(web: List[Tuple[str, str, str]], topic: str) -> str:
    candidates = [w for w in web if any(
        k in w[2].lower() for k in ("mechanism", "pathway", "complex", "subunit", "kinase", "signaling")
    )]
    if not candidates:
        return ""
    bullets: List[str] = []
    for cit, _title, snippet in candidates[:3]:
        sent = _first_sentence(snippet)
        if not sent:
            continue
        if cit and cit not in sent:
            sent = f"{sent} {cit}"
        bullets.append(f"- {sent}.")
    if not bullets:
        return ""
    return f"**Mechanistic context — {topic}.**\n" + "\n".join(bullets)


def _clinical_paragraph(web: List[Tuple[str, str, str]], query: str) -> str:
    relevant = [w for w in web if any(
        k in w[2].lower()
        for k in ("patient", "clinical", "trial", "cohort", "disease", "treatment", "therapy", "drug")
    )]
    if not relevant:
        return ""
    bullets: List[str] = []
    for cit, _title, snippet in relevant[:3]:
        sent = _first_sentence(snippet)
        if not sent:
            continue
        if cit and cit not in sent:
            sent = f"{sent} {cit}"
        bullets.append(f"- {sent}.")
    if not bullets:
        return ""
    return "**Clinical / translational evidence.**\n" + "\n".join(bullets)


def _contradictions_paragraph(state: MitoRAGState, web: List[Tuple[str, str, str]]) -> str:
    lines = ["**Open questions and contradictions.**"]
    for con in state.contradictions[:2]:
        line = f"- {con.summary or con.claim}"
        cites = [c for c, _, _ in web[:2] if c]
        if cites:
            line += " " + " ".join(cites)
        lines.append(line)
    return "\n".join(lines)


def _kg_paragraph(summary: str, evidence: List[Tuple[str, str, str]]) -> str:
    cite = next((c for c, _, _ in evidence if c), "")
    suffix = f" {cite}" if cite else ""
    return f"**Knowledge graph grounding.** {summary}{suffix}"


def _references_section(evidence: List[Tuple[str, str, str]]) -> str:
    refs: List[str] = []
    seen: set[str] = set()
    for cit, title, _ in evidence:
        if not cit or cit in seen:
            continue
        seen.add(cit)
        refs.append(f"- {cit} — {title}")
        if len(refs) >= 8:
            break
    if not refs:
        return ""
    return "**References used.**\n" + "\n".join(refs)


def _empty_fallback(query: str, retry_note: str) -> str:
    return (
        f"No retrieved evidence was available for: {query.rstrip('?')}. "
        f"Try enabling live web search (MITORAG_ENABLE_LIVE_WEB=1) and re-ingest the paper library."
        f"{retry_note}"
    )
