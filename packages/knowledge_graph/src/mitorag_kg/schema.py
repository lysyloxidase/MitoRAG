"""Node and edge type definitions for the mitochondrial knowledge graph."""

from __future__ import annotations

from typing import Dict, List, Mapping

from mitorag_kg.loader import GraphWriter, relationship_type

SUBMITO_COMPARTMENTS = ["matrix", "IMM", "IMS", "OMM"]

NODE_TYPES: Dict[str, Mapping[str, object]] = {
    "Gene": {
        "properties": [
            "hgnc_symbol",
            "entrez_id",
            "ensembl_id",
            "name",
            "mtdna_encoded",
            "chromosome",
        ],
        "example": "Gene(hgnc_symbol='MT-ND4', entrez_id=4538, mtdna_encoded=True)",
    },
    "Protein": {
        "properties": ["uniprot_id", "name", "mass_kda", "length_aa", "sub_mito_location"],
        "example": "Protein(uniprot_id='P03905', name='NADH-ubiquinone oxidoreductase chain 4')",
    },
    "Complex": {
        "properties": ["name", "n_subunits", "mass_kda", "location"],
        "example": "Complex(name='Complex I', n_subunits=45, mass_kda=1000)",
    },
    "Pathway": {
        "properties": ["reactome_id", "kegg_id", "mitocarta_pathway", "name", "category"],
        "example": "Pathway(name='Oxidative phosphorylation', kegg_id='hsa00190')",
    },
    "Metabolite": {
        "properties": ["chebi_id", "name", "formula", "mass_da"],
        "example": "Metabolite(chebi_id='CHEBI:15846', name='NAD+')",
    },
    "Reaction": {
        "properties": ["rhea_id", "reactome_id", "name", "ec_number"],
    },
    "Disease": {
        "properties": ["mondo_id", "omim_id", "name", "inheritance"],
        "example": "Disease(omim_id='540000', name='MELAS syndrome')",
    },
    "Variant": {
        "properties": ["hgvs", "position", "gene", "pathogenicity", "heteroplasmy_threshold"],
        "example": "Variant(hgvs='m.3243A>G', gene='MT-TL1', pathogenicity='pathogenic')",
    },
    "Drug": {
        "properties": ["drugbank_id", "name", "mechanism", "target", "clinical_status"],
        "example": (
            "Drug(name='Idebenone', target='Complex I bypass', "
            "clinical_status='EMA-approved')"
        ),
    },
    "Phenotype": {
        "properties": ["hpo_id", "name"],
        "example": "Phenotype(hpo_id='HP:0003200', name='Ragged-red fibers')",
    },
    "SubMitoCompartment": {
        "values": SUBMITO_COMPARTMENTS,
    },
    "Paper": {
        "properties": ["doi", "pmid", "title", "year", "journal", "authors"],
    },
    "Claim": {
        "properties": ["text", "confidence", "extraction_method"],
    },
    "Contradiction": {
        "properties": [
            "id",
            "subject_id",
            "object_id",
            "new_predicate",
            "existing_predicate",
            "evidence",
            "paper_doi",
        ],
    },
    "Hypothesis": {
        "properties": ["name", "description", "status"],
    },
}

EDGE_TYPES = [
    "encoded_by",
    "localizes_to",
    "part_of",
    "subunit_of",
    "participates_in",
    "catalyzes",
    "produces",
    "consumes",
    "regulates",
    "activates",
    "inhibits",
    "interacts_with",
    "causes",
    "treats",
    "associated_with",
    "mutated_in",
    "cited_by",
    "contradicts",
    "supports",
]

EDGE_LABELS = {edge: relationship_type(edge) for edge in EDGE_TYPES}

UNIQUE_CONSTRAINTS = {
    "Gene": "hgnc_symbol",
    "Protein": "uniprot_id",
    "Complex": "name",
    "Pathway": "name",
    "Metabolite": "chebi_id",
    "Reaction": "name",
    "Disease": "name",
    "Variant": "hgvs",
    "Drug": "name",
    "Phenotype": "hpo_id",
    "SubMitoCompartment": "name",
    "Paper": "pmid",
    "Claim": "text",
    "Contradiction": "id",
    "Hypothesis": "name",
}


def constraint_queries() -> List[str]:
    """Return idempotent Neo4j uniqueness constraints for the schema."""

    queries: List[str] = []
    for label, key in UNIQUE_CONSTRAINTS.items():
        queries.append(
            f"CREATE CONSTRAINT mitorag_{label.lower()}_{key} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
        )
    return queries


def ensure_schema(writer: GraphWriter) -> None:
    """Seed static compartment nodes required by multiple loaders."""

    for compartment in SUBMITO_COMPARTMENTS:
        writer.merge_node(
            "SubMitoCompartment",
            "name",
            {
                "name": str(compartment),
                "kind": "sub_mitochondrial_compartment",
            },
        )
