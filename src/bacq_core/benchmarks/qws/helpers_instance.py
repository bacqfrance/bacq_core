"""
Noe Olivier -- March 2026

Defines functions to consider an appropriate graph instance.
"""

import networkx as nx
import numpy as np


def get_destination_states(graph_type, n, d, num_instances=1):
    '''
    Sample destination nodes states from the graph instance(s).

    Arguments:
        .graph_type     -- str, type of graph (cycle, 2D-torus)
        .n              -- int, number of qubits for tehe problem size
        .d              -- int, distance between initial and destination nodes
        .num_instances  -- int, number of graph instances for a given problem size
    
    Returns:
        .destination_states -- list[str], bitstring of states of destination nodes
    '''
    num_dims = 0
    
    match graph_type:

        case "cycle":
            source_node = 0
            graph = nx.cycle_graph(2**n)
            graph_lengths = nx.single_source_shortest_path_length(graph, source_node)
            potential_destination_nodes = [node for node, dist in graph_lengths.items() if dist == d]
            num_dims = 1 

        case "2D-torus":
            source_node = (0,0)
            graph = nx.grid_2d_graph(2**n, 2**n, periodic=True)
            graph_lengths = nx.single_source_shortest_path_length(graph, source_node)
            potential_destination_nodes = [node for node, dist in graph_lengths.items() if dist == d]
            num_dims = 2

            for i, node in enumerate(potential_destination_nodes):
                potential_destination_nodes[i] = potential_destination_nodes[i][0] + potential_destination_nodes[i][1]*n

        case _:
            raise NotImplementedError(f"Graph type {graph_type} not implemented yet.")

    destination_states = []
    for k in range(num_instances):
        destination_node = np.random.choice(potential_destination_nodes)
        destination_states.append("{0:b}".format(destination_node).zfill(num_dims*n))

    return destination_states, num_dims
