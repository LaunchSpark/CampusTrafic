from __future__ import annotations

"""Top-level world container that groups graph-ready and observation state."""

from dataclasses import dataclass, field

from .connection import Connection
from .device_trace import DeviceTrace
from .graph import Graph
from .grid import Grid
from .types import DeviceId


@dataclass
class World:
    """Canonical in-memory state for the WiFi-flow digital twin world."""

    graph: Graph | None = None
    grid: Grid | None = None
    devices: list[DeviceTrace] = field(default_factory=list)

