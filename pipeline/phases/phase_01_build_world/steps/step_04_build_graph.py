from collections import defaultdict
from dataclasses import dataclass, field

from pipelineio.state import load_draft, save_draft
from pipeline.phases.phase_01_build_world.steps.step_01_build_devices import Trace
from pipeline.phases.phase_01_build_world.steps.step_03_resolve_people import People
from pipeline.phases.phase_01_build_world.steps.step_02_build_wap_index import WAPIndex


@dataclass
class Graph:
    spatialGraph: dict[str, list[tuple[str, Trace]]] = field(default_factory=lambda: defaultdict(list))
    node_counts: dict[str, int] = field(default_factory=dict)

    def import_data(self, wap_index: WAPIndex, people: People) -> tuple[WAPIndex, People]:
        return wap_index, people

    def build(self, wap_index: WAPIndex, people: People) -> None:
        """
        1. Iterate through every entry in the pre-built WAP_Index.
        2. Use identityMap to translate DeviceID -> Person.primary.
        3. Map the original Trace reference to the Primary Identity.
        """
        for wap_id, (times, devices, trace_refs) in wap_index.index.items():
            for i in range(len(devices)):
                original_device: str = devices[i]
                trace: Trace = trace_refs[i]

                # Map to primary actor
                person_device = people.identityMap.get(original_device, original_device)
                
                self.spatialGraph[wap_id].append((person_device, trace))

        # Count unique people per node
        for wap_id, visits in self.spatialGraph.items():
            unique_people = {person for person, _ in visits}
            self.node_counts[wap_id] = len(unique_people)

    def output(self, output_path: str) -> None:
        # Standardize the dict before output
        self.spatialGraph = dict(self.spatialGraph)
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "Graph":
        return load_draft(input_path)


INPUTS = ['data/artifacts/world_drafts/02_wap_index.pkl', 'data/artifacts/world_drafts/03_people.pkl']

import os
run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')
OUTPUTS = [f'data/artifacts/runs/{run_id}/world/final_graph.pkl']

def run(is_synthetic: bool = True) -> None:
    # Allow independent step testing by overriding inputs with static mock objects if synthetic
    target_input_1 = INPUTS[0]
    target_input_2 = INPUTS[1]
    target_output = OUTPUTS[0]
    
    if is_synthetic:
        target_input_1 = target_input_1.replace('world_drafts', 'synthetic_drafts')
        target_input_2 = target_input_2.replace('world_drafts', 'synthetic_drafts')
        target_output = target_output.replace('world_drafts', 'synthetic_drafts')

    wap_index = WAPIndex.load(target_input_1)
    people = People.load(target_input_2)
    
    graph = Graph() # Changed from WorldGraph to Graph to match existing class
    graph.import_data(wap_index, people)
    graph.build(wap_index, people) # Changed from clean/process to build to match existing class methods
    graph.output(target_output)
