"""
step_08_package_world.py
========================
Final packaging step for phase 01.

Assembles Graph, InterpolatedJourneysData, and FieldData into a single
clean `World` object that downstream phases can load and query without
knowing the internal structure of any individual step artifact.

World structure
───────────────
  World
   ├── graph              : Graph  (nodes, physical_edges, node_counts)
   ├── wap_timeslots      : dict[hour_key, dict[wap_id, WAPTimeslot]]
   │     WAPTimeslot
   │       ├── raw_u, raw_v   – resultant displacement vector (SVG units)
   │       ├── magnitude      – |vector|
   │       ├── dir_u, dir_v   – unit direction
   │       └── traveler_count – unique persons seen at this WAP this hour
   └── flow_timeslots     : dict[hour_key, list[FlowSample]]
         FlowSample  (corridor-sampled, graph-interpolated)
           ├── x, y           – SVG coordinates
           ├── raw_u, raw_v   – corridor-projected blended vector
           ├── magnitude
           └── dir_u, dir_v
"""
from __future__ import annotations

import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipelineio.state import load_draft, save_draft

# ── Phase-01 type imports (required for pickle round-trip) ──────────────────
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_04_build_graph import Graph
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_06_interpolate_paths import (
    InterpolatedJourneysData,
)
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_07_build_field import (
    FieldData,
    FieldVector,
)

# ---------------------------------------------------------------------------
# World data model
# ---------------------------------------------------------------------------

@dataclass
class WAPTimeslot:
    """Flow vector and traveler count for one WAP in one 1-hour window."""
    wap_id: str
    hour_key: int           # epoch-ms start of the hour
    # Raw accumulated displacement vector (sum of all person movements *from* this WAP)
    raw_u: float = 0.0
    raw_v: float = 0.0
    # Pre-computed derived fields
    magnitude: float = 0.0
    dir_u: float = 0.0
    dir_v: float = 0.0
    # Number of unique persons seen at this WAP during the hour
    traveler_count: int = 0

    def direction_degrees(self) -> Optional[float]:
        """Bearing in degrees (0° = East/→, 90° = South/↓ in SVG coords).
        Returns None if there is no movement vector."""
        if self.magnitude < 1e-9:
            return None
        return math.degrees(math.atan2(self.dir_v, self.dir_u)) % 360


@dataclass
class FlowSample:
    """A single corridor sample point's interpolated vector for one hour.

    This is a lightweight copy of FieldVector that does not carry sample_id
    to keep the World artifact lean.
    """
    x: float
    y: float
    raw_u: float
    raw_v: float
    magnitude: float
    dir_u: float
    dir_v: float


@dataclass
class World:
    """Top-level world object — the single source of truth for phase 02+."""

    # Raw graph topology
    graph: Optional[Graph] = None

    # Per-WAP per-hour summary: { hour_key → { wap_id → WAPTimeslot } }
    wap_timeslots: Dict[int, Dict[str, WAPTimeslot]] = field(default_factory=dict)

    # Corridor flow field: { hour_key → [FlowSample, …] }
    flow_timeslots: Dict[int, List[FlowSample]] = field(default_factory=dict)

    # ── Convenience accessors ───────────────────────────────────────────────

    def hours(self) -> List[int]:
        """Sorted list of all hour_keys present in the World."""
        return sorted(set(self.wap_timeslots.keys()) | set(self.flow_timeslots.keys()))

    def get_wap(self, hour_key: int, wap_id: str) -> Optional[WAPTimeslot]:
        return self.wap_timeslots.get(hour_key, {}).get(wap_id)

    def get_flow(self, hour_key: int) -> List[FlowSample]:
        return self.flow_timeslots.get(hour_key, [])

    def top_waps(self, hour_key: int, n: int = 10) -> List[WAPTimeslot]:
        """Return the n highest-traveler-count WAPs for a given hour."""
        bucket = self.wap_timeslots.get(hour_key, {})
        return sorted(bucket.values(), key=lambda w: w.traveler_count, reverse=True)[:n]

    # ── Persistence ─────────────────────────────────────────────────────────

    def output(self, path: str) -> None:
        save_draft(self, path)

    @classmethod
    def load(cls, path: str) -> "World":
        return load_draft(path)

    # ── Stats helper ────────────────────────────────────────────────────────

    def summary(self) -> str:
        n_hours   = len(self.hours())
        n_wap_obs = sum(len(v) for v in self.wap_timeslots.values())
        n_samples = sum(len(v) for v in self.flow_timeslots.values())
        return (
            f"World | {n_hours} hours | "
            f"{n_wap_obs} WAP-timeslots | "
            f"{n_samples} corridor field samples"
        )


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------

run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = [
    f"data/artifacts/runs/{run_id}/world/final_graph.pkl",
    f"data/artifacts/runs/{run_id}/world/final_journeys.pkl",
    f"data/artifacts/runs/{run_id}/world/final_field.pkl",
]
OUTPUTS = [f"data/artifacts/runs/{run_id}/world/final_world.pkl"]

HOUR_MS = 3_600_000
EPS     = 1e-9


# ---------------------------------------------------------------------------
# Assembly helpers
# ---------------------------------------------------------------------------

