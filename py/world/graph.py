from __future__ import annotations

"""Topological graph structures used by the world representation."""

from dataclasses import dataclass, field
from typing import Any

from .types import EdgeId, NodeId


@dataclass(frozen=True)
class Node:
    """A graph node with planar coordinates and optional metadata."""

    id: NodeId
    x: float
    y: float
    meta: dict[str, Any] | None = None


# TODO:
# - Define required Node metadata keys (building/floor labels, semantics).
# - Document coordinate reference system and precision expectations.
# - Add normalization hooks for imported node identifiers.


@dataclass(frozen=True)
class Edge:
    """A weighted graph edge between two nodes."""

    id: EdgeId
    src: NodeId
    dst: NodeId
    weight: float
    bidirectional: bool = False


# TODO:
# - Standardize weight meaning (distance meters vs. traversal seconds).
# - Decide whether bidirectional=True is expanded to two directed edges at load time.
# - Add optional precomputed direction vector/length caches if performance requires.
# - Define edge metadata extension points for capacities/restrictions.


@dataclass
class Graph:
    """Collection of world nodes and edges keyed by stable identifiers."""

    nodes: dict[NodeId, Node] = field(default_factory=dict)
    edges: dict[EdgeId, Edge] = field(default_factory=dict)


# TODO:
# - Provide adjacency-view builders for forward/reverse traversals.
# - Validate referential integrity (dangling node IDs, duplicate logical edges).
# - Add lightweight indexing for neighborhood queries.
# - Finalize import/export schema mapping for data/artifacts/.../world payloads.
