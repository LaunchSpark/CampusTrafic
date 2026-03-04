# Purpose
Define the io domain logic for the Python engine.

# What goes here
- Pure Python business logic, transformations, and domain utilities for io.
- Functions/classes consumed by batch pipelines and artifact builders.

# What does NOT go here
- HTTP handlers, FastAPI request objects, or web concerns.
- Persistent raw artifacts that belong under data directories.

# How it is used
- Called from engine workflows to build run outputs.
- Reads from data inputs via IO abstractions and writes via artifact writers.
- Keeps deterministic behavior for monthly retrain runs.

# Notes
- MVP: required module boundary; implementation depth can grow incrementally.
