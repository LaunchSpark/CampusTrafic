import os

from pipelineio.state import load_draft, save_draft
from py.world.grid import Grid

INPUTS = ["data/artifacts/world_drafts/03_with_graph.pkl"]

run_id = os.environ.get("PIPELINE_RUN_ID", "EXAMPLE_RUN_ID")
OUTPUTS = [f"data/artifacts/runs/{run_id}/world/final_world.pkl"]


def run() -> None:
    world = load_draft(INPUTS[0])

    world.grid = Grid(min_x=0.0, min_y=0.0, max_x=100.0, max_y=100.0, cell_size=1.0)

    save_draft(world, OUTPUTS[0])
