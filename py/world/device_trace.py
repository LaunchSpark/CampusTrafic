from __future__ import annotations

from dataclasses import dataclass, field

from py.world.connection import Connection
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
        rows: list[dict[str, str | int]] = []
        for idx in range(len(self.connections) - 1):
            first = self.connections[idx]
            second = self.connections[idx + 1]

            t_from = first.end_ts_ms if first.end_ts_ms is not None else first.start_ts_ms
            t_to = second.start_ts_ms
            if t_from is None or t_to is None:
                continue

            dt = t_to - t_from
            if dt < 0:
                continue

            rows.append(
                {
                    "device_id": str(self.device_id),
                    "from_wap": str(first.node_id),
                    "to_wap": str(second.node_id),
                    "t_from_ms": t_from,
                    "t_to_ms": t_to,
                    "dt_ms": dt,
                }
            )

        return rows
