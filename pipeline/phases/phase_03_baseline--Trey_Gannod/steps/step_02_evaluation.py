"""
PIPELINE STEP: BASELINE EVALUATION (PROBABILITY + FLOW)
======================================================
Evaluates the BaselineTransitionModel using held-out test data.
Standardized to match the exact evaluation flow of Phase 04 (Residual Model).
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
# PLOTTING UTILITIES (Ported from Phase 04 to guarantee 1:1 visual parity)
# ---------------------------------------------------------------------------

def plot_wap_actual_vs_predicted_full_range(
    df: pd.DataFrame,
    wap_id: str,
    output_path: str | None = None,
) -> None:
    wap_df = df[df["wap_id"].astype(str) == str(wap_id)].copy()

    if wap_df.empty:
        print(f"No data found for wap_id={wap_id}")
        return

    wap_df = wap_df.sort_values("timestamp_utc")

    plt.figure(figsize=(12, 5))
    plt.plot(
        wap_df["timestamp_utc"],
        wap_df["traveler_count"],
        label="Actual",
        marker="o",
        linewidth=1.5,
    )
    plt.plot(
        wap_df["timestamp_utc"],
        wap_df["predicted_traveler_count"],
        label="Predicted (Baseline)",
        marker="x",
        linewidth=1.5,
    )
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel("Traveler Count / Magnitude")
    plt.title(f"Baseline Traffic for WAP {wap_id} (Test Set)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()


def plot_residuals(actual, predicted, output_path=None):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    residuals = predicted - actual

    plt.figure(figsize=(8, 6))
    plt.scatter(actual, residuals, s=18, alpha=0.35, edgecolors="none")
    plt.axhline(0, linestyle="--", linewidth=1.5, color="red")
    plt.xlabel("Actual Count")
    plt.ylabel("Residual (predicted - actual)")
    plt.title("Baseline: Residuals vs Actual")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()


def plot_predicted_vs_actual(
    actual: np.ndarray,
    predicted: np.ndarray,
    output_path: str | None = None,
    title: str = "Baseline Model: Predicted vs Actual",
    normalize: bool = True,
) -> None:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if len(actual) == 0 or len(predicted) == 0:
        return

    shared_max = max(actual.max(), predicted.max(), 1.0)

    if normalize:
        actual_plot = actual / shared_max
        predicted_plot = predicted / shared_max
        xlabel = "Actual (Test Data, normalized)"
        ylabel = "Predicted (Baseline, normalized)"
        min_v, max_v = 0.0, 1.0
    else:
        actual_plot = actual
        predicted_plot = predicted
        xlabel = "Actual (Test Data)"
        ylabel = "Predicted (Baseline)"
        min_v = min(actual_plot.min(), predicted_plot.min())
        max_v = max(actual_plot.max(), predicted_plot.max())

    sizes = 20 + 120 * (actual / shared_max)

    plt.figure(figsize=(8, 6))
    plt.scatter(actual_plot, predicted_plot, s=sizes, alpha=0.65, edgecolors="black", linewidths=0.7)
    plt.plot([min_v, max_v], [min_v, max_v], linestyle="--", linewidth=1.5, label="Ideal y=x")

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()


def plot_regression_accuracy_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    output_path: str | None = None,
) -> None:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if len(actual) == 0:
        return

    exact_acc = float((predicted == actual).mean())
    acc_pm1 = float((np.abs(predicted - actual) <= 1).mean())
    acc_pm2 = float((np.abs(predicted - actual) <= 2).mean())

    denom = np.maximum(actual, 1.0)
    pct_error = np.abs(predicted - actual) / denom
    acc_10pct = float((pct_error <= 0.10).mean())
    acc_20pct = float((pct_error <= 0.20).mean())

    labels = ["Exact match", "Within ±1", "Within ±2", "Within 10%", "Within 20%"]
    values = [exact_acc, acc_pm1, acc_pm2, acc_10pct, acc_20pct]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, values, color="teal")
    plt.ylim(0, 1.0)
    plt.ylabel("Accuracy")
    plt.title("Baseline Regression Accuracy Metrics (Test Set)")
    plt.grid(axis="y", alpha=0.3)

    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, min(val + 0.02, 0.98), f"{val:.3f}", ha="center", va="bottom")

    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()

def plot_campus_aggregate_traffic(df: pd.DataFrame, output_path: str | None = None) -> None:
    """Line chart showing the macro-level campus traffic over time."""
    # Sum all WAPs together for each hour
    agg_df = df.groupby("timestamp_utc")[["traveler_count", "predicted_traveler_count"]].sum().reset_index()
    agg_df = agg_df.sort_values("timestamp_utc")

    plt.figure(figsize=(14, 6))
    plt.plot(agg_df["timestamp_utc"], agg_df["traveler_count"], label="Actual Campus Total", linewidth=2, color="blue")
    plt.plot(agg_df["timestamp_utc"], agg_df["predicted_traveler_count"], label="Predicted Campus Total", linewidth=2, linestyle="--", color="orange")
    
    plt.xlabel("Timeline (UTC)")
    plt.ylabel("Total Network Headcount")
    plt.title("Macro View: Total Campus Traffic Over Time")
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()

def plot_wap_vector_components(df: pd.DataFrame, wap_id: str, output_path: str | None = None) -> None:
    """Line chart showing the X (u) and Y (v) vector components over time for a specific WAP."""
    wap_df = df[df["wap_id"].astype(str) == str(wap_id)].copy()
    if wap_df.empty: return
    wap_df = wap_df.sort_values("timestamp_utc")

    # Reconstruct the predicted vectors using the unit directions
    wap_df["pred_u"] = wap_df["predicted_traveler_count"] * wap_df["dir_u"]
    wap_df["pred_v"] = wap_df["predicted_traveler_count"] * wap_df["dir_v"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Plot X-Component (U)
    ax1.plot(wap_df["timestamp_utc"], wap_df["actual_u"], label="Actual X-Vector", marker="o", markersize=3, color="teal")
    ax1.plot(wap_df["timestamp_utc"], wap_df["pred_u"], label="Predicted X-Vector", marker="x", markersize=3, color="red", linestyle="--")
    ax1.set_ylabel("X Movement (U)")
    ax1.set_title(f"X-Axis Movement for {wap_id}")
    ax1.grid(alpha=0.3)
    ax1.legend()

    # Plot Y-Component (V)
    ax2.plot(wap_df["timestamp_utc"], wap_df["actual_v"], label="Actual Y-Vector", marker="o", markersize=3, color="purple")
    ax2.plot(wap_df["timestamp_utc"], wap_df["pred_v"], label="Predicted Y-Vector", marker="x", markersize=3, color="orange", linestyle="--")
    ax2.set_ylabel("Y Movement (V)")
    ax2.set_title(f"Y-Axis Movement for {wap_id}")
    ax2.grid(alpha=0.3)
    ax2.legend()

    plt.xlabel("Timeline (UTC)")
    plt.xticks(rotation=45)
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



# ---------------------------------------------------------------------------
# CORE EVALUATION
# ---------------------------------------------------------------------------

def evaluate_model(
    world: World, 
    model: BaselineTransitionModel, 
    test_hours: list[int], 
    output_dir: Path
) -> EvaluationResult:
    """Evaluate baseline model against the hidden test hours and generate standard metrics."""
    
    # We will build a DataFrame of the test data so we can use the same WAP-specific plots
    rows = []
    
    y_true_edge, y_pred_edge = [], []
    topology = {k: list(v.keys()) for k, v in world.graph.physical_edges.items()} if world.graph else {}

    for hk in test_hours:
        hour_of_day = int((hk / 3600_000) % 24)
        timeslot_map = world.wap_timeslots.get(hk, {})

        for wap_id, timeslot in timeslot_map.items():
            # Extract the literal integer traveler count 
            actual_count = int(timeslot.traveler_count)

            # Node outbound prediction (using fallbacks)
            pred_count_raw = model.hour_node_means.get(
                (hour_of_day, wap_id),
                model.global_node_means.get(wap_id, model.global_mean)
            )
            # Clip to 0 and cast to int to match XGBoost constraints
            pred_count = int(np.rint(max(0.0, pred_count_raw)))
            
            rows.append({
                "timestamp_utc": pd.to_datetime(hk, unit="ms", utc=True),
                "wap_id": wap_id,
                "traveler_count": actual_count,
                "predicted_traveler_count": pred_count,
                "dir_u": timeslot.dir_u,      # ADD THIS
                "dir_v": timeslot.dir_v,      # ADD THIS
                "actual_u": timeslot.raw_u,   # ADD THIS
                "actual_v": timeslot.raw_v    # ADD THIS
            })

            # Edge flow predictions
            adjacent_nodes = topology.get(wap_id, [])
            if adjacent_nodes:
                # Ground truth approximation: equal split
                flow_share = actual_count / len(adjacent_nodes)
            

    df = pd.DataFrame(rows)
    
    if df.empty:
        return EvaluationResult(0.0, 0.0, 0.0, 0.0, 0)

    actual_counts = df["traveler_count"].to_numpy()
    pred_counts = df["predicted_traveler_count"].to_numpy()

    # --- CALCULATE METRICS EXACTLY LIKE PHASE 04 ---
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

    # Calculate Edge Flow (Not measured in Phase 04, but useful for Baseline)
    edge_rmse = float(np.sqrt(np.mean((np.array(y_true_edge) - np.array(y_pred_edge))**2))) if y_true_edge else 0.0
    ss_res_edge = np.sum((np.array(y_true_edge) - np.array(y_pred_edge))**2)
    ss_tot_edge = np.sum((np.array(y_true_edge) - np.mean(y_true_edge))**2) if y_true_edge else 0.0
    edge_r2 = float(1.0 - (ss_res_edge / ss_tot_edge)) if ss_tot_edge > 0 else 0.0

    # --- PRINT PARITY WITH PHASE 04 ---
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

    # --- GENERATE PLOTS ---
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plot_predicted_vs_actual(
        actual=actual_counts,
        predicted=pred_counts,
        output_path=str(output_dir / "predicted_vs_actual.svg"),
        title="Baseline Model: Predicted vs Actual (Test Set)",
        normalize=True
    )
    
    plot_residuals(
        actual=actual_counts,
        predicted=pred_counts,
        output_path=str(output_dir / "residuals_vs_actual.svg")
    )
    
    plot_regression_accuracy_metrics(
        actual=actual_counts,
        predicted=pred_counts,
        output_path=str(output_dir / "regression_accuracy_metrics.png")
    )
    
    # Generate the exact same WAP-specific plot from Phase 04
    plot_wap_actual_vs_predicted_full_range(
        df=df,
        wap_id="PRSC-RM204",
        output_path=str(output_dir / "wap_full_test_pred_vs_act.svg")
    )

    # New Visualizations!
    plot_campus_aggregate_traffic(df, str(output_dir / "macro_campus_traffic.svg"))
    plot_hourly_rmse(df, str(output_dir / "hourly_rmse_breakdown.png"))
    
    # Pick a busy WAP to test the Vector plotting
    plot_wap_vector_components(df, "PRSC-RM204", str(output_dir / "wap_vector_components.svg"))

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
    print("-" * 40)
    results = evaluate_model(world, model, test_hours, Path(target_output_dir))
    print("-" * 40)
    print(f"Evaluation Complete! ({results.n_samples} timeslots evaluated)")
    print(f"Plots saved to {target_output_dir}")

    if progress_callback:
        progress_callback(1.0)