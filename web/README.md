# Purpose
Host the Web UI that consumes artifacts and calls FastAPI endpoints.

# What goes here
- UI pages, reusable components, visualization modules, and admin/training views.
- Client-side code for browsing runs and interacting with draft/train APIs.

# What does NOT go here
- Backend API handlers or Python modeling logic.
- Persisted artifact files from completed runs.

# How it is used
- Calls API artifact routes (`/runs`, `/runs/{run_id}/world`, fields, metrics).
- Calls admin draft routes and training control/status routes.
- Renders outputs produced by Python engine and served by API.

# Notes
- MVP can be minimal UI as long as run selection + key views are supported.
