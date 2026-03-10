# Python Engine (`py/`)

Core computation logic implemented as importable pure Python modules.

## Role

- Power data processing for the pure DAG `pipeline/`.
- Produce immutable anemic data models (`World`, `Graph`, etc.) with no explicit I/O constraints.
- Provide deterministic domain logic for modeling and analysis operations.

## Domains

- `world/`, `routing/`, `flow/`, `field/`, `modeling/`, `eval/`, and `io/`.
(Note: Orchestration is now handled entirely outside this package via the `pipeline` engine and `run.py`)

