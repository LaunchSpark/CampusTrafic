from collections import defaultdict
from dataclasses import dataclass, field
import re
import os

from pipelineio.state import load_draft, save_draft
from .step_03_resolve_people import People
from .step_02_build_wap_index import WAPIndex


@dataclass
class Graph:
    nodes: dict[str, dict[str, str]] = field(default_factory=dict)
    node_counts: dict[str, int] = field(default_factory=dict)
    physical_edges: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(dict))

    def import_data(self, wap_index: WAPIndex, people: People) -> tuple[WAPIndex, People]:
        return wap_index, people

    def build(self, wap_index: WAPIndex, people: People, is_synthetic: bool = True) -> None:
        """
        1. Parse every known WAP into spatial metadata.
        2. Resolve identity counts directly from the inverted index.
        3. Load physical routing constraints from the SVG topologic map.
        """
        for wap_id, (times, devices, trace_refs) in wap_index.index.items():
            # Identity mapping
            unique_people = {people.identityMap.get(d, d) for d in devices}
            self.node_counts[wap_id] = len(unique_people)
            
            # Spatial metadata
            parts = wap_id.split('-')
            building = parts[0] if len(parts) > 0 else "UNKNOWN"
            room = parts[1] if len(parts) > 1 else "UNKNOWN"
            if room.startswith("RM"):
                room = room[2:]
            sub_room = "-".join(parts[2:]) if len(parts) > 2 else "NONE"
            
            self.nodes[wap_id] = {
                "building": building,
                "room": room,
                "subRoom": sub_room
            }

        # Load topological SVG edges
        self._load_svg_adjacency_matrix(is_synthetic)

    def _load_svg_adjacency_matrix(self, is_synthetic: bool) -> None:
        """
        Parses SVG strings to define true physical adjacency.
        WAPs within the same building are physically adjacent (weight = 20,000ms).
        """
        if is_synthetic:
            svg_path = "data/raw/synthetic/export route.svg"
            try:
                with open(svg_path, "r", encoding="utf-8") as f:
                    content = f.read()
                matches = re.findall(r'id="([^"]+)__([^"]+)"', content)
                for w1, w2 in matches:
                    self.physical_edges[w1][w2] = 20000.0  # Base 20 seconds
                    self.physical_edges[w2][w1] = 20000.0
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
                self.physical_edges[w1][w2] = 20000.0
                self.physical_edges[w2][w1] = 20000.0
                
        b_names = sorted(list(buildings.keys()))
        for i in range(len(b_names) - 1):
            if buildings[b_names[i]] and buildings[b_names[i+1]]:
                w1 = buildings[b_names[i]][0]
                w2 = buildings[b_names[i+1]][0]
                self.physical_edges[w1][w2] = 120000.0 # Base 2 min between buildings
                self.physical_edges[w2][w1] = 120000.0

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
    graph.build(wap_index, people, is_synthetic=is_synthetic)
    graph.output(target_output)
