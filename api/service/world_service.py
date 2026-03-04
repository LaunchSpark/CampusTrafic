from api.schemas.models import PublishDraftResponse, WorldDraft
from py.io import world_drafts


def list_world_drafts() -> list[WorldDraft]:
    return [WorldDraft(**draft) for draft in world_drafts.list_drafts()]


def create_world_draft() -> WorldDraft:
    return WorldDraft(**world_drafts.create_draft())


def update_world_draft(id: str, payload: dict) -> WorldDraft | None:
    draft = world_drafts.update_draft(id, payload)
    if draft is None:
        return None
    return WorldDraft(**draft)


def publish_world_draft(id: str) -> PublishDraftResponse | None:
    published = world_drafts.publish_draft(id)
    if published is None:
        return None
    return PublishDraftResponse(**published)
