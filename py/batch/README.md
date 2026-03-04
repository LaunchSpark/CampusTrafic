# Batch Jobs (`py/batch/`)

Periodic retraining pipeline orchestration (typically monthly).

## Standard pipeline

1. Ingest last 12 months of data.
2. Clean and build movement traces.
3. Compute edge-flow labels.
4. Train hierarchical models.
5. Evaluate model performance.
6. Export artifacts to `data/artifacts/runs/{run_id}`.
7. Precompute field tiles for playback.

Output: a fully self-contained artifact set per run.
