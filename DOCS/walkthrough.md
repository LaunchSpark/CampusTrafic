# CampusTrafic Migration Walkthrough

The project has been fully migrated to a purely functional DAG pipeline architecture without breaking the original topological requirements.

## 1. Engine Scaffolding

We successfully implemented the internal pipeline engine under the new `pipelineio/` and [pipeline/](file:///Users/lucasstarkey/Desktop/CampusTrafic/pipeline/run_logic/executor.py#37-41) directories.

- **[pipelineio/config.py](file:///Users/lucasstarkey/Desktop/CampusTrafic/pipelineio/config.py)**: Reads `PIPELINE_HTTP_TIMEOUT` and `PIPELINE_CACHE_DIR`.
- **[pipelineio/uris.py](file:///Users/lucasstarkey/Desktop/CampusTrafic/pipelineio/uris.py) & [pipelineio/meta.py](file:///Users/lucasstarkey/Desktop/CampusTrafic/pipelineio/meta.py)**: Supports HTTP and Local File sources, correctly calculating `mtime_ns`, `size`, `etag` via `.stat()` or `HEAD` requests.
- **[pipelineio/atomic.py](file:///Users/lucasstarkey/Desktop/CampusTrafic/pipelineio/atomic.py)**: Guaranteed atomic safe writes routing to a hidden temp file before utilizing `os.replace`.
- **[pipelineio/state.py](file:///Users/lucasstarkey/Desktop/CampusTrafic/pipelineio/state.py)**: Streamlined `<step>.pkl` state dumping.
- **`pipeline/run_logic/`**: The planner creates airtight SHA-256 caching by combining python version, step source code, and meta-data diffing of IO boundaries.

## 2. Model Inversion of Control

The application domain models within `py/world/` were stripped of `DeviceMapBuilder` static coordination and implicit parsing behaviors:

- `world.py`: Removed `.construct()`, now an anemic `dataclass` mapping instances.
- `graph.py`: Removed `.build()`. Only stores `Node` and `Edge`.
- `device_trace.py`: Removed `.from_observation_rows()`.

## 3. Pure Functional Topology

All logic was rewritten into strictly typed functional steps inside `pipeline/steps/`.

- `01_init_world`
- `02_build_devices`
- `03_build_graph`
- `04_build_grid`

> [!TIP]
> Each step contains exactly `INPUTS`, `OUTPUTS`, and `run()`. The metadata differences (e.g. `size changed`, `source code changed`) automatically direct the engine to SKIP or RUN.

## 4. API Wiring

The FastAPI application was rewired:
1. Dead Orchestration modules `py/batch/pipeline_runner.py` and `py/io/world_drafts.py` were permanently deleted.
2. `api/service/train_service.py` executes the pipeline async via `subprocess` locally by invoking `run.py`.
3. `api/service/runs_service.py` safely reads from the new `pipelineio.state.load_draft()` schemas.

## Validation Results

The pipeline successfully cascades evaluation through the steps:

```bash
> uv run python run.py

--- Evaluating Step: 01_init_world ---
[01_init_world] RUN (No cache found)
[01_init_world] DONE

--- Evaluating Step: 02_build_devices ---
[02_build_devices] RUN (No cache found)
...
```

The subsequent evaluation flawlessly hits the internal cache planner layer and cascades SKIPs:

```bash
> uv run python run.py

--- Evaluating Step: 01_init_world ---
[01_init_world] SKIP (SKIP)

--- Evaluating Step: 02_build_devices ---
[02_build_devices] SKIP (SKIP)
```
