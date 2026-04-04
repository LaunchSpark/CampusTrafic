import numpy as np
from scipy.interpolate import griddata

def draw_flow_direction(ax, points, vectors, magnitudes=None, method='linear'):

    points = np.array(points, dtype=float)
    vectors = np.array(vectors, dtype=float)

    x = points[:, 0]
    y = points[:, 1]
    u = vectors[:, 0]
    v = vectors[:, 1]

    # Create grid
    grid_x, grid_y = np.meshgrid(
    np.linspace(x.min(), x.max(), 100),
    np.linspace(y.min(), y.max(), 100)
)

    grid_u = griddata(points, u, (grid_x, grid_y), method=method)
    grid_v = griddata(points, v, (grid_x, grid_y), method=method)

    ax.quiver(grid_x, grid_y, 
              grid_u, grid_v, 
              angles='xy', 
              scale_units='xy', 
              scale=1, 
              color='blue', 
              alpha=0.7
              )

    if magnitudes is not None:
        magnitudes = np.array(magnitudes, dtype=float)
        grid_magnitudes = griddata(points, magnitudes, (grid_x, grid_y), method=method, fill_value=0)
        ax.contourf(grid_x, grid_y, grid_magnitudes, levels=20, cmap='viridis', alpha=0.5)