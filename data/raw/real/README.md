# Real Ingestion Events (`data/raw/real/`)

Immutable node-hit events exactly as received from Wi-Fi logs.

## Typical fields

- `device_id`
- `timestamp`
- `wap_id`

## Rules

- No transformations occur here.
- Use this as the source-of-truth ingestion layer for monthly retraining.
