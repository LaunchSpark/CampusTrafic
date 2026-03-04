# Purpose
Provide a thin FastAPI service over filesystem artifacts and admin/train controls.

# What goes here
- Service wiring, route handlers, schemas, and optional static serving config.
- Endpoint contracts for run browsing, world drafts, and training control.

# What does NOT go here
- Core modeling/field logic (belongs in `py/`).
- Long-running training implementations.

# How it is used
- Serves artifact endpoints: `/runs`, `/runs/{run_id}/world`, `/runs/{run_id}/fields/index`, `/runs/{run_id}/fields/tiles/...`, `/runs/{run_id}/metrics/...`.
- Serves admin endpoints: `/world/drafts`, `/world/drafts/{id}`, `/world/drafts/{id}/publish`.
- Serves training endpoints: `/train/start`, `/train/status`, `/train/logs`, `/train/metrics/live`.

# Notes
- MVP keeps API thin: validate/authorize/request-map, then delegate to engine/storage.
