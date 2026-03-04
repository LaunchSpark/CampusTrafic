# Purpose
Store run-level evaluation and quality metrics.

# What goes here
- Aggregate metrics files and diagnostics.
- Time-sliced or scenario-specific metric outputs.

# What does NOT go here
- Model weights/tree blobs or field tile payloads.
- Mutable admin drafts.

# How it is used
- Written by Python eval pipeline.
- Served via `/runs/{run_id}/metrics/...` endpoints.
- Displayed in Web training/admin monitoring views.

# Notes
- MVP requires enough metrics to compare monthly runs.
