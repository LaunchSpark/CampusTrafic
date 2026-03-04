# Purpose
Hold immutable source-like inputs before feature engineering.

# What goes here
- Imported datasets used to build monthly runs.
- `real/` data snapshots from production-like sources.

# What does NOT go here
- Model outputs, metrics, or generated fields.
- Application code or API payload schemas.

# How it is used
- Python IO/batch logic reads from this folder.
- Data should be append-only by run date or snapshot.
- Downstream transforms write to `data/processed/`.

# Notes
- MVP requires at least one stable raw input feed.
