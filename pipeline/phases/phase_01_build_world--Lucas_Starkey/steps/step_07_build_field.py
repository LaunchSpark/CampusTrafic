"""
step_07_build_field.py
======================
Build a corridor-constrained, graph-distance-interpolated vector flow field
for every 1-hour window present in the journey data.

Inputs:
    final_graph.pkl       – Graph  (physical_edges, nodes, node_counts)
    final_journeys.pkl    – InterpolatedJourneysData
    export route.svg      – Bézier polylines for every corridor edge

Output:
    final_field.pkl       – FieldData  (hourly_fields, edge_samples)
"""
from __future__ import annotations

import heapq
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pipelineio.state import load_draft, save_draft
from .step_04_build_graph import Graph
from .step_06_interpolate_paths import InterpolatedJourneysData


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class EdgeSample:
    """A point sampled along a corridor edge polyline."""
    sample_id: str          # "{wap_a}__{wap_b}:{idx}"
    edge_id: str            # "wap_a__wap_b"
    wap_a: str
    wap_b: str
    x: float
    y: float
    dist_from_a: float      # arc-length distance along polyline to wap_a
    dist_from_b: float      # arc-length distance along polyline to wap_b
    tangent_x: float        # unit corridor tangent at this point
    tangent_y: float


@dataclass
class FieldVector:
    """Interpolated flow vector at one EdgeSample for one hour."""
    sample_id: str
    x: float
    y: float
    raw_u: float            # pre-normalization blended vector component
    raw_v: float
    magnitude: float        # |raw|  — use for colour / opacity
    dir_u: float            # unit direction (0 if magnitude=0)
    dir_v: float


@dataclass
class HourlyField:
    """All FieldVectors for a single 1-hour bucket."""
    hour_key: int           # epoch-ms of the hour's start (floored)
    vectors: List[FieldVector] = field(default_factory=list)


@dataclass
class FieldData:
    """Top-level artifact saved to disk."""
    edge_samples: List[EdgeSample] = field(default_factory=list)
    hourly_fields: List[HourlyField] = field(default_factory=list)

    def output(self, output_path: str) -> None:
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "FieldData":
        return load_draft(input_path)


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------

run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = [
    f"data/artifacts/runs/{run_id}/world/final_graph.pkl",
    f"data/artifacts/runs/{run_id}/world/final_journeys.pkl",
]
OUTPUTS = [f"data/artifacts/runs/{run_id}/world/final_field.pkl"]

SVG_PATH = "data/raw/synthetic/export route.svg"

# Tunable constants (overridable via pipeline_config kwargs)
SAMPLE_STEP_DEFAULT = 15.0      # SVG units between corridor samples
SIGMA_MULT_DEFAULT  = 2.0       # σ = sigma_mult × mean_edge_length
TANGENT_ALPHA_DEFAULT = 0.8     # 0 = pure raw blend, 1 = fully corridor-locked
BEZIER_SEGS         = 30        # linear segments per Bézier curve
HOUR_MS             = 3_600_000
EPS                 = 1e-9


# ---------------------------------------------------------------------------
# SVG parsing — cubic Bézier → polyline
# ---------------------------------------------------------------------------

def _bezier_point(p0, p1, p2, p3, t: float) -> Tuple[float, float]:
    """Cubic Bézier point at parameter t ∈ [0, 1]."""
    mt = 1.0 - t
    x = mt**3 * p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0]
    y = mt**3 * p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
    return (x, y)


def _parse_svg_edges(svg_path: str) -> Dict[str, List[Tuple[float, float]]]:
    """
    Parse every <path id="nodeA__nodeB" d="M … C … [C …]"> element.

    Returns:
        dict mapping "wap_a__wap_b" → polyline [(x,y), …]
        (start point is always wap_a's SVG position)
    """
    with open(svg_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r'<path\s+id="([^"]+)"\s+d="([^"]+)"',
        re.DOTALL
    )

    edges: Dict[str, List[Tuple[float, float]]] = {}

    for m in pattern.finditer(content):
        pid = m.group(1)
        d_str = m.group(2).strip()

        if "__" not in pid:
            continue  # not a corridor edge

        # Tokenise path data
        tokens = re.findall(r'[MCc]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', d_str)
        i = 0
        polyline: List[Tuple[float, float]] = []
        cur = (0.0, 0.0)

        while i < len(tokens):
            tok = tokens[i]
            if tok == "M":
                cur = (float(tokens[i+1]), float(tokens[i+2]))
                polyline.append(cur)
                i += 3
            elif tok == "C":
                # One or more cubic Bézier segments follow (6 numbers each)
                i += 1
                while i + 5 < len(tokens) and not tokens[i].isalpha():
                    p1 = (float(tokens[i]),   float(tokens[i+1]))
                    p2 = (float(tokens[i+2]), float(tokens[i+3]))
                    p3 = (float(tokens[i+4]), float(tokens[i+5]))
                    for k in range(1, BEZIER_SEGS + 1):
                        t = k / BEZIER_SEGS
                        polyline.append(_bezier_point(cur, p1, p2, p3, t))
                    cur = p3
                    i += 6
            else:
                i += 1  # skip unknown tokens

        if len(polyline) >= 2:
            edges[pid] = polyline

    return edges


