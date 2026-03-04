# Purpose
Store real-world raw inputs used for training/evaluation runs.

# What goes here
- Source snapshots (CSV/JSON/Parquet/etc.) from real feeds.
- Metadata files describing snapshot timestamp/source.

# What does NOT go here
- Synthetic generated datasets.
- Processed feature tables or run artifacts.

# How it is used
- Python engine ingests these files as authoritative observations.
- Inputs should be traceable to snapshot dates.
- Outputs derived from here move to `data/processed/`.

# Notes
- MVP: real data can be small but should be reproducible.
