"""
PIPELINE STEP: BASELINE EVALUATION
=================================
Evaluates the BaselineTransitionModel produced in step_01.
"""

from typing import Any
from dataclasses import dataclass, field
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pipelineio.state import load_draft, save_draft
from .step_01_baseline import BaselineTransitionModel
import os


@dataclass
class BaselineEvaluation:
    # Stores evaluation metrics
    metrics: dict[str, float] = field(default_factory=dict)
    plot_path: str | None = None

    def _build_transition_comparison_points(
        self, baseline_model: BaselineTransitionModel
    ) -> list[tuple[float, float, int, str, str]]:
        """
        Build tuples of:
            (actual_transition_frequency, predicted_transition_probability, count, origin, destination)
        """
        points: list[tuple[float, float, int, str, str]] = []

        for origin, destinations in baseline_model.transition_counts.items():
            total_outbound = sum(destinations.values())
            if total_outbound <= 0:
                continue

            predicted_for_origin = baseline_model.transition_probs.get(origin, {})
            for destination, count in destinations.items():
                if count <= 0:
                    continue
                actual_frequency = count / total_outbound
                predicted_probability = float(predicted_for_origin.get(destination, 0.0))
                points.append(
                    (actual_frequency, predicted_probability, int(count), str(origin), str(destination))
                )
        return points

    def _plot_predicted_vs_actual(
        self,
        points: list[tuple[float, float, int, str, str]],
        output_path: str | None = None,
    ) -> None:
        """
        Scatter plot for predicted transition probabilities vs actual observed frequencies.
        Point size is weighted by observed transition counts.
        """
        if not points:
            print("No transition points found. Skipping baseline evaluation plot.")
            return

        actual = np.array([p[0] for p in points], dtype=float)
        predicted = np.array([p[1] for p in points], dtype=float)
        counts = np.array([p[2] for p in points], dtype=float)

        point_sizes = 20 + 120 * (counts / max(counts.max(), 1.0))

        plt.figure(figsize=(8, 6))
        plt.scatter(
            actual,
            predicted,
            s=point_sizes,
            alpha=0.65,
            edgecolors="black",
            linewidth=0.4,
            label="Observed transitions",
        )

        min_v = float(min(actual.min(), predicted.min()))
        max_v = float(max(actual.max(), predicted.max()))
        plt.plot([min_v, max_v], [min_v, max_v], linestyle="--", linewidth=1.5, label="Ideal: y=x")

        plt.xlabel("Actual Transition Frequency")
        plt.ylabel("Predicted Probability")
        plt.title("Baseline Model: Predicted vs Actual Transitions")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, dpi=150)
            plt.close()
            self.plot_path = output_path
            print(f"Saved baseline predicted-vs-actual plot to {output_path}")
        else:
            plt.show()

    def process(
        self,
        baseline_model: BaselineTransitionModel,
        plot_output_path: str | None = None,
        custom_param: int = 10,
        progress_callback=None
    ) -> None:
        """
        Evaluation logic using the trained baseline model.
        """
        if progress_callback:
            progress_callback(0.2)

        points = self._build_transition_comparison_points(baseline_model)

        if progress_callback:
            progress_callback(0.6)

        if points:
            actual = np.array([p[0] for p in points], dtype=float)
            predicted = np.array([p[1] for p in points], dtype=float)
            counts = np.array([p[2] for p in points], dtype=float)

            abs_errors = np.abs(predicted - actual)
            weighted_mae = float(np.average(abs_errors, weights=np.maximum(counts, 1.0)))
            rmse = float(np.sqrt(np.mean((predicted - actual) ** 2)))
            corr = float(np.corrcoef(actual, predicted)[0, 1]) if len(points) > 1 else 1.0

            self.metrics["num_transitions"] = float(len(points))
            self.metrics["weighted_mae"] = weighted_mae
            self.metrics["rmse"] = rmse
            self.metrics["pearson_corr"] = corr
            self.metrics["custom_param"] = float(custom_param)
        else:
            self.metrics["num_transitions"] = 0.0
            self.metrics["weighted_mae"] = 0.0
            self.metrics["rmse"] = 0.0
            self.metrics["pearson_corr"] = 0.0
            self.metrics["custom_param"] = float(custom_param)

        self._plot_predicted_vs_actual(points, output_path=plot_output_path)

        if progress_callback:
            progress_callback(1.0)

    def output(self, output_path: str) -> None:
        """Save evaluation results."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "BaselineEvaluation":
        """Load saved evaluation."""
        return load_draft(input_path)


# --- Paths ---
run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')

INPUTS = [
    f'data/artifacts/runs/{run_id}/model_tree/baseline_transitions.pkl'
]

OUTPUTS = [
    f'data/artifacts/runs/{run_id}/model_tree/baseline_evaluation.pkl'
]


def run(
    is_synthetic: bool = False,   # Force real data
    custom_param: int = 10,
    progress_callback=None
) -> None:
    """
    Entry point for pipeline execution.
    """
    target_input = INPUTS[0]
    target_output = OUTPUTS[0]

    # Safety check
    if not os.path.exists(target_input):
        raise FileNotFoundError(
            f"\nExpected input not found:\n{target_input}\n\n"
            "Make sure step_01_baseline ran successfully with is_synthetic=False."
        )

    # 1. Load model from step_01
    baseline_model = BaselineTransitionModel.load(target_input)

    # 2. Create evaluation object
    evaluation = BaselineEvaluation()

    plot_output_path = target_output.replace(".pkl", "_predicted_vs_actual.png")

    # 3. Run evaluation logic
    evaluation.process(
        baseline_model,
        plot_output_path=plot_output_path,
        custom_param=custom_param,
        progress_callback=progress_callback
    )

    # 4. Save results
    evaluation.output(target_output)
