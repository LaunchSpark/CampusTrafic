# Purpose
Contain cleaned, validated, model-ready datasets.

# What goes here
- Feature tables and normalized intermediates.
- Validation-ready datasets used by modeling/eval steps.

# What does NOT go here
- Raw uncleaned source dumps.
- Final run artifacts (`world`, `fields`, `metrics`, model trees).

# How it is used
- Python engine writes deterministic transforms here.
- Modeling and evaluation modules read from here.
- Artifacts for serving are emitted to `data/artifacts/runs/<run_id>/`.

# Notes
- MVP requires deterministic transforms from `data/raw/`.
