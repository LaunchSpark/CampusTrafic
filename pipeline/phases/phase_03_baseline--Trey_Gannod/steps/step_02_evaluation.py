"""
PIPELINE STEP: BASELINE EVALUATION (PROBABILITY + FLOW)
======================================================
Evaluates the BaselineTransitionModel using held-out test data.
Focuses entirely on temporal line-chart visualizations to track accuracy over time.
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
import pandas as pd
from sklearn.metrics import r2_score

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


# ---------------------------------------------------------------------------
# TIME-SERIES VISUALIZATIONS
# ---------------------------------------------------------------------------

def plot_campus_aggregate_traffic(df: pd.DataFrame, output_path: str | None = None) -> None:
    """Line chart showing the macro-level campus traffic over time."""
    agg_df = df.groupby("timestamp_utc")[["traveler_count", "predicted_traveler_count"]].sum().reset_index()
    agg_df = agg_df.sort_values("timestamp_utc")

    plt.figure(figsize=(14, 6))
    plt.plot(agg_df["timestamp_utc"], agg_df["traveler_count"], label="Actual Campus Total", linewidth=2, color="blue")
    plt.plot(agg_df["timestamp_utc"], agg_df["predicted_traveler_count"], label="Predicted Campus Total", linewidth=2, linestyle="--", color="orange")
    
    plt.xlabel("Timeline (UTC)")
    plt.ylabel("Total Network Headcount")
    plt.title("Macro View: Total Campus Traffic Over Time (Test Set)")
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()


def plot_hourly_rmse(df: pd.DataFrame, output_path: str | None = None) -> None:
    """Bar chart showing which hours of the day the model struggles with most."""
    df["hour_of_day"] = df["timestamp_utc"].dt.hour
    df["squared_error"] = (df["predicted_traveler_count"] - df["traveler_count"]) ** 2
    
    hourly_rmse = np.sqrt(df.groupby("hour_of_day")["squared_error"].mean())
    
    plt.figure(figsize=(10, 5))
    hourly_rmse.plot(kind="bar", color="coral", edgecolor="black")
    plt.xlabel("Hour of Day (UTC)")
    plt.ylabel("RMSE")
    plt.title("Prediction Error (RMSE) by Hour of Day")
    plt.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=0)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()


def plot_wap_actual_vs_predicted_full_range(df: pd.DataFrame, wap_id: str, output_path: str | None = None) -> None:
    """Line chart showing the traffic for a single specific WAP."""
    wap_df = df[df["wap_id"].astype(str) == str(wap_id)].copy()
    if wap_df.empty: return
    wap_df = wap_df.sort_values("timestamp_utc")

    plt.figure(figsize=(12, 5))
    plt.plot(wap_df["timestamp_utc"], wap_df["traveler_count"], label="Actual", marker="o", markersize=4, linewidth=1.5)
    plt.plot(wap_df["timestamp_utc"], wap_df["predicted_traveler_count"], label="Predicted (Baseline)", marker="x", markersize=4, linewidth=1.5)
    
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel("Traveler Count")
    plt.title(f"Baseline Traffic for WAP {wap_id} (Test Set)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()


# ---------------------------------------------------------------------------
# CORE EVALUATION
# ---------------------------------------------------------------------------

def evaluate_model(
    world: World, 
    model: BaselineTransitionModel, 
    test_hours: list[int], 
    output_dir: Path
) -> EvaluationResult:
    rows = []
    y_true_edge, y_pred_edge = [], []
    topology = {k: list(v.keys()) for k, v in world.graph.physical_edges.items()} if world.graph else {}

    for hk in test_hours:
        hour_of_day = int((hk / 3600_000) % 24)
        timeslot_map = world.wap_timeslots.get(hk, {})

        for wap_id, timeslot in timeslot_map.items():
            actual_count = int(timeslot.traveler_count)

            pred_count_raw = model.hour_node_means.get(
                (hour_of_day, wap_id),
                model.global_node_means.get(wap_id, model.global_mean)
            )
            pred_count = int(np.rint(max(0.0, pred_count_raw)))
            
            rows.append({
                "timestamp_utc": pd.to_datetime(hk, unit="ms", utc=True),
                "wap_id": wap_id,
                "traveler_count": actual_count,
                "predicted_traveler_count": pred_count
            })

            adjacent_nodes = topology.get(wap_id, [])
            if adjacent_nodes:
                flow_share = actual_count / len(adjacent_nodes)
                for next_node in adjacent_nodes:
                    y_true_edge.append(flow_share)
                    pred_flow = model.predict_flow(hour_of_day, wap_id, next_node)
                    y_pred_edge.append(max(0.0, pred_flow))

    df = pd.DataFrame(rows)
    
    if df.empty:
        return EvaluationResult(0.0, 0.0, 0.0, 0.0, 0)

    actual_counts = df["traveler_count"].to_numpy()
    pred_counts = df["predicted_traveler_count"].to_numpy()

    mae = float(np.mean(np.abs(pred_counts - actual_counts)))
    rmse = float(np.sqrt(np.mean((pred_counts - actual_counts) ** 2)))
    r_squared = float(r2_score(actual_counts, pred_counts))

    exact_accuracy = float((pred_counts == actual_counts).mean())
    accuracy_pm1 = float((np.abs(pred_counts - actual_counts) <= 1).mean())
    accuracy_pm2 = float((np.abs(pred_counts - actual_counts) <= 2).mean())

    denom = np.maximum(actual_counts, 1)
    pct_error = np.abs(pred_counts - actual_counts) / denom
    accuracy_10pct = float((pct_error <= 0.10).mean())
    accuracy_20pct = float((pct_error <= 0.20).mean())

    edge_rmse = float(np.sqrt(np.mean((np.array(y_true_edge) - np.array(y_pred_edge))**2))) if y_true_edge else 0.0
    ss_res_edge = np.sum((np.array(y_true_edge) - np.array(y_pred_edge))**2)
    ss_tot_edge = np.sum((np.array(y_true_edge) - np.mean(y_true_edge))**2) if y_true_edge else 0.0
    edge_r2 = float(1.0 - (ss_res_edge / ss_tot_edge)) if ss_tot_edge > 0 else 0.0

    print(f"Test MAE: {mae:.4f}")
    print(f"Test RMSE: {rmse:.4f}")
    print(f"Test R Squared: {r_squared:.4f}")
    print(f"Test exact-match accuracy: {exact_accuracy:.4f}")
    print(f"Test accuracy within ±1 traveler: {accuracy_pm1:.4f}")
    print(f"Test accuracy within ±2 travelers: {accuracy_pm2:.4f}")
    print(f"Test accuracy within 10%: {accuracy_10pct:.4f}")
    print(f"Test accuracy within 20%: {accuracy_20pct:.4f}")
    print(f"Test date range: {df['timestamp_utc'].min()} to {df['timestamp_utc'].max()}")
    print(f"Unique test WAPs: {df['wap_id'].nunique()}")

    # GENERATE PRUNED VISUALS
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plot_campus_aggregate_traffic(df, str(output_dir / "macro_campus_traffic.svg"))
    plot_hourly_rmse(df, str(output_dir / "hourly_rmse_breakdown.png"))
    plot_wap_actual_vs_predicted_full_range(df, "PRSC-RM204", str(output_dir / "wap_full_test_pred_vs_act.svg"))

    return EvaluationResult(rmse, r_squared, edge_rmse, edge_r2, len(df))


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
    print("-" * 40)
    results = evaluate_model(world, model, test_hours, Path(target_output_dir))
    print("-" * 40)
    print(f"Evaluation Complete! ({results.n_samples} timeslots evaluated)")
    print(f"Plots saved to {target_output_dir}")

    if progress_callback:
        progress_callback(1.0)