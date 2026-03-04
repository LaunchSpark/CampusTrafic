# Purpose
Define FastAPI app bootstrapping and shared service composition.

# What goes here
- App factory, dependency wiring, config loading, and lifecycle hooks.
- Shared adapters that map HTTP calls to Python engine/storage operations.

# What does NOT go here
- Heavy business logic or model computation.
- UI assets except optional static mount declarations.

# How it is used
- Initializes handlers for `/runs`, `/world/drafts`, and `/train/*` endpoint groups.
- Connects route layer to filesystem-backed artifact access.
- Enforces cross-cutting concerns (auth, logging, error mapping).

# Notes
- MVP can keep bootstrapping simple but must keep engine coupling minimal.
