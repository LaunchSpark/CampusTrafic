# World package (`py/world`)

This package contains world-domain anemic data structures used to hold canonical in-memory state. These structures do not contain any I/O orchestration or implicit parsing.

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

### `World` (`world.py`)

Current `World` fields:

| Field | Type | Notes |
|---|---|---|
| `graph` | `Graph \| None` | |
| `grid` | `Grid \| None` | |
| `devices` | `list[DeviceTrace]` | |

## Device mapping + trace assembly

### `DeviceTrace` (`device_trace.py`)

A pure dataclass tying a `DeviceId` to a list of its `Connection` objects.

### `DeviceMap` / `DeviceMapBuilder` (`device_map.py`)

Legacy structure for assembling raw maps.

## Public exports (`py/world/__init__.py`)

- Structures: `World`, `Grid`, `Graph`, `Node`, `Edge`, `Connection`
- Pipeline: `DeviceMap`, `DeviceMapBuilder`, `DevicePipeline`
- Type aliases: `DeviceId`, `NodeId`, `EdgeId`

