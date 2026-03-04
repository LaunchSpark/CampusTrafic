from fastapi import APIRouter, HTTPException

from api.schemas.models import (
    PublishDraftResponse,
    WorldDraft,
    WorldDraftCreateResponse,
    WorldDraftList,
    WorldDraftUpdatePayload,
)
from api.service import world_service

router = APIRouter(prefix="/world", tags=["world"])


@router.get("/drafts", response_model=WorldDraftList)
async def list_world_drafts() -> WorldDraftList:
    return WorldDraftList(drafts=world_service.list_world_drafts())


@router.post("/drafts", response_model=WorldDraftCreateResponse)
async def create_world_draft() -> WorldDraftCreateResponse:
    return WorldDraftCreateResponse(draft=world_service.create_world_draft())


@router.put("/drafts/{id}", response_model=WorldDraft)
async def update_world_draft(id: str, payload: WorldDraftUpdatePayload) -> WorldDraft:
    draft = world_service.update_world_draft(id, payload.payload)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/drafts/{id}/publish", response_model=PublishDraftResponse)
async def publish_world_draft(id: str) -> PublishDraftResponse:
    published = world_service.publish_world_draft(id)
    if published is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return published
