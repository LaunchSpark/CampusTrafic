from __future__ import annotations

"""Internal NumPy-backed columnar utilities for world trace processing.

Invariants:
- Missing timestamps are represented as 0 in numeric arrays plus explicit boolean
  masks (`start_valid`, `end_valid`). This avoids NaN float coercion and keeps all
  timestamp math in `int64`.
- Connection arrays preserve the caller-provided order. Any ordering assumptions
  (for example sorted-by-start before transition generation) must be enforced by
  the caller.
- Node identifiers are carried as object-dtype arrays of canonical string values,
  so no lossy integer encoding/decoding step is required.
"""

from dataclasses import dataclass

import numpy as np

from .connection import Connection


@dataclass(frozen=True)
class ConnectionColumns:
    node_id: np.ndarray
    start_ts_ms: np.ndarray
    end_ts_ms: np.ndarray
    start_valid: np.ndarray
    end_valid: np.ndarray


@dataclass(frozen=True)
class TransitionColumns:
    from_node: np.ndarray
    to_node: np.ndarray
    t_from_ms: np.ndarray
    t_to_ms: np.ndarray
    dt_ms: np.ndarray


def connections_to_columns(connections: list[Connection]) -> ConnectionColumns:
    size = len(connections)
    node_id = np.empty(size, dtype=object)
    start_ts_ms = np.zeros(size, dtype=np.int64)
    end_ts_ms = np.zeros(size, dtype=np.int64)
    start_valid = np.zeros(size, dtype=bool)
    end_valid = np.zeros(size, dtype=bool)

    for idx, conn in enumerate(connections):
        node_id[idx] = str(conn.node_id)
        if conn.start_ts_ms is not None:
            start_ts_ms[idx] = int(conn.start_ts_ms)
            start_valid[idx] = True
        if conn.end_ts_ms is not None:
            end_ts_ms[idx] = int(conn.end_ts_ms)
            end_valid[idx] = True

    return ConnectionColumns(
        node_id=node_id,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        start_valid=start_valid,
        end_valid=end_valid,
    )


def transition_columns(columns: ConnectionColumns) -> TransitionColumns:
    if len(columns.node_id) < 2:
        empty_obj = np.empty(0, dtype=object)
        empty_i64 = np.empty(0, dtype=np.int64)
        return TransitionColumns(empty_obj, empty_obj, empty_i64, empty_i64, empty_i64)

    from_node = columns.node_id[:-1]
    to_node = columns.node_id[1:]

    t_from_ms = np.where(columns.end_valid[:-1], columns.end_ts_ms[:-1], columns.start_ts_ms[:-1])
    t_from_valid = columns.end_valid[:-1] | columns.start_valid[:-1]

    t_to_ms = columns.start_ts_ms[1:]
    t_to_valid = columns.start_valid[1:]

    dt_ms = t_to_ms - t_from_ms
    valid = t_from_valid & t_to_valid & (dt_ms >= 0)

    return TransitionColumns(
        from_node=from_node[valid],
        to_node=to_node[valid],
        t_from_ms=t_from_ms[valid],
        t_to_ms=t_to_ms[valid],
        dt_ms=dt_ms[valid],
    )


def transition_rows(
    *,
    device_id: str,
    transitions: TransitionColumns,
    from_key: str,
    to_key: str,
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for idx in range(len(transitions.dt_ms)):
        rows.append(
            {
                "device_id": device_id,
                from_key: str(transitions.from_node[idx]),
                to_key: str(transitions.to_node[idx]),
                "t_from_ms": int(transitions.t_from_ms[idx]),
                "t_to_ms": int(transitions.t_to_ms[idx]),
                "dt_ms": int(transitions.dt_ms[idx]),
            }
        )
    return rows
