# Purpose
Host the Python-first digital-twin engine (pure logic layer).

# What goes here
- Domain modules for world, routing, flow, field generation, modeling, eval, IO, and batch orchestration.
- Code that reads inputs and writes run artifacts.

# What does NOT go here
- HTTP routing/controllers or web UI components.
- Direct framework-coupled API request/response logic.

# How it is used
- Invoked by batch jobs for monthly retraining.
- Produces artifacts under `data/artifacts/runs/<run_id>/`.
- Exposed externally only through FastAPI thin-service adapters.

# Notes
- MVP prioritizes deterministic pipelines and stable artifact schemas.
