"""
PIPELINE STEP TEMPLATE
======================
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import os

from typing import Any

from pipelineio.state import load_draft, save_draft

@dataclass
class BaselineTransitionModel:
    # Global metrics
    transition_counts: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    transition_probs: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(dict))
    
    # Hourly metrics
    hourly_counts: dict[int, dict[str, dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )

    def process(self, journeys_data: Any, time_threshold_minutes: int = 120, progress_callback=None) -> None:
        total_users = len(journeys_data.journeys)
        
        # 1. Iterate over the pre-built Journeys
        for idx, journey in enumerate(journeys_data.journeys):
            if progress_callback and idx % max(1, total_users // 25) == 0:
                progress_callback(idx / max(1, total_users) * 0.9)
                
            waypoints = journey.waypoints
            
            # 2. Count Transitions
            for i in range(len(waypoints) - 1):
                wp_a = waypoints[i]
                wp_b = waypoints[i+1]
                
                # Timestamps are in ms, convert difference to minutes
                time_diff_minutes = (wp_b.timestamp - wp_a.timestamp) / (1000.0 * 60.0)
                
                node_a = wp_a.wap_id
                node_b = wp_b.wap_id
                
                if node_a != node_b and time_diff_minutes <= time_threshold_minutes:
                    # Global count
                    self.transition_counts[node_a][node_b] += 1
                    
                    # Hourly count
                    try:
                        journey_hour = datetime.fromtimestamp(wp_a.timestamp / 1000.0).hour
                        self.hourly_counts[journey_hour][node_a][node_b] += 1
                    except Exception:
                        pass # Handle edge-cases where the timestamp is malformed

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

# Use interpolated journeys produced by world step 06.
INPUTS = [f'data/artifacts/runs/{run_id}/world/final_journeys.pkl']
OUTPUTS = [f'data/artifacts/runs/{run_id}/model_tree/baseline_transitions.pkl']

def run(is_synthetic: bool = True, time_threshold_minutes: int = 120, custom_param: int = 10, progress_callback=None) -> None:
    target_input = INPUTS[0]
    target_output = OUTPUTS[0]
    
    if is_synthetic:
        target_input = target_input.replace('runs/' + run_id, 'synthetic_drafts')
        target_output = target_output.replace('runs/' + run_id, 'synthetic_drafts')
    
    # 1. Load interpolated journeys data from final_journeys.pkl
    journeys_data = load_draft(target_input)
    
    # 2. Instantiate model
    model = BaselineTransitionModel()
    
    # 3. Execute logic
    model.process(journeys_data, time_threshold_minutes=time_threshold_minutes, progress_callback=progress_callback)
    
    # 4. Save output
    model.output(target_output)