import hashlib
import importlib
import inspect
import json
import sys

from pipelineio.config import PIPELINE_CACHE_DIR
from pipelineio.explain import explain_meta_diff
from pipelineio.meta import get_input_meta, get_output_meta


def calculate_step_hash(step_name: str, step_module) -> tuple[str, dict]:
    source_code = inspect.getsource(step_module.run)
    inputs_meta = {uri: get_input_meta(uri) for uri in getattr(step_module, "INPUTS", [])}
    outputs_meta = {uri: get_output_meta(uri) for uri in getattr(step_module, "OUTPUTS", [])}

    state = {
        "step_name": step_name,
        "python_version": sys.version_info[:3],
        "source_code": source_code,
        "inputs": inputs_meta,
        "outputs": outputs_meta,
    }

    state_json = json.dumps(state, sort_keys=True)
    return hashlib.sha256(state_json.encode("utf-8")).hexdigest(), state


def plan_step(step_name: str) -> tuple[bool, str | None, dict]:
    module_name = f"pipeline.steps.{step_name}"
    step_module = importlib.import_module(module_name)

    current_hash, current_state = calculate_step_hash(step_name, step_module)

    cache_file = PIPELINE_CACHE_DIR / f"{step_name}.json"
    if not cache_file.exists():
        return True, "No cache found", current_state

    try:
        with open(cache_file, "r") as f:
            cached_data = json.load(f)

        if cached_data.get("hash") != current_hash:
            old_state = cached_data.get("state", {})
            if old_state.get("source_code") != current_state.get("source_code"):
                return True, "Source code changed", current_state

            for uri, meta in current_state.get("inputs", {}).items():
                old_meta = old_state.get("inputs", {}).get(uri, {})
                diff = explain_meta_diff(old_meta, meta)
                if diff:
                    return True, f"Input {uri}: {diff}", current_state

            for uri, meta in current_state.get("outputs", {}).items():
                old_meta = old_state.get("outputs", {}).get(uri, {})
                diff = explain_meta_diff(old_meta, meta)
                if diff:
                    return True, f"Output {uri}: {diff}", current_state

            return True, "Hash mismatch (unknown reason)", current_state

        return False, "SKIP", current_state
    except Exception as e:
        return True, f"Cache read error: {e}", current_state
