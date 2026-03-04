from __future__ import annotations

"""Top-level world container that groups spatial, graph, and observation state."""

from dataclasses import dataclass, field

from .connection import Connection
from .graph import Graph
from .grid import Grid
from .types import DeviceId


@dataclass
class World:
    """Canonical in-memory state for the WiFi-flow digital twin world."""

    grid: Grid
    graph: Graph
    device_connections: dict[DeviceId, list[Connection]] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate world invariants.

        Raises:
            ValueError: If structural or temporal invariants are violated.
        """

        # TODO:
        # - Validate graph referential integrity and unique IDs.
        # - Ensure each Connection references an existing NodeId.
        # - Enforce connection ordering/sorting and timestamp monotonicity per device.
        # - Check grid bounds/cell size against graph coordinate extents.
        raise NotImplementedError("World.validate() is scaffolding-only for now.")

    def to_dict(self) -> dict[str, object]:
        """Serialize world state to a plain dictionary representation."""

        # TODO:
        # - Define stable schema version for persisted world dictionaries.
        # - Encode NewType identifiers and timestamps consistently.
        # - Align output fields with py.io.artifacts/world_drafts conventions.
        raise NotImplementedError("World.to_dict() is scaffolding-only for now.")

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "World":
        """Build a world from a plain dictionary representation."""

        # TODO:
        # - Parse and validate required keys for grid/graph/device connections.
        # - Enforce strict typing/normalization during ingestion.
        # - Support schema upgrades for older draft/artifact versions.
        raise NotImplementedError("World.from_dict() is scaffolding-only for now.")

    def with_connections(self, device_connections: dict[DeviceId, list[Connection]]) -> "World":
        """Return a shallow-copy world with replaced device connection mapping."""

        # TODO:
        # - Decide copy policy (deep copy vs. ownership transfer) for lists/records.
        # - Preserve immutability expectations for downstream training/inference stages.
        # - Clarify representation for teleportation/missing-observation segments.
        return World(grid=self.grid, graph=self.graph, device_connections=device_connections)


# TODO:
# - Keep World as pure state: no routing, flow inference, or model-training behavior.
# - Document invariants for per-device connection lists (sorted by time, non-null node IDs).
# - Define downstream encoding for missing pings, gaps, and teleportation anomalies.
