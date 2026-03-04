# API Routes (`api/routes/`)

HTTP handlers grouped by domain.

## What belongs here

- Request parsing and response shaping.
- Route modules for artifacts, admin drafts, and training control.
- Mapping HTTP semantics to service-layer calls.

## Keep route handlers thin

- Validate request.
- Call service.
- Return typed schema response.

## Route surface

- `/runs*` for immutable artifact browsing.
- `/world/drafts*` for editable world drafts.
- `/train/*` for lifecycle, logs, and live metrics.
