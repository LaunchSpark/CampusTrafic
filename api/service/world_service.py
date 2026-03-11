from api.schemas.models import PublishDraftResponse, WorldDraft

def list_world_drafts() -> list[WorldDraft]:
    # TODO: Refactor drafting after DAG migration
    return []

def create_world_draft() -> WorldDraft:
    raise NotImplementedError("Drafting is temporarily disabled")

def update_world_draft(id: str, payload: dict) -> WorldDraft | None:
    raise NotImplementedError("Drafting is temporarily disabled")

def publish_world_draft(id: str) -> PublishDraftResponse | None:
    raise NotImplementedError("Drafting is temporarily disabled")
