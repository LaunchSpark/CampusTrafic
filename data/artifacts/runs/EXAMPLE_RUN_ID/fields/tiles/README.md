# Purpose
Hold field tile payloads referenced by `fields/index.json`.

# What goes here
- Time-windowed tile files (JSON or binary) for maps/heat fields.
- Naming that can be resolved from index entries.

# What does NOT go here
- Global index files (keep in parent `fields/`).
- Unreferenced debug dumps.

# How it is used
- Python engine writes tiles during field generation.
- API streams tiles from `/runs/{run_id}/fields/tiles/...`.
- Web UI requests only tiles needed for current viewport/time.

# Notes
- MVP may start with coarse tile granularity.
