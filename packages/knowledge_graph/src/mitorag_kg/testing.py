"""In-memory graph used by Phase 3 tests and offline smoke checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple


def _empty_properties() -> Dict[str, object]:
    return {}


def _empty_labels() -> Set[str]:
    return set()


@dataclass
class MemoryNode:
    id: str
    labels: Set[str] = field(default_factory=_empty_labels)
    properties: Dict[str, object] = field(default_factory=_empty_properties)


@dataclass
class MemoryRelationship:
    start_id: str
    relationship_type: str
    end_id: str
    properties: Dict[str, object] = field(default_factory=_empty_properties)


class InMemoryKG:
    """A tiny property graph with the same writer surface as the Neo4j adapter."""

    def __init__(self) -> None:
        self.nodes: Dict[str, MemoryNode] = {}
        self.relationships: List[MemoryRelationship] = []
        self._index: Dict[Tuple[str, str, str], str] = {}
        self._next_id = 1

    def merge_node(self, label: str, key: str, properties: Mapping[str, object]) -> str:
        if key not in properties:
            raise KeyError(f"Missing key property {key} for {label}")
        index_key = (label, key, _hashable(properties[key]))
        node_id = self._index.get(index_key)
        if node_id is None:
            node_id = str(self._next_id)
            self._next_id += 1
            self.nodes[node_id] = MemoryNode(id=node_id, labels={label}, properties={})
            self._index[index_key] = node_id
        node = self.nodes[node_id]
        node.labels.add(label)
        node.properties.update(dict(properties))
        return node_id

    def merge_relationship(
        self,
        start_label: str,
        start_key: str,
        start_value: object,
        relationship_type: str,
        end_label: str,
        end_key: str,
        end_value: object,
        properties: Optional[Mapping[str, object]] = None,
    ) -> None:
        start = self.get_node(start_label, start_key, start_value)
        end = self.get_node(end_label, end_key, end_value)
        if start is None:
            raise KeyError(f"Missing start node {start_label}.{start_key}={start_value}")
        if end is None:
            raise KeyError(f"Missing end node {end_label}.{end_key}={end_value}")
        rel_properties = dict(properties or {})
        for rel in self.relationships:
            if (
                rel.start_id == start.id
                and rel.end_id == end.id
                and rel.relationship_type == relationship_type
            ):
                rel.properties.update(rel_properties)
                return
        self.relationships.append(
            MemoryRelationship(
                start_id=start.id,
                relationship_type=relationship_type,
                end_id=end.id,
                properties=rel_properties,
            )
        )

    def get_node(self, label: str, key: str, value: object) -> Optional[MemoryNode]:
        node_id = self._index.get((label, key, _hashable(value)))
        if node_id is None:
            return None
        return self.nodes[node_id]

    def find_nodes(self, label: str, **properties: object) -> List[MemoryNode]:
        matches: List[MemoryNode] = []
        for node in self.nodes.values():
            if label not in node.labels:
                continue
            if all(node.properties.get(key) == value for key, value in properties.items()):
                matches.append(node)
        return matches

    def count_nodes(self, label: str) -> int:
        return sum(1 for node in self.nodes.values() if label in node.labels)

    def count_nodes_with_properties(self, label: str, property_names: Iterable[str]) -> int:
        names = list(property_names)
        return sum(
            1
            for node in self.nodes.values()
            if label in node.labels and all(name in node.properties for name in names)
        )

    def count_relationships(self, relationship_type: str) -> int:
        return sum(1 for rel in self.relationships if rel.relationship_type == relationship_type)

    def relationship_exists(
        self,
        start_id: str,
        relationship_type: str,
        end_id: str,
    ) -> bool:
        return any(
            rel.start_id == start_id
            and rel.relationship_type == relationship_type
            and rel.end_id == end_id
            for rel in self.relationships
        )

    def count_localized_proteins(self, compartment_name: str) -> int:
        compartment = self.get_node("SubMitoCompartment", "name", compartment_name)
        if compartment is None:
            return 0
        count = 0
        for rel in self.relationships:
            if rel.relationship_type != "LOCALIZES_TO" or rel.end_id != compartment.id:
                continue
            start = self.nodes[rel.start_id]
            if "Protein" in start.labels:
                count += 1
        return count

    def has_mitomap_path(
        self,
        hgvs: str,
        gene_symbol: str,
        complex_name: str,
        pathway_name: str,
    ) -> bool:
        variant = self.get_node("Variant", "hgvs", hgvs)
        gene = self.get_node("Gene", "hgnc_symbol", gene_symbol)
        complex_node = self.get_node("Complex", "name", complex_name)
        pathway = self.get_node("Pathway", "name", pathway_name)
        if not variant or not gene or not complex_node or not pathway:
            return False
        variant_to_gene = self.relationship_exists(variant.id, "ASSOCIATED_WITH", gene.id)
        gene_to_complex = self.relationship_exists(gene.id, "PART_OF", complex_node.id)
        complex_to_pathway = self.relationship_exists(
            complex_node.id,
            "PARTICIPATES_IN",
            pathway.id,
        )
        return variant_to_gene and gene_to_complex and complex_to_pathway

    def run_scalar(self, cypher: str) -> int:
        normalized = " ".join(cypher.split())
        if "RETURN count(p)" in normalized and "SubMitoCompartment {name:'matrix'}" in normalized:
            return self.count_localized_proteins("matrix")
        raise NotImplementedError(f"InMemoryKG cannot evaluate query: {cypher}")


def _hashable(value: object) -> str:
    return str(value)

