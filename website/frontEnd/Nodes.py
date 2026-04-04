import matplotlib.pyplot as plt

def draw_nodes_edges(ax, nodes, edges, show_labels=True):
    # Draw edges
    for n1, n2 in edges:
        x1, y1 = nodes[n1]["x"], nodes[n1]["y"]
        x2, y2 = nodes[n2]["x"], nodes[n2]["y"]
        ax.plot([x1, x2], [y1, y2], linestyle="-", linewidth=1, alpha=0.5, color='gray', zorder=1)

    # Draw nodes
    xs = [nodes[name]["x"] for name in nodes]
    ys = [nodes[name]["y"] for name in nodes]
    ax.scatter(xs, ys, s=60, color='red', edgecolor='black', zorder=2)

    if show_labels:
        for name, data in nodes.items():
            ax.text(data["x"], data["y"] + 0.05, name, fontsize=8, ha="center", zorder=3)