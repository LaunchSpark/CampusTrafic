"""
PIPELINE STEP TEMPLATE
======================

How to create a new pipeline step:
1. Copy this file into your target phase directory: `pipeline/phases/phase_XX_name/steps/step_YY_name.py`
2. Update the `INPUTS` and `OUTPUTS` lists with your desired artifact read/write paths.
3. Rename `YourDataClass` to represent the core anemic data structure you are building.
4. Write your business logic inside the methods of your dataclass.
5. Modify the `run()` function to accept your required hyperparameters.

About the Progress Bar:
-----------------------
If your step processes data in a loop and you want a live progress bar in the terminal:
1. Include `progress_callback=None` in your `run()` function signature.
2. Pass it down to your processing method.
3. Periodically call `progress_callback(float)` with a value between 0.0 and 1.0.
   Example: `progress_callback(current_idx / total_items)`
4. Best Practice: To prevent the UI drawing from slowing down your logic, only 
   trigger the callback every N iterations (e.g., `if idx % 50 == 0:`).

About Hyperparameters:
----------------------
Any arguments you add to the `run()` signature (except `progress_callback` and `is_synthetic`) 
will be automatically discovered by the orchestrator and appended to `PIPELINE_CONFIG` in `run.py`.

About Synthetic Data:
---------------------
The `is_synthetic` flag allows independent component testing. When True, the pipeline 
automatically replaces the `world_drafts` directory with `synthetic_drafts`. This lets you 
read/write mock data safely without polluting the main production cache.
"""

from typing import Any
from dataclasses import dataclass, field
from pipelineio.state import load_draft, save_draft
from .step_01_baseline import BaselineTransitionModel

@dataclass
class BaselineEvaluation:
    # Example state properties for evaluation metrics
    metrics: dict[str, float] = field(default_factory=dict)

    def process(self, baseline_model: BaselineTransitionModel, custom_param: int = 10, progress_callback=None) -> None:
        """
        Your baseline evaluation metrics/business logic reside here.
        """
        # --- LIVE PROGRESS HOOK ---
        if progress_callback:
            progress_callback(0.5)
            
        # TODO: Implement your evaluation comparison logic using `baseline_model`
        self.metrics["example_score"] = 0.95
        
        if progress_callback:
            progress_callback(1.0)

    def output(self, output_path: str) -> None:
        """Persists the class state to disc via pickle."""
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "BaselineEvaluation":
        """Loads a hydrated class instance from disc."""
        return load_draft(input_path)


# Declare the artifact paths this step depends on and generates
run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')
INPUTS = [f'data/artifacts/runs/{run_id}/model_tree/baseline_transitions.pkl']
OUTPUTS = [f'data/artifacts/runs/{run_id}/model_tree/baseline_evaluation.pkl']


def run(is_synthetic: bool = True, custom_param: int = 10, progress_callback=None) -> None:
    """
    The auto-discovered orchestrator entry point.
    """
    target_input = INPUTS[0]
    target_output = OUTPUTS[0]
    
    if is_synthetic:
        target_input = target_input.replace('runs/' + run_id, 'synthetic_drafts')
        target_output = target_output.replace('runs/' + run_id, 'synthetic_drafts')
    
    # 1. Load the model generated from step 01
    baseline_model = BaselineTransitionModel.load(target_input)
    
    # 2. Instantiate this step's data structure
    evaluation = BaselineEvaluation()
    
    # 3. Execute business logic
    evaluation.process(baseline_model, custom_param=custom_param, progress_callback=progress_callback)
    
    # 4. Save the evaluated metrics
    evaluation.output(target_output)