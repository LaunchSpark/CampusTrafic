# CampusTrafic

CampusTrafic uses a **clean monthly-retrain digital-twin architecture** driven by a pure functional DAG pipeline:

- A functional DAG pipeline (`pipeline/` & `pipelineio/`) orchestrates data processing with SHA-256 caching.
- Python engine precomputes playback-ready artifacts using pure anemic data structures.
- FastAPI stays thin (serving/orchestration/admin/training control).
- Web UI reads static artifacts for fast exploration.

## Architecture at a glance

1. Ingest raw Wi-Fi node hits into `data/raw/real/`.
2. Build cleaned trajectories and edge-flow labels in `data/processed/`.
3. Run monthly training via `run.py` to export immutable artifacts to `data/artifacts/runs/{run_id}/`.
4. Serve artifacts and operational endpoints from `api/`.
5. Render playback/admin/training experiences from `website/web/`.

## Core guarantees

- **Reproducible**: each `run_id` is immutable and step logic determines cache validity.
- **Fast UI**: frontend reads precomputed data.
- **Separation of concerns**: Heavy computation remains in Python modules, completely isolated from state management.
