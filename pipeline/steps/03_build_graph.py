from pipelineio.state import load_draft, save_draft
from py.world.graph import Edge, Graph, Node

INPUTS = ["data/artifacts/world_drafts/02_with_devices.pkl"]
OUTPUTS = ["data/artifacts/world_drafts/03_with_graph.pkl"]


def run() -> None:
    world = load_draft(INPUTS[0])

    nodes = {}
    edges = {}

    for device in world.devices:
        conns = device.connections
        for i in range(len(conns)):
            node_id = str(conns[i].node_id)
            if node_id not in nodes:
                nodes[node_id] = Node(id=node_id, x=0.0, y=0.0)

            if i > 0:
                prev_id = str(conns[i - 1].node_id)
                if prev_id != node_id:
                    edge_id = f"{prev_id}-{node_id}"
                    if edge_id not in edges:
                        edges[edge_id] = Edge(id=edge_id, src=prev_id, dst=node_id, weight=1.0)
                    else:
                        # For a real implementation, we'd increment weight here
                        pass

    world.graph = Graph(nodes=nodes, edges=edges)
    save_draft(world, OUTPUTS[0])
