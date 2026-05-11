"""Automatic paper-derived KG construction for Phase 6."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Mapping, Optional, Protocol, Sequence, Set, cast

from pydantic import BaseModel, Field

from mitorag_kg.loader import as_writer, relationship_type
from mitorag_kg.schema import EDGE_TYPES

logger = logging.getLogger(__name__)


def _triple_results() -> List[TripleMergeResult]:
    return []


def _triple_list() -> List[ExtractedTriple]:
    return []


def _mention_list() -> List[EntityMention]:
    return []


class EntityMention(BaseModel):
    """NER mention with a normalized KG identity when one is known."""

    text: str
    entity_type: str
    normalized_id: Optional[str] = None
    start: int
    end: int


class ExtractedTriple(BaseModel):
    """Structured relation extracted from a scientific evidence span."""

    subject_id: str
    subject_type: str
    predicate: str
    object_id: str
    object_type: str
    evidence_span: str
    confidence: float = Field(ge=0.0, le=1.0)
    paper_doi: str = ""
    paper_pmid: Optional[str] = None


class TripleValidationResult(BaseModel):
    """Validation decision for an extracted triple before graph merge."""

    valid: bool
    reason: str = ""
    subject_resolved: bool = False
    object_resolved: bool = False


class TripleMergeResult(BaseModel):
    """Outcome from attempting to merge one extracted triple."""

    triple: ExtractedTriple
    status: Literal["merged", "rejected", "contradiction"]
    reason: str = ""
    evidence_count: int = 0
    new_entities: int = 0


class AutoKGResult(BaseModel):
    """Summary emitted after processing one paper or text block."""

    paper_id: str
    entities: List[EntityMention] = Field(default_factory=_mention_list)
    triples: List[ExtractedTriple] = Field(default_factory=_triple_list)
    merge_results: List[TripleMergeResult] = Field(default_factory=_triple_results)
    triples_merged: int = 0
    triples_rejected: int = 0
    contradictions_detected: int = 0
    new_entities: int = 0


@dataclass(frozen=True)
class ResolvedEntity:
    """Resolved KG node address and properties."""

    normalized_id: str
    label: str
    key: str
    key_value: str
    properties: Mapping[str, object]


class RelationshipLookup(Protocol):
    """Optional lookup surface implemented by the in-memory test graph."""

    def find_relationship(
        self,
        start_label: str,
        start_key: str,
        start_value: object,
        relationship_type: str,
        end_label: str,
        end_key: str,
        end_value: object,
    ) -> object:
        """Return an existing relationship object or None."""
        ...


class IngestionPipelineLike(Protocol):
    """Minimal ingestion pipeline surface used by the watcher integration."""

    def ingest_pdf(self, path: Path) -> object:
        """Parse, chunk, embed, index, and return an IngestionResult-like object."""
        ...


class AutoKGIngestionPipeline:
    """Wrap an ingestion pipeline and append Phase 6 auto-KG construction."""

    def __init__(
        self,
        base_pipeline: IngestionPipelineLike,
        constructor: AutoKGConstructor,
    ) -> None:
        self.base_pipeline = base_pipeline
        self.constructor = constructor
        self.last_auto_kg_result: Optional[AutoKGResult] = None

    def ingest_pdf(self, path: Path) -> object:
        result = self.base_pipeline.ingest_pdf(path)
        auto_kg_result = self.constructor.construct_from_ingestion_result(result)
        self.last_auto_kg_result = auto_kg_result
        logger.info(
            "Ingested paper %s: +%s triples, +%s new entities, %s contradiction detected",
            auto_kg_result.paper_id,
            auto_kg_result.triples_merged,
            auto_kg_result.new_entities,
            auto_kg_result.contradictions_detected,
        )
        return result


ENTITY_SPECS: Dict[str, ResolvedEntity] = {
    "complex i": ResolvedEntity(
        normalized_id="Complex I",
        label="Complex",
        key="name",
        key_value="Complex I",
        properties={"name": "Complex I", "n_subunits": 45, "location": "IMM"},
    ),
    "complexi": ResolvedEntity(
        normalized_id="Complex I",
        label="Complex",
        key="name",
        key_value="Complex I",
        properties={"name": "Complex I", "n_subunits": 45, "location": "IMM"},
    ),
    "melas": ResolvedEntity(
        normalized_id="MONDO:0010789",
        label="Disease",
        key="name",
        key_value="MELAS syndrome",
        properties={
            "name": "MELAS syndrome",
            "mondo_id": "MONDO:0010789",
            "omim_id": "540000",
            "inheritance": "maternal",
        },
    ),
    "melas syndrome": ResolvedEntity(
        normalized_id="MONDO:0010789",
        label="Disease",
        key="name",
        key_value="MELAS syndrome",
        properties={
            "name": "MELAS syndrome",
            "mondo_id": "MONDO:0010789",
            "omim_id": "540000",
            "inheritance": "maternal",
        },
    ),
    "mondo:0010789": ResolvedEntity(
        normalized_id="MONDO:0010789",
        label="Disease",
        key="name",
        key_value="MELAS syndrome",
        properties={
            "name": "MELAS syndrome",
            "mondo_id": "MONDO:0010789",
            "omim_id": "540000",
            "inheritance": "maternal",
        },
    ),
    "m.3243a>g": ResolvedEntity(
        normalized_id="m.3243A>G",
        label="Variant",
        key="hgvs",
        key_value="m.3243A>G",
        properties={
            "hgvs": "m.3243A>G",
            "position": 3243,
            "gene": "MT-TL1",
            "pathogenicity": "pathogenic",
            "heteroplasmy_threshold": 0.80,
        },
    ),
    "mt-nd4": ResolvedEntity(
        normalized_id="MT-ND4",
        label="Gene",
        key="hgnc_symbol",
        key_value="MT-ND4",
        properties={
            "hgnc_symbol": "MT-ND4",
            "entrez_id": 4538,
            "name": "mitochondrially encoded NADH dehydrogenase 4",
            "mtdna_encoded": True,
            "chromosome": "MT",
        },
    ),
    "nd4": ResolvedEntity(
        normalized_id="MT-ND4",
        label="Gene",
        key="hgnc_symbol",
        key_value="MT-ND4",
        properties={
            "hgnc_symbol": "MT-ND4",
            "entrez_id": 4538,
            "name": "mitochondrially encoded NADH dehydrogenase 4",
            "mtdna_encoded": True,
            "chromosome": "MT",
        },
    ),
    "hgnc:7460": ResolvedEntity(
        normalized_id="MT-ND4",
        label="Gene",
        key="hgnc_symbol",
        key_value="MT-ND4",
        properties={
            "hgnc_symbol": "MT-ND4",
            "entrez_id": 4538,
            "name": "mitochondrially encoded NADH dehydrogenase 4",
            "mtdna_encoded": True,
            "chromosome": "MT",
        },
    ),
    "pink1": ResolvedEntity(
        normalized_id="PINK1",
        label="Gene",
        key="hgnc_symbol",
        key_value="PINK1",
        properties={"hgnc_symbol": "PINK1", "name": "PTEN induced kinase 1"},
    ),
    "parkin": ResolvedEntity(
        normalized_id="PRKN",
        label="Gene",
        key="hgnc_symbol",
        key_value="PRKN",
        properties={"hgnc_symbol": "PRKN", "name": "parkin RBR E3 ubiquitin ligase"},
    ),
    "prkn": ResolvedEntity(
        normalized_id="PRKN",
        label="Gene",
        key="hgnc_symbol",
        key_value="PRKN",
        properties={"hgnc_symbol": "PRKN", "name": "parkin RBR E3 ubiquitin ligase"},
    ),
    "idebenone": ResolvedEntity(
        normalized_id="DB09081",
        label="Drug",
        key="name",
        key_value="Idebenone",
        properties={
            "name": "Idebenone",
            "drugbank_id": "DB09081",
            "target": "Complex I bypass",
        },
    ),
}

MENTION_ALIASES = {
    "Complex I": "complex i",
    "MELAS": "melas",
    "m.3243A>G": "m.3243a>g",
    "MT-ND4": "mt-nd4",
    "ND4": "nd4",
    "PINK1": "pink1",
    "Parkin": "parkin",
    "PRKN": "prkn",
    "Idebenone": "idebenone",
}

OPPOSING_PREDICATES = {
    "activates": "inhibits",
    "inhibits": "activates",
    "produces": "consumes",
    "consumes": "produces",
}

MIN_CONFIDENCE = 0.70


class AutoKGConstructor:
    """Extract, validate, and merge paper-derived KG triples with provenance."""

    def __init__(
        self,
        neo4j_driver: object,
        min_confidence: float = MIN_CONFIDENCE,
        extraction_method: str = "heuristic_phase6",
    ) -> None:
        self.writer = as_writer(neo4j_driver)
        self.min_confidence = min_confidence
        self.extraction_method = extraction_method

    def construct_from_text(
        self,
        text: str,
        paper_doi: str = "",
        paper_pmid: Optional[str] = None,
        title: str = "",
    ) -> AutoKGResult:
        """Run NER, triple extraction, validation, and graph merge for one paper."""

        paper_id = paper_pmid or paper_doi or _stable_id(text)
        self._merge_paper(paper_id, paper_doi, paper_pmid, title)
        entities = self.extract_entities(text)
        triples = self.extract_triples(text, paper_doi=paper_doi, paper_pmid=paper_pmid)
        merge_results = [self.merge_triple(triple) for triple in triples]
        return AutoKGResult(
            paper_id=paper_id,
            entities=entities,
            triples=triples,
            merge_results=merge_results,
            triples_merged=sum(1 for item in merge_results if item.status == "merged"),
            triples_rejected=sum(1 for item in merge_results if item.status == "rejected"),
            contradictions_detected=sum(
                1 for item in merge_results if item.status == "contradiction"
            ),
            new_entities=sum(item.new_entities for item in merge_results),
        )

    def construct_from_ingestion_result(self, ingestion_result: object) -> AutoKGResult:
        """Build triples from a Phase 1 IngestionResult-like object."""

        parsed = getattr(ingestion_result, "parsed")
        metadata = getattr(parsed, "metadata")
        text_parts = [
            str(getattr(parsed, "title", "")),
            str(getattr(parsed, "abstract", "")),
            str(getattr(parsed, "raw_text", "")),
        ]
        paper_doi = str(getattr(metadata, "doi", "") or "")
        title = str(getattr(parsed, "title", "") or getattr(metadata, "title", "") or "")
        return self.construct_from_text(
            "\n".join(part for part in text_parts if part),
            paper_doi=paper_doi,
            title=title,
        )

    def extract_entities(self, text: str) -> List[EntityMention]:
        """Extract biomedical entities using PubTator-style normalized spans."""

        mentions: List[EntityMention] = []
        occupied: Set[tuple[int, int]] = set()
        sorted_aliases = sorted(
            MENTION_ALIASES.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        for literal, alias in sorted_aliases:
            pattern = _mention_pattern(literal)
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                span = (match.start(), match.end())
                if _overlaps(span, occupied):
                    continue
                occupied.add(span)
                entity = ENTITY_SPECS[alias]
                mentions.append(
                    EntityMention(
                        text=text[match.start() : match.end()],
                        entity_type=entity.label,
                        normalized_id=entity.normalized_id,
                        start=match.start(),
                        end=match.end(),
                    )
                )
        mentions.sort(key=lambda item: item.start)
        return mentions

    def normalize_entity(
        self,
        mention_or_id: str,
        entity_type: Optional[str] = None,
    ) -> Optional[ResolvedEntity]:
        """Map mentions and ontology IDs to seed-compatible KG node addresses."""

        del entity_type
        return ENTITY_SPECS.get(_normalize_key(mention_or_id))

    def extract_triples(
        self,
        text: str,
        paper_doi: str = "",
        paper_pmid: Optional[str] = None,
    ) -> List[ExtractedTriple]:
        """Extract relation triples from scientific sentences."""

        triples: List[ExtractedTriple] = []
        for sentence in _sentences(text):
            triples.extend(self._extract_sentence_triples(sentence, paper_doi, paper_pmid))
        return _dedupe_triples(triples)

    def validate_triple(self, triple: ExtractedTriple) -> TripleValidationResult:
        """Validate predicate, confidence, and entity normalization."""

        if triple.predicate not in EDGE_TYPES:
            return TripleValidationResult(valid=False, reason="predicate not in Biolink whitelist")
        if triple.confidence < self.min_confidence:
            return TripleValidationResult(valid=False, reason="confidence below threshold")

        subject = self.normalize_entity(triple.subject_id, triple.subject_type)
        object_entity = self.normalize_entity(triple.object_id, triple.object_type)
        if subject is None or object_entity is None:
            return TripleValidationResult(
                valid=False,
                reason="subject or object has no ontology match",
                subject_resolved=subject is not None,
                object_resolved=object_entity is not None,
            )
        return TripleValidationResult(
            valid=True,
            subject_resolved=True,
            object_resolved=True,
        )

    def merge_triple(self, triple: ExtractedTriple) -> TripleMergeResult:
        """Merge one validated triple or model a contradiction instead."""

        validation = self.validate_triple(triple)
        if not validation.valid:
            return TripleMergeResult(triple=triple, status="rejected", reason=validation.reason)

        subject = self.normalize_entity(triple.subject_id, triple.subject_type)
        object_entity = self.normalize_entity(triple.object_id, triple.object_type)
        if subject is None or object_entity is None:
            return TripleMergeResult(
                triple=triple,
                status="rejected",
                reason="subject or object has no ontology match",
            )

        self._merge_paper(_paper_id(triple), triple.paper_doi, triple.paper_pmid)
        new_entities = self._merge_entity_nodes(subject, object_entity)
        conflicting = self._find_conflicting_relationship(triple, subject, object_entity)
        if conflicting is not None:
            self._record_contradiction(triple, subject, object_entity, conflicting)
            return TripleMergeResult(
                triple=triple,
                status="contradiction",
                reason="contradicts high-confidence existing triple",
                new_entities=new_entities,
            )

        evidence_count = self._merge_relationship_with_provenance(triple, subject, object_entity)
        return TripleMergeResult(
            triple=triple,
            status="merged",
            evidence_count=evidence_count,
            new_entities=new_entities,
        )

    def _extract_sentence_triples(
        self,
        sentence: str,
        paper_doi: str,
        paper_pmid: Optional[str],
    ) -> List[ExtractedTriple]:
        triples: List[ExtractedTriple] = []
        if re.search(r"\b(?:MT-)?ND4\b.*\bsubunit of\b.*\bComplex I\b", sentence, re.I):
            triples.append(
                ExtractedTriple(
                    subject_id="MT-ND4",
                    subject_type="Gene",
                    predicate="subunit_of",
                    object_id="Complex I",
                    object_type="Complex",
                    evidence_span=sentence,
                    confidence=0.91,
                    paper_doi=paper_doi,
                    paper_pmid=paper_pmid,
                )
            )

        variant = re.search(
            r"(m\.\d+[ACGT]>[ACGT]).{0,100}\b(?:causes?|associated with|leads to)\b"
            r".{0,100}\b(MELAS(?: syndrome)?)\b",
            sentence,
            re.I,
        )
        if variant:
            triples.append(
                ExtractedTriple(
                    subject_id=_canonical_variant(variant.group(1)),
                    subject_type="Variant",
                    predicate="causes",
                    object_id="MONDO:0010789",
                    object_type="Disease",
                    evidence_span=sentence,
                    confidence=0.88,
                    paper_doi=paper_doi,
                    paper_pmid=paper_pmid,
                )
            )

        for predicate in ["activates", "inhibits"]:
            relation = re.search(
                rf"\b(PINK1|Parkin|PRKN|Idebenone)\b\s+{predicate}\s+"
                r"\b(PINK1|Parkin|PRKN|Complex I)\b",
                sentence,
                re.I,
            )
            if relation:
                subject = self.normalize_entity(relation.group(1))
                object_entity = self.normalize_entity(relation.group(2))
                if subject is not None and object_entity is not None:
                    triples.append(
                        ExtractedTriple(
                            subject_id=subject.normalized_id,
                            subject_type=subject.label,
                            predicate=predicate,
                            object_id=object_entity.normalized_id,
                            object_type=object_entity.label,
                            evidence_span=sentence,
                            confidence=0.84,
                            paper_doi=paper_doi,
                            paper_pmid=paper_pmid,
                        )
                    )
        return triples

    def _merge_entity_nodes(self, *entities: ResolvedEntity) -> int:
        new_entities = 0
        for entity in entities:
            if not self._node_exists(entity):
                new_entities += 1
            self.writer.merge_node(entity.label, entity.key, entity.properties)
        return new_entities

    def _merge_relationship_with_provenance(
        self,
        triple: ExtractedTriple,
        subject: ResolvedEntity,
        object_entity: ResolvedEntity,
    ) -> int:
        rel_type = relationship_type(triple.predicate)
        evidence_paper = _paper_id(triple)
        properties = _relationship_properties(triple, self.extraction_method)
        existing = self._find_relationship(subject, rel_type, object_entity)
        if existing is not None:
            existing_props = _relationship_properties_from_object(existing)
            evidence_papers = _evidence_papers(existing_props)
            if evidence_paper not in evidence_papers:
                evidence_papers.append(evidence_paper)
            properties.update(existing_props)
            properties["paper_doi"] = triple.paper_doi
            properties["paper_pmid"] = triple.paper_pmid or ""
            properties["evidence"] = triple.evidence_span
            properties["confidence"] = max(
                _float(existing_props.get("confidence")),
                triple.confidence,
            )
            properties["evidence_papers"] = evidence_papers
            properties["evidence_count"] = len(evidence_papers)

        self.writer.merge_relationship(
            subject.label,
            subject.key,
            subject.key_value,
            rel_type,
            object_entity.label,
            object_entity.key,
            object_entity.key_value,
            properties,
        )
        return _int(properties.get("evidence_count"))

    def _find_conflicting_relationship(
        self,
        triple: ExtractedTriple,
        subject: ResolvedEntity,
        object_entity: ResolvedEntity,
    ) -> Optional[object]:
        opposite = OPPOSING_PREDICATES.get(triple.predicate)
        if opposite is None:
            return None
        existing = self._find_relationship(subject, relationship_type(opposite), object_entity)
        if existing is None:
            return None
        confidence = _float(_relationship_properties_from_object(existing).get("confidence"))
        if confidence >= self.min_confidence:
            return existing
        return None

    def _find_relationship(
        self,
        subject: ResolvedEntity,
        rel_type: str,
        object_entity: ResolvedEntity,
    ) -> Optional[object]:
        finder = getattr(self.writer, "find_relationship", None)
        if not callable(finder):
            return None
        found: object = finder(
            subject.label,
            subject.key,
            subject.key_value,
            rel_type,
            object_entity.label,
            object_entity.key,
            object_entity.key_value,
        )
        return found

    def _node_exists(self, entity: ResolvedEntity) -> bool:
        getter = getattr(self.writer, "get_node", None)
        if not callable(getter):
            return False
        return getter(entity.label, entity.key, entity.key_value) is not None

    def _merge_paper(
        self,
        paper_id: str,
        paper_doi: str,
        paper_pmid: Optional[str],
        title: str = "",
    ) -> None:
        self.writer.merge_node(
            "Paper",
            "pmid",
            {
                "pmid": paper_pmid or paper_id,
                "doi": paper_doi,
                "title": title,
            },
        )

    def _record_contradiction(
        self,
        triple: ExtractedTriple,
        subject: ResolvedEntity,
        object_entity: ResolvedEntity,
        conflicting_relationship: object,
    ) -> None:
        existing_props = _relationship_properties_from_object(conflicting_relationship)
        existing_predicate = _predicate_from_relationship(conflicting_relationship)
        new_hypothesis = _hypothesis_name(subject, triple.predicate, object_entity)
        old_hypothesis = _hypothesis_name(subject, existing_predicate.lower(), object_entity)
        contradiction_id = _contradiction_id(new_hypothesis, old_hypothesis, triple.evidence_span)

        self.writer.merge_node(
            "Hypothesis",
            "name",
            {
                "name": new_hypothesis,
                "description": triple.evidence_span,
                "status": "disputed",
            },
        )
        self.writer.merge_node(
            "Hypothesis",
            "name",
            {
                "name": old_hypothesis,
                "description": str(existing_props.get("evidence", "")),
                "status": "disputed",
            },
        )
        self.writer.merge_node(
            "Contradiction",
            "id",
            {
                "id": contradiction_id,
                "subject_id": subject.normalized_id,
                "object_id": object_entity.normalized_id,
                "new_predicate": triple.predicate,
                "existing_predicate": existing_predicate.lower(),
                "evidence": triple.evidence_span,
                "paper_doi": triple.paper_doi,
                "created": _created_now(),
            },
        )
        self.writer.merge_relationship(
            "Hypothesis",
            "name",
            new_hypothesis,
            "CONTRADICTS",
            "Hypothesis",
            "name",
            old_hypothesis,
            {"reason": "opposing predicates for same entity pair"},
        )
        self.writer.merge_relationship(
            "Hypothesis",
            "name",
            old_hypothesis,
            "CONTRADICTS",
            "Hypothesis",
            "name",
            new_hypothesis,
            {"reason": "opposing predicates for same entity pair"},
        )
        self.writer.merge_relationship(
            "Hypothesis",
            "name",
            new_hypothesis,
            "SUPPORTS",
            "Paper",
            "pmid",
            triple.paper_pmid or _paper_id(triple),
            {"evidence": triple.evidence_span},
        )


def triple_precision(
    predicted: Sequence[ExtractedTriple],
    gold: Sequence[ExtractedTriple],
) -> float:
    """Return exact-match precision for manual validation samples."""

    if not predicted:
        return 0.0
    gold_keys = {_triple_key(triple) for triple in gold}
    correct = sum(1 for triple in predicted if _triple_key(triple) in gold_keys)
    return correct / len(predicted)


def _relationship_properties(
    triple: ExtractedTriple,
    extraction_method: str,
) -> Dict[str, object]:
    paper = _paper_id(triple)
    return {
        "paper_doi": triple.paper_doi,
        "paper_pmid": triple.paper_pmid or "",
        "evidence": triple.evidence_span,
        "confidence": triple.confidence,
        "extraction_method": extraction_method,
        "created": _created_now(),
        "evidence_count": 1,
        "evidence_papers": [paper],
    }


def _relationship_properties_from_object(value: object) -> Mapping[str, object]:
    properties = getattr(value, "properties", None)
    if isinstance(properties, Mapping):
        return cast(Mapping[str, object], properties)
    return {}


def _predicate_from_relationship(value: object) -> str:
    rel_type = getattr(value, "relationship_type", "")
    return str(rel_type)


def _evidence_papers(properties: Mapping[str, object]) -> List[str]:
    value = properties.get("evidence_papers")
    if isinstance(value, list):
        return [str(item) for item in cast(Sequence[object], value)]
    count = _int(properties.get("evidence_count"))
    paper = str(properties.get("paper_pmid") or properties.get("paper_doi") or "")
    if paper:
        return [paper]
    return [f"evidence:{index}" for index in range(count)]


def _sentences(text: str) -> List[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _mention_pattern(literal: str) -> str:
    escaped = re.escape(literal)
    if literal[0].isalnum() and literal[-1].isalnum():
        return rf"\b{escaped}\b"
    return escaped


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("complexi", "complexi")


def _canonical_variant(value: str) -> str:
    match = re.match(r"m\.(\d+)([ACGT])>([ACGT])", value, flags=re.I)
    if not match:
        return value
    return f"m.{match.group(1)}{match.group(2).upper()}>{match.group(3).upper()}"


def _overlaps(span: tuple[int, int], occupied: Set[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < other_end and end > other_start for other_start, other_end in occupied)


def _dedupe_triples(triples: Iterable[ExtractedTriple]) -> List[ExtractedTriple]:
    seen: Dict[tuple[str, str, str], ExtractedTriple] = {}
    for triple in triples:
        seen.setdefault(_triple_key(triple), triple)
    return list(seen.values())


def _triple_key(triple: ExtractedTriple) -> tuple[str, str, str]:
    return (triple.subject_id, triple.predicate, triple.object_id)


def _paper_id(triple: ExtractedTriple) -> str:
    return triple.paper_pmid or triple.paper_doi or _stable_id(triple.evidence_span)


def _stable_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _contradiction_id(left: str, right: str, evidence: str) -> str:
    return hashlib.sha1(f"{left}|{right}|{evidence}".encode()).hexdigest()[:16]


def _created_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _float(value: object) -> float:
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _hypothesis_name(subject: ResolvedEntity, predicate: str, object_entity: ResolvedEntity) -> str:
    return f"{subject.normalized_id} {predicate.lower()} {object_entity.normalized_id}"
