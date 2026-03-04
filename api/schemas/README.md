# API Schemas (`api/schemas/`)

Data contracts for FastAPI endpoints.

## Scope

- Request/response models for run listing, world export, field indices/tiles, metrics, drafts, and training APIs.
- Shared enums/types (time windows, run state, tile resolution, etc.).

## Design goals

- Keep API contracts explicit and stable for the frontend.
- Encode invariants close to boundaries.
- Reflect artifact metadata structure (`fields/index.json`, run metadata, world versioning).
