import editdistance
import re
from munkres import Munkres
from unidecode import unidecode
from repoze.lru import lru_cache

from inspirehep.modules.authors.utils import scan_author_string_for_phrases


def obj_edit_dist(l1, l2):
    dst = [[max(r, c) for c in xrange(len(l2) + 1)]
           for r in xrange(len(l1) + 1)]

    for r, e1 in enumerate(l1, 1):
        for c, e2 in enumerate(l2, 1):
            d = 0 if e1 == e2 else 1
            dst[r][c] = min(dst[r - 1][c] + 1,
                            dst[r][c - 1] + 1,
                            dst[r - 1][c - 1] + d)
    return dst[len(l1)][len(l2)]


def normed_edit_dist(s1, s2):
    return float(editdistance.eval(s1, s2)) / max(len(s1), len(s2), 1)


class Token(object):
    def __init__(self, token):
        self.token = re.sub(r'[^a-z\'-]', '', token.lower())

    def __eq__(self, other):
        return self.token == other.token

    def __repr__(self):
        return repr('{}: {}'.format(self.__class__.__name__,
                                    self.token))

class Initial(Token):

    def __eq__(self, other):
        return self.token == other.token[:len(self.token)]


@lru_cache(10000)
def parse_name(name):
    parsed = []
    phrases = scan_author_string_for_phrases(name)
    tokens = phrases['lastnames'] + phrases['nonlastnames']
    for token in tokens:
        if len(token) == 1:
            parsed.append(Initial(token))
        else:
            parsed.append(Token(token))
    return parsed

def normalize_author_name(author):
    name = author.get('full_name')
    phrases = scan_author_string_for_phrases(name)
    return (tuple(n.lower() for n in phrases['lastnames']) +
            tuple(n[0].lower() for n in phrases['nonlastnames'][:1]))


def token_distance(t1, t2):
    if isinstance(t1, Initial) or isinstance(t2, Initial):
        if t1.token == t2.token:
            return 0
        if t1 == t2:
            return 0.05
        return 1.0
    return normed_edit_dist(t1.token, t2.token)


def author_munkredist(x, y):
    name_x = unidecode(x.get('full_name'))
    name_y = unidecode(y.get('full_name'))

    parsed_x = parse_name(name_x)
    parsed_y = parse_name(name_y)

    dst = [[token_distance(tx, ty) for ty in parsed_y] for tx in parsed_x]

    matcher = Munkres()
    idx = matcher.compute(dst)
    cost = 0.0
    for ix, iy in idx:
        cost += dst[ix][iy]

    return cost / max(min(len(x), len(y)), 1)
