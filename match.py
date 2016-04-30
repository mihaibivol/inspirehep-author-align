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


def match(l1, l2, thresh, dist_fn, norm_fn):
    l1_only = []
    l2_only = []
    common = []

    # First add list entries to buckets to filter out some of the N^2
    # distance calculation.
    munk_match_l1_idx = set(range(len(l1)))
    munk_match_l2_idx = set(range(len(l2)))

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
        munk_match_l1_idx.remove(e1_idx)
        munk_match_l2_idx.remove(e2_idx)
        common.append([e1, e2])

    # There are no guarantees on set iteration order.
    munk_match_l1_idx = list(munk_match_l1_idx)
    munk_match_l2_idx = list(munk_match_l2_idx)

    # Calculate distance for the unmatched entries
    dist_map = {(l1_idx, l2_idx): dist_fn(l1[l1_idx], l2[l2_idx])
                for l1_idx in munk_match_l1_idx
                for l2_idx in munk_match_l2_idx}

    # Call Munkres on connected components on the remaining bipartite graph.
    components = BipartiteConnectedComponents()
    for l1_i in munk_match_l1_idx:
        for l2_i in munk_match_l2_idx:
            if dist_map[l1_i,l2_i] > thresh:
                continue
            components.add_edge(l1_i, l2_i)

    missing_from_l1 = set(munk_match_l1_idx)
    missing_from_l2 = set(munk_match_l2_idx)

    for l1_indices, l2_indices in components.get_connected_components():
        part_l1 = [l1[i] for i in l1_indices]
        part_l2 = [l2[i] for i in l2_indices]
        missing_from_l1.difference_update(l1_indices)
        missing_from_l2.difference_update(l2_indices)

        part_dist_matrix = [[dist_map[l1_i, l2_i]
                             for l2_i in l2_indices]
                            for l1_i in l1_indices]
        part_cmn, part_l1, part_l2 = match_munkres(part_l1, part_l2,
                                                   part_dist_matrix, thresh)

        common.extend(part_cmn)
        l1_only.extend(part_l1)
        l2_only.extend(part_l2)

    for idx in missing_from_l1:
        l1_only.append(l1[idx])
    for idx in missing_from_l2:
        l2_only.append(l2[idx])

    return common, l1_only, l2_only


def match_munkres(l1, l2, dist_matrix, thresh):
    common = []
    l1_only = []
    l2_only = []
    if len(l1) == 1 and len(l2) == 1:
        if dist_matrix[0][0] > thresh:
            return [], l1[:], l2[:]
        else:
            return [[l1[0], l2[0]]], [], []

    missing_in_l1 = set(range(len(l1)))
    missing_in_l2 = set(range(len(l2)))


    m = Munkres()
    indices = m.compute(dist_matrix)
    for l1_idx, l2_idx in indices:
        if dist_matrix[l1_idx][l2_idx] > thresh:
            l1_only.append(l1[l1_idx])
            l2_only.append(l2[l2_idx])
        else:
            common.append([l1[l1_idx], l2[l2_idx]])
        missing_in_l1.remove(l1_idx)
        missing_in_l2.remove(l2_idx)

    for e1_idx in missing_in_l1:
        l1_only.append(l1[e1_idx])

    for e2_idx in missing_in_l2:
        l2_only.append(l2[e2_idx])

    return common, l1_only, l2_only
