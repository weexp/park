import numpy as np
import math
from itertools import permutations

from park import core, spaces, logger
from park.param import config
from park.utils import seeding

pkl_repo = {
    'inception': 'tmp_cache/inception.pkl'
}

class TFPlacementEnv(core.Env):
    """
    Assign a placement to each operation group of a
    computational graph of deep-learning models.
    The goal is to minimize runtime of the computational graph. 

    * STATE *
        A matrix of current queue occupancy. The (i, j) element in
        the matrix indicates the queue length (number of backlogged
        packets) in the i-th input queue connecting to j-th output
        port.

    * ACTIONS *
        [0, 1, ..., n!-1] where n is the number of ports. The index
        corresponding to the permutation of mapping. The permuation
        is generated using itertools.permutations.
        For example, n=3, ports={0, 1, 2}, itertools.permutations([
        0, 1, 2]) = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0),
        (2, 0, 1), (2, 1, 0)]. Action 1 corresponds to (0, 2, 1),
        i.e., maps packet from input queue 0 to output port 0,
        input 1 to output 2 and input 2 to output 1.

    * REWARD *
        Negative number of packets remaining in the queue after the 
        action. So sum of reward indicates total packet delay.
    
    * REFERENCE *
        Chapter 4
        Communication networks: an optimization, control, and stochastic networks perspective
        R Srikant and L Ying
    """
    def __init__(self):
        # observation and action space
        self.setup_env()
        self.setup_space()
        # random seed
        self.seed(config.seed)

    def setup_env(self):
        device_names = ['/device:GPU:%d' % i for i in range(config.pl_n_devs)]
        gpu_devs = filter(lambda dev: 'GPU' in dev, device_names)
        gpu_devs = list(sorted(gpu_devs))

        if config.pl_graph not in pkl_repo:
            raise Exception('Requesting for model "%s" which doesnot exist in repo.\n\
                                     Please choose from one of the following %s' % \
                                     (config.pl_graph, ' '.join(pkl_repo.keys())))

        pickled_inp_file = pkl_repo[config.pl_graph]
        with open(pickled_inp_file, 'rb') as f:
            j = pickle.load(f)
            mg, G, ungroup_map = j['optim_mg'], j['G'], j['ungrouped_mapping']
            op_perf, step_stats = j['op_perf'], j['step_stats']

        self.mg = mg
        self.ungroup_map = ungroup_map
        self.n_devs = config.pl_n_devs
        self.gpu_devs = gpu_devs
        self.devs = self.gpu_devs
        self.grouped_G = G

        self.sim = ImportantOpsSimulator(mg, op_perf, step_stats, device_names)
        self.node_order = list(nx.topological_sort(G))

    def reset(self):
        node_features = {}
        edge_features = {}
        cur_pl = {}
        for node in self.G.nodes():
            # checkout step function for this order as well
            node_features[node] = [self.sim.cost_d[node],\
                                   self.sim.out_d[node],\
                                   0,\
                                   0]
            cur_pl[node] = node_features[node][2]
            for neigh in G.neighbors(node):
                # dummy edge feature for now
                # TODO: Allow for no edge feature possibility
                edge_features[[node, neigh]] = -1

        node_features[self.node_order[0]][-1] = 1

        self.s = DirectedGraph(node_features, edge_features)
        self.cur_node_idx = 0
        self.cur_pl = cur_pl
        self.prev_rt = self.get_rt(self.cur_pl)

        return self.s


    def setup_space(self):
        # cost (e.g., execution delay estimation in micro-seconds),
        # mem (e.g., op group memory requirements on GPU in bytes),
        # current placement(e.g., GPU 1),
        # one-hot-bit (i.e., currently working on this node)

        node_space = Tuple([\
                Box(low=0, high=10 * (1e6), shape=(1,)),
                Box(low=0, high=10 * (1e6), shape=(1,)),
                Discrete(self.n_devs), 
                Discrete(2)])
        self.observation_space = Graph(node_space, Null())
        self.action_space = Discrete(self.n_devs)

    def ungroup_pl(self, pl):
        ungroup_map = self.ungroup_map
        ungrouped_pl = {}

        for op in self.mg.graph_def.node:
            name = op.name
            grp_ctr = ungroup_map[name]
            ungrouped_pl[name] = pl[grp_ctr] 

        return ungrouped_pl

    # takes op-group placement and 
    # returns runtime of the placement in seconds
    def get_rt(pl):
        pl = self.ungroup_pl(pl)
        rt = self.sim.simulate(pl)
        return rt / 1e6


    def step(self, action):
        assert self.action_space.contains(action)

        action = int(action)
        node_order = self.node_order
        cur_node_idx = self.cur_node_idx
        cur_node = node_order[cur_node_idx]
        next_node = node_order[cur_node_idx + 1]

        self.cur_pl[cur_node] = action
        rt = self.get_rt(self.cur_pl)
        reward = rt - self.prev_rt

        self.s.update_nodes({cur_node:\
                            [self.sim.cost_d[node],\
                            self.sim.out_d[node],\
                            int(action),\
                            0], \

                            next_node:\
                                [self.sim.cost_d[next_node],\
                                self.sim.out_d[next_node],\
                                self.cur_pl[next_node],\
                                1]
                        })

        self.cur_node_idx += 1
        self.prev_rt = rt
        if self.cur_node_idx == len(self.node_order):
            done = True
        else:
            done = False

        assert self.observation_space.contains(self.s)

        return self.s, reward, done, {}

    def seed(self, seed):
        self.np_random = seeding.np_random(seed)