def _arc_lengths(polyline: List[Tuple[float, float]]) -> List[float]:
    """Cumulative arc-lengths along the polyline (starts at 0)."""
    cum = [0.0]
    for i in range(1, len(polyline)):
        dx = polyline[i][0] - polyline[i-1][0]
        dy = polyline[i][1] - polyline[i-1][1]
        cum.append(cum[-1] + math.hypot(dx, dy))
    return cum


# ---------------------------------------------------------------------------
# WAP coordinate extraction (from SVG M-points)
# ---------------------------------------------------------------------------

def _extract_wap_coords(svg_path: str) -> Dict[str, Tuple[float, float]]:
    """
    Extract each WAP's (x, y) from the M-command of every corridor path.
    Multiple paths may reference the same WAP as endpoint; pick the first seen.
    """
    with open(svg_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'<path\s+id="([^"]+)"\s+d="M\s*([\d.]+)\s+([\d.]+)')
    coords: Dict[str, Tuple[float, float]] = {}

    for m in pattern.finditer(content):
        pid = m.group(1)
        if "__" not in pid:
            continue
        wap_a, wap_b = pid.split("__", 1)
        x, y = float(m.group(2)), float(m.group(3))
        if wap_a not in coords:
            coords[wap_a] = (x, y)

        # wap_b coordinate = last point of parsed polyline (handled elsewhere)

    return coords


# ---------------------------------------------------------------------------
# Corridor edge sampling
# ---------------------------------------------------------------------------

def _sample_corridor_edges(
    svg_edges: Dict[str, List[Tuple[float, float]]],
    step: float,
) -> List[EdgeSample]:
    """Walk every corridor edge polyline and emit evenly-spaced samples."""
    samples: List[EdgeSample] = []

    for edge_id, polyline in svg_edges.items():
        if "__" not in edge_id:
            continue

        wap_a, wap_b = edge_id.split("__", 1)
        cum = _arc_lengths(polyline)
        total_len = cum[-1]
        if total_len < EPS:
            continue

        dist = 0.0
        idx = 0
        while dist <= total_len + EPS:
            # Interpolate position along polyline at distance `dist`
            seg = 0
            for s in range(len(cum) - 1):
                if cum[s] <= dist <= cum[s+1]:
                    seg = s
                    break
            else:
                seg = len(cum) - 2

            seg_len = cum[seg+1] - cum[seg]
            t = (dist - cum[seg]) / seg_len if seg_len > EPS else 0.0
            x = polyline[seg][0] + t * (polyline[seg+1][0] - polyline[seg][0])
            y = polyline[seg][1] + t * (polyline[seg+1][1] - polyline[seg][1])

            # Tangent vector (forward direction along edge)
            dx = polyline[seg+1][0] - polyline[seg][0]
            dy = polyline[seg+1][1] - polyline[seg][1]
            mag = math.hypot(dx, dy)
            tx = dx / mag if mag > EPS else 1.0
            ty = dy / mag if mag > EPS else 0.0

            samples.append(EdgeSample(
                sample_id=f"{edge_id}:{idx}",
                edge_id=edge_id,
                wap_a=wap_a,
                wap_b=wap_b,
                x=x, y=y,
                dist_from_a=dist,
                dist_from_b=total_len - dist,
                tangent_x=tx,
                tangent_y=ty,
            ))
            idx += 1
            dist += step

    return samples


# ---------------------------------------------------------------------------
# All-pairs shortest paths from source nodes (Dijkstra)
# ---------------------------------------------------------------------------

