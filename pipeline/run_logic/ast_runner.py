import hashlib
import importlib
import importlib.util
import inspect
import json
import sys
import pprint
from pathlib import Path
from typing import Any
from types import ModuleType

from pipelineio.config import PIPELINE_CACHE_DIR
from pipelineio.explain import explain_meta_diff
from pipelineio.meta import get_input_meta, get_output_meta


def _sanitize_module_part(name: str) -> str:
    sanitized = []
    for ch in name:
        sanitized.append(ch if ch.isalnum() or ch == "_" else "_")
    result = "".join(sanitized)
    if result and result[0].isdigit():
        result = f"_{result}"
    return result


def _ensure_namespace_package(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
    else:
        existing_path = list(getattr(module, "__path__", []))
        if str(path) not in existing_path:
            existing_path.append(str(path))
            module.__path__ = existing_path


def load_step_module(phase_dir: Path, step_file: Path):
    phase_pkg = _sanitize_module_part(phase_dir.name)
    base_pkg = f"pipeline.phases.{phase_pkg}"
    steps_pkg = f"{base_pkg}.steps"
    module_name = f"{steps_pkg}.{step_file.stem}"

    _ensure_namespace_package(base_pkg, phase_dir)
    _ensure_namespace_package(steps_pkg, phase_dir / "steps")

    spec = importlib.util.spec_from_file_location(module_name, step_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load spec for {step_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, module_name


def calculate_step_hash(step_name: str, step_module, kwargs: dict[str, Any]) -> tuple[str, dict]:
    try:
        source_code = inspect.getsource(step_module)
    except OSError:
        source_code = inspect.getsource(step_module.run)

    raw_inputs = getattr(step_module, "INPUTS", [])
    raw_outputs = getattr(step_module, "OUTPUTS", [])
    
    # Pre-calculate the dynamic pathing substitutions if this is a synthetic run
    # so the cache hashes the actual generated mocks instead of the missing real files
    is_synthetic = kwargs.get("is_synthetic", False)
    
    # Some steps use explicitly indexed array routing, parse string matching
    if is_synthetic:
        resolved_inputs = [uri.replace('world_drafts', 'synthetic_drafts') for uri in raw_inputs]
        resolved_outputs = [uri.replace('world_drafts', 'synthetic_drafts') for uri in raw_outputs]
    else:
        resolved_inputs = raw_inputs
        resolved_outputs = raw_outputs

    inputs_meta = {uri: get_input_meta(uri) for uri in resolved_inputs}
    outputs_meta = {uri: get_output_meta(uri) for uri in resolved_outputs}

    state = {
        "step_name": step_name,
        "python_version": sys.version_info[:3],
        "source_code": source_code,
        "inputs": inputs_meta,
        "outputs": outputs_meta,
        "kwargs": kwargs,
    }

    state_json = json.dumps(state, sort_keys=True)
    return hashlib.sha256(state_json.encode("utf-8")).hexdigest(), state


def plan_and_execute_step(step_name: str, step_module, args: list[Any], kwargs: dict[str, Any], pad_length: int = 25) -> None:

    current_hash, current_state = calculate_step_hash(step_name, step_module, kwargs)

    cache_file = PIPELINE_CACHE_DIR / f"{step_name}.json"
    should_run = True
    reason = "No cache found"

    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)

            if cached_data.get("hash") == current_hash:
                should_run = False
                reason = "SKIP"
            else:
                old_state = cached_data.get("state", {})
                if old_state.get("source_code") != current_state.get("source_code"):
                    reason = "Source code changed"
                elif old_state.get("kwargs") != current_state.get("kwargs"):
                    reason = f"Hyperparameters changed: {old_state.get('kwargs')} -> {current_state.get('kwargs')}"
                else:
                    for uri, meta in current_state.get("inputs", {}).items():
                        old_meta = old_state.get("inputs", {}).get(uri, {})
                        diff = explain_meta_diff(old_meta, meta)
                        if diff:
                            reason = f"Input {uri}: {diff}"
                            break
                    else:
                        for uri, meta in current_state.get("outputs", {}).items():
                            old_meta = old_state.get("outputs", {}).get(uri, {})
                            diff = explain_meta_diff(old_meta, meta)
                            if diff:
                                reason = f"Output {uri}: {diff}"
                                break
                        else:
                            reason = "Hash mismatch (unknown reason)"
        except Exception as e:
            reason = f"Cache read error: {e}"

    name_padded = f"{step_name:<{pad_length}}"
    if not should_run:
        print(f"{name_padded} -:[██████████]:___Skipped")
        return

    import time
    from concurrent.futures import ThreadPoolExecutor

    sig = inspect.signature(step_module.run)
    shared_state = {"progress": 0.0, "error": None}
    
    def progress_callback(p: float):
        shared_state["progress"] = min(max(p, 0.0), 1.0)
        
    run_kwargs = kwargs.copy()
    if "progress_callback" in sig.parameters:
        run_kwargs["progress_callback"] = progress_callback

    start_time = time.time()
    
    def run_step():
        try:
            step_module.run(*args, **run_kwargs)
            shared_state["progress"] = 1.0
        except Exception as e:
            shared_state["error"] = e
            
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_step)
        
        while not future.done():
            elapsed = time.time() - start_time
            p_val = shared_state["progress"]
            
            total_eighths = int(p_val * 80)
            full_blocks = total_eighths // 8
            remainder = total_eighths % 8
            
            blocks = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]
            
            bar_str = ("█" * full_blocks)
            if full_blocks < 10:
                bar_str += blocks[remainder]
                
            spaces = 10 - len(bar_str)
            bar_str += (" " * spaces)
            
            sys.stdout.write(f"{name_padded} -:[{bar_str}]:___Running: {elapsed:.1f}s\r")
            sys.stdout.flush()
            time.sleep(0.1)
            
    if shared_state["error"]:
        print()
        raise shared_state["error"]

    duration = time.time() - start_time

    new_hash, new_state = calculate_step_hash(step_name, step_module, kwargs)
    cache_data = {"hash": new_hash, "state": new_state}

    with open(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)

    # Use \r to overwrite the Running... line without a newline so it looks clean, but we must add \n to move down
    sys.stdout.write(f"{name_padded} -:[██████████]:___Done: {duration:.1f}s       \n")
    sys.stdout.flush()


