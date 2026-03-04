# Purpose
Document expected layout for a single run artifact package.

# What goes here
- `model_tree/` model structure artifacts.
- `metrics/` evaluation and monitoring outputs.
- `fields/` field index + tile payloads.
- `world/` published world artifact for the run.

# What does NOT go here
- Mutable draft worlds (use `data/artifacts/world_drafts/`).
- Raw or processed training inputs.

# How it is used
- Use `EXAMPLE_RUN_ID` as documentation only.
- Real run IDs should follow monthly style like `YYYY-MM-01`.
- API serves this shape via `/runs/{run_id}/...` endpoints.

# Notes
- MVP requires stable naming and immutable run contents.
