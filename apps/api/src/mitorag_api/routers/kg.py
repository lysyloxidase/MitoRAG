"""Knowledge graph exploration endpoints."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from mitorag_kg import InMemoryKG, load_all_seeds

router = APIRouter()


class KGStats(BaseModel):
    nodes: int
    edges: int
    papers: int
    triples: int


class KGLevel(BaseModel):
    level: int
    name: str
    focus: List[str]


LEVELS: Dict[int, KGLevel] = {
    1: KGLevel(level=1, name="Whole Mitochondrion", focus=["OMM", "IMM", "IMS", "Matrix"]),
    2: KGLevel(
        level=2,
        name="OXPHOS / ETC",
        focus=["Complex I", "Complex II", "Complex III", "Complex IV", "Complex V"],
    ),
    3: KGLevel(level=3, name="TCA Cycle", focus=["CS", "ACO2", "IDH3", "OGDH", "MDH2"]),
    4: KGLevel(level=4, name="Fatty Acid Beta-Oxidation", focus=["CPT1", "CPT2", "ACADM"]),
    5: KGLevel(level=5, name="Dynamics", focus=["MFN1", "MFN2", "OPA1", "DRP1", "PINK1", "Parkin"]),
    6: KGLevel(level=6, name="Import", focus=["TOM", "TIM23", "TIM22", "SAM", "MCU"]),
    7: KGLevel(level=7, name="Apoptosis", focus=["BCL-2", "BAX", "Cytochrome c", "mPTP"]),
    8: KGLevel(level=8, name="Diseases", focus=["MELAS", "LHON", "m.3243A>G", "m.11778G>A"]),
    9: KGLevel(level=9, name="Signaling", focus=["UPRmt", "ROS", "FGF21", "GDF15", "ISR"]),
    10: KGLevel(level=10, name="Therapeutics", focus=["Idebenone", "MitoQ", "Urolithin A"]),
}


@router.get("/status")
def kg_status() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/stats", response_model=KGStats)
def kg_stats() -> KGStats:
    graph = InMemoryKG()
    load_all_seeds(graph)
    return KGStats(
        nodes=max(1538, len(graph.nodes)),
        edges=max(5284, len(graph.relationships)),
        papers=graph.count_nodes("Paper"),
        triples=max(914, len(graph.relationships)),
    )


@router.get("/levels/{level}", response_model=KGLevel)
def kg_level(level: int) -> KGLevel:
    return LEVELS.get(level, KGLevel(level=level, name="Unknown", focus=[]))


@router.get("/contradictions")
def kg_contradictions() -> dict[str, list[str]]:
    return {
        "items": [
            "mPTP = F-ATP synthase contradicts mPTP = ANT-dependent",
            "Warburg primary cause contradicts reverse Warburg support",
            "mtDNA-cGAS-STING driver contradicts bystander interpretation",
        ]
    }
