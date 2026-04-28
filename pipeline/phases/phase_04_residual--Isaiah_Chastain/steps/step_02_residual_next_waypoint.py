from dataclasses import dataclass, field
import os
import pickle
import sys
import time
import types
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb

from pipelineio.state import load_draft, save_draft


run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = [f"data/artifacts/runs/{run_id}/world/final_journeys.pkl"]
MODEL_OUTPUT = f"data/artifacts/runs/{run_id}/residual/xgb_next_waypoint_model.pkl"
EVAL_OUTPUT = f"data/artifacts/runs/{run_id}/residual/xgb_next_waypoint_evaluation.pkl"


@dataclass
class XGBNextWaypointModel:
    feature_columns: list[str] = field(default_factory=list)
    class_labels: list[str] = field(default_factory=list)
    model: Any = None
    allowed_next_by_origin: dict[str, list[str]] = field(default_factory=dict)
    global_fallback_label: str | None = None

    def output(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "XGBNextWaypointModel":
        return load_draft(input_path)


@dataclass
class XGBNextWaypointEvaluation:
    metrics: dict[str, float] = field(default_factory=dict)
    plot_path: str | None = None

    def _build_top1_points(
        self,
        test_df: pd.DataFrame,
        pred_proba: np.ndarray,
        class_labels: list[str],
    ) -> list[tuple[float, float, int, str]]:
        pred_top1_idx = np.argmax(pred_proba, axis=1)
        class_labels_arr = np.asarray(class_labels, dtype=object)
        pred_top1_labels = class_labels_arr[pred_top1_idx]
        pred_top1_conf = pred_proba[np.arange(len(pred_proba)), pred_top1_idx]

        eval_df = pd.DataFrame(
            {
                "origin": test_df["wap_id"].astype(str).to_numpy(),
                "true_label": test_df["next_wap_id"].astype(str).to_numpy(),
                "pred_label": pred_top1_labels,
                "pred_conf": pred_top1_conf,
            }
        )
        eval_df["correct"] = (eval_df["true_label"] == eval_df["pred_label"]).astype(int)

        grouped = (
            eval_df.groupby("origin", dropna=False)
            .agg(
                actual_top1_accuracy=("correct", "mean"),
                mean_top1_confidence=("pred_conf", "mean"),
                count=("correct", "size"),
            )
            .reset_index()
        )

        return list(
            zip(
                grouped["actual_top1_accuracy"].astype(float).to_numpy(),
                grouped["mean_top1_confidence"].astype(float).to_numpy(),
                grouped["count"].astype(int).to_numpy(),
                grouped["origin"].astype(str).to_numpy(),
            )
        )

    def _plot_top1_confidence_vs_accuracy(self, points, output_path=None):
        if not points:
            print("No points to plot.")
            return

        actual = np.array([p[0] for p in points], dtype=float)
        predicted = np.array([p[1] for p in points], dtype=float)
        counts = np.array([p[2] for p in points], dtype=float)

        sizes = 20 + 120 * (counts / max(counts.max(), 1.0))

        plt.figure(figsize=(8, 6))
        plt.scatter(actual, predicted, s=sizes, alpha=0.65, edgecolors="black")

        min_v = min(actual.min(), predicted.min())
        max_v = max(actual.max(), predicted.max())

        plt.plot([min_v, max_v], [min_v, max_v], linestyle="--", label="Ideal y=x")

        plt.xlabel("Actual Top-1 Accuracy")
        plt.ylabel("Mean Top-1 Predicted Confidence")
        plt.title("XGBoost Model: Top-1 Accuracy vs Confidence (Test Set)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, dpi=150)
            plt.close()
            self.plot_path = output_path
            print(f"Saved plot to {output_path}")
        else:
            plt.show()

    def process(
        self,
        test_df: pd.DataFrame,
        pred_proba: np.ndarray,
        class_labels: list[str],
        plot_output_path=None,
        progress_callback=None,
    ):
        if progress_callback:
            progress_callback(0.75)

        pred_top1_idx = np.argmax(pred_proba, axis=1)
        class_labels_arr = np.asarray(class_labels, dtype=object)
        pred_top1_labels = class_labels_arr[pred_top1_idx]
        true_labels = test_df["next_wap_id"].astype(str).to_numpy()
        correct = (pred_top1_labels == true_labels).astype(int)

        self.metrics["top1_accuracy"] = float(correct.mean()) if len(correct) > 0 else 0.0

        points = self._build_top1_points(
            test_df=test_df,
            pred_proba=pred_proba,
            class_labels=class_labels,
        )

        if points:
            actual = np.array([p[0] for p in points], dtype=float)
            predicted = np.array([p[1] for p in points], dtype=float)
            counts = np.array([p[2] for p in points], dtype=float)

            errors = predicted - actual
            abs_errors = np.abs(errors)

            self.metrics["weighted_mae"] = float(np.average(abs_errors, weights=counts))
            self.metrics["rmse"] = float(np.sqrt(np.mean(errors ** 2)))
            self.metrics["pearson_corr"] = (
                float(np.corrcoef(actual, predicted)[0, 1]) if len(points) > 1 else 0.0
            )

            ss_res = np.sum((actual - predicted) ** 2)
            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            self.metrics["r2"] = float(1.0 - (ss_res / ss_tot if ss_tot > 0 else 0.0))
            self.metrics["num_origins"] = float(len(points))
        else:
            self.metrics["weighted_mae"] = 0.0
            self.metrics["rmse"] = 0.0
            self.metrics["pearson_corr"] = 0.0
            self.metrics["r2"] = 0.0
            self.metrics["num_origins"] = 0.0

        print("\n================ NEXT-WAYPOINT EVALUATION ================\n")
        for key, value in self.metrics.items():
            print(f"{key}: {value}")
        print("\n=========================================================\n")

        self._plot_top1_confidence_vs_accuracy(points, output_path=plot_output_path)

        if progress_callback:
            progress_callback(1.0)

    def output(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_draft(self, output_path)


def _load_journeys(input_path: str) -> Any:
    mod_j = "pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_05_build_journeys"
    mod_i = "pipeline.phases.phase_01_build_world__Lucas_Starkey.steps.step_06_interpolate_paths"

    if mod_j not in sys.modules:
        sys.modules[mod_j] = types.ModuleType(mod_j)
    if mod_i not in sys.modules:
        sys.modules[mod_i] = types.ModuleType(mod_i)

    @dataclass
    class Waypoint:
        wap_id: str
        timestamp: float
        is_stay: bool = False
        is_inferred: bool = False

    Waypoint.__module__ = mod_j
    sys.modules[mod_j].Waypoint = Waypoint

    @dataclass
    class Journey:
        person_id: str
        waypoints: list[Waypoint] = field(default_factory=list)

    Journey.__module__ = mod_j
    sys.modules[mod_j].Journey = Journey

    @dataclass
    class RoutingModel:
        empirical_edge_counts: dict = field(default_factory=dict)
        empirical_edge_times: dict = field(default_factory=dict)

    RoutingModel.__module__ = mod_i
    sys.modules[mod_i].RoutingModel = RoutingModel

    @dataclass
    class InterpolatedJourneysData:
        journeys: list[Journey] = field(default_factory=list)
        model: RoutingModel | None = None

    InterpolatedJourneysData.__module__ = mod_i
    sys.modules[mod_i].InterpolatedJourneysData = InterpolatedJourneysData

    with open(input_path, "rb") as f:
        return pickle.load(f)


def _flatten_journeys_to_events(journeys_obj: Any, progress_callback=None) -> pd.DataFrame:
    if not hasattr(journeys_obj, "journeys"):
        raise ValueError("Expected a journeys object with a .journeys attribute.")

    journeys = journeys_obj.journeys
    if not isinstance(journeys, list):
        raise ValueError("Expected journeys_obj.journeys to be a list.")

    rows: list[tuple[int, int, float, str, int, int]] = []
    total = max(1, len(journeys))

    for j_idx, journey in enumerate(journeys):
        if progress_callback and j_idx % max(1, total // 40) == 0:
            progress_callback(0.10 + 0.20 * (j_idx / total))

        wps = getattr(journey, "waypoints", None)
        if not wps:
            continue

        for wp_idx, wp in enumerate(wps):
            wap_id = getattr(wp, "wap_id", None)
            if wap_id is None:
                continue

            rows.append(
                (
                    j_idx,
                    wp_idx,
                    float(getattr(wp, "timestamp", 0.0) or 0.0),
                    str(wap_id),
                    int(bool(getattr(wp, "is_stay", False))),
                    int(bool(getattr(wp, "is_inferred", False))),
                )
            )

    if not rows:
        raise ValueError("No waypoint rows were produced from the journeys artifact.")

    df = pd.DataFrame(
        rows,
        columns=[
            "journey_index",
            "waypoint_index",
            "timestamp_ms",
            "wap_id",
            "is_stay",
            "is_inferred",
        ],
    )

    df = df.sort_values(["journey_index", "timestamp_ms", "waypoint_index"]).reset_index(drop=True)
    return df


def _build_next_waypoint_training_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "timestamp_ms" not in df.columns:
        raise ValueError("Expected 'timestamp_ms' in journeys data.")
    if "wap_id" not in df.columns:
        raise ValueError("Expected 'wap_id' in journeys data.")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True, errors="coerce")
    if df["timestamp_utc"].isna().any():
        raise ValueError("Found invalid timestamp_utc values in journeys data.")

    if "journey_index" not in df.columns:
        if "journey_id" in df.columns:
            df["journey_index"] = df["journey_id"]
        else:
            raise ValueError("Expected 'journey_index' or 'journey_id' in journeys data.")

    df = df.sort_values(["journey_index", "timestamp_ms", "waypoint_index"]).reset_index(drop=True)

    grouped = df.groupby("journey_index", sort=False)

    df["next_wap_id"] = grouped["wap_id"].shift(-1)
    df["next_timestamp_utc"] = grouped["timestamp_utc"].shift(-1)
    df["prev_wap_id"] = grouped["wap_id"].shift(1)
    df["prev_timestamp_utc"] = grouped["timestamp_utc"].shift(1)
    df["prev2_wap_id"] = grouped["wap_id"].shift(2)
    df["prev2_timestamp_utc"] = grouped["timestamp_utc"].shift(2)

    df["hour_of_day"] = df["timestamp_utc"].dt.hour
    df["day_of_week"] = df["timestamp_utc"].dt.dayofweek
    df["day_of_month"] = df["timestamp_utc"].dt.day
    df["month"] = df["timestamp_utc"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    df["seconds_from_prev"] = (
        (df["timestamp_utc"] - df["prev_timestamp_utc"]).dt.total_seconds()
    ).fillna(0.0)

    df["seconds_from_prev2"] = (
        (df["timestamp_utc"] - df["prev2_timestamp_utc"]).dt.total_seconds()
    ).fillna(0.0)

    df["seconds_to_next"] = (
        (df["next_timestamp_utc"] - df["timestamp_utc"]).dt.total_seconds()
    ).fillna(0.0)

    if "is_stay" not in df.columns:
        df["is_stay"] = (
            df["prev_wap_id"].astype(str).fillna("NONE") == df["wap_id"].astype(str).fillna("NONE")
        ).astype(int)

    if "is_inferred" not in df.columns:
        df["is_inferred"] = 0

    df = df[df["next_wap_id"].notna()].copy()
    return df


def _apply_origin_candidate_mask(
    pred_proba: np.ndarray,
    origins: np.ndarray,
    class_labels: list[str],
    allowed_next_by_origin: dict[str, list[str]],
    global_fallback_label: str | None,
) -> np.ndarray:
    if pred_proba.size == 0:
        return pred_proba

    masked = pred_proba.copy()
    class_to_idx = {label: i for i, label in enumerate(class_labels)}

    if global_fallback_label is None or global_fallback_label not in class_to_idx:
        global_fallback_idx = int(np.argmax(masked.mean(axis=0)))
    else:
        global_fallback_idx = class_to_idx[global_fallback_label]

    for i, origin in enumerate(origins.astype(str)):
        allowed_labels = allowed_next_by_origin.get(origin)
        if not allowed_labels:
            row = np.zeros(masked.shape[1], dtype=float)
            row[global_fallback_idx] = 1.0
            masked[i] = row
            continue

        allowed_idx = [class_to_idx[label] for label in allowed_labels if label in class_to_idx]
        if not allowed_idx:
            row = np.zeros(masked.shape[1], dtype=float)
            row[global_fallback_idx] = 1.0
            masked[i] = row
            continue

        keep_mask = np.zeros(masked.shape[1], dtype=bool)
        keep_mask[allowed_idx] = True
        masked[i, ~keep_mask] = 0.0

        row_sum = masked[i].sum()
        if row_sum > 0:
            masked[i] /= row_sum
        else:
            row = np.zeros(masked.shape[1], dtype=float)
            row[global_fallback_idx] = 1.0
            masked[i] = row

    return masked


def run(is_synthetic: bool = False, custom_param: int = 10, progress_callback=None):
    timing_enabled = str(os.environ.get("RESIDUAL_TIMING", "")).strip().lower() in {"1", "true", "yes"}
    t0 = time.perf_counter()

    def log_timing(label: str) -> None:
        if timing_enabled:
            elapsed = time.perf_counter() - t0
            print(f"[timing] {label}: {elapsed:.3f}s")

    input_path = INPUTS[0]

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Missing journeys artifact: {input_path}")

    if progress_callback:
        progress_callback(0.05)

    journeys_obj = _load_journeys(input_path)
    log_timing("load journeys")

    raw_df = _flatten_journeys_to_events(journeys_obj, progress_callback=progress_callback)
    log_timing("flatten journeys")

    if progress_callback:
        progress_callback(0.15)

    df = _build_next_waypoint_training_table(raw_df)
    log_timing("build training table")

    feature_columns = [
        "wap_id",
        "prev_wap_id",
        "prev2_wap_id",
        "hour_of_day",
        "day_of_week",
        "day_of_month",
        "month",
        "is_weekend",
        "seconds_from_prev",
        "seconds_from_prev2",
        "is_stay",
        "is_inferred",
    ]

    available_feature_columns = [c for c in feature_columns if c in df.columns]
    if "wap_id" not in available_feature_columns:
        raise ValueError("Expected 'wap_id' in training table.")
    if "next_wap_id" not in df.columns:
        raise ValueError("Expected 'next_wap_id' in training table.")

    ts_unique = np.sort(df["timestamp_utc"].astype("int64").unique())
    if len(ts_unique) < 2:
        raise ValueError("Not enough unique timestamps to create time splits.")

    # Overall 70/30 train/test split (no separate validation set).
    train_cut = ts_unique[int(len(ts_unique) * 0.70)]

    ts_int = df["timestamp_utc"].astype("int64")
    train_df = df[ts_int < train_cut].copy()
    test_df = df[ts_int >= train_cut].copy()

    if len(train_df) == 0 or len(test_df) == 0:
        raise ValueError(
            f"Time split produced empty set(s): "
            f"train={len(train_df)}, test={len(test_df)}"
        )

    print(f"Total rows before filtering: {len(df):,}")
    print(f"Train: {len(train_df):,} | Test: {len(test_df):,}")

    categorical_cols = [c for c in ["wap_id", "prev_wap_id", "prev2_wap_id"] if c in available_feature_columns]
    for frame in (train_df, test_df):
        for col in categorical_cols:
            frame[col] = frame[col].fillna("NONE").astype(str)

    min_class_count = int(os.environ.get("NEXT_WAP_MIN_CLASS_COUNT", "20"))
    train_target_counts = train_df["next_wap_id"].astype(str).value_counts()
    kept_labels = set(train_target_counts[train_target_counts >= min_class_count].index)

    train_df = train_df[train_df["next_wap_id"].astype(str).isin(kept_labels)].copy()
    test_df = test_df[test_df["next_wap_id"].astype(str).isin(kept_labels)].copy()

    if len(train_df) == 0 or len(test_df) == 0:
        raise ValueError(
            f"After rare-class filtering: train={len(train_df)}, test={len(test_df)}"
        )

    max_train_rows = int(os.environ.get("NEXT_WAP_MAX_TRAIN_ROWS", "250000"))
    if len(train_df) > max_train_rows:
        train_df = train_df.sample(n=max_train_rows, random_state=42).copy()
        train_df = train_df.sort_values("timestamp_utc").reset_index(drop=True)

    print(f"Train rows after filtering/sampling: {len(train_df):,}")
    print(f"Test rows after filtering: {len(test_df):,}")

    class_labels = sorted(train_df["next_wap_id"].astype(str).unique())
    if len(class_labels) < 2:
        raise ValueError("Need at least 2 target classes to train multiclass XGBoost.")

    class_to_idx = {label: i for i, label in enumerate(class_labels)}

    test_df = test_df[test_df["next_wap_id"].astype(str).isin(class_to_idx)].copy()

    if len(test_df) == 0:
        raise ValueError(
            f"After filtering unseen targets: test={len(test_df)}"
        )

    allowed_next_by_origin = (
        train_df.groupby("wap_id")["next_wap_id"]
        .apply(lambda s: sorted(set(s.astype(str))))
        .to_dict()
    )
    global_fallback_label = train_df["next_wap_id"].astype(str).mode().iloc[0]

    print(f"Num classes: {len(class_labels):,}")
    print(f"Unique wap_id in train: {train_df['wap_id'].nunique():,}")
    if "prev_wap_id" in train_df.columns:
        print(f"Unique prev_wap_id in train: {train_df['prev_wap_id'].nunique():,}")
    if "prev2_wap_id" in train_df.columns:
        print(f"Unique prev2_wap_id in train: {train_df['prev2_wap_id'].nunique():,}")
    print(f"Num features: {len(available_feature_columns):,}")

    # Internal eval slice from the training period for early stopping
    # (does not affect the overall 70/30 train/test split).
    train_ts_unique = np.sort(train_df["timestamp_utc"].astype("int64").unique())
    eval_cut = train_ts_unique[int(len(train_ts_unique) * 0.85)] if len(train_ts_unique) >= 2 else None
    train_ts_int = train_df["timestamp_utc"].astype("int64")

    if eval_cut is None:
        fit_df = train_df.copy()
        eval_df = train_df.tail(max(1, len(train_df) // 10)).copy()
        fit_df = train_df.iloc[: max(1, len(train_df) - len(eval_df))].copy()
    else:
        fit_df = train_df[train_ts_int < eval_cut].copy()
        eval_df = train_df[train_ts_int >= eval_cut].copy()

    if len(fit_df) == 0 or len(eval_df) == 0:
        fit_df = train_df.copy()
        eval_df = train_df.tail(max(1, len(train_df) // 10)).copy()

    print(f"Train-fit rows (for training): {len(fit_df):,}")
    print(f"Train-eval rows (for early stopping): {len(eval_df):,}")

    y_train = fit_df["next_wap_id"].astype(str).map(class_to_idx)
    y_valid = eval_df["next_wap_id"].astype(str).map(class_to_idx)
    y_test = test_df["next_wap_id"].astype(str).map(class_to_idx)

    X_train = fit_df[available_feature_columns].copy()
    X_valid = eval_df[available_feature_columns].copy()
    X_test = test_df[available_feature_columns].copy()

    for col in categorical_cols:
        seen_train_values = set(X_train[col].astype(str).unique())
        X_valid[col] = X_valid[col].astype(str)
        X_test[col] = X_test[col].astype(str)

        unseen_valid = ~X_valid[col].isin(seen_train_values)
        X_valid.loc[unseen_valid, col] = "NONE"
        unseen_test = ~X_test[col].isin(seen_train_values)
        X_test.loc[unseen_test, col] = "NONE"

        X_train[col] = X_train[col].astype("category")
        X_valid[col] = X_valid[col].astype("category")
        X_test[col] = X_test[col].astype("category")

    if progress_callback:
        progress_callback(0.35)

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(class_labels),
        n_estimators=60,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        random_state=42,
        enable_categorical=True,
        tree_method="hist",
        eval_metric="mlogloss",
        early_stopping_rounds=10,
        n_jobs=-1,
    )

    print("Starting model.fit()...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_valid, y_valid)],
        verbose=True,
    )
    print("Finished model.fit()")
    log_timing("train model")

    wrapped_model = XGBNextWaypointModel(
        feature_columns=available_feature_columns,
        class_labels=class_labels,
        model=model,
        allowed_next_by_origin=allowed_next_by_origin,
        global_fallback_label=global_fallback_label,
    )
    wrapped_model.output(MODEL_OUTPUT)

    if progress_callback:
        progress_callback(0.65)

    pred_proba_raw = model.predict_proba(X_test)
    pred_proba = _apply_origin_candidate_mask(
        pred_proba=pred_proba_raw,
        origins=test_df["wap_id"].astype(str).to_numpy(),
        class_labels=class_labels,
        allowed_next_by_origin=allowed_next_by_origin,
        global_fallback_label=global_fallback_label,
    )
    log_timing("predict proba + candidate mask")

    evaluation = XGBNextWaypointEvaluation()
    plot_output_path = EVAL_OUTPUT.replace(".pkl", "_top1_confidence_vs_accuracy.svg")

    evaluation.process(
        test_df=test_df,
        pred_proba=pred_proba,
        class_labels=class_labels,
        plot_output_path=plot_output_path,
        progress_callback=progress_callback,
    )
    log_timing("evaluate + plot")

    pred_top1_idx = np.argmax(pred_proba, axis=1)
    y_test_array = y_test.to_numpy(dtype=int, copy=False)
    accuracy = float((pred_top1_idx == y_test_array).mean()) if len(y_test_array) else 0.0
    print(f"Total test accuracy (top-1): {accuracy:.4f}")

    evaluation.output(EVAL_OUTPUT)
