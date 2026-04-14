"""
PIPELINE STEP: BASELINE EVALUATION
=================================
Evaluates the BaselineTransitionModel produced in step_01.
"""

from typing import Any
from dataclasses import dataclass, field
from pipelineio.state import load_draft, save_draft
from .step_01_baseline import BaselineTransitionModel
import os


@dataclass
class BaselineEvaluation:
    # Stores evaluation metrics
    metrics: dict[str, float] = field(default_factory=dict)

    def process(
        self,
        baseline_model: BaselineTransitionModel,
        custom_param: int = 10,
        progress_callback=None
    ) -> None:
        """
        Evaluation logic using the trained baseline model.
        """
        if progress_callback:
            progress_callback(0.5)

        # TODO: Replace with real evaluation logic
        self.metrics["example_score"] = 0.95

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

    # 3. Run evaluation logic
    evaluation.process(
        baseline_model,
        custom_param=custom_param,
        progress_callback=progress_callback
    )

    # 4. Save results
    evaluation.output(target_output)