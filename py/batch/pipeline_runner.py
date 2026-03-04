from __future__ import annotations

from py.world.world import World


def run_raw_to_world_pipeline() -> World:
    return World.construct()
