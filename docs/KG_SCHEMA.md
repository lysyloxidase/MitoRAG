# Knowledge Graph Schema

Phase 3 implements the mitochondrial KG schema and seed loaders. The schema uses
Biolink-style predicate names in Python and Neo4j relationship types in uppercase
Cypher, for example `encoded_by` -> `ENCODED_BY`.

## Nodes

Core labels:

- `Gene`, keyed by `hgnc_symbol`
- `Protein`, keyed by `uniprot_id`
- `Complex`, keyed by `name`
- `Pathway`, keyed by `name`
- `Metabolite`, keyed by `chebi_id`
- `Reaction`, keyed by `name`
- `Disease`, keyed by `name`
- `Variant`, keyed by `hgvs`
- `Drug`, keyed by `name`
- `Phenotype`, keyed by `hpo_id`
- `SubMitoCompartment`, keyed by `name`
- `Paper`, `Claim`, and `Hypothesis`

## Seeds

The loaders support a real Neo4j driver through `Neo4jGraphWriter`, and tests use
`InMemoryKG` with the same writer surface.

- MitoCarta 3.0: 1,136 genes and 1,136 proteins, 149 pathways, ETC complexes,
  and sub-mitochondrial localization counts of 525 matrix, 359 IMM, 53 IMS, and
  112 OMM.
- Reactome: mitochondrial pathway annotations merged onto 600 MitoCarta
  proteins by UniProt ID.
- KEGG: core mitochondrial pathways such as OXPHOS (`hsa00190`) and TCA cycle.
- Gene Ontology: `GO:0005739` mitochondrial compartment hierarchy.
- MITOMAP: five canonical pathogenic mtDNA variants with heteroplasmy thresholds.
- HPO/MONDO: mitochondrial disease and phenotype edges.
- ChEBI: core metabolites including NAD+, NADH, ATP, ADP, succinate, and citrate.
- Therapeutics: 10 drug nodes with target edges.
- Hypotheses: disputed mPTP hypotheses linked by `CONTRADICTS`.

## Query Example

```cypher
MATCH (g:Gene)-[:ENCODED_BY]-(p:Protein)-[:LOCALIZES_TO]->
(c:SubMitoCompartment {name:'matrix'})
RETURN count(p)
```

The offline seed returns `525` for this query. Phase 6 will add paper-derived
claims and provenance down to chunk ID.
