from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunInfo(BaseModel):
    run_id: str


class RunList(BaseModel):
    runs: list[RunInfo]


class WorldResponse(BaseModel):
    run_id: str
    world: dict[str, Any]


class FieldIndex(BaseModel):
    run_id: str
    index: dict[str, Any]


class TileResponse(BaseModel):
    run_id: str
    tile_id: str
    tile: dict[str, Any]


class MetricsResponse(BaseModel):
    run_id: str
    metrics: dict[str, Any]


class WorldDraft(BaseModel):
    id: str
    payload: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorldDraftList(BaseModel):
    drafts: list[WorldDraft]


class WorldDraftCreateResponse(BaseModel):
    draft: WorldDraft


class WorldDraftUpdatePayload(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class PublishDraftResponse(BaseModel):
    draft_id: str
    run_id: str
    published: bool


class TrainingStartResponse(BaseModel):
    started: bool
    run_id: str | None = None
    message: str


class TrainingStatusResponse(BaseModel):
    status: str
    active_run_id: str | None = None


class TrainingLogsResponse(BaseModel):
    logs: list[str]


class LiveMetricsResponse(BaseModel):
    metrics: dict[str, Any]
