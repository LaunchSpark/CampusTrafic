import os
import re
import sys
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from pipeline.run_logic.ast_runner import load_step_module
from pipelineio.state import load_draft
from datetime import datetime, timezone


def load_required_modules():
    phase_dir = PROJECT_ROOT / "pipeline" / "phases" / "phase_01_build_world--Lucas_Starkey"
    load_step_module(phase_dir, phase_dir / "steps" / "step_01_build_devices.py")
    load_step_module(phase_dir, phase_dir / "steps" / "step_03_resolve_people.py")
    load_step_module(phase_dir, phase_dir / "steps" / "step_04_build_graph.py")
    load_step_module(phase_dir, phase_dir / "steps" / "step_05_build_journeys.py")
    load_step_module(phase_dir, phase_dir / "steps" / "step_06_interpolate_paths.py")

def load_graph_artifact(run_id="EXAMPLE_RUN_ID"):
    path = str(PROJECT_ROOT / f"data/artifacts/runs/{run_id}/world/final_graph.pkl")
    print("Loading graph artifact from:", path)
    obj = load_draft(path)
    print("Loaded object type:", type(obj))
    return obj

def load_world_artifact(run_id="EXAMPLE_RUN_ID"):
    path = str(PROJECT_ROOT / f"data/artifacts/runs/{run_id}/world/final_world.pkl")
    print("Loading world artifact from:", path)
    obj = load_draft(path)
    print("Loaded object type:", type(obj))
    return obj

def load_field_artifact(run_id="EXAMPLE_RUN_ID"):
    path = str(PROJECT_ROOT / f"data/artifacts/runs/{run_id}/world/final_field.pkl")
    print("Loading field artifact from:", path)
    obj = load_draft(path)
    print("Loaded object type:", type(obj))
    return obj

def graph_to_edges(graph):

    edges = []
    seen = set()

    for u, neighbors in graph.physical_edges.items():
        for v in neighbors:
            edge = tuple(sorted((u, v)))
            if edge not in seen:
                seen.add(edge)
                edges.append(edge)

    return edges


def parse_svg_coords_and_edges(svg_path):

    svg_path = Path(svg_path)
    tree = ET.parse(svg_path)
    root = tree.getroot()

    ns = {"svg": "http://www.w3.org/2000/svg"}
    paths = root.findall(".//svg:path", ns)
    if not paths:
        paths = root.findall(".//path")

    coord_accumulator = {}
    edge_list = []

    number_pattern = re.compile(r"-?\d+(?:\.\d+)?")

    for p in paths:
        pid = p.attrib.get("id", "")
        d = p.attrib.get("d", "")

        if "__" not in pid or not d:
            continue

        u, v = pid.split("__", 1)
        nums = [float(x) for x in number_pattern.findall(d)]

        if len(nums) < 4:
            continue

        x1, y1 = nums[0], nums[1]
        x2, y2 = nums[-2], nums[-1]

        coord_accumulator.setdefault(u, []).append((x1, y1))
        coord_accumulator.setdefault(v, []).append((x2, y2))

        edge = tuple(sorted((u, v)))
        if edge not in edge_list:
            edge_list.append(edge)

    coords = {}
    for node, pts in coord_accumulator.items():
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        coords[node] = (sum(xs) / len(xs), sum(ys) / len(ys))

    return coords, edge_list


def build_nodes_from_coords(graph, coords):

    return {
        node_id: {"x": coords[node_id][0], "y": coords[node_id][1]}
        for node_id in graph.nodes.keys()
        if node_id in coords
    }


def _get_first_attr(obj, names, default=None):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _extract_sample_fields(sample):
    x = _get_first_attr(sample, ["x"], None)
    y = _get_first_attr(sample, ["y"], None)

    if (x is None or y is None) and hasattr(sample, "point"):
        point = getattr(sample, "point")
        if isinstance(point, (tuple, list)) and len(point) >= 2:
            x, y = point[0], point[1]

    u = _get_first_attr(sample, ["u", "raw_u"], None)
    v = _get_first_attr(sample, ["v", "raw_v"], None)
    magnitude = _get_first_attr(sample, ["magnitude", "mag", "count", "n"], 0)
    hour = _get_first_attr(sample, ["hour"], None)

    if hour is None:
        ts = _get_first_attr(sample, ["timestamp", "time", "ts"], None)
        if ts is not None and hasattr(ts, "hour"):
            hour = ts.hour

    return x, y, u, v, magnitude, hour


