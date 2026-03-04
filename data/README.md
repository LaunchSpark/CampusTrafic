# Purpose
Store all persisted datasets and generated artifacts for monthly retrain runs.

# What goes here
- Raw inputs under `raw/`.
- Cleaned/feature-ready data under `processed/`.
- Run outputs and world drafts under `artifacts/`.
- File-based assets shared by Python engine, API, and Web UI.

# What does NOT go here
- Python source code, API code, or UI code.
- Temporary local experiments outside defined subfolders.

# How it is used
- Python engine reads `raw/` + `processed/` and writes `artifacts/`.
- FastAPI serves artifacts and world draft content from this tree.
- Web UI consumes API responses derived from this tree.

# Notes
- Required for MVP as the canonical filesystem data store.
