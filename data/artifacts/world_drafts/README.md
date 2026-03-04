# Purpose
Store editable world drafts before publishing to a run artifact.

# What goes here
- Draft world documents created/updated by admin workflows.
- Draft metadata (author, timestamps, validation state).

# What does NOT go here
- Immutable published run world artifacts.
- Training metrics or field tile outputs.

# How it is used
- Admin panel edits drafts via `/world/drafts` endpoints.
- API supports `/world/drafts`, `/world/drafts/{id}`, and publish flow.
- Publishing later creates a world artifact under a run.

# Notes
- MVP supports draft CRUD; publish may be a controlled operation.
