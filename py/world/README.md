# World package (`py/world`)

This package contains world-domain data structures and orchestration entrypoints used to build canonical in-memory state from raw device observations.

## Core aliases (`types.py`)

- `DeviceId`
- `NodeId`
- `EdgeId`
- `TimestampMs`

## Core structures

### `Connection` (`connection.py`)

Represents a device association with one WAP/node over a time interval.

| Field | Type |
|---|---|
| `node_id` | `NodeId` |
| `start_ts_ms` | `int \| None` |
| `end_ts_ms` | `int \| None` |
| `meta` | `dict[str, Any] \| None` |

### `Graph` (`graph.py`)

| Field | Type |
|---|---|
| `nodes` | `dict[NodeId, Node]` |
| `edges` | `dict[EdgeId, Edge]` |

`Graph.build(device_map_builder=...)` optionally triggers device-map building during world construction.

### `World` (`world.py`)

Current `World` fields:

| Field | Type | Notes |
|---|---|---|
| `graph` | `Graph \| None` | Auto-built in `__post_init__` if omitted |
| `graphs` | `dict[str, dict[str, dict[str, list[dict[str, int \| str]]]]]` | `wap -> date -> time -> connections_from_here[]` |
| `device_connections` | `dict[DeviceId, list[Connection]]` | Canonical parented per-device traces |
| `grid` | `None` | Not implemented yet |

Important methods:

- `World.construct(paths=None, threshold_ms=300_000) -> World`
- `World.with_connections(device_connections) -> World`

`graphs[wap][date][time]` list item schema:

- `device_id`
- `to_wap`
- `t_from_ms`
- `t_to_ms`
- `dt_ms`

## Device mapping + trace assembly

### `DeviceTrace` (`device_trace.py`)

Encapsulates per-device trace assembly from normalized rows and emits transition rows from consecutive connections.

### `DeviceMap` / `DeviceMapBuilder` (`device_map.py`)

`DeviceMapBuilder` provides:

1. `normalize_raw_logs()`
2. `build_traces_and_transitions(observations_csv)`
3. `build_parent_map(traces)`
4. `apply_parent_map(traces, parent_map)`
5. `build()`

`PipelinePaths` defaults:

- `data/raw/real`
- `data/processed/observations/observations_normalized.csv`
- `data/processed/transitions/transitions.csv`
- `data/processed/deviceParentMap.csv`
- `data/processed/observations_parented/observations_parented.csv`

## Compatibility façade

### `DevicePipeline` (`device_pipeline.py`)

Compatibility wrapper for legacy call sites. It delegates pipeline operations to `py.io.pipeline_io` and world construction.

## IO adapters used by world/batch facades

### `py/io/pipeline_io.py`

Pipeline-level adapter functions:

- `normalize_raw_logs`
- `build_traces_and_transitions`
- `build_parent_map`
- `apply_parent_map`
- `run_pipeline`

These are used by:

- `py/world/device_pipeline.py` (compatibility façade)
- `py/batch/pipeline_runner.py` (via `World.construct`)

## Public exports (`py/world/__init__.py`)

- Structures: `World`, `Grid`, `Graph`, `Node`, `Edge`, `Connection`
- Pipeline: `DeviceMap`, `DeviceMapBuilder`, `DevicePipeline`, `PipelinePaths`
- Type aliases: `DeviceId`, `NodeId`, `EdgeId`
