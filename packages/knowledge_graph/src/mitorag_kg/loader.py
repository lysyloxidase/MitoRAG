"""Shared loader result and graph writer utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple, cast

LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
REL_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _empty_details() -> Dict[str, object]:
    return {}


def _empty_warnings() -> List[str]:
    return []


@dataclass(frozen=True)
class LoadResult:
    """Summary returned by each seed loader."""

    loader: str
    nodes_loaded: int = 0
    relationships_loaded: int = 0
    details: Mapping[str, object] = field(default_factory=_empty_details)
    warnings: Sequence[str] = field(default_factory=_empty_warnings)


class GraphWriter(Protocol):
    """Minimal write surface used by all seed loaders."""

    def merge_node(self, label: str, key: str, properties: Mapping[str, object]) -> str:
        """Merge a node by label/key and update its properties."""
        ...

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
        """Merge a typed relationship between two already merged nodes."""
        ...


class Neo4jGraphWriter:
    """GraphWriter adapter for the official Neo4j Python driver."""

    def __init__(self, driver: object) -> None:
        self.driver = driver

    def merge_node(self, label: str, key: str, properties: Mapping[str, object]) -> str:
        _validate_label(label)
        _validate_key(key)
        cypher = (
            f"MERGE (n:{label} {{{key}: $key_value}}) "
            "SET n += $properties "
            "RETURN elementId(n) AS id"
        )
        parameters = {
            "key_value": properties[key],
            "properties": dict(properties),
        }
        records = _execute_query(self.driver, cypher, parameters)
        if records:
            value = records[0].get("id")
            return str(value)
        return f"{label}:{properties[key]}"

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
        _validate_label(start_label)
        _validate_label(end_label)
        _validate_key(start_key)
        _validate_key(end_key)
        _validate_relationship(relationship_type)
        cypher = (
            f"MATCH (a:{start_label} {{{start_key}: $start_value}}) "
            f"MATCH (b:{end_label} {{{end_key}: $end_value}}) "
            f"MERGE (a)-[r:{relationship_type}]->(b) "
            "SET r += $properties"
        )
        _execute_query(
            self.driver,
            cypher,
            {
                "start_value": start_value,
                "end_value": end_value,
                "properties": dict(properties or {}),
            },
        )


def as_writer(driver_or_writer: object) -> GraphWriter:
    """Return a GraphWriter from either a writer-like object or a Neo4j driver."""

    if hasattr(driver_or_writer, "merge_node") and hasattr(driver_or_writer, "merge_relationship"):
        return cast(GraphWriter, driver_or_writer)
    return Neo4jGraphWriter(driver_or_writer)


def merge_many_nodes(
    writer: GraphWriter,
    label: str,
    key: str,
    rows: Iterable[Mapping[str, object]],
) -> int:
    count = 0
    for row in rows:
        writer.merge_node(label, key, row)
        count += 1
    return count


def relationship_type(predicate: str) -> str:
    """Convert a Biolink-style predicate into a Neo4j relationship type."""

    rel_type = predicate.upper()
    _validate_relationship(rel_type)
    return rel_type


def _execute_query(
    driver: object,
    cypher: str,
    parameters: Mapping[str, object],
) -> List[Mapping[str, object]]:
    if hasattr(driver, "execute_query"):
        result: object = cast(Any, driver).execute_query(cypher, dict(parameters))
        if isinstance(result, tuple):
            tuple_result = cast(Tuple[object, ...], result)
            if not tuple_result:
                return []
            return _records_to_mappings(tuple_result[0])
        records_object: object = result
        return _records_to_mappings(records_object)

    if hasattr(driver, "session"):
        with cast(Any, driver).session() as session:
            records: object = session.run(cypher, dict(parameters))
            return _records_to_mappings(records)

    raise TypeError("Expected a Neo4j driver or GraphWriter-compatible object")


def _records_to_mappings(records: object) -> List[Mapping[str, object]]:
    if records is None:
        return []
    output: List[Mapping[str, object]] = []
    for record in cast(Iterable[object], records):
        if isinstance(record, Mapping):
            output.append(cast(Mapping[str, object], record))
        elif hasattr(record, "data"):
            data = cast(Any, record).data()
            if isinstance(data, Mapping):
                output.append(cast(Mapping[str, object], data))
    return output


def _validate_label(label: str) -> None:
    if not LABEL_RE.match(label):
        raise ValueError(f"Unsafe Neo4j label: {label}")


def _validate_key(key: str) -> None:
    if not LABEL_RE.match(key):
        raise ValueError(f"Unsafe Neo4j property key: {key}")


def _validate_relationship(rel_type: str) -> None:
    if not REL_RE.match(rel_type):
        raise ValueError(f"Unsafe Neo4j relationship type: {rel_type}")


RelationshipSpec = Tuple[str, str, object, str, str, str, object, Mapping[str, object]]
