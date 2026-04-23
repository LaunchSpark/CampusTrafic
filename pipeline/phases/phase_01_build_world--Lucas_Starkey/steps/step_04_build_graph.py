from collections import defaultdict
from dataclasses import dataclass, field
import os
from pathlib import Path
import re

from pipelineio.state import load_draft, save_draft
from .step_03_resolve_people import People
from .step_02_build_wap_index import WAPIndex


SYNTHETIC_SVG_PATH = "../../../data/raw/synthetic/export route.svg"
REAL_SVG_SOURCE = "C:/Users/isaia/Desktop/CampusTrafic/data/raw/real/Brun Individual Vectors.svg"
BASE_EDGE_WEIGHT_MS = 20000.0
INTER_BUILDING_EDGE_WEIGHT_MS = 120000.0


def _parse_metadata_from_node_id(node_id: str) -> dict[str, str]:
    if node_id.lower().startswith("trav-"):
        return {
            "building": "BRUN",
            "room": "CONNECTOR",
            "subRoom": node_id,
        }

    parts = node_id.split("-")
    building = parts[0] if len(parts) > 0 else "UNKNOWN"
    room = parts[1] if len(parts) > 1 else "UNKNOWN"
    if room.startswith("RM"):
        room = room[2:]
    sub_room = "-".join(parts[2:]) if len(parts) > 2 else "NONE"

    return {
        "building": building,
        "room": room,
        "subRoom": sub_room,
    }


def _normalize_real_node_key(node_id: str) -> str:
    raw = node_id.strip()
    if not raw:
        return ""

    compact = raw.replace(" ", "").replace("trrav-", "trav-")

    trav_match = re.match(r"(?i)^trav-brun-?(.*)$", compact)
    if trav_match:
        return f"trav-brun{trav_match.group(1).lower()}"

    brun_rm_match = re.match(r"(?i)^brun-rm(.*)$", compact)
    if brun_rm_match:
        return f"brun-{brun_rm_match.group(1).lower()}"

    brun_match = re.match(r"(?i)^brun-?(.*)$", compact)
    if brun_match:
        return f"brun-{brun_match.group(1).lower()}"

    return compact.lower()


def _canonical_graph_node_id(normalized_key: str) -> str:
    if normalized_key.startswith("trav-"):
        return normalized_key
    if normalized_key.startswith("brun-"):
        return f"BRUN-{normalized_key[5:].upper()}"
    return normalized_key


def _select_preferred_wap_id(normalized_key: str, normalized_wap_groups: dict[str, list[str]], wap_index: WAPIndex) -> str:
    matched_waps = normalized_wap_groups[normalized_key]
    return max(
        matched_waps,
        key=lambda wap_id: (len(wap_index.index[wap_id][1]), wap_id),
    )


def _discover_real_svg_paths(svg_source: str | os.PathLike[str]) -> list[Path]:
    source = Path(svg_source)
    if source.is_dir():
        return sorted(path for path in source.iterdir() if path.suffix.lower() == ".svg")
    return [source]


def _parse_synthetic_svg_edges(svg_path: str | os.PathLike[str]) -> list[tuple[str, str]]:
    with open(svg_path, "r", encoding="utf-8") as f:
        content = f.read()
    return re.findall(r'id="([^"]+)__([^"]+)"', content)


def _parse_real_svg_graph(
    svg_source: str | os.PathLike[str],
) -> tuple[set[str], set[tuple[str, str]]]:
    normalized_nodes: set[str] = set()
    normalized_edges: set[tuple[str, str]] = set()

    for svg_path in _discover_real_svg_paths(svg_source):
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()

        for path_id in re.findall(r'<path\s+id="([^"]+)"', content):
            parts = [part.strip() for part in path_id.split(",") if part.strip()]
            if len(parts) != 2:
                continue

            left = _normalize_real_node_key(parts[0])
            right = _normalize_real_node_key(parts[1])
            if not left or not right:
                continue

            normalized_nodes.add(left)
            normalized_nodes.add(right)
            if left == right:
                continue
            normalized_edges.add(tuple(sorted((left, right))))

    return normalized_nodes, normalized_edges


