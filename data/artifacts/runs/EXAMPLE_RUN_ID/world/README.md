# Purpose
Store the published world artifact snapshot for a run.

# What goes here
- World graph/metadata files associated with `run_id`.
- Immutable published representation consumed by clients.

# What does NOT go here
- Draft edits prior to publish.
- Metrics or field tile payloads.

# How it is used
- Produced by Python pipeline or draft publish workflow.
- Served via `/runs/{run_id}/world` endpoint.
- Consumed by Web UI for topology/device context.

# Notes
- MVP requires read-only world artifact retrieval.
