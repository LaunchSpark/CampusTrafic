# Purpose
Store model-tree artifacts for one run.

# What goes here
- Serialized tree/topology outputs used for inference or inspection.
- Metadata needed to interpret model tree nodes.

# What does NOT go here
- Field tiles, world artifacts, or draft world edits.
- Raw training snapshots.

# How it is used
- Produced by Python modeling pipeline.
- Served by API under run-scoped artifact routes.
- Consumed by Web UI visualizations when needed.

# Notes
- MVP can keep format simple as long as schema is stable.
