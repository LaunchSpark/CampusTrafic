from __future__ import annotations

from pathlib import Path

from py.world.connection import Connection
from py.world.device_map import DeviceMapBuilder, PipelinePaths
from py.world.types import DeviceId
from py.world.world import World


def normalize_raw_logs(raw_dir: Path, out_dir: Path) -> Path:
    paths = PipelinePaths(raw_dir=raw_dir, observations_dir=out_dir)
    return DeviceMapBuilder(paths=paths).normalize_raw_logs()


def build_traces_and_transitions(observations_csv: Path) -> dict[DeviceId, list[Connection]]:
    return DeviceMapBuilder().build_traces_and_transitions(observations_csv)


def build_parent_map(
    traces: dict[DeviceId, list[Connection]], threshold_ms: int = 300_000
) -> tuple[dict[DeviceId, DeviceId], dict[DeviceId, bool]]:
    return DeviceMapBuilder(threshold_ms=threshold_ms).build_parent_map(traces)


def apply_parent_map(
    traces: dict[DeviceId, list[Connection]],
    parent_map: dict[DeviceId, DeviceId],
) -> World:
    builder = DeviceMapBuilder()
    device_connections = builder.apply_parent_map(traces, parent_map)
    return World().with_connections(device_connections)


def run_pipeline(paths: PipelinePaths | None = None, threshold_ms: int = 300_000) -> World:
    return World.construct(paths=paths, threshold_ms=threshold_ms)
