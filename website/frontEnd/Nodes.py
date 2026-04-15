import matplotlib.pyplot as plt
import networkx as nx

def draw_nodes_edges(ax, nodes, edges, show_labels=True, node_counts=None):

    for n1, n2 in edges:
        if n1 not in nodes or n2 not in nodes:
            continue

        x1, y1 = nodes[n1]["x"], nodes[n1]["y"]
        x2, y2 = nodes[n2]["x"], nodes[n2]["y"]

        ax.plot(
            [x1, x2],
            [y1, y2],
            linestyle="-",
            linewidth=1,
            alpha=0.3,
            color="gray",
            zorder=1,
        )

    xs = [nodes[n]["x"] for n in nodes]
    ys = [nodes[n]["y"] for n in nodes]

    if node_counts:
        sizes = [50 + node_counts.get(n, 0) * 5 for n in nodes]
    else:
        sizes = [60 for _ in nodes]

    ax.scatter(xs, ys, s=sizes, color="red", edgecolor="black", zorder=2)

    if show_labels:
        for name, data in nodes.items():
            ax.text(
                data["x"],
                data["y"] + 0.05,
                name,
                fontsize=7,
                ha="center",
                zorder=3,
            )