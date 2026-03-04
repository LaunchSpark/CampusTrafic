# CampusTrafic

CampusTrafic uses a **clean monthly-retrain digital-twin architecture**:

- Python engine precomputes playback-ready artifacts.
- FastAPI stays thin (serving/orchestration/admin/training control).
- Web UI reads static artifacts for fast exploration.

## Architecture at a glance

1. Ingest raw Wi-Fi node hits into `data/raw/real/`.
2. Build cleaned trajectories and edge-flow labels in `data/processed/`.
3. Run monthly training and export immutable artifacts under `data/artifacts/runs/{run_id}/`.
4. Serve artifacts and operational endpoints from `api/`.
5. Render playback/admin/training experiences from `web/`.

## Core guarantees

- **Reproducible**: each `run_id` is immutable.
- **Fast UI**: frontend reads precomputed field tiles and metadata.
- **Separation of concerns**: heavy computation remains in Python modules under `py/`.
