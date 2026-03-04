from __future__ import annotations

from pathlib import Path

from py.io import pipeline_io
from py.world.connection import Connection
from py.world.device_map import DeviceMapBuilder, PipelinePaths
from py.world.types import DeviceId
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from py.world.world import World


class DevicePipeline:
    """Compatibility façade for legacy pipeline call sites."""

    def __init__(self, paths: PipelinePaths | None = None, threshold_ms: int = 300_000) -> None:
        self._paths = paths
        self._threshold_ms = threshold_ms

    @classmethod
    def parse_device_id(cls, value: str | None) -> DeviceId | None:
        return DeviceMapBuilder.parse_device_id(value)

    @classmethod
    def parse_wap_id(cls, value: str | None):
        return DeviceMapBuilder.parse_wap_id(value)

    @staticmethod
    def parse_timestamp_ms(value: str | int | float | None) -> int | None:
        return DeviceMapBuilder.parse_timestamp_ms(value)

    def normalize_raw_logs(self) -> Path:
        paths = self._paths or PipelinePaths()
        return pipeline_io.normalize_raw_logs(paths.raw_dir, paths.observations_dir)

    def build_traces_and_transitions(self, observations_csv: Path) -> dict[DeviceId, list[Connection]]:
        return pipeline_io.build_traces_and_transitions(observations_csv)

    def build_parent_map(
        self,
        traces: dict[DeviceId, list[Connection]],
    ) -> tuple[dict[DeviceId, DeviceId], dict[DeviceId, bool]]:
        return pipeline_io.build_parent_map(traces, threshold_ms=self._threshold_ms)

    def apply_parent_map(
        self,
        traces: dict[DeviceId, list[Connection]],
        parent_map: dict[DeviceId, DeviceId],
    ) -> "World":
        return pipeline_io.apply_parent_map(traces, parent_map)

    def run(self) -> "World":
        return pipeline_io.run_pipeline(paths=self._paths, threshold_ms=self._threshold_ms)