def update_config_json(config: dict[str, Any]) -> None:
    """Writes the completed configuration out to a dedicated pipeline_config.json file."""
    config_path = Path("pipeline_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def discover_and_run_pipeline(config: dict[str, Any] = None) -> None:
    """
    Automatically discovers and runs pipeline phases and steps from the filesystem.
    Validates hyperparameters via reflection against PIPELINE_CONFIG.
    """
    if config is None:
        config = {}
        
    PIPELINE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        phases_dir = Path(__file__).resolve().parent.parent / "phases"
        if not phases_dir.exists() or not phases_dir.is_dir():
            raise FileNotFoundError(f"Phases directory not found at {phases_dir}")
    except Exception as e:
        print(f"ERROR resolving pipeline phases directory: {e}")
        return

    phase_dirs = sorted([d for d in phases_dir.iterdir() if d.is_dir() and d.name.startswith("phase_")])
    
    discovered_steps = []
    
    for phase_dir in phase_dirs:
        steps_dir = phase_dir / "steps"
        if not steps_dir.exists():
            continue
            
        step_files = sorted([f for f in steps_dir.glob("step_*.py") if f.is_file()])
        for step_file in step_files:
            discovered_steps.append((phase_dir, step_file, step_file.stem))

    needs_update = False

    for phase_dir, step_file, step_short_name in discovered_steps:
        try:
            step_module, module_name = load_step_module(phase_dir, step_file)
            sig = inspect.signature(step_module.run)
            phase_name = phase_dir.name
            
            if phase_name not in config:
                config[phase_name] = {}
                needs_update = True
                
            phase_config = config[phase_name]
            
            # Ensure the config dictionary has an entry for this step
            if step_short_name not in phase_config:
                phase_config[step_short_name] = {}
                needs_update = True
                
            step_config = phase_config[step_short_name]
            
            # Check for missing parameters in the step definition
            for param_name, param in sig.parameters.items():
                if param_name == "progress_callback":
                    continue
                if param_name not in step_config:
                    needs_update = True
                    # Fill with default if available, otherwise explicit None or placeholder
                    if param.default is not inspect.Parameter.empty:
                        step_config[param_name] = param.default
                    else:
                        step_config[param_name] = None
                        
        except Exception as e:
            print(f"[{module_name}] ERROR during inspection: {e}")
            raise

    if needs_update:
        update_config_json(config)
        print("\n\n\033[93mValidation Error: pipeline_config.json was incomplete or missing arguments.\033[0m")
        print("\033[93mIt has been auto-updated with defaults. Please review pipeline_config.json and re-run.\033[0m\n")
        sys.exit(1)

    # Execution Loop
    current_phase = None
    
    # Calculate pad length per phase
    phase_pad_lengths = {}
    for phase_dir, _step_file, step_short_name in discovered_steps:
        phase_name = phase_dir.name
        if phase_name not in phase_pad_lengths:
            phase_pad_lengths[phase_name] = len(step_short_name)
        else:
            phase_pad_lengths[phase_name] = max(phase_pad_lengths[phase_name], len(step_short_name))
            
    for phase_dir, step_file, step_short_name in discovered_steps:
        phase_name = phase_dir.name
        pad_length = phase_pad_lengths.get(phase_name, 25)
        
        try:
            phase_num = phase_name.split("_")[1]
        except IndexError:
            phase_num = "??"
            
        if phase_name != current_phase:
            current_phase = phase_name
            total_width = pad_length + 29
            phase_text = f"+_/(phase {phase_num})\\_+"
            
            left_dash = (total_width - len(phase_text)) // 2
            right_dash = total_width - len(phase_text) - left_dash
            
            print(f"\n{'-' * left_dash}{phase_text}{'-' * right_dash}")
            print(phase_name.center(total_width))
            print("-" * total_width)

        try:
            step_module, module_name = load_step_module(phase_dir, step_file)
            step_config = config.get(phase_name, {}).get(step_short_name, {})
            plan_and_execute_step(step_short_name, step_module, [], step_config, pad_length=pad_length)
        except Exception as e:
            print(f"[{module_name}] ERROR during execution: {e}")
            raise
