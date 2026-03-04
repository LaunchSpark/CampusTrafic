# Purpose
Optional static hosting area served by FastAPI.

# What goes here
- Optional built UI bundles or static artifact previews.
- Static files intentionally published by service configuration.

# What does NOT go here
- Source web app code (belongs in `web/`).
- Core run artifact storage (belongs in `data/artifacts/`).

# How it is used
- May be mounted for static delivery while API still exposes `/runs*`, `/world/drafts*`, and `/train/*` endpoints.
- Can provide admin/training convenience pages in MVP if needed.
- Remains optional if deployment serves web assets elsewhere.

# Notes
- MVP: optional directory; keep empty unless static serving is required.
