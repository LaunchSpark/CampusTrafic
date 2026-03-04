from __future__ import annotations

"""Public world data-structure exports and centralized IO wiring."""

from py.io import artifacts as artifacts_io
from py.io import world_drafts as drafts_io
from py.io.paths import ARTIFACTS, DATA_ROOT, PROCESSED_DATA, RAW_DATA, REPO_ROOT, RUNS_DIR, WORLD_DRAFTS_DIR

from .connection import Connection
from .graph import Edge, Graph, Node
from .grid import Grid
from .types import DeviceId, EdgeId, NodeId
from .world import World

__all__ = [
    "Connection",
    "DeviceId",
    "Edge",
    "EdgeId",
    "Graph",
    "Grid",
    "Node",
    "NodeId",
    "World",
    "artifacts_io",
    "drafts_io",
    "REPO_ROOT",
    "DATA_ROOT",
    "RAW_DATA",
    "PROCESSED_DATA",
    "ARTIFACTS",
    "RUNS_DIR",
    "WORLD_DRAFTS_DIR",
]
