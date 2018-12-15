import numpy as np
from park import core
from park.spaces.rng import np_random
from park.utils.graph import DirectedGraph


class Graph(core.Space):
    """
    The element of this space is a DirectedGraph object.
    The node features and edge features need to be confined
    within their ranges.
    """
    def __init__(self, node_low=None, node_high=None, edge_low=None, edge_high=None):
        assert node_low.shape == node_high.shape
        assert len(node_low.shape) == 1
        assert edge_low.shape == edge_high.shape
        assert len(edge_low.shape) == 1
        self.node_low = node_low
        self.node_high = node_high
        self.edge_low = edge_low
        self.edge_high = edge_high
        core.Space.__init__(self, 'graph_float32', (), np.float32)

    def sample(self, valid_list=None):
        if valid_list is None:
            return np_random.randint(self.n)
        else:
            assert len(valid_list) <= self.n
            return valid_list[np_random.randint(len(valid_list))]

    def contains(self, x):
        is_element = type(x) == DirectedGraph
        if is_element:
            # Note: this step can be slow
            node_features, _ = x._node_features_tensor()
            edge_features, _ = x._edge_features_tensor()

            is_element = (node_features >= self.node_low).all() and \
                         (node_features <= self.node_high).all() and \
                         (edge_features >= self.edge_low).all() and \
                         (edge_features <= self.edge_high).all()
        return is_element