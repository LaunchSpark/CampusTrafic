from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from py.world.connection import Connection
from py.world.device_map import DeviceMapBuilder, OBSERVATIONS_COLUMNS, PipelinePaths
from py.world.device_trace import DeviceTrace
from py.world.types import DeviceId, NodeId


def legacy_transition_rows(device_id: DeviceId, connections: list[Connection]) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for idx in range(len(connections) - 1):
        first = connections[idx]
        second = connections[idx + 1]

        t_from = first.end_ts_ms if first.end_ts_ms is not None else first.start_ts_ms
        t_to = second.start_ts_ms
        if t_from is None or t_to is None:
            continue

        dt = t_to - t_from
        if dt < 0:
            continue

        rows.append(
            {
                "device_id": str(device_id),
                "from_wap": str(first.node_id),
                "to_wap": str(second.node_id),
                "t_from_ms": t_from,
                "t_to_ms": t_to,
                "dt_ms": dt,
            }
        )
    return rows


def legacy_nearby(index: dict[NodeId, list[tuple[int, DeviceId]]], wap: NodeId, ts: int, threshold: int) -> set[DeviceId]:
    events = index.get(wap, [])
    return {device for event_ts, device in events if ts - threshold <= event_ts <= ts + threshold}


class RefactorParityTests(unittest.TestCase):
    def test_transition_parity_with_nulls_and_negative_durations(self) -> None:
        device = DeviceId("d1")
        conns = [
            Connection(node_id=NodeId("A"), start_ts_ms=1000, end_ts_ms=1200),
            Connection(node_id=NodeId("B"), start_ts_ms=1300, end_ts_ms=None),
            Connection(node_id=NodeId("C"), start_ts_ms=None, end_ts_ms=1700),
            Connection(node_id=NodeId("D"), start_ts_ms=1250, end_ts_ms=1400),  # negative from previous end
            Connection(node_id=NodeId("E"), start_ts_ms=1800, end_ts_ms=None),
        ]

        trace = DeviceTrace(device_id=device, connections=conns)
        self.assertEqual(trace.to_transition_rows(), legacy_transition_rows(device, conns))

    def test_nearby_lookup_threshold_boundaries(self) -> None:
        traces = {
            DeviceId("d1"): [Connection(node_id=NodeId("wap1"), start_ts_ms=1000)],
            DeviceId("d2"): [Connection(node_id=NodeId("wap1"), start_ts_ms=1300)],
            DeviceId("d3"): [Connection(node_id=NodeId("wap1"), start_ts_ms=700)],
            DeviceId("d4"): [Connection(node_id=NodeId("wap1"), start_ts_ms=1301)],
        }
        threshold = 300
        query_ts = 1000

        new_index = DeviceMapBuilder._build_wap_time_index(traces)
        new_result = DeviceMapBuilder._nearby_devices(new_index, NodeId("wap1"), query_ts, threshold)

        legacy_index: dict[NodeId, list[tuple[int, DeviceId]]] = {NodeId("wap1"): []}
        for device, conns in traces.items():
            for conn in conns:
                if conn.start_ts_ms is not None:
                    legacy_index[NodeId("wap1")].append((conn.start_ts_ms, device))
        legacy_index[NodeId("wap1")].sort(key=lambda item: (item[0], str(item[1])))

        self.assertEqual(new_result, legacy_nearby(legacy_index, NodeId("wap1"), query_ts, threshold))

    def test_normalize_raw_logs_schema_and_sorting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw_dir = base / "raw"
            raw_dir.mkdir()
            raw_csv = raw_dir / "sample.csv"
            with raw_csv.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["device", "wap", "timestamp", "end_ts"])
                writer.writeheader()
                writer.writerow({"device": "b", "wap": "z", "timestamp": "200", "end_ts": ""})
                writer.writerow({"device": "a", "wap": "z", "timestamp": "100", "end_ts": "150"})
                writer.writerow({"device": "a", "wap": "y", "timestamp": "100", "end_ts": ""})

            paths = PipelinePaths(
                raw_dir=raw_dir,
                observations_dir=base / "obs",
                transitions_csv=base / "transitions.csv",
                parent_map_csv=base / "parent.csv",
                observations_parented_csv=base / "parented.csv",
            )
            builder = DeviceMapBuilder(paths=paths)
            out = builder.normalize_raw_logs()

            with out.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, OBSERVATIONS_COLUMNS)
                rows = list(reader)

            self.assertEqual(
                rows,
                [
                    {"device_id": "a", "wap_id": "y", "start_ts_ms": "100", "end_ts_ms": ""},
                    {"device_id": "a", "wap_id": "z", "start_ts_ms": "100", "end_ts_ms": "150"},
                    {"device_id": "b", "wap_id": "z", "start_ts_ms": "200", "end_ts_ms": ""},
                ],
            )


if __name__ == "__main__":
    unittest.main()
