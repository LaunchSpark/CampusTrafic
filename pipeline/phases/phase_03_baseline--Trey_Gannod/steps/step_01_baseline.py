"""
PIPELINE STEP: BASELINE TRANSITION MODEL (WITH TRAIN/TEST SPLIT + FLOW)
=======================================================================
Consumes the Phase 01 World object to build a transition probability model.
Uses 70% of the historical hours for training, saves the remaining 30% for evaluation.

Calculates:
- outbound_totals: Expected magnitude per node at a given hour.
- flow_matrix: Expected transition volume from one node to another at a given hour.

Includes a robust hierarchical fallback system for missing data combinations.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Setup local imports for the AST runner
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import Phase 01 classes so unpickling the World object works natively
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_08_package_world import World, WAPTimeslot


def chronological_split(world: World, train_ratio: float = 0.70) -> Tuple[List[int], List[int]]:
    """Splits the World's hour keys chronologically."""
    hours = world.hours()
    if not hours:
        raise ValueError("World object contains no hourly data.")
    
    split_index = max(1, int(len(hours) * train_ratio))
    return hours[:split_index], hours[split_index:]


@dataclass
class BaselineTransitionModel:
    """Predictive baseline model for campus traffic flow."""
    
    # Core Predictive Matrices
    outbound_totals: Dict[Tuple[int, str], float] = field(default_factory=dict)
    flow_matrix: Dict[Tuple[int, str, str], float] = field(default_factory=dict)
    
    # Fallback Matrices
    hour_node_means: Dict[Tuple[int, str], float] = field(default_factory=dict)
    global_node_means: Dict[str, float] = field(default_factory=dict)
    global_mean: float = 0.0
    
    # Topology Cache (Required to distribute fallbacks evenly across pathways)
    physical_edges: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def fit(cls, world: World, train_hours: List[int]) -> "BaselineTransitionModel":
        """Builds the probability matrices using the training subset of the World data."""
        hour_node_acc: Dict[Tuple[int, str], List[float]] = {}
        flow_acc: Dict[Tuple[int, str, str], List[float]] = {}
        global_node_acc: Dict[str, List[float]] = {}
        global_acc: List[float] = []
        
        # Cache the graph topology
        topology = {k: list(v.keys()) for k, v in world.graph.physical_edges.items()} if world.graph else {}

        for hk in train_hours:
            # Convert epoch ms hour_key to hour-of-day (0-23)
            # (Assuming UTC for simplicity, adjust with timezone offset if needed)
            hour_of_day = int((hk / 3600_000) % 24)
            
            timeslot_map = world.wap_timeslots.get(hk, {})
            
            for wap_id, timeslot in timeslot_map.items():
                mag = timeslot.magnitude
                
                # Accumulate values for averaging
                hour_node_acc.setdefault((hour_of_day, wap_id), []).append(mag)
                global_node_acc.setdefault(wap_id, []).append(mag)
                global_acc.append(mag)
                
                # Process Flow Matrix (Transitions)
                adjacent_nodes = topology.get(wap_id, [])
                if adjacent_nodes:
                    # BASELINE APPROXIMATION: 
                    # Without literal WAP coordinates mapped to the graph, we divide the 
                    # outgoing magnitude equally among all valid physical pathways.
                    # (A future upgraded model could use the dot product of timeslot.dir_u/v 
                    # against the literal edge geometry to weight these shares!)
                    flow_share = mag / len(adjacent_nodes)
                    for next_node in adjacent_nodes:
                        flow_acc.setdefault((hour_of_day, wap_id, next_node), []).append(flow_share)

        # Helper to average lists in a dictionary
        def dict_avg(d: dict) -> dict:
            return {k: sum(v) / len(v) for k, v in d.items() if v}

        return cls(
            outbound_totals=dict_avg(hour_node_acc),
            flow_matrix=dict_avg(flow_acc),
            hour_node_means=dict_avg(hour_node_acc),
            global_node_means=dict_avg(global_node_acc),
            global_mean=sum(global_acc) / len(global_acc) if global_acc else 0.0,
            physical_edges=topology
        )

    def predict_flow(self, hour_of_day: int, current_node: str, next_node: str) -> float:
        """Predict expected traffic volume between two nodes with hierarchical fallbacks."""
        hour_of_day = hour_of_day % 24
        
        # Plan A: Exact historical match for this specific hour and pathway
        exact_key = (hour_of_day, current_node, next_node)
        if exact_key in self.flow_matrix:
            return self.flow_matrix[exact_key]
            
        neighbor_count = max(1, len(self.physical_edges.get(current_node, [])))
        
        # Plan B: We know how busy the node is at this hour, distribute evenly
        hour_key = (hour_of_day, current_node)
        if hour_key in self.hour_node_means:
            return self.hour_node_means[hour_key] / neighbor_count
            
        # Plan C: We know how busy the node is generally, distribute evenly
        if current_node in self.global_node_means:
            return self.global_node_means[current_node] / neighbor_count
            
        # Plan D: Complete cold start
        return self.global_mean / neighbor_count

    def to_dict(self) -> dict[str, Any]:
        """Serialize model to a JSON-friendly format."""
        return {
            "outbound_totals": [{"hour": h, "node": c, "val": v} for (h, c), v in self.outbound_totals.items()],
            "flow_matrix": [{"hour": h, "curr": c, "next": n, "val": v} for (h, c, n), v in self.flow_matrix.items()],
            "hour_node_means": [{"hour": h, "node": c, "val": v} for (h, c), v in self.hour_node_means.items()],
            "global_node_means": self.global_node_means,
            "global_mean": self.global_mean,
            "physical_edges": self.physical_edges
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BaselineTransitionModel":
        """Deserialize model from JSON payload."""
        return cls(
            outbound_totals={(r["hour"], r["node"]): r["val"] for r in payload["outbound_totals"]},
            flow_matrix={(r["hour"], r["curr"], r["next"]): r["val"] for r in payload["flow_matrix"]},
            hour_node_means={(r["hour"], r["node"]): r["val"] for r in payload["hour_node_means"]},
            global_node_means=payload["global_node_means"],
            global_mean=payload["global_mean"],
            physical_edges=payload["physical_edges"]
        )

    def save(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BaselineTransitionModel":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)


# ---------------------------------------------------------------------------
# PIPELINE ENTRY POINT
# ---------------------------------------------------------------------------
run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = [f"data/artifacts/runs/{run_id}/world/final_world.pkl"]
OUTPUTS = [
    f"data/artifacts/runs/{run_id}/baseline/baseline_model.json",
    f"data/artifacts/runs/{run_id}/baseline/test_hours.json"
]

def run(is_synthetic: bool = False, train_ratio: float = 0.70, progress_callback=None, **kwargs) -> None:
    """Entry point for the AST Runner."""
    target_input = INPUTS[0]
    model_output = OUTPUTS[0]
    test_hours_output = OUTPUTS[1]
    
    if is_synthetic:
        target_input = target_input.replace('world', 'synthetic')
        model_output = model_output.replace('baseline', 'synthetic_baseline')
        test_hours_output = test_hours_output.replace('baseline', 'synthetic_baseline')
        
    print(f"Loading Phase 01 World Object from {target_input}...")
    world = World.load(target_input)
    
    print(f"Splitting data chronologically ({int(train_ratio*100)}/{int((1-train_ratio)*100)})...")
    train_hours, test_hours = chronological_split(world, train_ratio=train_ratio)
    
    print(f"Fitting Baseline Model on {len(train_hours)} training hours...")
    model = BaselineTransitionModel.fit(world, train_hours)
    
    print(f"Saving baseline model to {model_output}...")
    model.save(model_output)
    
    print(f"Saving test set metadata to {test_hours_output}...")
    test_path = Path(test_hours_output)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(json.dumps(test_hours, indent=2), encoding="utf-8")
    
    if progress_callback:
        progress_callback(1.0)