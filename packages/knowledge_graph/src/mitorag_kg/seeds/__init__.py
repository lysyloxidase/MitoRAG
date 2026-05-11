"""Seed loaders for the MitoRAG knowledge graph."""

from mitorag_kg.seeds.chebi import ChEBILoader
from mitorag_kg.seeds.gene_ontology import GeneOntologyLoader
from mitorag_kg.seeds.hpo_mondo import HPOMONDOLoader
from mitorag_kg.seeds.hypotheses import HypothesisLoader
from mitorag_kg.seeds.kegg import KEGGLoader
from mitorag_kg.seeds.mitocarta import MitoCartaLoader
from mitorag_kg.seeds.mitomap import MITOMAPLoader
from mitorag_kg.seeds.reactome import ReactomeLoader
from mitorag_kg.seeds.therapeutics import TherapeuticsLoader

DEFAULT_LOADERS = [
    GeneOntologyLoader,
    MitoCartaLoader,
    ReactomeLoader,
    KEGGLoader,
    ChEBILoader,
    MITOMAPLoader,
    HPOMONDOLoader,
    TherapeuticsLoader,
    HypothesisLoader,
]

__all__ = [
    "DEFAULT_LOADERS",
    "ChEBILoader",
    "GeneOntologyLoader",
    "HPOMONDOLoader",
    "HypothesisLoader",
    "KEGGLoader",
    "MITOMAPLoader",
    "MitoCartaLoader",
    "ReactomeLoader",
    "TherapeuticsLoader",
    "load_all_seeds",
]


def load_all_seeds(neo4j_driver: object) -> list[object]:
    """Load all Phase 3 seed sources in dependency order."""

    return [loader_cls().load(neo4j_driver) for loader_cls in DEFAULT_LOADERS]
