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


@dataclass(frozen=True)
class Edge:
    """A weighted graph edge between two nodes."""

    id: EdgeId
    src: NodeId
    dst: NodeId
    weight: float
    bidirectional: bool = False


@dataclass
class Graph:
    """Collection of world nodes and edges keyed by stable identifiers."""

    nodes: dict[NodeId, Node] = field(default_factory=dict)
    edges: dict[EdgeId, Edge] = field(default_factory=dict)

