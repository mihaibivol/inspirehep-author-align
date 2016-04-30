from munkres import Munkres

from utils import BipartiteConnectedComponents
from utils import group_by_fn


IDS = ['inspire_id', 'orcid', 'inspire_bai', 'record', 'uuid']
def ground_truth_distance(x, y, thresh=None):
    for _id in IDS:
        if _id in x and _id in y:
            if x[_id] == y[_id]:
                return 0
            else:
                return 1
    assert False


def match(l1, l2, thresh, dist_fn, norm_funcs):
    common = []
    l1_only = []
    l2_only = []

    # Use the distance function and threshold on hints given by normalization
    # functions. The lighter the normalization, the greater the chance to
    # match more elements but also to have uncertainty in matching.

    # TODO investigate if we can deal with the uncertainty by using munkres
    # for filtering out common instances.
    for norm_fn in norm_funcs:
        new_common, l1, l2 = _match_by_norm_func(l1, l2, norm_fn,
                                                 dist_fn, thresh)
        common.extend(new_common)

    # Take any remaining umatched entries and try to match them using the
    # Munkres algorithm.
    dist_matrix = [[dist_fn(e1, e2) for e2 in l2] for e1 in l1]

    # Call Munkres on connected components on the remaining bipartite graph.
    # Since we cutoff from the cost anything that is greater than the
    # threshold.
    components = BipartiteConnectedComponents()
    for l1_i in xrange(len(l1)):
        for l2_i in xrange(len(l2)):
            if dist_matrix[l1_i][l2_i] > thresh:
                continue
            components.add_edge(l1_i, l2_i)

    l1_only_idx = set(range(len(l1)))
    l2_only_idx = set(range(len(l2)))

    for l1_indices, l2_indices in components.get_connected_components():
        part_l1 = [l1[i] for i in l1_indices]
        part_l2 = [l2[i] for i in l2_indices]
        l1_only_idx.difference_update(l1_indices)
        l2_only_idx.difference_update(l2_indices)

        part_dist_matrix = [[dist_matrix[l1_i][l2_i] for l2_i in l2_indices]
                            for l1_i in l1_indices]
        part_cmn, part_l1, part_l2 = _match_munkres(part_l1, part_l2,
                                                    part_dist_matrix, thresh)

        common.extend(part_cmn)
        l1_only.extend(part_l1)
        l2_only.extend(part_l2)

    l1_only.extend(_filter_indices(l1, l1_only_idx))
    l2_only.extend(_filter_indices(l2, l2_only_idx))

    return common, l1_only, l2_only


def _match_by_norm_func(l1, l2, norm_fn, dist_fn, thresh):
    common = []

    l1_only_idx = set(range(len(l1)))
    l2_only_idx = set(range(len(l2)))

    buckets_l1 = group_by_fn(enumerate(l1), lambda x: norm_fn(x[1]))
    buckets_l2 = group_by_fn(enumerate(l2), lambda x: norm_fn(x[1]))

    for normed, l1_elements in buckets_l1.items():
        l2_elements = buckets_l2.get(normed, [])
        if len(l1_elements) != 1 or len(l2_elements) != 1:
            continue
        e1_idx, e1 = l1_elements[0]
        e2_idx, e2 = l2_elements[0]
        if dist_fn(e1, e2) > thresh:
            continue
        l1_only_idx.remove(e1_idx)
        l2_only_idx.remove(e2_idx)
        common.append([e1, e2])

    l1_only = _filter_indices(l1, l1_only_idx)
    l2_only = _filter_indices(l2, l2_only_idx)

    return common, l1_only, l2_only


def _match_munkres(l1, l2, dist_matrix, thresh):
    common = []
    if len(l1) == 1 and len(l2) == 1:
        if dist_matrix[0][0] > thresh:
            return [], l1[:], l2[:]
        else:
            return [[l1[0], l2[0]]], [], []

    l1_only_idx = set(range(len(l1)))
    l2_only_idx = set(range(len(l2)))

    m = Munkres()
    indices = m.compute(dist_matrix)
    for l1_idx, l2_idx in indices:
        if dist_matrix[l1_idx][l2_idx] > thresh:
            continue
        common.append([l1[l1_idx], l2[l2_idx]])
        l1_only_idx.remove(l1_idx)
        l2_only_idx.remove(l2_idx)

    l1_only = _filter_indices(l1, l1_only_idx)
    l2_only = _filter_indices(l2, l2_only_idx)

    return common, l1_only, l2_only


def _filter_indices(lst, indices):
    return [lst[i] for i in indices]