def _find_samples_container(obj):
    for name in [
        "flow_samples",
        "field_samples",
        "corridor_field_samples",
        "samples",
    ]:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None

from datetime import datetime, timezone

def _coerce_hour_key(key):
    if hasattr(key, "hour"):
        return key.hour

    if isinstance(key, int):
        # handle epoch milliseconds
        if key > 10**10:
            return datetime.fromtimestamp(key / 1000, tz=timezone.utc).hour
        return key

    if isinstance(key, float):
        if key > 10**10:
            return datetime.fromtimestamp(key / 1000, tz=timezone.utc).hour
        return int(key)

    if isinstance(key, str):
        key = key.strip()
        if key.isdigit():
            n = int(key)
            if n > 10**10:
                return datetime.fromtimestamp(n / 1000, tz=timezone.utc).hour
            return n

    return None


def _extract_sample_fields(sample):

    if isinstance(sample, dict):
        x = sample.get("x")
        y = sample.get("y")
        u = sample.get("u", sample.get("raw_u"))
        v = sample.get("v", sample.get("raw_v"))
        magnitude = sample.get("magnitude", sample.get("mag", sample.get("count", 0)))
        return x, y, u, v, magnitude

    x = getattr(sample, "x", None)
    y = getattr(sample, "y", None)

    if (x is None or y is None) and hasattr(sample, "point"):
        point = getattr(sample, "point")
        if isinstance(point, (tuple, list)) and len(point) >= 2:
            x, y = point[0], point[1]

    u = getattr(sample, "u", getattr(sample, "raw_u", None))
    v = getattr(sample, "v", getattr(sample, "raw_v", None))
    magnitude = getattr(sample, "magnitude", getattr(sample, "mag", getattr(sample, "count", 0)))

    return x, y, u, v, magnitude


def load_hour_slice(run_id="EXAMPLE_RUN_ID", hour=None):
    world = load_world_artifact(run_id)

    if not hasattr(world, "flow_timeslots"):
        raise RuntimeError("World object has no flow_timeslots")

    by_hour = {}

    for slot_key, samples in world.flow_timeslots.items():
        h = _coerce_hour_key(slot_key)
        if h is None:
            continue

        if isinstance(samples, dict):
            iterable = list(samples.values())
        else:
            iterable = list(samples)

        for sample in iterable:
            x, y, u, v, magnitude = _extract_sample_fields(sample)
            if x is None or y is None or u is None or v is None:
                continue

            by_hour.setdefault(h, []).append((x, y, u, v, magnitude))

    if not by_hour:
        raise RuntimeError("No usable flow data found in world.flow_timeslots")

    if hour is None:
        counts = {h: len(v) for h, v in by_hour.items()}
        hour = max(counts, key=counts.get)

    selected = by_hour.get(hour, [])
    if not selected:
        raise RuntimeError(f"No flow data found for hour {hour}")

    points = [(x, y) for x, y, _, _, _ in selected]
    vectors = [(u, v) for _, _, u, v, _ in selected]
    magnitudes = [m for _, _, _, _, m in selected]

    return hour, points, vectors, magnitudes

def get_available_buildings(graph):
    buildings = set()

    for node_id, meta in graph.nodes.items():
        building = meta.get("building")
        if building:
            buildings.add(building)
        else:
            prefix = node_id.split("-")[0]
            buildings.add(prefix)

    return sorted(buildings)


