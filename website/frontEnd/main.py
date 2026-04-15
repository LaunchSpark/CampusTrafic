import matplotlib.pyplot as plt
import argparse

from Nodes import draw_nodes_edges
from Vectors import draw_flow_direction
from Background import draw_svg_background

from LoadData import (
    load_required_modules,
    load_graph_artifact,
    graph_to_edges,
    parse_svg_coords_and_edges,
    build_nodes_from_coords,
    load_hour_slice,
    load_wap_counts_for_hour,
    aggregate_hourly_vectors_to_nodes,
    filter_nodes_and_edges_by_prefix,
    filter_nodes_and_edges_by_floor,
    filter_flow_to_near_nodes,
)

ALLOWED_BUILDINGS = ["BRUN", "BRWN", "CLEM", "PRSC"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="EXAMPLE_RUN_ID")
    parser.add_argument("--hour", type=int, default=None)
    parser.add_argument("--svg", required=True)
    parser.add_argument("--save", default="flow.png")
    parser.add_argument("--hide-labels", action="store_true")
    parser.add_argument("--building", default=None)
    parser.add_argument("--floor", type=int, default=None)
    args = parser.parse_args()


    load_required_modules()

    graph = load_graph_artifact(args.run_id)
    edges = graph_to_edges(graph)

    coords, svg_edges = parse_svg_coords_and_edges(args.svg)
    nodes = build_nodes_from_coords(graph, coords)

    edge_list = edges if edges else svg_edges

    hour, points, vectors, magnitudes = load_hour_slice(args.run_id, args.hour)
    hourly_node_counts = load_wap_counts_for_hour(args.run_id, hour)


    building = args.building

    if building is None:
        print("\nAvailable buildings:")
        for b in ALLOWED_BUILDINGS:
            print(f" - {b}")

        building = input("Enter building acronym (blank to exit): ").strip().upper()

        if building == "":
            print("No building selected. Exiting.")
            return

    if building not in ALLOWED_BUILDINGS:
        raise ValueError(
            f"Building '{building}' not found. Options: {', '.join(ALLOWED_BUILDINGS)}"
        )


    nodes, edge_list = filter_nodes_and_edges_by_prefix(
        nodes, edge_list, [building]
    )


    if args.floor is not None:
        nodes, edge_list = filter_nodes_and_edges_by_floor(
            nodes,
            edge_list,
            graph.nodes,
            args.floor,
        )


    if len(nodes) == 0:
        print(f"No nodes found for {building} floor {args.floor}")
        return


    points, vectors, magnitudes = aggregate_hourly_vectors_to_nodes(
        nodes,
        points,
        vectors,
        magnitudes,
    )

    points, vectors, magnitudes = filter_flow_to_near_nodes(
        nodes,
        points,
        vectors,
        magnitudes,
        radius=60,
    )

    fig2, ax2 = plt.subplots(figsize=(12, 10))

    draw_svg_background(ax2, args.svg)

    draw_nodes_edges(
        ax2,
        nodes,
        edge_list,
        show_labels=not args.hide_labels,
        node_counts={
            k: v for k, v in getattr(graph, "node_counts", {}).items() if k in nodes
        },
    )

    spatial_title = f"{building} Spatial Graph"
    if args.floor:
        spatial_title = f"{building} Floor {args.floor} Spatial Graph"

    ax2.set_title(spatial_title)
    ax2.set_aspect("equal")
    ax2.set_xticks([])
    ax2.set_yticks([])

    plt.tight_layout()
    fig2.savefig(f"{building.lower()}_spatial.png", dpi=180)

    fig, ax = plt.subplots(figsize=(14, 10))

    draw_svg_background(ax, args.svg)

    draw_nodes_edges(
        ax,
        nodes,
        edge_list,
        show_labels=not args.hide_labels,
        node_counts={
            k: v for k, v in hourly_node_counts.items() if k in nodes
        } if hourly_node_counts else None,
    )

    draw_flow_direction(
        ax,
        points,
        vectors,
        magnitudes=magnitudes,
        method="linear",
        grid_size=12,
    )

    flow_title = f"{building} Flow | Hour {hour}:00–{hour+1}:00"
    if args.floor:
        flow_title = f"{building} Floor {args.floor} Flow | Hour {hour}:00–{hour+1}:00"

    ax.set_title(flow_title)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])

    plt.tight_layout()
    fig.savefig(args.save, dpi=180)

    print(f"Saved: {building.lower()}_spatial.png")
    print(f"Saved: {args.save}")

    plt.show()


if __name__ == "__main__":
    main()