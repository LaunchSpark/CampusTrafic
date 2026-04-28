import math
import os
import pickle
import sys
import types
from sklearn.metrics import r2_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import xgboost as xgb

from pipelineio.state import load_draft, save_draft


run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = [f"data/artifacts/runs/{run_id}/world/final_world.pkl"]
OUTPUTS = [f"data/artifacts/runs/{run_id}/residual/modeling_dataframe.pkl"]

HOUR_MS = 3_600_000

def plot_wap_actual_vs_predicted_full_range(
    df: pd.DataFrame,
    wap_id: str,
    output_path: str | None = None,
) -> None:
    """
    Plot actual vs predicted traveler_count for one WAP over all available timestamps.
    Requires columns:
      - timestamp_utc
      - wap_id
      - traveler_count
      - predicted_traveler_count
    """
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
        label="Predicted",
        marker="x",
        linewidth=1.5,
    )
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel("Traveler Count")
    plt.title(f"Actual vs Predicted Traffic for WAP {wap_id} (Full Test Range)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"Saved actual-vs-predicted WAP plot to {output_path}")
    else:
        plt.show()

def plot_wap_week_traffic(
    df: pd.DataFrame,
    wap_id: str,
    start_date: str,
    output_path: str | None = None,
) -> None:
    """
    Plot actual traveler_count for one WAP over a 7-day window.

    Args:
        df: dataframe containing timestamp_utc, wap_id, traveler_count
        wap_id: the WAP to plot
        start_date: inclusive start date, e.g. "2024-01-15"
        output_path: optional file path to save the figure
    """
    start_ts = pd.Timestamp(start_date, tz="UTC")
    end_ts = start_ts + pd.Timedelta(days=7)

    wap_df = df[
        (df["wap_id"] == wap_id)
        & (df["timestamp_utc"] >= start_ts)
        & (df["timestamp_utc"] < end_ts)
    ].copy()

    if wap_df.empty:
        print(f"No data found for wap_id={wap_id} between {start_ts} and {end_ts}")
        return

    wap_df = wap_df.sort_values("timestamp_utc")

    plt.figure(figsize=(12, 5))
    plt.plot(wap_df["timestamp_utc"], wap_df["traveler_count"], marker="o", linewidth=1.5)
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel("Traveler Count")
    plt.title(f"Traffic for WAP {wap_id} from {start_ts.date()} to {end_ts.date()}")
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"Saved WAP traffic plot to {output_path}")
    else:
        plt.show()

@dataclass
class ModelingDataset:
    features: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_columns: list[str] = field(default_factory=list)
    target_column: str = "traveler_count"
    split_column: str = "dataset_split"

    def output(self, output_path: str) -> None:
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "ModelingDataset":
        return load_draft(input_path)


def _install_phase01_pickle_stubs() -> None:
    """Registers lightweight stand-ins so phase-01 world artifacts can unpickle here."""
    module_names = [
        "pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_04_build_graph",
        "pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_08_package_world",
    ]

    for name in module_names:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    graph_module = sys.modules[module_names[0]]
    world_module = sys.modules[module_names[1]]

    if not hasattr(graph_module, "Graph"):
        @dataclass
        class Graph:
            nodes: dict[str, dict[str, str]] = field(default_factory=dict)
            node_counts: dict[str, int] = field(default_factory=dict)
            physical_edges: dict[str, dict[str, float]] = field(default_factory=dict)

        Graph.__module__ = graph_module.__name__
        graph_module.Graph = Graph

    if not hasattr(world_module, "WAPTimeslot"):
        @dataclass
        class WAPTimeslot:
            wap_id: str
            hour_key: int
            raw_u: float = 0.0
            raw_v: float = 0.0
            magnitude: float = 0.0
            dir_u: float = 0.0
            dir_v: float = 0.0
            traveler_count: int = 0

        WAPTimeslot.__module__ = world_module.__name__
        world_module.WAPTimeslot = WAPTimeslot

    if not hasattr(world_module, "FlowSample"):
        @dataclass
        class FlowSample:
            x: float
            y: float
            raw_u: float
            raw_v: float
            magnitude: float
            dir_u: float
            dir_v: float

        FlowSample.__module__ = world_module.__name__
        world_module.FlowSample = FlowSample

    if not hasattr(world_module, "World"):
        @dataclass
        class World:
            graph: object = None
            wap_timeslots: dict = field(default_factory=dict)
            flow_timeslots: dict = field(default_factory=dict)

        World.__module__ = world_module.__name__
        world_module.World = World