def _dijkstra_from(
    start: str,
    adj: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    dist: Dict[str, float] = defaultdict(lambda: math.inf)
    dist[start] = 0.0
    heap = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj.get(u, {}).items():
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dict(dist)


def _all_pairs_sp(
    source_nodes: List[str],
    adj: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    return {n: _dijkstra_from(n, adj) for n in source_nodes}


# ---------------------------------------------------------------------------
# Hourly raw vectors
# ---------------------------------------------------------------------------

def _build_hourly_node_vectors(
    journeys_data: InterpolatedJourneysData,
    wap_coords: Dict[str, Tuple[float, float]],
) -> Tuple[Dict[int, Dict[str, Tuple[float, float]]], int, int]:
    """
    For each 1-hour bucket, compute the *raw accumulated* vector at each WAP.
    Returns (hourly_vectors, t_min_ms, t_max_ms).

    raw vector = sum of all (dx, dy) displacements *from* that WAP
    """
    hourly: Dict[int, Dict[str, List]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))

    t_min, t_max = math.inf, -math.inf

    for journey in journeys_data.journeys:
        wps = journey.waypoints
        for i in range(len(wps) - 1):
            wp      = wps[i]
            next_wp = wps[i + 1]

            if wp.wap_id not in wap_coords or next_wp.wap_id not in wap_coords:
                continue
            if wp.wap_id == next_wp.wap_id:
                continue

            t = wp.timestamp
            t_min = min(t_min, t)
            t_max = max(t_max, t)

            hk = int(t // HOUR_MS) * HOUR_MS

            xa, ya = wap_coords[wp.wap_id]
            xb, yb = wap_coords[next_wp.wap_id]

            hourly[hk][wp.wap_id][0] += (xb - xa)
            hourly[hk][wp.wap_id][1] += (yb - ya)
            hourly[hk][wp.wap_id][2] += 1

    # Convert to final dict[hk][wap_id] = (u, v)  ← raw sum (not mean)
    result: Dict[int, Dict[str, Tuple[float, float]]] = {}
    for hk, wap_map in hourly.items():
        result[hk] = {}
        for wap_id, (su, sv, cnt) in wap_map.items():
            if cnt > 0:
                result[hk][wap_id] = (su, sv)

    t_min_i = int(t_min) if t_min != math.inf else 0
    t_max_i = int(t_max) if t_max != -math.inf else 0
    return result, t_min_i, t_max_i


# ---------------------------------------------------------------------------
# Field interpolation for one hour
# ---------------------------------------------------------------------------

def _interpolate_hour(
    samples: List[EdgeSample],
    node_vectors: Dict[str, Tuple[float, float]],  # wap → (u, v)
    sp: Dict[str, Dict[str, float]],               # sp[src][node] = dist
    sigma: float,
    tangent_alpha: float,
) -> List[FieldVector]:
    """Compute a FieldVector for every EdgeSample for one hour bucket."""
    vectors: List[FieldVector] = []

    if not node_vectors:
        return vectors

    # Pre-flatten source nodes for fast iteration
    source_list = list(node_vectors.items())  # [(wap_id, (u,v)), …]

    for s in samples:
        wu = 0.0
        wv = 0.0
        w_sum = 0.0

        for src_id, (su, sv) in source_list:
            src_sp = sp.get(src_id, {})
            d_a = src_sp.get(s.wap_a, math.inf)
            d_b = src_sp.get(s.wap_b, math.inf)
            d_sample = min(d_a + s.dist_from_a, d_b + s.dist_from_b)

            if d_sample == math.inf:
                continue

            strength = math.hypot(su, sv) + EPS
            w = strength * math.exp(-(d_sample ** 2) / (2 * sigma ** 2 + EPS))

            wu += w * su
            wv += w * sv
            w_sum += w

        if w_sum < EPS:
            continue

        raw_u = wu / w_sum
        raw_v = wv / w_sum

        # --- Corridor tangent projection ---
        dot = raw_u * s.tangent_x + raw_v * s.tangent_y
        proj_u = dot * s.tangent_x
        proj_v = dot * s.tangent_y
        final_u = tangent_alpha * proj_u + (1.0 - tangent_alpha) * raw_u
        final_v = tangent_alpha * proj_v + (1.0 - tangent_alpha) * raw_v

        mag = math.hypot(final_u, final_v)
        if mag > EPS:
            dir_u = final_u / mag
            dir_v = final_v / mag
        else:
            dir_u = dir_v = 0.0

        vectors.append(FieldVector(
            sample_id=s.sample_id,
            x=s.x, y=s.y,
            raw_u=final_u, raw_v=final_v,
            magnitude=mag,
            dir_u=dir_u, dir_v=dir_v,
        ))

    return vectors


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

def run(
    sample_step: float = SAMPLE_STEP_DEFAULT,
    sigma_multiplier: float = SIGMA_MULT_DEFAULT,
    tangent_alpha: float = TANGENT_ALPHA_DEFAULT,
    progress_callback=None,
    **kwargs,
) -> None:
    # --- Load inputs ---
    graph: Graph                            = load_draft(INPUTS[0])
    journeys_data: InterpolatedJourneysData = load_draft(INPUTS[1])

    def _prog(msg: str, frac: float = -1.0):
        print(msg)
        if progress_callback and frac >= 0.0:
            try:
                progress_callback(frac)
            except Exception:
                pass

    _prog("Step 7 | Parsing SVG edge geometry…", 0.0)
    svg_edges  = _parse_svg_edges(SVG_PATH)
    wap_coords = _extract_wap_coords(SVG_PATH)

    # Fill in wap_b coords (last polyline point) for any wap_b not yet seen
    for edge_id, polyline in svg_edges.items():
        if "__" not in edge_id:
            continue
        _, wap_b = edge_id.split("__", 1)
        if wap_b not in wap_coords and polyline:
            wap_coords[wap_b] = polyline[-1]

    _prog(f"Step 7 | {len(svg_edges)} corridor edges, {len(wap_coords)} WAP coordinates", 0.05)

    # --- Sample corridors ---
    _prog(f"Step 7 | Sampling corridor edges (step={sample_step} SVG units)…", 0.1)
    samples = _sample_corridor_edges(svg_edges, sample_step)
    _prog(f"Step 7 | {len(samples)} corridor sample points", 0.15)

    # --- Compute mean edge length for σ ---
    edge_lengths: List[float] = []
    for polyline in svg_edges.values():
        cum = _arc_lengths(polyline)
        if cum:
            edge_lengths.append(cum[-1])
    mean_edge_len = (sum(edge_lengths) / len(edge_lengths)) if edge_lengths else 100.0
    sigma = sigma_multiplier * mean_edge_len
    _prog(f"Step 7 | σ = {sigma:.1f} SVG units (mean edge len = {mean_edge_len:.1f})", 0.2)

    # --- All-pairs shortest paths from WAPs that can be source nodes ---
    all_waps = set(wap_coords.keys()) & set(graph.physical_edges.keys())
    _prog(f"Step 7 | Running Dijkstra from {len(all_waps)} WAP nodes…", 0.25)
    sp = _all_pairs_sp(list(all_waps), graph.physical_edges)

    # --- Build hourly node vectors ---
    _prog("Step 7 | Extracting hourly raw node vectors from journeys…", 0.35)
    hourly_vectors, t_min, t_max = _build_hourly_node_vectors(journeys_data, wap_coords)
    _prog(f"Step 7 | {len(hourly_vectors)} hour buckets  "
          f"(t_min={t_min // HOUR_MS}h  t_max={(t_max // HOUR_MS)+1}h)", 0.4)

    # --- Interpolate field for each hour ---
    field_data = FieldData(edge_samples=samples)

    for h_idx, (hk, node_vecs) in enumerate(sorted(hourly_vectors.items())):
        h_frac = 0.4 + 0.55 * (h_idx / max(1, len(hourly_vectors)))
        _prog(f"Step 7 | Interpolating hour {h_idx+1}/{len(hourly_vectors)} "
              f"({len(node_vecs)} source nodes)…", h_frac)

        hour_vectors = _interpolate_hour(
            samples, node_vecs, sp, sigma, tangent_alpha
        )
        field_data.hourly_fields.append(HourlyField(
            hour_key=hk,
            vectors=hour_vectors,
        ))

    total_vecs = sum(len(hf.vectors) for hf in field_data.hourly_fields)
    _prog(f"Step 7 | Done. {total_vecs} total field vectors across "
          f"{len(field_data.hourly_fields)} hours. Saving…", 0.98)
    field_data.output(OUTPUTS[0])
    _prog(f"Step 7 | Saved → {OUTPUTS[0]}", 1.0)
