import os
from api.schemas.models import RunInfo
from pipelineio.state import load_draft


def list_runs() -> list[RunInfo]:
    runs_dir = "data/artifacts/runs"
    if not os.path.exists(runs_dir):
        return []
    return [RunInfo(run_id=d) for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]


def get_world(run_id: str) -> dict | None:
    try:
        world = load_draft(f"data/artifacts/runs/{run_id}/world/final_world.pkl")
        return {
            "graph_nodes": len(world.graph.nodes) if world.graph else 0,
            "devices": len(world.devices)
        }
    except Exception:
        return None


def get_field_index(run_id: str) -> dict | None:
    return None


def get_field_tile(run_id: str, tile_id: str) -> dict | None:
    return None


def get_metrics(run_id: str) -> dict | None:
    return None