def _build_wap_timeslots(
    journeys_data: InterpolatedJourneysData,
    svg_path: str = "data/raw/synthetic/export route.svg",
) -> Dict[int, Dict[str, WAPTimeslot]]:
    """Build WAPTimeslot records from the journey waypoints."""
    import re

    # Parse WAP SVG coordinates (same logic as step 07)
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = re.compile(r'<path\s+id="([^"]+)"\s+d="M\s*([\d.]+)\s+([\d.]+)')
        wap_coords: Dict[str, tuple] = {}
        for m in pattern.finditer(content):
            pid = m.group(1)
            if "__" not in pid:
                continue
            wap_a = pid.split("__", 1)[0]
            if wap_a not in wap_coords:
                wap_coords[wap_a] = (float(m.group(2)), float(m.group(3)))
    except Exception as e:
        print(f"  [warn] Could not parse SVG coords: {e}")
        wap_coords = {}

    # Accumulators: hour_key → wap_id → (sum_dx, sum_dy, {person_ids})
    acc: Dict[int, Dict[str, list]] = defaultdict(
        lambda: defaultdict(lambda: [0.0, 0.0, set()])
    )

    for journey in journeys_data.journeys:
        wps = journey.waypoints
        pid = journey.person_id

        # Count unique travelers per WAP per hour (from any waypoint ping)
        for wp in wps:
            hk = int(wp.timestamp // HOUR_MS) * HOUR_MS
            acc[hk][wp.wap_id][2].add(pid)

        # Accumulate displacement vectors for each transition
        for i in range(len(wps) - 1):
            wp      = wps[i]
            next_wp = wps[i + 1]
            if wp.wap_id == next_wp.wap_id:
                continue
            if wp.wap_id not in wap_coords or next_wp.wap_id not in wap_coords:
                continue
            xa, ya = wap_coords[wp.wap_id]
            xb, yb = wap_coords[next_wp.wap_id]
            hk = int(wp.timestamp // HOUR_MS) * HOUR_MS
            acc[hk][wp.wap_id][0] += (xb - xa)
            acc[hk][wp.wap_id][1] += (yb - ya)

    # Convert to WAPTimeslot records
    wap_timeslots: Dict[int, Dict[str, WAPTimeslot]] = {}
    for hk, wap_map in acc.items():
        wap_timeslots[hk] = {}
        for wap_id, (su, sv, people_set) in wap_map.items():
            mag = math.hypot(su, sv)
            du  = su / mag if mag > EPS else 0.0
            dv  = sv / mag if mag > EPS else 0.0
            wap_timeslots[hk][wap_id] = WAPTimeslot(
                wap_id        = wap_id,
                hour_key      = hk,
                raw_u         = su,
                raw_v         = sv,
                magnitude     = mag,
                dir_u         = du,
                dir_v         = dv,
                traveler_count= len(people_set),
            )

    return wap_timeslots


def _build_flow_timeslots(
    field_data: FieldData,
) -> Dict[int, List[FlowSample]]:
    """Convert FieldData into the lightweight FlowSample dict."""
    result: Dict[int, List[FlowSample]] = {}
    for hf in field_data.hourly_fields:
        result[hf.hour_key] = [
            FlowSample(
                x         = v.x,
                y         = v.y,
                raw_u     = v.raw_u,
                raw_v     = v.raw_v,
                magnitude = v.magnitude,
                dir_u     = v.dir_u,
                dir_v     = v.dir_v,
            )
            for v in hf.vectors
        ]
    return result


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

def run(progress_callback=None, **kwargs) -> None:
    def _prog(msg: str, frac: float = -1.0):
        print(msg)
        if progress_callback and frac >= 0.0:
            try:
                progress_callback(frac)
            except Exception:
                pass

    _prog("Step 8 | Loading phase-01 artifacts…", 0.0)
    graph: Graph                            = load_draft(INPUTS[0])
    journeys_data: InterpolatedJourneysData = load_draft(INPUTS[1])
    field_data: FieldData                   = load_draft(INPUTS[2])

    _prog("Step 8 | Building WAP timeslots (vectors + traveler counts)…", 0.1)
    wap_timeslots = _build_wap_timeslots(journeys_data)
    n_wap_obs = sum(len(v) for v in wap_timeslots.values())
    _prog(f"Step 8 | {n_wap_obs} WAP-timeslot records across "
          f"{len(wap_timeslots)} hours", 0.5)

    _prog("Step 8 | Converting corridor field samples to FlowSample…", 0.6)
    flow_timeslots = _build_flow_timeslots(field_data)
    n_samples = sum(len(v) for v in flow_timeslots.values())
    _prog(f"Step 8 | {n_samples} corridor field samples across "
          f"{len(flow_timeslots)} hours", 0.7)

    _prog("Step 8 | Assembling World object…", 0.8)
    world = World(
        graph          = graph,
        wap_timeslots  = wap_timeslots,
        flow_timeslots = flow_timeslots,
    )

    _prog(f"Step 8 | {world.summary()}", 0.9)
    _prog(f"Step 8 | Saving → {OUTPUTS[0]}", 0.95)
    world.output(OUTPUTS[0])
    _prog("Step 8 | Done ✓", 1.0)
