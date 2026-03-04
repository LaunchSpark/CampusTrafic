# Data Store (`data/`)

Filesystem-backed storage for ingestion, intermediate datasets, and immutable run artifacts.

## Layout

- `raw/` — immutable ingestion layer.
- `processed/` — cleaned and structured traces + labels.
- `artifacts/` — published run outputs and editable world drafts.

## Contract

This tree is the canonical shared store used by batch training, FastAPI serving, and UI playback.
