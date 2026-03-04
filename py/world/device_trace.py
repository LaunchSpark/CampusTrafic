from __future__ import annotations

from dataclasses import dataclass, field

from py.world.connection import Connection
from py.world.trace_arrays import connections_to_columns, transition_columns, transition_rows
from py.world.types import DeviceId


@dataclass
class DeviceTrace:
    device_id: DeviceId
    connections: list[Connection] = field(default_factory=list)

    @classmethod
    def from_observation_rows(
        cls,
        device_id: DeviceId,
        rows: list[dict[str, str]],
        parse_wap_id,
        parse_timestamp_ms,
    ) -> "DeviceTrace":
        ordered_rows = sorted(
            rows,
            key=lambda row: (
                parse_timestamp_ms(row.get("start_ts_ms")) or 0,
                str(row.get("wap_id") or ""),
            ),
        )

        connections: list[Connection] = []
        for row in ordered_rows:
            wap = parse_wap_id(row.get("wap_id"))
            if wap is None:
                continue
            connections.append(
                Connection(
                    node_id=wap,
                    start_ts_ms=parse_timestamp_ms(row.get("start_ts_ms")),
                    end_ts_ms=parse_timestamp_ms(row.get("end_ts_ms")),
                )
            )

        return cls(device_id=device_id, connections=connections)

    def to_transition_rows(self) -> list[dict[str, str | int]]:
        transitions = transition_columns(connections_to_columns(self.connections))
        return transition_rows(
            device_id=str(self.device_id),
            transitions=transitions,
            from_key="from_wap",
            to_key="to_wap",
        )
