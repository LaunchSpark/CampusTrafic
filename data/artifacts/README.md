# Purpose
Store publishable artifacts produced by the Python engine.

# What goes here
- Per-run outputs in `runs/`.
- Editable draft world definitions in `world_drafts/`.

# What does NOT go here
- Raw/processed training inputs.
- API/web source code or temporary scratch files.

# How it is used
- Python engine writes run artifacts consumed by API endpoints.
- FastAPI serves artifacts to the Web UI.
- Admin actions may create/update world drafts.

# Notes
- MVP requires stable artifact layout for API consumers.
