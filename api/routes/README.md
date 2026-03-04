# Purpose
Contain HTTP route handlers grouped by domain.

# What goes here
- Endpoint modules for run artifacts, world drafts, and training control.
- Thin request parsing and response shaping logic.

# What does NOT go here
- Data science/model logic from `py/`.
- Persistent artifact files.

# How it is used
- Implement high-level routes: `/runs`, `/runs/{run_id}/world`, `/runs/{run_id}/fields/index`, `/runs/{run_id}/fields/tiles/...`, `/runs/{run_id}/metrics/...`.
- Implement draft routes: `/world/drafts`, `/world/drafts/{id}`, `/world/drafts/{id}/publish`.
- Implement train routes: `/train/start`, `/train/status`, `/train/logs`, `/train/metrics/live`.

# Notes
- MVP route handlers should stay thin and delegate immediately.
