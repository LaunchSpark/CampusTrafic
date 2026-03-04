# Purpose
Namespace all immutable artifacts by run identifier.

# What goes here
- One folder per run, e.g., `YYYY-MM-01` for monthly retrain.
- Each run includes `model_tree/`, `metrics/`, `fields/`, and `world/`.

# What does NOT go here
- Draft-only editable world content.
- Cross-run temporary outputs or local notebooks.

# How it is used
- Python engine writes a complete run package atomically.
- FastAPI reads this structure for `/runs` and child endpoints.
- Web UI selects a run and visualizes its artifacts.

# Notes
- MVP supports read-only serving of completed runs.
