"""
PIPELINE STEP: XGBOOST NEXT-WAYPOINT MODEL + EVALUATION
=======================================================
Trains an XGBoost multiclass classifier to predict next distinct waypoint,
then evaluates it using the same metrics/plot style as the baseline model.
"""

from dataclasses import dataclass, field
import os
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb

from pipelineio.state import load_draft, save_draft


# -----------------------------
# Paths
# -----------------------------
run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")

INPUTS = "next_waypoint_training_table.csv"

MODEL_OUTPUT = f"data/artifacts/runs/{run_id}/residual/xgb_next_waypoint_model.pkl"
EVAL_OUTPUT = f"data/artifacts/runs/{run_id}/residual/xgb_next_waypoint_evaluation.pkl"

@dataclass
class XGBTop1AccuracyEvaluation:
    metrics: dict[str, float] = field(default_factory=dict)
    plot_path: str | None = None

    def _build_top1_accuracy_points(
        self,
        test_df: pd.DataFrame,
        pred_proba: np.ndarray,
        class_labels: list[str],
    ) -> list[tuple[float, float, int, str]]:
        """
        Build points of:
            (actual_top1_accuracy, mean_top1_confidence, count, origin)

        For each origin (current wap), compare:
          - actual top-1 accuracy on rows from that origin
          - mean predicted top-1 confidence on rows from that origin
        """
        points = []

        pred_top1_idx = np.argmax(pred_proba, axis=1)
        pred_top1_labels = np.array([class_labels[i] for i in pred_top1_idx])
        pred_top1_conf = pred_proba[np.arange(len(pred_proba)), pred_top1_idx]

        eval_df = test_df.copy()
        eval_df["origin"] = eval_df["wap_id"].astype(str)
        eval_df["true_label"] = eval_df["next_wap_id"].astype(str)
        eval_df["pred_label"] = pred_top1_labels
        eval_df["pred_conf"] = pred_top1_conf
        eval_df["correct"] = (eval_df["true_label"] == eval_df["pred_label"]).astype(int)

        grouped = (
            eval_df.groupby("origin")
            .agg(
                actual_top1_accuracy=("correct", "mean"),
                mean_top1_confidence=("pred_conf", "mean"),
                count=("correct", "size"),
            )
            .reset_index()
        )

        for _, row in grouped.iterrows():
            points.append(
                (
                    float(row["actual_top1_accuracy"]),
                    float(row["mean_top1_confidence"]),
                    int(row["count"]),
                    str(row["origin"]),
                )
            )

        return points

    def _plot_top1_accuracy(self, points, output_path=None):
        if not points:
            print("No points to plot.")
            return

        actual = np.array([p[0] for p in points])
        predicted = np.array([p[1] for p in points])
        counts = np.array([p[2] for p in points])

        sizes = 20 + 120 * (counts / max(counts.max(), 1))

        plt.figure(figsize=(8, 6))
        plt.scatter(actual, predicted, s=sizes, alpha=0.65, edgecolors="black")

        min_v = min(actual.min(), predicted.min())
        max_v = max(actual.max(), predicted.max())

        plt.plot([min_v, max_v], [min_v, max_v], linestyle="--", label="Ideal y=x")

        plt.xlabel("Actual Top-1 Accuracy")
        plt.ylabel("Mean Top-1 Predicted Confidence")
        plt.title("XGBoost Model: Top-1 Accuracy vs Confidence (Test Set)")
        plt.grid(True)
        plt.legend()

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
            progress_callback(0.5)

        points = self._build_top1_accuracy_points(
            test_df=test_df,
            pred_proba=pred_proba,
            class_labels=class_labels,
        )

        pred_top1_idx = np.argmax(pred_proba, axis=1)
        pred_top1_labels = np.array([class_labels[i] for i in pred_top1_idx])
        true_labels = test_df["next_wap_id"].astype(str).to_numpy()
        correct = (pred_top1_labels == true_labels).astype(int)

        if progress_callback:
            progress_callback(0.8)

        if len(correct) > 0:
            self.metrics["top1_accuracy"] = float(correct.mean())
        else:
            self.metrics["top1_accuracy"] = 0.0

        if points:
            actual = np.array([p[0] for p in points])
            predicted = np.array([p[1] for p in points])
            counts = np.array([p[2] for p in points])

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

        print("\n================ TOP-1 ACCURACY EVALUATION ================\n")
        for key, value in self.metrics.items():
            print(f"{key}: {value}")
        print("\n==========================================================\n")

        self._plot_top1_accuracy(points, output_path=plot_output_path)

        if progress_callback:
            progress_callback(1.0)

    def output(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_draft(self, output_path)

@dataclass
class XGBNextWaypointModel:
    feature_columns: list[str] = field(default_factory=list)
    class_labels: list[str] = field(default_factory=list)
    model: Any = None

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

    def _build_transition_comparison_points(
        self,
        test_df: pd.DataFrame,
        pred_proba: np.ndarray,
        class_labels: list[str],
    ) -> list[tuple[float, float, int, str, str]]:
        """
        Build points of:
            (actual_frequency, predicted_probability, count, origin, destination)

        For each origin (current wap), compare:
          - actual test frequency to each destination
          - mean predicted probability to each destination
        """
        points = []

        class_index_to_label = {i: label for i, label in enumerate(class_labels)}

        test_df = test_df.copy()
        test_df["origin"] = test_df["wap_id"].astype(str)
        test_df["destination"] = test_df["next_wap_id"].astype(str)

        # Actual counts per (origin, destination)
        actual_counts = (
            test_df.groupby(["origin", "destination"])
            .size()
            .rename("count")
            .reset_index()
        )

        # Total outbound per origin
        outbound_counts = (
            test_df.groupby("origin")
            .size()
            .rename("total_outbound")
            .reset_index()
        )

        actual_counts = actual_counts.merge(outbound_counts, on="origin", how="left")
        actual_counts["actual_frequency"] = actual_counts["count"] / actual_counts["total_outbound"]

        # Mean predicted probability per (origin, destination)
        pred_df = pd.DataFrame(pred_proba, columns=[class_index_to_label[i] for i in range(pred_proba.shape[1])])
        pred_df["origin"] = test_df["origin"].to_numpy()

        predicted_records = []
        for origin, group in pred_df.groupby("origin"):
            mean_probs = group.drop(columns=["origin"]).mean(axis=0)
            for destination, mean_prob in mean_probs.items():
                predicted_records.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "predicted_probability": float(mean_prob),
                    }
                )

        predicted_df = pd.DataFrame(predicted_records)

        merged = actual_counts.merge(
            predicted_df,
            on=["origin", "destination"],
            how="left",
        )
        merged["predicted_probability"] = merged["predicted_probability"].fillna(0.0)

        for _, row in merged.iterrows():
            points.append(
                (
                    float(row["actual_frequency"]),
                    float(row["predicted_probability"]),
                    int(row["count"]),
                    str(row["origin"]),
                    str(row["destination"]),
                )
            )

        return points

    def _plot_predicted_vs_actual(self, points, output_path=None):
        if not points:
            print("No points to plot.")
            return

        actual = np.array([p[0] for p in points])
        predicted = np.array([p[1] for p in points])
        counts = np.array([p[2] for p in points])

        sizes = 20 + 120 * (counts / max(counts.max(), 1))

        plt.figure(figsize=(8, 6))
        plt.scatter(actual, predicted, s=sizes, alpha=0.65, edgecolors="black")

        min_v = min(actual.min(), predicted.min())
        max_v = max(actual.max(), predicted.max())

        plt.plot([min_v, max_v], [min_v, max_v], linestyle="--", label="Ideal y=x")

        plt.xlabel("Actual (Test Frequency)")
        plt.ylabel("Predicted (Model Probability)")
        plt.title("XGBoost Model: Predicted vs Actual (Test Set)")
        plt.grid(True)
        plt.legend()

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
            progress_callback(0.5)

        points = self._build_transition_comparison_points(
            test_df=test_df,
            pred_proba=pred_proba,
            class_labels=class_labels,
        )

        if progress_callback:
            progress_callback(0.8)

        if points:
            actual = np.array([p[0] for p in points])
            predicted = np.array([p[1] for p in points])
            counts = np.array([p[2] for p in points])

            errors = predicted - actual
            abs_errors = np.abs(errors)

            self.metrics["weighted_mae"] = float(np.average(abs_errors, weights=counts))
            self.metrics["rmse"] = float(np.sqrt(np.mean(errors ** 2)))
            self.metrics["pearson_corr"] = (
                float(np.corrcoef(actual, predicted)[0, 1]) if len(points) > 1 else 0.0
            )

            ss_res = np.sum((actual - predicted) ** 2)
            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            r2 = 1.0 - (ss_res / ss_tot if ss_tot > 0 else 0.0)
            self.metrics["r2"] = float(r2)

            self.metrics["num_transitions"] = float(len(points))
        else:
            self.metrics["weighted_mae"] = 0.0
            self.metrics["rmse"] = 0.0
            self.metrics["pearson_corr"] = 0.0
            self.metrics["r2"] = 0.0
            self.metrics["num_transitions"] = 0.0

        print("\n================ XGBOOST EVALUATION METRICS ================\n")
        for key, value in self.metrics.items():
            print(f"{key}: {value}")
        print("\n===========================================================\n")

        self._plot_predicted_vs_actual(points, output_path=plot_output_path)

        if progress_callback:
            progress_callback(1.0)

    def output(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_draft(self, output_path)


def run(is_synthetic: bool = False, custom_param: int = 10, progress_callback=None):
    input_csv = INPUTS

    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Missing training table: {input_csv}")

    if progress_callback:
        progress_callback(0.1)

    df = pd.read_csv(input_csv, parse_dates=["timestamp_utc", "next_timestamp_utc", "prev_timestamp_utc"])

    # Keep rows with valid target
    df = df[df["next_wap_id"].notna()].copy()

    # Feature columns
    feature_columns = [
        "wap_id",
        "prev_wap_id",
        "hour_of_day",
        "day_of_week",
        "day_of_month",
        "month",
        "is_weekend",
        "seconds_from_prev",
        "is_stay",
        "is_inferred"
    ]

    available_feature_columns = [c for c in feature_columns if c in df.columns]
    if "wap_id" not in available_feature_columns:
        raise ValueError("Expected 'wap_id' in training table.")
    if "next_wap_id" not in df.columns:
        raise ValueError("Expected 'next_wap_id' in training table.")

    # Chronological split
    rng = np.random.default_rng(42)
    journey_ids = df["journey_index"].drop_duplicates().to_numpy()
    journey_ids = rng.permutation(journey_ids)
    split_idx = int(0.7 * len(journey_ids))
    train_journeys = set(journey_ids[:split_idx])
    test_journeys = set(journey_ids[split_idx:])
    
    train_df = df[df["journey_index"].isin(train_journeys)].copy()
    test_df = df[df["journey_index"].isin(test_journeys)].copy()

    print(f"Total rows: {len(df)}")
    print(f"Train: {len(train_df)} | Test: {len(test_df)}")

    # Encode categorical columns
    categorical_cols = [c for c in ["wap_id", "prev_wap_id"] if c in available_feature_columns]
    for frame in (train_df, test_df):
        for col in categorical_cols:
            frame[col] = frame[col].fillna("NONE").astype("category")

    # Target encoding
    class_labels = sorted(train_df["next_wap_id"].astype(str).unique())
    class_to_idx = {label: i for i, label in enumerate(class_labels)}

    # Filter test rows to seen labels only for this version
    test_df = test_df[test_df["next_wap_id"].astype(str).isin(class_to_idx)].copy()

    y_train = train_df["next_wap_id"].astype(str).map(class_to_idx)
    y_test = test_df["next_wap_id"].astype(str).map(class_to_idx)

    X_train = train_df[available_feature_columns].copy()

    X_test = test_df[available_feature_columns].copy()

    for col in categorical_cols:
        X_test[col] = X_test[col].astype(str)
        unseen_mask = ~X_test[col].isin(X_train[col].astype(str).unique())
        X_test.loc[unseen_mask, col] = "NONE"
        X_train[col] = X_train[col].astype(str).astype("category")
        X_test[col] = X_test[col].astype("category")

    if progress_callback:
        progress_callback(0.3)

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(class_labels),
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        enable_categorical=True,
        tree_method="hist",
        eval_metric="mlogloss",
    )

    model.fit(
        X_train,
        y_train,
        verbose=False,
    )

    wrapped_model = XGBNextWaypointModel(
        feature_columns=available_feature_columns,
        class_labels=class_labels,
        model=model,
    )
    wrapped_model.output(MODEL_OUTPUT)

    if progress_callback:
        progress_callback(0.6)

    pred_proba = model.predict_proba(X_test)

    top1_eval = XGBTop1AccuracyEvaluation()
    top1_plot_output_path = EVAL_OUTPUT.replace(".pkl", "_top1_accuracy_vs_confidence.svg")
    top1_eval_output_path = EVAL_OUTPUT.replace(".pkl", "_top1_accuracy.pkl")

    top1_eval.process(
        test_df=test_df,
        pred_proba=pred_proba,
        class_labels=class_labels,
        plot_output_path=top1_plot_output_path,
        progress_callback=progress_callback,
    )

    top1_eval.output(top1_eval_output_path)

    pred_top1_idx = np.argmax(pred_proba, axis=1)
    y_test_array = y_test.to_numpy()

    accuracy = float((pred_top1_idx == y_test_array).mean())
    print(f"Test accuracy (top-1): {accuracy:.4f}")

    evaluation = XGBNextWaypointEvaluation()
    plot_output_path = EVAL_OUTPUT.replace(".pkl", "_predicted_vs_actual.svg")

    evaluation.process(
        test_df=test_df,
        pred_proba=pred_proba,
        class_labels=class_labels,
        plot_output_path=plot_output_path,
        progress_callback=progress_callback,
    )

    evaluation.output(EVAL_OUTPUT)