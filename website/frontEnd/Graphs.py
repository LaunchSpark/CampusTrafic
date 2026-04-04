import matplotlib.pyplot as plt
import networkx as nx

def draw_graph(graph):
    plt.figure(figsize=(10, 10))
    pos = nx.spring_layout(graph, seed=42)
    nx.draw(graph, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=500)
    
    plt.title("Graph Visualization")
    plt.show()