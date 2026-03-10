from pipelineio.state import save_draft
from py.world.world import World

INPUTS = []
OUTPUTS = ["data/artifacts/world_drafts/01_empty.pkl"]


def run() -> None:
    world = World()
    save_draft(world, OUTPUTS[0])
