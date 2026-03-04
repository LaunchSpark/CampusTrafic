from datetime import datetime, timezone
from uuid import uuid4

from api.schemas.models import (
    LiveMetricsResponse,
    TrainingLogsResponse,
    TrainingStartResponse,
    TrainingStatusResponse,
)

_training_state: dict[str, str | list[str] | dict] = {
    "status": "idle",
    "active_run_id": None,
    "logs": [],
    "metrics": {},
}


def start_training() -> TrainingStartResponse:
    run_id = datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S-") + uuid4().hex[:6]
    _training_state["status"] = "running"
    _training_state["active_run_id"] = run_id
    _training_state["logs"] = [f"training started for {run_id}"]
    _training_state["metrics"] = {"progress": 0.0}
    return TrainingStartResponse(started=True, run_id=run_id, message="Training job queued")


def get_training_status() -> TrainingStatusResponse:
    return TrainingStatusResponse(
        status=str(_training_state["status"]),
        active_run_id=_training_state["active_run_id"],
    )


def get_training_logs() -> TrainingLogsResponse:
    return TrainingLogsResponse(logs=list(_training_state["logs"]))


def get_live_metrics() -> LiveMetricsResponse:
    return LiveMetricsResponse(metrics=dict(_training_state["metrics"]))
