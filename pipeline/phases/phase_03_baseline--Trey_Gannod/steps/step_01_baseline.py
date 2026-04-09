"""
PIPELINE STEP TEMPLATE
======================

How to create a new pipeline step:
1. Copy this file into your target phase directory: `pipeline/phases/phase_XX_name/steps/step_YY_name.py`
2. Update the `INPUTS` and `OUTPUTS` lists with your desired artifact read/write paths.
3. Rename `YourDataClass` to represent the core anemic data structure you are building.
4. Write your business logic inside the methods of your dataclass.
5. Modify the `run()` function to accept your required hyperparameters.

About the Progress Bar:
-----------------------
If your step processes data in a loop and you want a live progress bar in the terminal:
1. Include `progress_callback=None` in your `run()` function signature.
2. Pass it down to your processing method.
3. Periodically call `progress_callback(float)` with a value between 0.0 and 1.0.
   Example: `progress_callback(current_idx / total_items)`
4. Best Practice: To prevent the UI drawing from slowing down your logic, only 
   trigger the callback every N iterations (e.g., `if idx % 50 == 0:`).

About Hyperparameters:
----------------------
Any arguments you add to the `run()` signature (except `progress_callback` and `is_synthetic`) 
will be automatically discovered by the orchestrator and appended to `PIPELINE_CONFIG` in `run.py`.

About Synthetic Data:
---------------------
The `is_synthetic` flag allows independent component testing. When True, the pipeline 
automatically replaces the `world_drafts` directory with `synthetic_drafts`. This lets you 
read/write mock data safely without polluting the main production cache.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import os

from pipelineio.state import load_draft, save_draft
from pipeline.phases.phase_01_build_world.steps.step_04_build_graph import Graph

@dataclass
class BaselineTransitionModel:
    # Global metrics
    transition_counts: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    transition_probs: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(dict))
    
    # NEW: Hourly metrics
    # Format: hourly_counts[hour_of_day][origin_node][destination_node] = raw_count
    hourly_counts: dict[int, dict[str, dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )

    def process(self, spatial_graph: Graph, time_threshold_minutes: int = 120, progress_callback=None) -> None:
        user_trajectories = defaultdict(list)
        items = list(spatial_graph.spatialGraph.items())
        total_waps = len(items)
        
        # 1. Build trajectories
        for idx, (wap_id, visits) in enumerate(items):
            if progress_callback and idx % max(1, total_waps // 25) == 0:
                progress_callback((idx / max(1, total_waps)) * 0.4)
                
            for person_device, trace in visits:
                user_trajectories[person_device].append((trace.timestamp, wap_id))

        # 2. Sort and Count Transitions
        total_users = len(user_trajectories)
        for idx, (person, trajectory) in enumerate(user_trajectories.items()):
            if progress_callback and idx % max(1, total_users // 25) == 0:
                progress_callback(0.4 + (idx / max(1, total_users)) * 0.5)
                
            trajectory.sort(key=lambda x: x[0]) 
            
            for i in range(len(trajectory) - 1):
                time_a, node_a = trajectory[i]
                time_b, node_b = trajectory[i+1]
                
                time_diff_minutes = (time_b - time_a).total_seconds() / 60
                
                if node_a != node_b and time_diff_minutes <= time_threshold_minutes:
                    # Global count
                    self.transition_counts[node_a][node_b] += 1
                    
                    # Hourly count (Using the hour the journey started)
                    journey_hour = time_a.hour
                    self.hourly_counts[journey_hour][node_a][node_b] += 1

        # 3. Calculate Global Significance
        for origin, destinations in self.transition_counts.items():
            total_outbound = sum(destinations.values())
            for destination, count in destinations.items():
                self.transition_probs[origin][destination] = count / total_outbound

        # 4. Standardize dicts for clean pickling
        if progress_callback:
            progress_callback(0.99)
            
        self.transition_counts = {k: dict(v) for k, v in self.transition_counts.items()}
        self.transition_probs = {k: dict(v) for k, v in self.transition_probs.items()}
        self.hourly_counts = {
            hour: {orig: dict(dests) for orig, dests in origin_data.items()}
            for hour, origin_data in self.hourly_counts.items()
        }

    def output(self, output_path: str) -> None:
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "BaselineTransitionModel":
        return load_draft(input_path)

# Environment and Paths
run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')
INPUTS = [f'data/artifacts/runs/{run_id}/world/final_graph.pkl']
OUTPUTS = [f'data/artifacts/runs/{run_id}/model_tree/baseline_transitions.pkl']

def run(is_synthetic: bool = True, time_threshold_minutes: int = 120, progress_callback=None) -> None:
    target_input = INPUTS[0]
    target_output = OUTPUTS[0]
    
    if is_synthetic:
        target_input = target_input.replace('runs/' + run_id, 'synthetic_drafts')
        target_output = target_output.replace('runs/' + run_id, 'synthetic_drafts')
    
    # 1. Load input graph
    input_graph = Graph.load(target_input)
    
    # 2. Instantiate model
    model = BaselineTransitionModel()
    
    # 3. Execute logic
    model.process(input_graph, time_threshold_minutes=time_threshold_minutes, progress_callback=progress_callback)
    
    # 4. Save output to model_tree/ as defined in MODELING_README.md
    model.output(target_output)