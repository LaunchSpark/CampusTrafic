import numpy as np
from scipy.interpolate import griddata

def draw_flow_direction(ax, points, vectors, magnitudes=None, method="linear", grid_size=20):
    if not points or not vectors:
        return

    points = np.array(points, dtype=float)
    vectors = np.array(vectors, dtype=float)

    if len(points) == 1:
        x, y = points[0]
        u, v = vectors[0]
        ax.quiver(
            [x], [y], [u], [v],
            angles="xy",
            scale_units="xy",
            scale=1,
            color="blue",
            alpha=0.8,
            zorder=5,
        )
        return

    if len(points) < 3:
        ax.quiver(
            points[:, 0],
            points[:, 1],
            vectors[:, 0],
            vectors[:, 1],
            angles="xy",
            scale_units="xy",
            scale=1,
            color="blue",
            alpha=0.8,
            zorder=5,
        )
        return

    x = points[:, 0]
    y = points[:, 1]
    u = vectors[:, 0]
    v = vectors[:, 1]

    grid_x, grid_y = np.meshgrid(
        np.linspace(x.min(), x.max(), grid_size),
        np.linspace(y.min(), y.max(), grid_size),
    )

    try:
        grid_u = griddata(points, u, (grid_x, grid_y), method=method, fill_value=0)
        grid_v = griddata(points, v, (grid_x, grid_y), method=method, fill_value=0)
    except Exception:
        ax.quiver(
            points[:, 0],
            points[:, 1],
            vectors[:, 0],
            vectors[:, 1],
            angles="xy",
            scale_units="xy",
            scale=1,
            color="blue",
            alpha=0.8,
            zorder=5,
        )
        return

    grid_u = np.nan_to_num(grid_u)
    grid_v = np.nan_to_num(grid_v)

    ax.quiver(
        grid_x,
        grid_y,
        grid_u,
        grid_v,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="blue",
        alpha=0.6,
        zorder=5,
    )

    if magnitudes is not None:
        magnitudes = np.array(magnitudes, dtype=float)
        try:
            grid_m = griddata(points, magnitudes, (grid_x, grid_y), method=method, fill_value=0)
            grid_m = np.nan_to_num(grid_m)
            ax.contourf(grid_x, grid_y, grid_m, levels=15, alpha=0.25, zorder=2)
        except Exception:
            pass