def _load_world_artifact(input_path: str):
    _install_phase01_pickle_stubs()
    with open(input_path, "rb") as f:
        return pickle.load(f)


def _flatten_world_to_frame(world, progress_callback=None) -> pd.DataFrame:
    graph = world.graph
    hour_keys = sorted(set(world.wap_timeslots.keys()) | set(world.flow_timeslots.keys()))
    wap_ids = sorted(graph.nodes.keys())

    total_rows = max(1, len(hour_keys) * len(wap_ids))
    built_rows = 0
    rows: list[dict] = []

    for hour_idx, hour_key in enumerate(hour_keys):
        hour_bucket = world.wap_timeslots.get(hour_key, {})
        for wap_id in wap_ids:
            timeslot = hour_bucket.get(wap_id)
            meta = graph.nodes.get(wap_id, {})

            rows.append(
                {
                    "hour_key": hour_key,
                    "wap_id": wap_id,
                    "traveler_count": int(getattr(timeslot, "traveler_count", 0) or 0),
                    "raw_u": float(getattr(timeslot, "raw_u", 0.0) or 0.0),
                    "raw_v": float(getattr(timeslot, "raw_v", 0.0) or 0.0),
                    "magnitude": float(getattr(timeslot, "magnitude", 0.0) or 0.0),
                    "dir_u": float(getattr(timeslot, "dir_u", 0.0) or 0.0),
                    "dir_v": float(getattr(timeslot, "dir_v", 0.0) or 0.0),
                    "building": meta.get("building", "UNKNOWN"),
                    "room": meta.get("room", "UNKNOWN"),
                    "sub_room": meta.get("subRoom", "NONE"),
                    "node_unique_people": int(graph.node_counts.get(wap_id, 0)),
                }
            )
            built_rows += 1

        if progress_callback and hour_idx % max(1, len(hour_keys) // 20) == 0:
            progress_callback(0.1 + 0.25 * (built_rows / total_rows))

    df = pd.DataFrame(rows)
    df["timestamp_utc"] = pd.to_datetime(df["hour_key"], unit="ms", utc=True)
    df["date"] = df["timestamp_utc"].dt.date.astype(str)
    df["hour_of_day"] = df["timestamp_utc"].dt.hour
    df["day_of_week"] = df["timestamp_utc"].dt.dayofweek
    df["day_of_month"] = df["timestamp_utc"].dt.day
    df["month"] = df["timestamp_utc"].dt.month
    df["week_of_year"] = df["timestamp_utc"].dt.isocalendar().week.astype(int)
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_month_start"] = df["timestamp_utc"].dt.is_month_start.astype(int)
    df["is_month_end"] = df["timestamp_utc"].dt.is_month_end.astype(int)
    df["target_log1p"] = df["traveler_count"].map(math.log1p)
    df.sort_values(["wap_id", "hour_key"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _add_temporal_features(df: pd.DataFrame, progress_callback=None) -> pd.DataFrame:
    grouped = df.groupby("wap_id", sort=False)

    lag_hours = [1, 2, 3, 24, 168]
    for idx, lag in enumerate(lag_hours, start=1):
        df[f"lag_{lag}h"] = grouped["traveler_count"].shift(lag)
        if progress_callback:
            progress_callback(0.35 + 0.1 * (idx / len(lag_hours)))

    shifted = grouped["traveler_count"].shift(1)
    rolling_windows = [3, 6, 24]
    for idx, window in enumerate(rolling_windows, start=1):
        rolling = shifted.groupby(df["wap_id"], sort=False).rolling(window=window, min_periods=1)
        df[f"rolling_mean_{window}h"] = rolling.mean().reset_index(level=0, drop=True)
        df[f"rolling_max_{window}h"] = rolling.max().reset_index(level=0, drop=True)
        df[f"rolling_std_{window}h"] = (
            rolling.std().reset_index(level=0, drop=True).fillna(0.0)
        )
        if progress_callback:
            progress_callback(0.45 + 0.15 * (idx / len(rolling_windows)))

    df["traffic_delta_1h"] = df["traveler_count"] - df["lag_1h"].fillna(0.0)
    df["traffic_delta_24h"] = df["traveler_count"] - df["lag_24h"].fillna(0.0)
    return df


def _add_neighbor_features(df: pd.DataFrame, graph, progress_callback=None) -> pd.DataFrame:
    prev_hour_pivot = df.pivot(index="hour_key", columns="wap_id", values="lag_1h")

    neighbor_sum_frames = {}
    neighbor_mean_frames = {}
    neighbor_max_frames = {}

    wap_ids = sorted(graph.nodes.keys())
    for idx, wap_id in enumerate(wap_ids, start=1):
        neighbors = sorted(graph.physical_edges.get(wap_id, {}).keys())
        if neighbors:
            neighbor_vals = prev_hour_pivot.reindex(columns=neighbors)
            neighbor_sum_frames[wap_id] = neighbor_vals.sum(axis=1, min_count=1).fillna(0.0)
            neighbor_mean_frames[wap_id] = neighbor_vals.mean(axis=1).fillna(0.0)
            neighbor_max_frames[wap_id] = neighbor_vals.max(axis=1).fillna(0.0)
        else:
            zero_series = pd.Series(0.0, index=prev_hour_pivot.index)
            neighbor_sum_frames[wap_id] = zero_series
            neighbor_mean_frames[wap_id] = zero_series
            neighbor_max_frames[wap_id] = zero_series

        if progress_callback and idx % max(1, len(wap_ids) // 10) == 0:
            progress_callback(0.6 + 0.15 * (idx / len(wap_ids)))

    neighbor_sum = pd.DataFrame(neighbor_sum_frames)
    neighbor_mean = pd.DataFrame(neighbor_mean_frames)
    neighbor_max = pd.DataFrame(neighbor_max_frames)

    lookup_keys = pd.MultiIndex.from_frame(df[["hour_key", "wap_id"]])
    df["neighbor_prev_hour_sum"] = neighbor_sum.stack().reindex(lookup_keys).to_numpy()
    df["neighbor_prev_hour_mean"] = neighbor_mean.stack().reindex(lookup_keys).to_numpy()
    df["neighbor_prev_hour_max"] = neighbor_max.stack().reindex(lookup_keys).to_numpy()
    return df


def _assign_time_splits(df: pd.DataFrame) -> pd.DataFrame:
    unique_hours = sorted(df["hour_key"].unique())
    train_cut = unique_hours[int(len(unique_hours) * 0.70)] if unique_hours else None

    def split_label(hour_key: int) -> str:
        if train_cut is None:
            return "train"
        if hour_key < train_cut:
            return "train"
        return "test"

    df["dataset_split"] = df["hour_key"].map(split_label)
    return df

def plot_residuals(actual, predicted, output_path=None):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    residuals = predicted - actual

    plt.figure(figsize=(8, 6))
    plt.scatter(actual, residuals, s=18, alpha=0.35, edgecolors="none")
    plt.axhline(0, linestyle="--", linewidth=1.5, color="red")
    plt.xlabel("Actual traveler count")
    plt.ylabel("Residual (predicted - actual)")
    plt.title("Residuals vs Actual")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path)
        plt.close()
    else:
        plt.show()

def plot_predicted_vs_actual(
    actual: np.ndarray,
    predicted: np.ndarray,
    output_path: str | None = None,
    title: str = "Residual Model: Predicted vs Actual (Test Set)",
    normalize: bool = True,
) -> None:
    """
    Scatter plot of predicted vs actual values.

    Args:
        actual: array of true traveler counts
        predicted: array of predicted traveler counts
        output_path: optional path to save figure
        title: plot title
        normalize: if True, scale both axes to [0, 1] using the shared max
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if len(actual) == 0 or len(predicted) == 0:
        print("No points to plot.")
        return

    shared_max = max(actual.max(), predicted.max(), 1.0)

    if normalize:
        actual_plot = actual / shared_max
        predicted_plot = predicted / shared_max
        xlabel = "Actual (Test Data, normalized)"
        ylabel = "Predicted (Model, normalized)"
        min_v, max_v = 0.0, 1.0
    else:
        actual_plot = actual
        predicted_plot = predicted
        xlabel = "Actual (Test Data)"
        ylabel = "Predicted (Model)"
        min_v = min(actual_plot.min(), predicted_plot.min())
        max_v = max(actual_plot.max(), predicted_plot.max())

    sizes = 20 + 120 * (actual / shared_max)

    plt.figure(figsize=(8, 6))
    plt.scatter(
        actual_plot,
        predicted_plot,
        s=sizes,
        alpha=0.65,
        edgecolors="black",
        linewidths=0.7,
    )

    plt.plot(
        [min_v, max_v],
        [min_v, max_v],
        linestyle="--",
        linewidth=1.5,
    )

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path)
        plt.close()
        print(f"Saved predicted-vs-actual plot to {output_path}")
    else:
        plt.show()


def run(is_synthetic: bool = True, custom_param: int = 10, progress_callback=None) -> None:
    """
    Build a model-ready dataframe and train a first-pass XGBoost regressor.
    """
    input_path = INPUTS[0]
    modeling_output_path = OUTPUTS[0]

    if progress_callback:
        progress_callback(0.02)

    world = _load_world_artifact(input_path)

    if progress_callback:
        progress_callback(0.08)

    modeling_df = _flatten_world_to_frame(world, progress_callback=progress_callback)
    modeling_df = _add_temporal_features(modeling_df, progress_callback=progress_callback)
    modeling_df = _add_neighbor_features(modeling_df, world.graph, progress_callback=progress_callback)
    modeling_df = _assign_time_splits(modeling_df)

    numeric_fill_zero = [
        "lag_1h",
        "lag_2h",
        "lag_3h",
        "lag_24h",
        "lag_168h",
        "rolling_mean_3h",
        "rolling_mean_6h",
        "rolling_mean_24h",
        "rolling_max_3h",
        "rolling_max_6h",
        "rolling_max_24h",
        "rolling_std_3h",
        "rolling_std_6h",
        "rolling_std_24h",
        "neighbor_prev_hour_sum",
        "neighbor_prev_hour_mean",
        "neighbor_prev_hour_max",
    ]
    modeling_df[numeric_fill_zero] = modeling_df[numeric_fill_zero].fillna(0.0)

    feature_columns = [
        "hour_of_day",
        "day_of_week",
        "day_of_month",
        "month",
        "week_of_year",
        "is_weekend",
        "is_month_start",
        "is_month_end",
        "raw_u",
        "raw_v",
        "magnitude",
        "dir_u",
        "dir_v",
        "node_unique_people",
        "lag_1h",
        "lag_2h",
        "lag_3h",
        "lag_24h",
        "lag_168h",
        "rolling_mean_3h",
        "rolling_mean_6h",
        "rolling_mean_24h",
        "rolling_max_3h",
        "rolling_max_6h",
        "rolling_max_24h",
        "rolling_std_3h",
        "rolling_std_6h",
        "rolling_std_24h",
        "neighbor_prev_hour_sum",
        "neighbor_prev_hour_mean",
        "neighbor_prev_hour_max",
        "building",
        "room",
        "sub_room",
        "wap_id",
    ]

    dataset = ModelingDataset(
        features=modeling_df,
        feature_columns=feature_columns,
        target_column="traveler_count",
        split_column="dataset_split",
    )
    dataset.output(modeling_output_path)

    if progress_callback:
        progress_callback(0.8)

    df = dataset.features.copy()
    df = df[~df["wap_id"].astype(str).str.contains("AIEB", regex=True, na=False)].copy()
    df = df[~df["wap_id"].astype(str).str.contains("Outdoor", regex=True, na=False)].copy()

    train_df = df[df[dataset.split_column] == "train"].copy()
    test_df = df[df[dataset.split_column] == "test"].copy()

    # Use an internal eval slice from the training period for early stopping,
    # while keeping the overall dataset split as 70/30 train/test.
    train_hours = sorted(train_df["hour_key"].unique())
    eval_cut = train_hours[int(len(train_hours) * 0.85)] if len(train_hours) >= 2 else None
    if eval_cut is None:
        fit_df = train_df
        eval_df = train_df.tail(max(1, len(train_df) // 10)).copy()
        fit_df = train_df.iloc[: max(1, len(train_df) - len(eval_df))].copy()
    else:
        fit_df = train_df[train_df["hour_key"] < eval_cut].copy()
        eval_df = train_df[train_df["hour_key"] >= eval_cut].copy()

    if len(fit_df) == 0 or len(eval_df) == 0:
        fit_df = train_df.copy()
        eval_df = train_df.tail(max(1, len(train_df) // 10)).copy()

    categorical_cols = ["building", "room", "sub_room", "wap_id"]
    for frame in (fit_df, eval_df, test_df):
        for col in categorical_cols:
            frame[col] = frame[col].astype("category")

    X_train = fit_df[dataset.feature_columns]
    y_train = fit_df["target_log1p"]
    X_valid = eval_df[dataset.feature_columns]
    y_valid = eval_df["target_log1p"]
    X_test = test_df[dataset.feature_columns]
    y_test = test_df[dataset.target_column]
    y_test_log = test_df["target_log1p"]

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        eval_metric="rmse",
        n_estimators=1000,
        learning_rate=0.03,
        max_depth=3,
        min_child_weight=5,
        subsample=0.7,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=2.0,
        gamma=0.1,
        random_state=42,
        enable_categorical=True,
        tree_method="hist",
        early_stopping_rounds=30,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_valid, y_valid)],
        verbose=False,
    )

    pred_log = model.predict(X_test)
    pred_count = np.expm1(pred_log)
    pred_count = np.clip(pred_count, 0.0, None)
    pred_count = np.rint(pred_count).astype(int)

    test_df = test_df.copy()
    test_df["predicted_traveler_count"] = pred_count

    mae = float(np.mean(np.abs(pred_count - y_test.to_numpy())))
    rmse = float(np.sqrt(np.mean((pred_count - y_test.to_numpy()) ** 2)))
    r_squared = float(r2_score(y_test.to_numpy(), pred_count))

    chosen_wap = None
    chosen_start = None

    wap_traffic = (
        test_df.assign(wap_id=test_df["wap_id"].astype(str))
        .groupby("wap_id", dropna=True)["traveler_count"]
        .sum()
        .sort_values(ascending=False)
    )

    residual_dir = f"data/artifacts/runs/{run_id}/residual"
    os.makedirs(residual_dir, exist_ok=True)

    busiest_wap = (
        test_df.assign(wap_id=test_df["wap_id"].astype(str))
        .groupby("wap_id")["traveler_count"]
        .sum()
        .sort_values(ascending=False)
        .index[0]
    )

    scatter_plot_path = f"{residual_dir}/predicted_vs_actual.svg"
    plot_predicted_vs_actual(
        actual=y_test.to_numpy(),
        predicted=pred_count,
        output_path=scatter_plot_path,
        title="Residual Model: Predicted vs Actual (Test Set)",
        normalize=True,
    )

    plot_residuals(
        actual=y_test.to_numpy(),
        predicted=pred_count,
        output_path=f"{residual_dir}/residuals_vs_actual.svg",
    )

    plot_wap_actual_vs_predicted_full_range(
        df=test_df.assign(wap_id=test_df["wap_id"].astype(str)),
        wap_id=busiest_wap,
        output_path=f"{residual_dir}/wap_full_test_pred_vs_act.svg",
    )

    if progress_callback:
        progress_callback(1.0)

    print(f"Built modeling dataframe with {len(modeling_df):,} rows.")
    print(f"Unique WAPs: {modeling_df['wap_id'].nunique():,}")
    print(f"Unique hours: {modeling_df['hour_key'].nunique():,}")
    print(f"Saved modeling dataset to {modeling_output_path}")
    print(f"Train rows: {len(train_df):,}")
    print(f"Train-fit rows (for training): {len(fit_df):,}")
    print(f"Train-eval rows (for early stopping): {len(eval_df):,}")
    print(f"Test rows: {len(test_df):,}")
    print(f"Test MAE: {mae:.4f}")
    print(f"Test RMSE: {rmse:.4f}")
    print(f"Test R Squared: {r_squared:.4f}")

    results = model.evals_result()

    train_rmse = results["validation_0"]["rmse"]
    valid_rmse = results["validation_1"]["rmse"]

    plot_path = f"data/artifacts/runs/{run_id}/residual/training_rmse.png"

    plt.figure(figsize=(10, 6))
    plt.plot(train_rmse, label="Train RMSE")
    plt.plot(valid_rmse, label="Train-Eval RMSE")
    plt.xlabel("Boosting Round")
    plt.ylabel("RMSE (log1p scale)")
    plt.title("XGBoost RMSE During Training")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(plot_path, dpi=150)
    plt.close()

    plot_wap_week_traffic(df=modeling_df, wap_id="AIEB-RM244-1", start_date="2026-02-01", output_path=f"data/artifacts/runs/{run_id}/residual/wap_week_traffic.png")
    print(f"Test date range: {test_df['timestamp_utc'].min()} to {test_df['timestamp_utc'].max()}")
    print(f"Unique test WAPs: {test_df['wap_id'].nunique()}")
    print(test_df.groupby('wap_id')['traveler_count'].sum().sort_values(ascending=False).head(10))
    #added to make run in pipeline

    exact_accuracy = float((pred_count == y_test.to_numpy()).mean())
    print(f"Test exact-match accuracy: {exact_accuracy:.4f}")

    actual = y_test.to_numpy()
    denom = np.maximum(actual, 1)  # avoid divide-by-zero
    pct_error = np.abs(pred_count - actual) / denom
    accuracy_within_10pct = float((pct_error <= 0.10).mean())
    print(f"Test accuracy within 10%: {accuracy_within_10pct:.4f}")

    print("This makes it run")
