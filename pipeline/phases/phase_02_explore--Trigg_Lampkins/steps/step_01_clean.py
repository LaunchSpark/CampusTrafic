"""
phase_02_explore / step_01_clean.py
====================================
Explore the world artifacts.

Current scope:
  - Load Graph, InterpolatedJourneysData, and FieldData from phase 01
  - Find the first Monday whose data falls in the 9:00–10:00 hour bucket
  - Pick 10 representative WAPs (highest unique-person volume that hour)
  - Print each WAP's flow vector and unique-person count for that hour
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pipelineio.state import load_draft, save_draft

# ---------------------------------------------------------------------------
# Phase 01 types (imported so pickling works when the module is loaded via
# ast_runner — they must be in scope before unpickling)
# ---------------------------------------------------------------------------
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_04_build_graph import Graph
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_06_interpolate_paths import (
    InterpolatedJourneysData,
)
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_07_build_field import FieldData

# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------
run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = [
    f"data/artifacts/runs/{run_id}/world/final_graph.pkl",
    f"data/artifacts/runs/{run_id}/world/final_journeys.pkl",
    f"data/artifacts/runs/{run_id}/world/final_field.pkl",
]
OUTPUTS: list[str] = []   # exploration only — no artifact written yet

TOP_N_WAPS      = 10
TARGET_HOUR     = 9        # 09:00 – 10:00
TARGET_WEEKDAY  = 0        # Monday (Python: Mon=0 … Sun=6)
HOUR_MS         = 3_600_000


# ---------------------------------------------------------------------------
# Data class (placeholder — stores exploration results for future steps)
# ---------------------------------------------------------------------------
@dataclass
class ExploreResult:
    hour_key: int = 0
    wap_rows: list[dict] = field(default_factory=list)

    def output(self, path: str) -> None:
        save_draft(self, path)

    @classmethod
    def load(cls, path: str) -> "ExploreResult":
        return load_draft(path)


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------
def run(
    is_synthetic: bool = True,
    custom_param: int = 10,
    progress_callback=None,
    **kwargs,
) -> None:
    # ── Load world artifacts ────────────────────────────────────────────────
    graph: Graph                            = load_draft(INPUTS[0])
    journeys_data: InterpolatedJourneysData = load_draft(INPUTS[1])
    field_data: FieldData                   = load_draft(INPUTS[2])

    # ── Find first Monday 9:00-10:00 hour bucket ───────────────────────────
    # FieldData stores hour_key as epoch-ms floored to the hour.
    # Walk sorted hour keys and pick the first one that is a Monday 9 AM.
    target_hk: int | None = None
    for hf in sorted(field_data.hourly_fields, key=lambda h: h.hour_key):
        dt = datetime.fromtimestamp(hf.hour_key / 1000.0, tz=timezone.utc)
        if dt.weekday() == TARGET_WEEKDAY and dt.hour == TARGET_HOUR:
            target_hk = hf.hour_key
            break

    if target_hk is None:
        print(f"No Monday {TARGET_HOUR}:00 hour found in the field data.")
        return

    target_dt = datetime.fromtimestamp(target_hk / 1000.0, tz=timezone.utc)
    print(f"\n{'='*60}")
    print(f"  First Monday {TARGET_HOUR}:00–{TARGET_HOUR+1}:00 bucket")
    print(f"  Date (UTC): {target_dt.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # ── Count unique people per WAP in that hour (from journeys) ────────────
    wap_people: dict[str, set[str]] = {}
    for journey in journeys_data.journeys:
        for wp in journey.waypoints:
            t = wp.timestamp
            if int(t // HOUR_MS) * HOUR_MS == target_hk:
                wap_people.setdefault(wp.wap_id, set()).add(journey.person_id)

    # Sort by unique-person volume descending; take top N
    top_waps = sorted(wap_people.keys(),
                      key=lambda w: (-len(wap_people[w]), w))[:TOP_N_WAPS]

    available = len(wap_people)

    if not top_waps:
        print(f"No WAPs with journey data in the Monday {TARGET_HOUR}:00 hour bucket.")
        print("(Synthetic data may be sparse for this specific slot — "
              "try a different TARGET_HOUR or TARGET_WEEKDAY.)")
        return

    # ── Collect field vectors for those WAPs ────────────────────────────────
    # Map sample_id prefix → first matching FieldVector for the target hour
    hourly_field = next(
        (hf for hf in field_data.hourly_fields if hf.hour_key == target_hk),
        None,
    )

    # Build edge-sample lookup: wap_a or wap_b → list of vectors at that WAP's
    # immediate neighbourhood.  We pick the sample whose wap_a matches the WAP
    # (i.e. it is the corridor segment leaving from that node).
    sample_map: dict[str, list] = {}
    if hourly_field:
        sv_lookup: dict[str, object] = {v.sample_id: v for v in hourly_field.vectors}
        for es in field_data.edge_samples:
            sid = es.sample_id
            if sid in sv_lookup:
                fv = sv_lookup[sid]
                sample_map.setdefault(es.wap_a, []).append(fv)

    # ── Print summary table ─────────────────────────────────────────────────
    col = "{:<32} {:>8} {:>10} {:>10} {:>10} {:>10}"
    print(col.format("WAP ID", "People", "raw_u", "raw_v", "magnitude", "direction°"))
    print("-" * 80)

    result = ExploreResult(hour_key=target_hk)

    for wap_id in top_waps:
        people_count = len(wap_people.get(wap_id, set()))

        # Average all field vectors for samples on edges leaving this WAP
        fvs = sample_map.get(wap_id, [])
        if fvs:
            avg_raw_u  = sum(v.raw_u     for v in fvs) / len(fvs)
            avg_raw_v  = sum(v.raw_v     for v in fvs) / len(fvs)
            avg_mag    = sum(v.magnitude for v in fvs) / len(fvs)
            import math
            avg_dir_u  = sum(v.dir_u for v in fvs) / len(fvs)
            avg_dir_v  = sum(v.dir_v for v in fvs) / len(fvs)
            deg = math.degrees(math.atan2(avg_dir_v, avg_dir_u)) % 360
        else:
            avg_raw_u = avg_raw_v = avg_mag = 0.0
            deg = float("nan")

        row = {
            "wap_id":        wap_id,
            "people":        people_count,
            "raw_u":         round(avg_raw_u,  2),
            "raw_v":         round(avg_raw_v,  2),
            "magnitude":     round(avg_mag,    2),
            "direction_deg": round(deg,         1) if deg == deg else None,
        }
        result.wap_rows.append(row)

        print(col.format(
            wap_id[:32],
            people_count,
            f"{avg_raw_u:+.2f}",
            f"{avg_raw_v:+.2f}",
            f"{avg_mag:.2f}",
            f"{deg:.1f}°" if deg == deg else "  n/a",
        ))

    print(f"  Showing top {min(TOP_N_WAPS, available)} of {available} WAP(s) "
          f"with activity this hour.\n")
