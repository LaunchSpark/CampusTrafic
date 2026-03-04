from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from py.io.csv_io import list_csv_files, read_csv_rows, write_csv_rows
from py.io.paths import PROCESSED_DATA, RAW_DATA
from py.world.connection import Connection
from py.world.device_trace import DeviceTrace
from py.world.types import DeviceId, NodeId

OBSERVATIONS_COLUMNS = ["device_id", "wap_id", "start_ts_ms", "end_ts_ms"]
TRANSITIONS_COLUMNS = ["device_id", "from_wap", "to_wap", "t_from_ms", "t_to_ms", "dt_ms"]
PARENT_MAP_COLUMNS = ["deviceId", "parent", "isAmbiguous"]


@dataclass(frozen=True)
class PipelinePaths:
    raw_dir: Path = RAW_DATA / "real"
    observations_dir: Path = PROCESSED_DATA / "observations"
    transitions_csv: Path = PROCESSED_DATA / "transitions" / "transitions.csv"
    parent_map_csv: Path = PROCESSED_DATA / "deviceParentMap.csv"
    observations_parented_csv: Path = PROCESSED_DATA / "observations_parented" / "observations_parented.csv"


@dataclass
class DeviceMap:
    device_connections: dict[DeviceId, list[Connection]] = field(default_factory=dict)
    parent_map: dict[DeviceId, DeviceId] = field(default_factory=dict)
    ambiguous: dict[DeviceId, bool] = field(default_factory=dict)


