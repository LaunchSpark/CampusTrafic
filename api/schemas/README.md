# Purpose
Define API request/response schemas and validation contracts.

# What goes here
- Pydantic (or equivalent) schemas for runs, fields, metrics, drafts, and training endpoints.
- Shared enums/types used by route handlers.

# What does NOT go here
- Route implementation logic.
- Storage-side artifact payload files.

# How it is used
- Shapes responses for `/runs*`, `/world/drafts*`, and `/train/*` endpoints.
- Guards payload invariants before calling Python engine/storage.
- Keeps API contracts stable for Web UI consumers.

# Notes
- MVP requires minimal but explicit schema coverage for key endpoints.