@dataclass
class Graph:
    nodes: dict[str, dict[str, str]] = field(default_factory=dict)
    node_counts: dict[str, int] = field(default_factory=dict)
    physical_edges: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(dict))

    def import_data(self, wap_index: WAPIndex, people: People) -> tuple[WAPIndex, People]:
        return wap_index, people

    def build(
        self,
        wap_index: WAPIndex,
        people: People,
        is_synthetic: bool = True,
        real_svg_source: str = REAL_SVG_SOURCE,
    ) -> None:
        """
        1. Parse every known WAP into spatial metadata.
        2. Resolve identity counts directly from the inverted index.
        3. Load physical routing constraints from the SVG topologic map.
        """
        if not is_synthetic:
            self._build_real_graph(wap_index, people, real_svg_source)
            return

        for wap_id, (times, devices, trace_refs) in wap_index.index.items():
            # Identity mapping
            unique_people = {people.identityMap.get(d, d) for d in devices}
            self.node_counts[wap_id] = len(unique_people)
            
            # Spatial metadata
            self.nodes[wap_id] = _parse_metadata_from_node_id(wap_id)

        # Load topological SVG edges
        self._load_svg_adjacency_matrix(is_synthetic)

    def _build_real_graph(self, wap_index: WAPIndex, people: People, real_svg_source: str) -> None:
        normalized_svg_nodes, normalized_svg_edges = _parse_real_svg_graph(real_svg_source)
        if not normalized_svg_nodes:
            self._load_svg_adjacency_matrix(is_synthetic=False)
            return

        normalized_wap_groups: dict[str, list[str]] = defaultdict(list)
        for wap_id in wap_index.index.keys():
            normalized_key = _normalize_real_node_key(wap_id)
            if normalized_key in normalized_svg_nodes:
                normalized_wap_groups[normalized_key].append(wap_id)

        graph_node_ids = {
            normalized_key: (
                _select_preferred_wap_id(normalized_key, normalized_wap_groups, wap_index)
                if normalized_wap_groups[normalized_key]
                else _canonical_graph_node_id(normalized_key)
            )
            for normalized_key in normalized_svg_nodes
        }

        for normalized_key, graph_node_id in graph_node_ids.items():
            self.nodes[graph_node_id] = _parse_metadata_from_node_id(graph_node_id)

            matched_waps = normalized_wap_groups.get(normalized_key, [])
            if not matched_waps:
                continue

            unique_people = set()
            for wap_id in matched_waps:
                _, devices, _ = wap_index.index[wap_id]
                unique_people.update(people.identityMap.get(device_id, device_id) for device_id in devices)

            if unique_people:
                self.node_counts[graph_node_id] = len(unique_people)

        for left_key, right_key in normalized_svg_edges:
            left_node = graph_node_ids[left_key]
            right_node = graph_node_ids[right_key]
            self.physical_edges[left_node][right_node] = BASE_EDGE_WEIGHT_MS
            self.physical_edges[right_node][left_node] = BASE_EDGE_WEIGHT_MS

    def _load_svg_adjacency_matrix(self, is_synthetic: bool) -> None:
        """
        Parses SVG strings to define true physical adjacency.
        WAPs within the same building are physically adjacent (weight = 20,000ms).
        """
        if is_synthetic:
            try:
                matches = _parse_synthetic_svg_edges(SYNTHETIC_SVG_PATH)
                for w1, w2 in matches:
                    self.physical_edges[w1][w2] = BASE_EDGE_WEIGHT_MS
                    self.physical_edges[w2][w1] = BASE_EDGE_WEIGHT_MS
                return
            except Exception as e:
                print(f"Failed to load SVG for adjacency: {e}")
                
        # STUB Placeholder for generic building linear-linkages if real SVG isn't parsed
        buildings = defaultdict(list)
        for wap_id, meta in self.nodes.items():
            buildings[meta.get('building', 'UNKNOWN')].append(wap_id)
            
        for b_name, wap_list in buildings.items():
            wap_list.sort() # Ensure deterministic linear linkage
            for i in range(len(wap_list) - 1):
                w1 = wap_list[i]
                w2 = wap_list[i+1]
                self.physical_edges[w1][w2] = BASE_EDGE_WEIGHT_MS
                self.physical_edges[w2][w1] = BASE_EDGE_WEIGHT_MS
                
        b_names = sorted(list(buildings.keys()))
        for i in range(len(b_names) - 1):
            if buildings[b_names[i]] and buildings[b_names[i+1]]:
                w1 = buildings[b_names[i]][0]
                w2 = buildings[b_names[i+1]][0]
                self.physical_edges[w1][w2] = INTER_BUILDING_EDGE_WEIGHT_MS # Base 2 min between buildings
                self.physical_edges[w2][w1] = INTER_BUILDING_EDGE_WEIGHT_MS

    def output(self, output_path: str) -> None:
        # Standardize default dicts for pickling
        self.physical_edges = {k: dict(v) for k, v in self.physical_edges.items()}
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "Graph":
        return load_draft(input_path)


INPUTS = ['data/artifacts/world_drafts/02_wap_index.pkl', 'data/artifacts/world_drafts/03_people.pkl']

run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')
OUTPUTS = [f'data/artifacts/runs/{run_id}/world/final_graph.pkl']

# Note: The signature for run must match the arguments passed by ast_runner
def run(is_synthetic: bool = True, progress_callback=None, **kwargs) -> None:
    target_input_1 = INPUTS[0]
    target_input_2 = INPUTS[1]
    target_output = OUTPUTS[0]

    wap_index = WAPIndex.load(target_input_1)
    people = People.load(target_input_2)
    
    graph = Graph()
    graph.import_data(wap_index, people)
    graph.build(
        wap_index,
        people,
        is_synthetic=is_synthetic,
        real_svg_source=kwargs.get("real_svg_source", REAL_SVG_SOURCE),
    )
    graph.output(target_output)
