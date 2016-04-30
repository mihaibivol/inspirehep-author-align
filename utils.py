def group_by_fn(iterable, fn):
    buckets = {}
    for elem in iterable:
        key = fn(elem)
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(elem)
    return buckets


class BipartiteConnectedComponents(object):
    def __init__(self):
        self.parents = {}

    def add_edge(self, p1_node, p2_node):
        node_1 = (p1_node, None)
        node_2 = (None, p2_node)
        self._union(node_1, node_2)

    def get_connected_components(self):
        components_by_root = group_by_fn(self.parents.keys(),
                                         self._find)
        for root in components_by_root:
            components_by_root[root].append(root)

        for component in components_by_root.values():
            p1_nodes = []
            p2_nodes = []
            for p1_node, p2_node in component:
                if p1_node is None:
                    p2_nodes.append(p2_node)
                if p2_node is None:
                    p1_nodes.append(p1_node)
            yield (p1_nodes, p2_nodes)

    def _union(self, node_1, node_2):
        parent_1 = self._find(node_1)
        parent_2 = self._find(node_2)
        if parent_1 != parent_2:
            self.parents[parent_1] = parent_2

    def _find(self, node):
        root = node
        while root in self.parents:
            root = self.parents[root]
        while node in self.parents:
            prev_node = node
            node = self.parents[node]
            self.parents[prev_node] = root
        return root
