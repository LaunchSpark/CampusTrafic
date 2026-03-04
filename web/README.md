# Web UI (`web/`)

Frontend focused on browsing precomputed artifacts.

## Primary product: Playback UI

- Select `run_id`
- Time scrubber (hour/day/week)
- Vector-flow overlays
- Density heatmap
- Filters for term/daytype/day_of_week/date

## Optional surfaces

- Admin panel for world graph drafting/publishing
- Training dashboard for live status/metrics/run comparison

The UI should avoid expensive recomputation and rely on artifact endpoints.
