import matplotlib.pyplot as mpl
import numpy as np
import scipy.stats as stats
import pandas as pd
import geopandas as gpd
import networkx as nx

from Graphs import draw_graph
from Nodes import draw_nodes_edges
from website.frontEnd.Vectors import draw_flow_direction

def main():
    
    G = nx.Graph()
    G.add_edges_from([('A', 'B'), ('B', 'C'), ('C', 'A'), ('A', 'D'), ('D', 'E')])
   
    nodes = {
        'A': {'x': 0.0, 'y': 0.0},
        'B': {'x': 1.0, 'y': 0.0},
        'C': {'x': 0.5, 'y': 1.0},
        'D': {'x': -0.5, 'y': -0.5},
        'E': {'x': -1.0, 'y': -1.0}
        }

    edges = [('A', 'B'), 
             ('B', 'C'), 
             ('C', 'A'), 
             ('A', 'D'), 
             ('D', 'E')
             ]
    
    points = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0), (0.5, -0.5), (1.0, -1.0)]

    vectors = [(0.5, 0.5), (0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.2, -0.3)]
    
    magnitudes = [1, 2, 1.5, 2.5, 1.2]
    
    draw_graph(G)
    
    fig, ax = mpl.subplots(figsize=(10, 10))
    draw_nodes_edges(ax, nodes, edges, show_labels=True)
    draw_flow_direction(ax, points, vectors, magnitudes=None, method='linear')

    mpl.tight_layout()
    mpl.show()

if __name__ == "__main__":
    main()

