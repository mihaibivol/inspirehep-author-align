#!/usr/bin/env python

import sys
import os
import fnmatch
import glob
import ujson as json
from timeit import default_timer
from Queue import Queue

from distance import beardist
from distance import norm_funcs
from match import match



def extend_batch(batch):
    for c, l1, l2 in batch:
        for extended in extend_test(c, l1, l2):
            yield extended


def extend_test(common, l1, l2, chunks=100):
    chunks = min(len(common), chunks)
    chunk_size = len(common) / chunks if chunks else -1
    yield common, l1, l2
    for move_out in range(0, len(common), chunk_size):
        new_l1 = l1[:]
        new_l2 = l2[:] + [common[move_out][1]]
        new_common = common[:move_out] + common[move_out + 1:]
        if new_common:
            yield new_common, new_l1, new_l2


class MatchTester(object):
    def __init__(self, *match_args):
        self.cnt = 0
        self.match_args = match_args

        self.total_ents = set()
        self.uniq_matches = set()
        self.uniq_not_matches = set()
        self.times = []
        self.lengths = []

        self.uniq_nm = {}
        self.uniq_im = {}
        pass

    def check_ok(self, expected, actual):
        exp_cmn, exp_l1, exp_l2 = expected
        act_cmn, act_l1, act_l2 = actual

        for e1, e2 in exp_cmn:
            if [e1, e2] not in act_cmn:
                self.uniq_nm[(e1.get('full_name'),
                              e2.get('full_name'))] = e1, e2
        for e1, e2 in act_cmn:
            if [e1, e2] not in exp_cmn:
                self.uniq_im[(e1.get('full_name'),
                              e2.get('full_name'))] = e1, e2

    def test(self, common, l1_only, l2_only):
        l1 = l1_only[:]
        l2 = l2_only[:]
        self.uniq_matches.update((x.get('full_name'), y.get('full_name'))
                                 for x, y in common)
        self.uniq_not_matches.update((x.get('full_name'), y.get('full_name'))
                                     for x in l1 for y in l2)
        for l1_el, l2_el in common:
            l1.append(l1_el)
            l2.append(l2_el)
        if not l1 or not l2:
            assert False

        self.total_ents.update(x.get('full_name') for x in l1)
        self.total_ents.update(x.get('full_name') for x in l2)

        self.cnt += 1

        start_t = default_timer()
        actual = match(l1, l2, *self.match_args)
        self.times.append(default_timer() - start_t)
        self.lengths.append(len(l1) * len(l2))
        self.check_ok((common, l1_only, l2_only), actual)


    def log(self, verbose=False):
        stat = ('Tester Stats:\n'
                '================\n'
                'Total Count: {}\n'
                'Total Entities: {}\n'
                'Total Matches: {}\n'
                'Total Mismatches: {}\n'
                '======================\n'
                'Incorrect Matches: {}\n'
                'Not Matched: {}\n'.format(
                    self.cnt,
                    len(self.total_ents),
                    len(self.uniq_matches),
                    len(self.uniq_not_matches),
                    len(self.uniq_im),
                    len(self.uniq_nm)))
        if not verbose:
            return stat
        match_str = '<<\n\t{}\nwith\n\t{}\n>>'
        bad_match_str = 'Bad Match' + match_str
        not_match_str = 'Not Matched' + match_str

        verbose_output = ('Should Have Been Matched:\n{}\n\n'
                          'Should Not Have Been Matched:\n\n{}\n'
                          'And we processed on avg  : {} pairs\n'
                          '                 max     : {} pairs\n'
                          '                 95th_per: {} pairs\n\n'
                          'And it took on avg  : {} secs\n'
                          '            max     : {} secs\n'
                          '            95th_per: {} secs\n').format(
                              '\n'.join(not_match_str.format(x, y)
                                        for x, y in self.uniq_nm.values()),
                              '\n'.join(bad_match_str.format(x, y)
                                        for x, y in self.uniq_im.values()),
                              sum(self.lengths) / len(self.lengths),
                              max(self.lengths),
                              sorted(self.lengths)[int(len(self.lengths) * .95)],
                              sum(self.times) / len(self.times),
                              max(self.times),
                              sorted(self.times)[int(len(self.times) * .95)])
        return verbose_output + stat


class ProgramState(object):
    def __init__(self, max_tests, *match_args):
        self.running = True
        self.q = Queue(2)
        self.max_tests = max_tests
        self.match_args = match_args

        last_dump = sorted(
            [f for f in os.listdir('/tmp/')
             if fnmatch.fnmatch(f, '[0-9][0-9][0-9].txt')])[-1]
        next_dump = int(last_dump.replace('.txt', '')) + 1
        self.dump_file = '/tmp/%03d.txt' % next_dump

    def read_files(self):
        files = glob.glob('./author_list_tests/*.json')
        files.sort(key=os.path.getsize)
        for fn in files:
            if not self.running:
                return
            with open(fn) as f:
                self.q.put(json.load(f))
        self.q.put('END')

    def log(self, tester, verbose=False):
        s = tester.log(verbose)
        with open(self.dump_file, 'a') as f:
            f.write(s + '\n')
        print s

    def main(self):
        print 'SAVING ON %s' % self.dump_file
        import threading
        thread = threading.Thread(target=self.read_files)
        thread.start()

        tester = MatchTester(*self.match_args)
        while True:
            batch = self.q.get()
            if batch == 'END':
                self.log(tester, True)
                break
            for common, l1, l2 in extend_batch(batch):
                if tester.cnt == self.max_tests:
                    # Unblock q.put() if any
                    self.q.get()
                    self.running = False
                    thread.join()
                    self.log(tester, True)
                    sys.exit(0)

                tester.test(common, l1, l2)
                if tester.cnt % 20 == 0:
                    self.log(tester)

if __name__ == '__main__':
    max_tests = sys.maxint
    if len(sys.argv) > 1:
        max_tests = int(sys.argv[1])
    ProgramState(max_tests,
                 .5, beardist, norm_funcs).main()
