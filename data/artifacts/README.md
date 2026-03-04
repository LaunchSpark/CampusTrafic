# Artifacts (`data/artifacts/`)

Versioned outputs from training runs and editable world drafts.

## Structure

- `runs/` — immutable per-run exports.
- `world_drafts/` — mutable admin draft graphs.

## Invariants

- Published run artifacts are immutable.
- Historical behavior must remain reproducible.
