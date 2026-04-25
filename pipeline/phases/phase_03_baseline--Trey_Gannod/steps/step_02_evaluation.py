"""
PIPELINE STEP: BASELINE EVALUATION (PROBABILITY + FLOW)
======================================================
Evaluates the BaselineTransitionModel using held-out test data.
Now includes both node probability (busyness) and edge flow evaluation.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Setup local imports for the AST runner
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from step_01_baseline import BaselineTransitionModel

# Import Phase 01 World class for unpickling
from pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_08_package_world import World


@dataclass
class EvaluationResult:
    node_rmse: float
    node_r2: float
    edge_rmse: float
    edge_r2: float
    n_samples: int


def evaluate_model(
    world: World, 
    model: BaselineTransitionModel, 
    test_hours: list[int], 
    output_dir: Path
) -> EvaluationResult:
    """Evaluate baseline model against the hidden test hours."""
    y_true_node, y_pred_node = [], []
    y_true_edge, y_pred_edge = [], []

    topology = {k: list(v.keys()) for k, v in world.graph.physical_edges.items()} if world.graph else {}

    for hk in test_hours:
        hour_of_day = int((hk / 3600_000) % 24)
        timeslot_map = world.wap_timeslots.get(hk, {})

        for wap_id, timeslot in timeslot_map.items():
            mag = timeslot.magnitude
            y_true_node.append(mag)

            # Node outbound prediction (using fallbacks)
            pred_mag = model.hour_node_means.get(
                (hour_of_day, wap_id),
                model.global_node_means.get(wap_id, model.global_mean)
            )
            y_pred_node.append(pred_mag)

            # Edge flow predictions
            adjacent_nodes = topology.get(wap_id, [])
            if adjacent_nodes:
                # Ground truth approximation: equal split (mirrors baseline assumption)
                flow_share = mag / len(adjacent_nodes)
                for next_node in adjacent_nodes:
                    y_true_edge.append(flow_share)
                    
                    # Model's prediction for this specific edge
                    pred_flow = model.predict_flow(hour_of_day, wap_id, next_node)
                    y_pred_edge.append(pred_flow)

    def compute_metrics(yt: list[float], yp: list[float]) -> tuple[float, float]:
        if not yt: return 0.0, 0.0
        yt_arr, yp_arr = np.array(yt), np.array(yp)
        rmse = float(np.sqrt(np.mean((yt_arr - yp_arr)**2)))
        ss_res = np.sum((yt_arr - yp_arr)**2)
        ss_tot = np.sum((yt_arr - np.mean(yt_arr))**2)
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
        return rmse, r2

    node_rmse, node_r2 = compute_metrics(y_true_node, y_pred_node)
    edge_rmse, edge_r2 = compute_metrics(y_true_edge, y_pred_edge)

    output_dir.mkdir(parents=True, exist_ok=True)
    
    if y_true_node:
        _plot_predicted_vs_actual(
            np.array(y_true_node), np.array(y_pred_node), 
            output_dir / "node_pred_vs_actual.png", "Node Magnitude"
        )
        _plot_error_distribution(
            np.array(y_true_node) - np.array(y_pred_node), 
            output_dir / "node_error_dist.png"
        )
        
    if y_true_edge:
        _plot_predicted_vs_actual(
            np.array(y_true_edge), np.array(y_pred_edge), 
            output_dir / "edge_pred_vs_actual.png", "Edge Flow"
        )

    return EvaluationResult(node_rmse, node_r2, edge_rmse, edge_r2, len(y_true_node))


def _plot_predicted_vs_actual(y_true: np.ndarray, y_pred: np.ndarray, path: Path, title_prefix: str) -> None:
    plt.figure(figsize=(8, 6))
    plt.scatter(y_true, y_pred, alpha=0.3, edgecolors="none", s=10)

    lo = min(float(y_true.min()), float(y_pred.min()))
    hi = max(float(y_true.max()), float(y_pred.max()))
    plt.plot([lo, hi], [lo, hi], "r--", linewidth=1)

    plt.xlabel(f"Actual {title_prefix}")
    plt.ylabel(f"Predicted {title_prefix}")
    plt.title(f"{title_prefix}: Predicted vs Actual")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_error_distribution(errors: np.ndarray, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    plt.hist(errors, bins=40, alpha=0.75, color="teal")
    plt.xlabel("Prediction error (actual - predicted)")
    plt.ylabel("Frequency")
    plt.title("Error Distribution (Node Magnitude)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


# ---------------------------------------------------------------------------
# PIPELINE ENTRY POINT
# ---------------------------------------------------------------------------
run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = [
    f"data/artifacts/runs/{run_id}/world/final_world.pkl",
    f"data/artifacts/runs/{run_id}/baseline/baseline_model.json",
    f"data/artifacts/runs/{run_id}/baseline/test_hours.json"
]
OUTPUTS = [f"data/artifacts/runs/{run_id}/baseline/eval_plots/"]

def run(is_synthetic: bool = False, progress_callback=None, **kwargs) -> None:
    """Entry point for the AST Runner."""
    world_input = INPUTS[0]
    model_input = INPUTS[1]
    test_hours_input = INPUTS[2]
    target_output_dir = OUTPUTS[0]

    if is_synthetic:
        world_input = world_input.replace('world', 'synthetic')
        model_input = model_input.replace('baseline', 'synthetic_baseline')
        test_hours_input = test_hours_input.replace('baseline', 'synthetic_baseline')
        target_output_dir = target_output_dir.replace('baseline', 'synthetic_baseline')

    print(f"Loading Phase 01 World Object from {world_input}...")
    world = World.load(world_input)

    print(f"Loading Baseline Model from {model_input}...")
    model = BaselineTransitionModel.load(model_input)

    print(f"Loading test set metadata from {test_hours_input}...")
    test_hours = json.loads(Path(test_hours_input).read_text(encoding="utf-8"))

    print("Evaluating Baseline Model on hidden test data...")
    results = evaluate_model(world, model, test_hours, Path(target_output_dir))

    print(f"Evaluation Complete! ({results.n_samples} timeslots evaluated)")
    print(f"  Node Busyness - RMSE: {results.node_rmse:.4f}, R2: {results.node_r2:.4f}")
    print(f"  Edge Flow     - RMSE: {results.edge_rmse:.4f}, R2: {results.edge_r2:.4f}")
    print(f"Plots saved to {target_output_dir}")

    if progress_callback:
        progress_callback(1.0)