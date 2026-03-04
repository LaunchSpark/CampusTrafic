from __future__ import annotations

"""Spatial grid bounds and resolution metadata for world-level raster operations."""

from dataclasses import dataclass


@dataclass
class Grid:
    """Axis-aligned grid bounds and cell size for spatial discretization."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float
    cell_size: float


# TODO:
# - Add bbox/cell-size validation (positive extents, non-zero cell size).
# - Implement coordinate-to-cell and cell-to-coordinate indexing helpers.
# - Define transform conventions between map-space and pixel-space artifacts.
# - Align serialization fields with artifact schemas in data/artifacts world outputs.
