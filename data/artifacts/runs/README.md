# Run Artifacts (`data/artifacts/runs/`)

Each folder is a monthly retrain snapshot: `runs/{run_id}/`.

Example run id:

- `2026-03-01`

## Expected run contents

- `model_tree/` — trained hierarchical model outputs
- `metrics/` — evaluation summaries and drift artifacts
- `fields/` — playback-ready vectors/densities and tiles
- `world/` — exported graph + grid/coordinate specification

Each run should be fully self-contained for playback and comparison.
