# Purpose
Store run-scoped field descriptors and payload tiles.

# What goes here
- `index.json` describing available fields/time windows.
- `tiles/` containing time-windowed field payloads (JSON or binary).
- Optional metadata needed to decode tiles.

# What does NOT go here
- Model tree artifacts or world draft edits.
- Raw training datasets.

# How it is used
- Python field pipeline writes `index.json` + tile assets.
- API serves `/runs/{run_id}/fields/index` and `/runs/{run_id}/fields/tiles/...`.
- Web UI loads index first, then requests tiles on demand.

# Notes
- MVP requires deterministic tile naming and index references.
