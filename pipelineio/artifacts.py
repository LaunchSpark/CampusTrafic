import json
from pathlib import Path
from typing import Any

from pipelineio.paths import RUNS_DIR


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_runs() -> list[str]:
    if not RUNS_DIR.exists():
        return []
    return sorted([p.name for p in RUNS_DIR.iterdir() if p.is_dir()])


def load_world(run_id: str) -> dict[str, Any] | None:
    run_dir = RUNS_DIR / run_id
    candidates = [
        run_dir / "world" / "world.json",
        run_dir / "world" / "index.json",
        run_dir / "world" / f"{run_id}.json",
    ]
    for candidate in candidates:
        data = _load_json(candidate)
        if data is not None:
            return data
    return None


def load_field_index(run_id: str) -> dict[str, Any] | None:
    run_dir = RUNS_DIR / run_id
    candidates = [
        run_dir / "fields" / "index.json",
        run_dir / "index.json",
    ]
    for candidate in candidates:
        data = _load_json(candidate)
        if data is not None:
            return data
    return None


def load_field_tile(run_id: str, tile_id: str) -> dict[str, Any] | None:
    run_dir = RUNS_DIR / run_id
    candidates = [
        run_dir / "fields" / "tiles" / f"{tile_id}.json",
        run_dir / "tiles" / f"{tile_id}.json",
    ]
    for candidate in candidates:
        data = _load_json(candidate)
        if data is not None:
            return data
    return None


def load_metrics(run_id: str) -> dict[str, Any] | None:
    run_dir = RUNS_DIR / run_id
    candidates = [
        run_dir / "metrics" / "metrics.json",
        run_dir / "metrics" / "index.json",
    ]
    for candidate in candidates:
        data = _load_json(candidate)
        if data is not None:
            return data
    return None
