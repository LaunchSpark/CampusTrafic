from __future__ import annotations

"""Top-level world container that groups graph-ready and observation state."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .connection import Connection
from .device_map import DeviceMapBuilder, PipelinePaths
from .graph import Graph
from .trace_arrays import connections_to_columns, transition_columns
from .types import DeviceId

ConnectionsFromHere = list[dict[str, int | str]]
TimeBucket = dict[str, ConnectionsFromHere]
DateBucket = dict[str, TimeBucket]
GraphsByWap = dict[str, DateBucket]


@dataclass
class World:
    """Canonical in-memory state for the WiFi-flow digital twin world."""

    graph: Graph | None = None
    graphs: GraphsByWap = field(default_factory=dict)
    device_connections: dict[DeviceId, list[Connection]] = field(default_factory=dict)
    grid: None = None  # not implemented yet

    def __post_init__(self) -> None:
        if self.graph is None:
            self.graph = Graph.build()

    @staticmethod
    def _date_and_time(timestamp_ms: int) -> tuple[str, str]:
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")

    @classmethod
    def build_graphs(cls, device_connections: dict[DeviceId, list[Connection]]) -> GraphsByWap:
        graphs: GraphsByWap = {}

        for device_id, conns in device_connections.items():
            ordered = sorted(
                conns,
                key=lambda conn: (conn.start_ts_ms if conn.start_ts_ms is not None else -1, str(conn.node_id)),
            )
            transitions = transition_columns(connections_to_columns(ordered))
            for idx in range(len(transitions.dt_ms)):
                t_from = int(transitions.t_from_ms[idx])
                from_wap = str(transitions.from_node[idx])
                date_key, time_key = cls._date_and_time(t_from)
                graphs.setdefault(from_wap, {}).setdefault(date_key, {}).setdefault(time_key, []).append(
                    {
                        "device_id": str(device_id),
                        "to_wap": str(transitions.to_node[idx]),
                        "t_from_ms": t_from,
                        "t_to_ms": int(transitions.t_to_ms[idx]),
                        "dt_ms": int(transitions.dt_ms[idx]),
                    }
                )

        return graphs

    @classmethod
    def construct(
        cls,
        paths: PipelinePaths | None = None,
        data_path: Path | None = None,
        threshold_ms: int = 300_000,
    ) -> "World":
        """Orchestrate raw->processed pipeline and return a world."""

        if paths is None and data_path is not None:
            paths = PipelinePaths(raw_dir=data_path)

        builder = DeviceMapBuilder(paths=paths, threshold_ms=threshold_ms)
        graph = Graph.build(device_map_builder=builder)
        device_connections = builder.device_map.device_connections
        return cls(
            graph=graph,
            graphs=cls.build_graphs(device_connections),
            device_connections=device_connections,
            grid=None,
        )

    def validate(self) -> None:
        raise NotImplementedError("World.validate() is scaffolding-only for now.")

    def to_dict(self) -> dict[str, object]:
        raise NotImplementedError("World.to_dict() is scaffolding-only for now.")

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "World":
        raise NotImplementedError("World.from_dict() is scaffolding-only for now.")

    def with_connections(self, device_connections: dict[DeviceId, list[Connection]]) -> "World":
        return World(
            graph=self.graph,
            graphs=self.build_graphs(device_connections),
            device_connections=device_connections,
            grid=None,
        )
