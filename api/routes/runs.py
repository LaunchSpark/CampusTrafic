from fastapi import APIRouter, HTTPException

from api.schemas.models import FieldIndex, MetricsResponse, RunList, TileResponse, WorldResponse
from api.service import runs_service

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunList)
async def list_runs() -> RunList:
    return RunList(runs=runs_service.list_runs())


@router.get("/{run_id}/world", response_model=WorldResponse)
async def get_world(run_id: str) -> WorldResponse:
    world = runs_service.get_world(run_id)
    if world is None:
        raise HTTPException(status_code=404, detail="World artifact not found")
    return WorldResponse(run_id=run_id, world=world)


@router.get("/{run_id}/fields/index", response_model=FieldIndex)
async def get_field_index(run_id: str) -> FieldIndex:
    index = runs_service.get_field_index(run_id)
    if index is None:
        raise HTTPException(status_code=404, detail="Field index not found")
    return FieldIndex(run_id=run_id, index=index)


@router.get("/{run_id}/fields/tiles/{tile_id}", response_model=TileResponse)
async def get_field_tile(run_id: str, tile_id: str) -> TileResponse:
    tile = runs_service.get_field_tile(run_id, tile_id)
    if tile is None:
        raise HTTPException(status_code=404, detail="Field tile not found")
    return TileResponse(run_id=run_id, tile_id=tile_id, tile=tile)


@router.get("/{run_id}/metrics", response_model=MetricsResponse)
async def get_metrics(run_id: str) -> MetricsResponse:
    metrics = runs_service.get_metrics(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Metrics artifact not found")
    return MetricsResponse(run_id=run_id, metrics=metrics)
