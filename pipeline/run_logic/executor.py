import importlib
import json

from pipelineio.atomic import atomic_write_text
from pipelineio.config import PIPELINE_CACHE_DIR

from .planner import plan_step


def run_step(step_name: str) -> None:
    print(f"\n--- Evaluating Step: {step_name} ---")
    should_run, reason, current_state = plan_step(step_name)

    if not should_run:
        print(f"[{step_name}] SKIP ({reason})")
        return

    print(f"[{step_name}] RUN ({reason})")

    module_name = f"pipeline.steps.{step_name}"
    step_module = importlib.import_module(module_name)

    step_module.run()

    # Re-calculate hash after run to get the new output metadata correctly
    from .planner import calculate_step_hash

    new_hash, new_state = calculate_step_hash(step_name, step_module)

    cache_data = {"hash": new_hash, "state": new_state}

    cache_file = PIPELINE_CACHE_DIR / f"{step_name}.json"
    atomic_write_text(str(cache_file), json.dumps(cache_data, indent=2))
    print(f"[{step_name}] DONE")


def execute_pipeline(steps: list[str]) -> None:
    PIPELINE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for step in steps:
        run_step(step)
