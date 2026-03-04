# API (`api/`)

FastAPI is the thin orchestration/serving layer.

## Responsibilities

- Serve versioned run artifacts.
- Support admin map-builder draft workflows.
- Trigger and monitor training jobs.
- Expose training and evaluation metrics.

## Primary endpoint groups

- Artifact browsing: `/runs`, `/runs/{run_id}/world`, `/runs/{run_id}/fields/index`, `/runs/{run_id}/fields/tiles/...`, `/runs/{run_id}/metrics/...`
- Admin map builder: `/world/drafts`, `/world/drafts/{id}`, `/world/drafts/{id}/publish`
- Training control: `/train/start`, `/train/status`, `/train/logs`, `/train/metrics/live`

## Non-goals

- No core modeling/field computation here (that belongs in `py/`).
- No mutable storage of published run artifacts.
