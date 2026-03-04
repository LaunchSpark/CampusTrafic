# API Service Layer (`api/service/`)

Composition and orchestration glue between routes and Python/data subsystems.

## Responsibilities

- FastAPI app bootstrapping, dependency wiring, lifecycle hooks.
- Service functions for artifact lookup/streaming and draft publishing.
- Training job orchestration hooks (start/status/logs/live metrics).

## Constraints

- Keep heavy compute in `py/` or batch jobs.
- Keep this layer deterministic and filesystem-aware.