class DeviceMapBuilder:
    def __init__(self, paths: PipelinePaths | None = None, threshold_ms: int = 300_000) -> None:
        self.paths = paths or PipelinePaths()
        self.threshold_ms = threshold_ms
        self.device_map = DeviceMap()

    @staticmethod
    def _clean_str(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @classmethod
    def parse_device_id(cls, value: str | None) -> DeviceId | None:
        normalized = cls._clean_str(value)
        if normalized is None:
            return None
        return DeviceId(normalized)

    @classmethod
    def parse_wap_id(cls, value: str | None) -> NodeId | None:
        normalized = cls._clean_str(value)
        if normalized is None:
            return None
        return NodeId(normalized)

    @staticmethod
    def parse_timestamp_ms(value: str | int | float | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)

        raw = str(value).strip()
        if not raw:
            return None

        try:
            return int(raw)
        except ValueError:
            pass

        try:
            return int(float(raw))
        except ValueError:
            pass

        iso_candidate = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_candidate)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)

    def normalize_raw_logs(self) -> Path:
        rows_out: list[dict[str, str | int | None]] = []

        for csv_file in list_csv_files(self.paths.raw_dir):
            for row in read_csv_rows(csv_file):
                device = self.parse_device_id(row.get("device_id") or row.get("device"))
                wap = self.parse_wap_id(row.get("wap_id") or row.get("wap"))
                t0 = self.parse_timestamp_ms(row.get("start_ts") or row.get("timestamp"))
                t1 = self.parse_timestamp_ms(row.get("end_ts"))

                if device is None or wap is None or t0 is None:
                    continue

                rows_out.append(
                    {
                        "device_id": str(device),
                        "wap_id": str(wap),
                        "start_ts_ms": t0,
                        "end_ts_ms": t1,
                    }
                )

        rows_out.sort(key=lambda row: (str(row["device_id"]), int(row["start_ts_ms"]), str(row["wap_id"])))
        observations_csv = self.paths.observations_dir / "observations_normalized.csv"
        write_csv_rows(observations_csv, rows_out, OBSERVATIONS_COLUMNS)
        return observations_csv

    def build_traces_and_transitions(self, observations_csv: Path) -> dict[DeviceId, list[Connection]]:
        grouped: dict[DeviceId, list[dict[str, str]]] = defaultdict(list)
        for row in read_csv_rows(observations_csv):
            device = self.parse_device_id(row.get("device_id"))
            if device is None:
                continue
            grouped[device].append(row)

        traces: dict[DeviceId, list[Connection]] = {}
        transitions: list[dict[str, str | int]] = []

        for device, rows in grouped.items():
            trace = DeviceTrace.from_observation_rows(
                device_id=device,
                rows=rows,
                parse_wap_id=self.parse_wap_id,
                parse_timestamp_ms=self.parse_timestamp_ms,
            )
            traces[device] = trace.connections
            transitions.extend(trace.to_transition_rows())

        transitions.sort(
            key=lambda row: (
                str(row["device_id"]),
                int(row["t_from_ms"]),
                str(row["from_wap"]),
                str(row["to_wap"]),
            )
        )
        write_csv_rows(self.paths.transitions_csv, transitions, TRANSITIONS_COLUMNS)
        return traces

    @staticmethod
    def _build_wap_time_index(traces: dict[DeviceId, list[Connection]]) -> dict[NodeId, list[tuple[int, DeviceId]]]:
        wap_index: dict[NodeId, list[tuple[int, DeviceId]]] = defaultdict(list)
        for device, conns in traces.items():
            for conn in conns:
                if conn.start_ts_ms is None:
                    continue
                wap_index[conn.node_id].append((conn.start_ts_ms, device))

        for events in wap_index.values():
            events.sort(key=lambda event: (event[0], str(event[1])))
        return wap_index

    @staticmethod
    def _nearby_devices(
        wap_index: dict[NodeId, list[tuple[int, DeviceId]]],
        wap: NodeId,
        timestamp_ms: int,
        threshold_ms: int,
    ) -> set[DeviceId]:
        events = wap_index.get(wap, [])
        if not events:
            return set()

        times = [event_time for event_time, _ in events]
        left = bisect_left(times, timestamp_ms - threshold_ms)
        right = bisect_right(times, timestamp_ms + threshold_ms)
        return {device for _, device in events[left:right]}

    def build_parent_map(
        self,
        traces: dict[DeviceId, list[Connection]],
    ) -> tuple[dict[DeviceId, DeviceId], dict[DeviceId, bool]]:
        devices = sorted(traces.keys(), key=lambda device: (len(traces[device]), str(device)))
        parent_map: dict[DeviceId, DeviceId] = {}
        ambiguous: dict[DeviceId, bool] = {}

        wap_index = self._build_wap_time_index(traces)

        for device in devices:
            if device in parent_map:
                continue

            events = [(conn.node_id, conn.start_ts_ms) for conn in traces[device] if conn.start_ts_ms is not None]
            if not events:
                parent_map[device] = device
                ambiguous[device] = False
                continue

            scores: dict[DeviceId, int] = defaultdict(int)
            for wap, timestamp_ms in events:
                nearby = self._nearby_devices(wap_index, wap, timestamp_ms, self.threshold_ms)
                for candidate in nearby:
                    if candidate == device:
                        continue
                    if candidate in parent_map and parent_map[candidate] != candidate:
                        continue
                    scores[candidate] += 1

            if not scores:
                parent_map[device] = device
                ambiguous[device] = False
                continue

            best = max(scores.values())
            best_parents = [candidate for candidate, score in scores.items() if score == best]
            match_ratio = best / max(1, len(events))
            if match_ratio < 0.8:
                parent_map[device] = device
                ambiguous[device] = False
                continue

            ranked = sorted(best_parents, key=lambda candidate: (-len(traces[candidate]), str(candidate)))
            parent_map[device] = ranked[0]
            ambiguous[device] = len(best_parents) > 1

        rows = [
            {
                "deviceId": str(device),
                "parent": str(parent_map.get(device, device)),
                "isAmbiguous": 1 if ambiguous.get(device, False) else 0,
            }
            for device in sorted(devices, key=str)
        ]
        write_csv_rows(self.paths.parent_map_csv, rows, PARENT_MAP_COLUMNS)
        return parent_map, ambiguous

    def apply_parent_map(
        self,
        traces: dict[DeviceId, list[Connection]],
        parent_map: dict[DeviceId, DeviceId],
    ) -> dict[DeviceId, list[Connection]]:
        parented: dict[DeviceId, list[Connection]] = defaultdict(list)

        for device, conns in traces.items():
            parent = parent_map.get(device, device)
            parented[parent].extend(conns)

        for _, conns in parented.items():
            conns.sort(key=lambda conn: (conn.start_ts_ms if conn.start_ts_ms is not None else -1, str(conn.node_id)))

        rows: list[dict[str, str | int | None]] = []
        for parent, conns in sorted(parented.items(), key=lambda item: str(item[0])):
            for conn in conns:
                rows.append(
                    {
                        "device_id": str(parent),
                        "wap_id": str(conn.node_id),
                        "start_ts_ms": conn.start_ts_ms,
                        "end_ts_ms": conn.end_ts_ms,
                    }
                )

        rows.sort(
            key=lambda row: (
                str(row["device_id"]),
                int(row["start_ts_ms"]) if row["start_ts_ms"] is not None else -1,
                str(row["wap_id"]),
            )
        )
        write_csv_rows(self.paths.observations_parented_csv, rows, OBSERVATIONS_COLUMNS)
        return dict(parented)

    def build(self) -> DeviceMap:
        observations_csv = self.normalize_raw_logs()
        traces = self.build_traces_and_transitions(observations_csv)
        parent_map, ambiguous = self.build_parent_map(traces)
        device_connections = self.apply_parent_map(traces, parent_map)
        self.device_map = DeviceMap(
            device_connections=device_connections,
            parent_map=parent_map,
            ambiguous=ambiguous,
        )
        return self.device_map
