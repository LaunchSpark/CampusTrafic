from __future__ import annotations

"""Canonical identifier and primitive type aliases for world-domain state."""

from typing import NewType

DeviceId = NewType("DeviceId", str)
NodeId = NewType("NodeId", str)
EdgeId = NewType("EdgeId", str)
TimestampMs = NewType("TimestampMs", int)

# TODO:
# - Define canonical string normalization rules for DeviceId/NodeId/EdgeId.
# - Specify whether IDs are globally unique or scoped by dataset/campus.
# - Decide if TimestampMs should remain epoch-milliseconds or become a richer type.
# - Add parsing helpers once artifact schemas are finalized.
