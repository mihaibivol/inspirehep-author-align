import editdistance
import re
import pickle
import numpy as np
from munkres import Munkres
from unidecode import unidecode
from repoze.lru import lru_cache
from functools import partial

from inspirehep.modules.authors.utils import scan_author_string_for_phrases

dist_estimator = pickle.load(open('./linkage.dat', 'rb'))
SIGN = 0


def build_beard_auth(auth):
    aff = auth.get('affiliations', [])
    global SIGN
    SIGN += 1
    if aff:
        aff = aff[0]['value']
    return {'author_affiliation': aff,
            'author_name': auth.get('full_name', ''),
            'publication': {'authors': [], 'year': 2016},
            'signature_id': SIGN}


def beardist(x, y):
    x = build_beard_auth(x)
    y = build_beard_auth(y)
    return dist_estimator.predict_proba(np.array([[x, y]]))[0][1]


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


def normalize_author_name(author,
                          max_first_name_tokens=None,
                          first_name_to_initial=False):
    name = author.get('full_name')
    phrases = scan_author_string_for_phrases(name)
    last_fn_char = 1 if first_name_to_initial else None
    last_fn_idx = max_first_name_tokens
    return (tuple(n.lower() for n in phrases['lastnames']) +
            tuple(n.lower()[:last_fn_char]
                  for n in phrases['nonlastnames'][:last_fn_idx]))


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
    matched_only_initials = True
    for ix, iy in idx:
        cost += dst[ix][iy]
        if not any(isinstance(x, Initial)
                   for x in (parsed_x[ix], parsed_y[iy])):
            matched_only_initials = False
    if matched_only_initials:
        return 1.0
    return cost / max(min(len(x), len(y)), 1)


lowercase_id_norm = partial(normalize_author_name)
lowercase_fn_initials_norm = partial(normalize_author_name,
                                     first_name_to_initial=True)
lowercase_fst_initial_norm = partial(normalize_author_name,
                                     first_name_to_initial=True,
                                     max_first_name_tokens=1)
last_name_only_norm = partial(normalize_author_name,
                               first_name_to_initial=True,
                               max_first_name_tokens=0)


norm_funcs = [lowercase_fn_initials_norm,
              lowercase_fst_initial_norm,
              last_name_only_norm]
