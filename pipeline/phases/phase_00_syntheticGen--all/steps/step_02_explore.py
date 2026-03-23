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

# Define your anemic data structures here using @dataclass
@dataclass
class YourDataClass:
    # Example state properties
    items: list[str] = field(default_factory=list)

    def process(self, input_data: list[Any], custom_param: int = 10, progress_callback=None) -> None:
        """
        Your core business logic and transformations reside here.
        """
        total_items = len(input_data)
        
        for idx, item in enumerate(input_data):
            # --- LIVE PROGRESS HOOK ---
            # Update the progress bar periodically to prevent overwhelming the UI thread.
            if progress_callback and idx % max(1, total_items // 50) == 0:
                progress_callback(idx / max(1, total_items))
                
            # ... execute your logic ...
            self.items.append(str(item).upper())

    def output(self, output_path: str) -> None:
        """Persists the class state to disc via pickle."""
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "YourDataClass":
        """Loads a hydrated class instance from disc."""
        return load_draft(input_path)


# Declare the artifact paths this step depends on and generates
INPUTS = ['data/artifacts/world_drafts/example_input.pkl']
OUTPUTS = ['data/artifacts/world_drafts/example_output.pkl']


def run(custom_param: int = 10, progress_callback=None) -> None:
    """
    The auto-discovered orchestrator entry point.
    Parameters defined here are strictly enforced against `run.py`'s PIPELINE_CONFIG.
    """
    target_input = INPUTS[0].replace('world_drafts', 'synthetic_drafts')
    target_output = OUTPUTS[0].replace('world_drafts', 'synthetic_drafts')
    
    # 1. Load inputs (mocked here, use actual dependent classes in practice)
    # input_data = DependencyClass.load(target_input)
    input_data = ["example_1", "example_2", "example_3"] 
    
    # 2. Instantiate this step's anemic data structure empty
    data = YourDataClass()
    
    # 3. Execute business logic, passing down the target hyperparameters and callback
    data.process(input_data, custom_param=custom_param, progress_callback=progress_callback)
    
    # 4. Save the populated output state for the next step to consume
    # data.output(target_output)