def filter_nodes_and_edges_by_prefix(nodes, edges, prefixes):
    filtered_nodes = {
        node_id: data
        for node_id, data in nodes.items()
        if any(node_id.startswith(prefix) for prefix in prefixes)
    }

    filtered_edges = [
        (u, v)
        for u, v in edges
        if u in filtered_nodes and v in filtered_nodes
    ]

    return filtered_nodes, filtered_edges


def filter_flow_to_near_nodes(nodes, points, vectors, magnitudes, radius=40):
    filtered_points = []
    filtered_vectors = []
    filtered_magnitudes = []

    node_coords = [(data["x"], data["y"]) for data in nodes.values()]

    for (x, y), vec, mag in zip(points, vectors, magnitudes):
        keep = False
        for nx, ny in node_coords:
            dx = x - nx
            dy = y - ny
            if dx * dx + dy * dy <= radius * radius:
                keep = True
                break

        if keep:
            filtered_points.append((x, y))
            filtered_vectors.append(vec)
            filtered_magnitudes.append(mag)

    return filtered_points, filtered_vectors, filtered_magnitudes


def load_wap_counts_for_hour(run_id="EXAMPLE_RUN_ID", hour=None):
    world = load_world_artifact(run_id)

    if not hasattr(world, "wap_timeslots"):
        return {}

    hourly = {}

    for slot_key, samples in world.wap_timeslots.items():
        h = _coerce_hour_key(slot_key)
        if h is None:
            continue

        if isinstance(samples, dict):
            iterable = list(samples.items())
        else:
            iterable = list(samples)

        for item in iterable:
            # handle dict-style: wap_id -> sample
            if isinstance(item, tuple) and len(item) == 2:
                wap_id, sample = item
                count = getattr(sample, "count", None)
                if count is None and isinstance(sample, dict):
                    count = sample.get("count", 1)
                if count is None:
                    count = 1
                hourly.setdefault(h, {})[wap_id] = count

    if not hourly:
        return {}

    if hour is None:
        hour = max(hourly, key=lambda k: sum(hourly[k].values()))

    return hourly.get(hour, {})

def aggregate_hourly_vectors_to_nodes(nodes, points, vectors, magnitudes=None):
    aggregated_points = []
    aggregated_vectors = []
    aggregated_magnitudes = []

    if magnitudes is None:
        magnitudes = [1.0] * len(points)

    for node_id, node_data in nodes.items():
        nx, ny = node_data["x"], node_data["y"]

        total_u = 0.0
        total_v = 0.0
        total_m = 0.0

        for (x, y), (u, v), m in zip(points, vectors, magnitudes):
            dx = x - nx
            dy = y - ny
            dist2 = dx * dx + dy * dy

            weight = 1.0 / (dist2 + 1.0)

            total_u += u * m * weight
            total_v += v * m * weight
            total_m += m * weight

        if total_m > 0:
            aggregated_points.append((nx, ny))
            aggregated_vectors.append((total_u / total_m, total_v / total_m))
            aggregated_magnitudes.append(total_m)

    return aggregated_points, aggregated_vectors, aggregated_magnitudes

def extract_floor_from_graph_meta(node_meta):
    room = node_meta.get("room", "")

    digits = ""
    for c in room:
        if c.isdigit():
            digits += c
        else:
            break

    if not digits:
        return None

    return int(digits[0])


def filter_nodes_and_edges_by_floor(nodes, edges, graph_meta, floor):
    filtered_nodes = {
        node_id: data
        for node_id, data in nodes.items()
        if node_id in graph_meta and extract_floor_from_graph_meta(graph_meta[node_id]) == floor
    }

    filtered_edges = [
        (u, v)
        for u, v in edges
        if u in filtered_nodes and v in filtered_nodes
    ]

    return filtered_nodes, filtered_edges


def get_available_floors_for_building(graph_meta, building):
    floors = set()

    for node_id, meta in graph_meta.items():
        if not node_id.startswith(building):
            continue

        room = meta.get("room", "")
        digits = ""
        for c in room:
            if c.isdigit():
                digits += c
            else:
                break

        if digits:
            floors.add(int(digits[0]))

    return sorted(floors)