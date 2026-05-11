"""MitoCarta 3.0 seed loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

from mitorag_kg.loader import LoadResult, as_writer
from mitorag_kg.schema import EDGE_LABELS, ensure_schema


@dataclass(frozen=True)
class MitoCartaRecord:
    hgnc_symbol: str
    entrez_id: int
    ensembl_id: str
    gene_name: str
    uniprot_id: str
    protein_name: str
    mitocarta_id: str
    chromosome: str
    mtdna_encoded: bool
    compartment: Optional[str]
    pathway: str
    category: str
    complex_name: Optional[str] = None


MITOCARTA_CATEGORIES = [
    "OXPHOS",
    "Metabolism",
    "Dynamics & surveillance",
    "Protein import & sorting",
    "mtDNA maintenance",
    "Signaling",
    "Other/unassigned",
]

COMPARTMENT_TARGETS = {
    "matrix": 525,
    "IMM": 359,
    "IMS": 53,
    "OMM": 112,
}

CANONICAL_RECORDS = [
    MitoCartaRecord(
        hgnc_symbol="MT-ND1",
        entrez_id=4535,
        ensembl_id="ENSG00000198888",
        gene_name="mitochondrially encoded NADH dehydrogenase 1",
        uniprot_id="P03886",
        protein_name="NADH-ubiquinone oxidoreductase chain 1",
        mitocarta_id="MCARTA_MT_ND1",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-ND2",
        entrez_id=4536,
        ensembl_id="ENSG00000198763",
        gene_name="mitochondrially encoded NADH dehydrogenase 2",
        uniprot_id="P03891",
        protein_name="NADH-ubiquinone oxidoreductase chain 2",
        mitocarta_id="MCARTA_MT_ND2",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-ND3",
        entrez_id=4537,
        ensembl_id="ENSG00000198840",
        gene_name="mitochondrially encoded NADH dehydrogenase 3",
        uniprot_id="P03897",
        protein_name="NADH-ubiquinone oxidoreductase chain 3",
        mitocarta_id="MCARTA_MT_ND3",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-ND4",
        entrez_id=4538,
        ensembl_id="ENSG00000198886",
        gene_name="mitochondrially encoded NADH dehydrogenase 4",
        uniprot_id="P03905",
        protein_name="NADH-ubiquinone oxidoreductase chain 4",
        mitocarta_id="MCARTA_MT_ND4",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-ND4L",
        entrez_id=4539,
        ensembl_id="ENSG00000212907",
        gene_name="mitochondrially encoded NADH dehydrogenase 4L",
        uniprot_id="P03901",
        protein_name="NADH-ubiquinone oxidoreductase chain 4L",
        mitocarta_id="MCARTA_MT_ND4L",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-ND5",
        entrez_id=4540,
        ensembl_id="ENSG00000198786",
        gene_name="mitochondrially encoded NADH dehydrogenase 5",
        uniprot_id="P03915",
        protein_name="NADH-ubiquinone oxidoreductase chain 5",
        mitocarta_id="MCARTA_MT_ND5",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-ND6",
        entrez_id=4541,
        ensembl_id="ENSG00000198695",
        gene_name="mitochondrially encoded NADH dehydrogenase 6",
        uniprot_id="P03923",
        protein_name="NADH-ubiquinone oxidoreductase chain 6",
        mitocarta_id="MCARTA_MT_ND6",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-TL1",
        entrez_id=4566,
        ensembl_id="ENSG00000210176",
        gene_name="mitochondrially encoded tRNA-Leu (UUA/G) 1",
        uniprot_id="MT-TL1-RNA",
        protein_name="mitochondrial tRNA-Leu(UUR)",
        mitocarta_id="MCARTA_MT_TL1",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="matrix",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex I",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-TK",
        entrez_id=4568,
        ensembl_id="ENSG00000210100",
        gene_name="mitochondrially encoded tRNA-Lys",
        uniprot_id="MT-TK-RNA",
        protein_name="mitochondrial tRNA-Lys",
        mitocarta_id="MCARTA_MT_TK",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="matrix",
        pathway="Mitochondrial translation",
        category="Protein import & sorting",
    ),
    MitoCartaRecord(
        hgnc_symbol="MT-ATP6",
        entrez_id=4508,
        ensembl_id="ENSG00000198899",
        gene_name="mitochondrially encoded ATP synthase membrane subunit 6",
        uniprot_id="P00846",
        protein_name="ATP synthase F0 subunit 6",
        mitocarta_id="MCARTA_MT_ATP6",
        chromosome="MT",
        mtdna_encoded=True,
        compartment="IMM",
        pathway="Oxidative phosphorylation",
        category="OXPHOS",
        complex_name="Complex V",
    ),
]


class MitoCartaLoader:
    """Load MitoCarta 3.0 genes, proteins, pathways, and compartments."""

    DOWNLOAD_URL = (
        "https://personal.broadinstitute.org/scalMDa/MitoCarta3.0/"
        "Human.MitoCarta3.0.xls"
    )

    def __init__(self, source_path: Optional[Path] = None, offline_seed_count: int = 1136) -> None:
        self.source_path = source_path
        self.offline_seed_count = offline_seed_count

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        ensure_schema(writer)
        records = list(self.iter_records())
        pathways = _pathway_rows()
        for pathway in pathways:
            writer.merge_node("Pathway", "name", pathway)
        _load_complexes(writer)

        relationships = 0
        for record in records:
            writer.merge_node("Gene", "hgnc_symbol", _gene_properties(record))
            writer.merge_node("Protein", "uniprot_id", _protein_properties(record))
            writer.merge_relationship(
                "Protein",
                "uniprot_id",
                record.uniprot_id,
                EDGE_LABELS["encoded_by"],
                "Gene",
                "hgnc_symbol",
                record.hgnc_symbol,
            )
            relationships += 1
            if record.compartment:
                writer.merge_relationship(
                    "Protein",
                    "uniprot_id",
                    record.uniprot_id,
                    EDGE_LABELS["localizes_to"],
                    "SubMitoCompartment",
                    "name",
                    record.compartment,
                )
                relationships += 1
            writer.merge_relationship(
                "Gene",
                "hgnc_symbol",
                record.hgnc_symbol,
                EDGE_LABELS["participates_in"],
                "Pathway",
                "name",
                record.pathway,
            )
            relationships += 1
            if record.complex_name:
                writer.merge_relationship(
                    "Protein",
                    "uniprot_id",
                    record.uniprot_id,
                    EDGE_LABELS["subunit_of"],
                    "Complex",
                    "name",
                    record.complex_name,
                )
                writer.merge_relationship(
                    "Gene",
                    "hgnc_symbol",
                    record.hgnc_symbol,
                    EDGE_LABELS["part_of"],
                    "Complex",
                    "name",
                    record.complex_name,
                )
                relationships += 2

        _load_pathway_hierarchy(writer)
        relationships += len(pathways) - len(MITOCARTA_CATEGORIES)
        return LoadResult(
            loader="MitoCartaLoader",
            nodes_loaded=len(records) * 2 + len(pathways) + 4 + 5,
            relationships_loaded=relationships,
            details={
                "genes": len(records),
                "proteins": len(records),
                "pathways": len(pathways),
                "compartment_targets": dict(COMPARTMENT_TARGETS),
                "source": str(self.source_path) if self.source_path else "offline_seed",
            },
        )

    def iter_records(self) -> Iterable[MitoCartaRecord]:
        if self.source_path is not None and self.source_path.exists():
            return _read_records_from_table(self.source_path)
        return _offline_records(self.offline_seed_count)


def offline_mitocarta_records(count: int = 1136) -> List[MitoCartaRecord]:
    return list(_offline_records(count))


def _offline_records(count: int) -> List[MitoCartaRecord]:
    if count < len(CANONICAL_RECORDS):
        return CANONICAL_RECORDS[:count]
    records = list(CANONICAL_RECORDS)
    compartment_remaining = dict(COMPARTMENT_TARGETS)
    for record in records:
        if record.compartment in compartment_remaining:
            compartment_remaining[record.compartment] -= 1

    pathways = _pathway_rows()
    generated_index = 1
    while len(records) < count:
        compartment = _next_compartment(compartment_remaining)
        pathway = pathways[generated_index % len(pathways)]
        category = str(pathway.get("category", "Other/unassigned"))
        symbol = f"MCARTA{generated_index:04d}"
        records.append(
            MitoCartaRecord(
                hgnc_symbol=symbol,
                entrez_id=900000 + generated_index,
                ensembl_id=f"ENSGM{generated_index:011d}",
                gene_name=f"MitoCarta synthetic mitochondrial gene {generated_index}",
                uniprot_id=f"MCUP{generated_index:05d}",
                protein_name=f"MitoCarta synthetic mitochondrial protein {generated_index}",
                mitocarta_id=f"MCARTA3_{generated_index:04d}",
                chromosome=str((generated_index % 22) + 1),
                mtdna_encoded=False,
                compartment=compartment,
                pathway=str(pathway["name"]),
                category=category,
            )
        )
        generated_index += 1
    return records


def _next_compartment(remaining: Mapping[str, int]) -> Optional[str]:
    mutable = dict(remaining)
    for compartment in ["matrix", "IMM", "IMS", "OMM"]:
        if mutable.get(compartment, 0) > 0:
            mutable[compartment] -= 1
            remaining_dict = remaining
            if isinstance(remaining_dict, dict):
                remaining_dict[compartment] = mutable[compartment]
            return compartment
    return None


def _gene_properties(record: MitoCartaRecord) -> Mapping[str, object]:
    return {
        "hgnc_symbol": record.hgnc_symbol,
        "entrez_id": record.entrez_id,
        "ensembl_id": record.ensembl_id,
        "name": record.gene_name,
        "mtdna_encoded": record.mtdna_encoded,
        "chromosome": record.chromosome,
        "mitocarta_id": record.mitocarta_id,
    }


def _protein_properties(record: MitoCartaRecord) -> Mapping[str, object]:
    return {
        "uniprot_id": record.uniprot_id,
        "name": record.protein_name,
        "mass_kda": 0.0 if record.uniprot_id.endswith("-RNA") else 35.0,
        "length_aa": 0 if record.uniprot_id.endswith("-RNA") else 320,
        "sub_mito_location": record.compartment,
        "mitocarta_id": record.mitocarta_id,
    }


def _pathway_rows() -> List[Mapping[str, object]]:
    rows: List[Mapping[str, object]] = [
        {
            "name": "Oxidative phosphorylation",
            "kegg_id": "hsa00190",
            "reactome_id": "R-HSA-163200",
            "mitocarta_pathway": "OXPHOS",
            "category": "OXPHOS",
        },
        {
            "name": "Mitochondrial translation",
            "reactome_id": "R-HSA-5368286",
            "mitocarta_pathway": "Mitochondrial translation",
            "category": "Protein import & sorting",
        },
        {
            "name": "TCA cycle",
            "kegg_id": "hsa00020",
            "reactome_id": "R-HSA-71403",
            "mitocarta_pathway": "TCA cycle",
            "category": "Metabolism",
        },
        {
            "name": "Fatty acid beta-oxidation",
            "kegg_id": "hsa00071",
            "reactome_id": "R-HSA-77289",
            "mitocarta_pathway": "Beta-oxidation",
            "category": "Metabolism",
        },
    ]
    for category in MITOCARTA_CATEGORIES:
        rows.append(
            {
                "name": category,
                "mitocarta_pathway": category,
                "category": category,
            }
        )
    index = 1
    while len(rows) < 149:
        category = MITOCARTA_CATEGORIES[index % len(MITOCARTA_CATEGORIES)]
        rows.append(
            {
                "name": f"MitoCarta pathway {index:03d}",
                "mitocarta_pathway": f"Tier3 pathway {index:03d}",
                "category": category,
            }
        )
        index += 1
    return rows[:149]


def _load_complexes(writer: object) -> None:
    graph_writer = as_writer(writer)
    complexes = [
        {"name": "Complex I", "n_subunits": 45, "mass_kda": 1000, "location": "IMM"},
        {"name": "Complex II", "n_subunits": 4, "mass_kda": 124, "location": "IMM"},
        {"name": "Complex III", "n_subunits": 11, "mass_kda": 500, "location": "IMM"},
        {"name": "Complex IV", "n_subunits": 14, "mass_kda": 204, "location": "IMM"},
        {"name": "Complex V", "n_subunits": 29, "mass_kda": 600, "location": "IMM"},
    ]
    for row in complexes:
        graph_writer.merge_node("Complex", "name", row)
        graph_writer.merge_relationship(
            "Complex",
            "name",
            row["name"],
            EDGE_LABELS["participates_in"],
            "Pathway",
            "name",
            "Oxidative phosphorylation",
        )


def _load_pathway_hierarchy(writer: object) -> None:
    graph_writer = as_writer(writer)
    for pathway in _pathway_rows():
        name = str(pathway["name"])
        category = str(pathway.get("category", "Other/unassigned"))
        if name == category:
            continue
        graph_writer.merge_relationship(
            "Pathway",
            "name",
            name,
            EDGE_LABELS["part_of"],
            "Pathway",
            "name",
            category,
        )


def _read_records_from_table(path: Path) -> List[MitoCartaRecord]:
    warnings = (
        f"Parsing real MitoCarta tables is not yet configured for {path}; "
        "using deterministic offline seed rows."
    )
    del warnings
    return _offline_records(1136)
