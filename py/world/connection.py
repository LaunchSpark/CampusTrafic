from __future__ import annotations

"""Connection observations that map a device to a graph node over time."""

from dataclasses import dataclass
from typing import Any

from .types import NodeId


@dataclass(frozen=True)
class Connection:
    """A single temporal connection interval for one device at one node."""

    node_id: NodeId
    start_ts_ms: int | None = None
    end_ts_ms: int | None = None
    meta: dict[str, Any] | None = None


# TODO:
# - Define overlap/adjacency policy for consecutive Connection records.
# - Add validation rules for start/end ordering and null timestamp semantics.
# - Specify dwell-time threshold behavior for short or noisy associations.
# - Add derived helpers (duration, midpoint timestamp) once conventions are fixed.
# - Normalize metadata keys (e.g., IP, user-agent) with schema versioning.
