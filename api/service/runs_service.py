from api.schemas.models import RunInfo
from py.io import artifacts


def list_runs() -> list[RunInfo]:
    return [RunInfo(run_id=run_id) for run_id in artifacts.list_runs()]


def get_world(run_id: str) -> dict | None:
    return artifacts.load_world(run_id)


def get_field_index(run_id: str) -> dict | None:
    return artifacts.load_field_index(run_id)


def get_field_tile(run_id: str, tile_id: str) -> dict | None:
    return artifacts.load_field_tile(run_id, tile_id)


def get_metrics(run_id: str) -> dict | None:
    return artifacts.load_metrics(run_id)
