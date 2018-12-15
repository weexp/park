import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


class DirectedGraph(object):
    def __init__(self, node_features, edge_features):
        self.graph = nx.DiGraph()
        self.update_nodes(node_features)
        self.update_edges(edge_features)

    def update_nodes(self, node_features):
        self.graph.add_nodes_from(node_features.keys())
        for node in node_features:
            self.graph.nodes[node]['feature'] = node_features[node]

    def remove_nodes(self, nodes):
        self.graph.remove_nodes_from(nodes)

    def update_edges(self, edge_features):
        self.graph.add_edges_from(edge_features.keys())
        for edge in edge_features:
            assert len(edge) == 2
            self.graph[edge[0]][edge[1]]['feature'] = \
                edge_features[edge]

    def remove_edges(self, edges):
        self.graph.remove_edges_from(edges)

    def _node_features_tensor(self):
        node_features = []
        node_map = {}
        for (i, n) in enumerate(self.graph.nodes):
            node_features.append(self.graph.nodes[n]['feature'])
            node_map[i] = n

        return np.array(node_features), node_map

    def _edge_features_tensor(self):
        edge_features = []
        edge_map = {}
        for (i, e) in enumerate(self.graph.edges):
            edge_features.append(self.graph[e[0]][e[1]]['feature'])
            edge_map[i] = e

        return np.array(edge_features), edge_map

    def convert_to_tensor(self):
        # node feature matrix, adjacency matrix, edge feature matrix,
        # node map (node index -> node object),
        # edge map (edge index -> edge object)
        node_features, node_map = self._node_features_tensor()
        edge_features, edge_map = self._edge_features_tensor()
        adj_mat = nx.adjacency_matrix(self.graph)
        return node_features, edge_features, adj_mat, node_map, edge_map

    def get_neighbors(self, node):
        list_neighbors = [n for n in self.graph.neighbors(node)]
        return list_neighbors

    def visualize(self):
        # TODO: use pydot
        pass

