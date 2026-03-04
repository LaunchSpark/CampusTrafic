from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from py.io.paths import RUNS_DIR, WORLD_DRAFTS_DIR


def _draft_path(draft_id: str) -> Path:
    return WORLD_DRAFTS_DIR / f"{draft_id}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def list_drafts() -> list[dict]:
    WORLD_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    drafts: list[dict] = []
    for draft_file in sorted(WORLD_DRAFTS_DIR.glob("*.json")):
        draft = _load_json(draft_file)
        if draft is not None:
            drafts.append(draft)
    return drafts


def create_draft() -> dict:
    draft_id = uuid4().hex
    now = _now_iso()
    draft = {
        "id": draft_id,
        "payload": {},
        "created_at": now,
        "updated_at": now,
    }
    _write_json(_draft_path(draft_id), draft)
    return draft


def update_draft(draft_id: str, payload: dict) -> dict | None:
    path = _draft_path(draft_id)
    draft = _load_json(path)
    if draft is None:
        return None

    draft["payload"] = payload
    draft["updated_at"] = _now_iso()
    _write_json(path, draft)
    return draft


def publish_draft(draft_id: str) -> dict | None:
    path = _draft_path(draft_id)
    draft = _load_json(path)
    if draft is None:
        return None

    run_id = datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S-") + uuid4().hex[:6]
    run_world_dir = RUNS_DIR / run_id / "world"
    run_world_dir.mkdir(parents=True, exist_ok=True)

    _write_json(run_world_dir / "world.json", draft["payload"])
    _write_json(RUNS_DIR / run_id / "index.json", {"run_id": run_id, "source_draft_id": draft_id})

    archive_path = WORLD_DRAFTS_DIR / "published" / f"{draft_id}.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, archive_path)

    return {"draft_id": draft_id, "run_id": run_id, "published": True}
