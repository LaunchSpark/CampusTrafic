from fastapi import APIRouter

from api.schemas.models import (
    LiveMetricsResponse,
    TrainingLogsResponse,
    TrainingStartResponse,
    TrainingStatusResponse,
)
from api.service import train_service

router = APIRouter(prefix="/train", tags=["train"])


@router.post("/start", response_model=TrainingStartResponse)
async def start_training() -> TrainingStartResponse:
    return train_service.start_training()


@router.get("/status", response_model=TrainingStatusResponse)
async def get_training_status() -> TrainingStatusResponse:
    return train_service.get_training_status()


@router.get("/logs", response_model=TrainingLogsResponse)
async def get_training_logs() -> TrainingLogsResponse:
    return train_service.get_training_logs()


@router.get("/metrics/live", response_model=LiveMetricsResponse)
async def get_live_metrics() -> LiveMetricsResponse:
    return train_service.get_live_metrics()
