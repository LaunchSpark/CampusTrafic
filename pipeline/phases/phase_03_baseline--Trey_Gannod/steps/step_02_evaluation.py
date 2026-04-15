"""
PIPELINE STEP: BASELINE EVALUATION (PROBABILITY + FLOW)
======================================================
Evaluates the BaselineTransitionModel using held-out test data.
Now includes both probability and flow evaluation.
"""

from typing import Any
from dataclasses import dataclass, field
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from pipelineio.state import load_draft, save_draft
from .step_01_baseline import BaselineTransitionModel
import os
from collections import defaultdict

matplotlib.use("Agg")


@dataclass
class BaselineEvaluation:
    metrics: dict[str, float] = field(default_factory=dict)
    plot_path: str | None = None

    # -----------------------------
    # Build test-set actual counts
    # -----------------------------
    def _compute_test_transition_counts(self, journeys_data: Any) -> dict:
        counts = defaultdict(lambda: defaultdict(int))

        for journey in journeys_data.journeys:
            waypoints = journey.waypoints

            for i in range(len(waypoints) - 1):
                wp_a = waypoints[i]
                wp_b = waypoints[i + 1]

                node_a = wp_a.wap_id
                node_b = wp_b.wap_id

                if node_a != node_b:
                    counts[node_a][node_b] += 1

        return counts

    # ----------------------------------------
    # Build comparison points (prob + flow)
    # ----------------------------------------
    def _build_points(
        self,
        baseline_model: BaselineTransitionModel,
        test_counts: dict
    ):
        prob_points = []
        flow_points = []

        for origin, destinations in test_counts.items():
            total_outbound = sum(destinations.values())
            if total_outbound == 0:
                continue

            predicted_probs = baseline_model.transition_probs.get(origin, {})
            predicted_flows = baseline_model.flow_matrix.get(origin, {})

            for destination, count in destinations.items():
                # Probability
                actual_prob = count / total_outbound
                predicted_prob = float(predicted_probs.get(destination, 0.0))

                # Flow
                actual_flow = float(count)
                predicted_flow = float(predicted_flows.get(destination, 0.0))

                prob_points.append((actual_prob, predicted_prob, count))
                flow_points.append((actual_flow, predicted_flow, count))

        return prob_points, flow_points

    # -----------------------------
    # Plot (probability)
    # -----------------------------
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
        plt.title("Baseline Model: Predicted vs Actual (Probability)")
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

    # -----------------------------
    # Core evaluation logic
    # -----------------------------
    def process(
        self,
        baseline_model: BaselineTransitionModel,
        test_journeys_data: Any,
        plot_output_path=None,
        custom_param: int = 10,
        progress_callback=None
    ):

        if progress_callback:
            progress_callback(0.2)

        test_counts = self._compute_test_transition_counts(test_journeys_data)

        if progress_callback:
            progress_callback(0.5)

        prob_points, flow_points = self._build_points(
            baseline_model,
            test_counts
        )

        if progress_callback:
            progress_callback(0.8)

        # -----------------------------
        # Probability metrics
        # -----------------------------
        if prob_points:
            actual = np.array([p[0] for p in prob_points])
            predicted = np.array([p[1] for p in prob_points])
            counts = np.array([p[2] for p in prob_points])

            errors = predicted - actual
            abs_errors = np.abs(errors)

            self.metrics["prob_weighted_mae"] = float(np.average(abs_errors, weights=counts))
            self.metrics["prob_rmse"] = float(np.sqrt(np.mean(errors ** 2)))

            ss_res = np.sum((actual - predicted) ** 2)
            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            self.metrics["prob_r2"] = float(1.0 - (ss_res / ss_tot if ss_tot > 0 else 0.0))

        # -----------------------------
        # Flow metrics
        # -----------------------------
        if flow_points:
            actual = np.array([p[0] for p in flow_points])
            predicted = np.array([p[1] for p in flow_points])

            errors = predicted - actual
            abs_errors = np.abs(errors)

            self.metrics["flow_mae"] = float(np.mean(abs_errors))
            self.metrics["flow_rmse"] = float(np.sqrt(np.mean(errors ** 2)))

            ss_res = np.sum((actual - predicted) ** 2)
            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            self.metrics["flow_r2"] = float(1.0 - (ss_res / ss_tot if ss_tot > 0 else 0.0))

        self.metrics["num_transitions"] = float(len(prob_points))

        # Print metrics
        print("\n================ BASELINE EVALUATION METRICS ================\n")
        for key, value in self.metrics.items():
            print(f"{key}: {value}")
        print("\n=============================================================\n")

        # Plot probability comparison
        self._plot_predicted_vs_actual(prob_points, output_path=plot_output_path)

        if progress_callback:
            progress_callback(1.0)

    # -----------------------------
    # Save
    # -----------------------------
    def output(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_draft(self, output_path)


# -----------------------------
# Paths
# -----------------------------
run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')

MODEL_INPUT = f'data/artifacts/runs/{run_id}/model_tree/baseline_transitions.pkl'
TEST_INPUT = f'data/artifacts/runs/{run_id}/model_tree/baseline_test_journeys.pkl'
OUTPUT = f'data/artifacts/runs/{run_id}/model_tree/baseline_evaluation.pkl'


def run(
    is_synthetic: bool = False,
    custom_param: int = 10,
    progress_callback=None
):

    if not os.path.exists(MODEL_INPUT):
        raise FileNotFoundError("Missing trained model. Run step_01 first.")

    if not os.path.exists(TEST_INPUT):
        raise FileNotFoundError("Missing test set. Run step_01 first.")

    baseline_model = BaselineTransitionModel.load(MODEL_INPUT)
    test_journeys = load_draft(TEST_INPUT)

    evaluation = BaselineEvaluation()

    plot_output_path = OUTPUT.replace(".pkl", "_predicted_vs_actual.svg")

    evaluation.process(
        baseline_model,
        test_journeys,
        plot_output_path=plot_output_path,
        custom_param=custom_param,
        progress_callback=progress_callback
    )

    evaluation.output(OUTPUT)