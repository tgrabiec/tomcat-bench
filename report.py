#!/usr/bin/env python
import os
import json
import argparse
import bench
import numpy
import itertools
from operator import attrgetter
from collections import defaultdict
from itertools import ifilter
from json_utils import *

class TestRun(object):
    def __init__(self, id):
        self.id = id
        self._properties = None

    def get_test_dir(self):
        return os.path.join(bench.bench_base, 'results', self.id)

    def get_properties_path(id):
        os.path.join(self.get_test_dir(), 'properties.json')

    @property
    def datetime(self):
        return self.properties['datetime']

    @property
    def properties(self):
        if self._properties:
            return self._properties

        path = os.path.join(self.get_test_dir(), 'properties.json')
        if os.path.exists(path):
            self._properties = load_json(path)
            self.enrich(self._properties)
            return self._properties

    def enrich(self, properties):
        properties['date'] = properties['datetime'].split(' ')[0]

def get_all_ids():
    return os.listdir(os.path.join(bench.bench_base, 'results'))

def get_all_tests():
    for id in get_all_ids():
        test = TestRun(id)
        if test.properties:
            yield test

class stat_collector():
    def __init__(self):
        self.min = None
        self.max = None
        self.count = 0
        self.samples = []

    def add(self, value):
        value = float(value)
        self.samples.append(value)
        self.min = min(self.min or value, value)
        self.max = max(self.max or value, value)
        self.count += 1

    @property
    def sum(self):
        return sum(self.samples)

    @property
    def std(self):
        return numpy.std(self.samples)

    @property
    def avg(self):
        return self.sum / self.count

class test_stats:
    def __init__(self):
        self.count = 0
        self.throughput = stat_collector()
        self.max_latency = stat_collector()
        self.errors = stat_collector()

def get_tests(args):
    return get_all_tests()

def print_stats(args):
    def get_stats(tests):
        s = test_stats()
        for test in tests:
            s.throughput.add(test.properties['wrk']['throughput'])
            s.max_latency.add(test.properties['wrk']['latency']['max'])
            s.errors.add(test.properties['wrk']['errors'])
            s.count += 1
        return s

    def grouper(t):
         return tuple((get_field(t.properties, field_spec) for field_spec in args.groupby))

    tests = list(t for t in get_tests(args) if not t.properties['wrk']['errors'])
    grouped_tests = dict(((k, get_stats(t)) for k,t in itertools.groupby(sorted(tests, key=grouper), grouper)))

    for name in ['throughput', 'max_latency', 'errors']:
        print name
        print '======'
        print

        min_avg = min(getattr(stats, name).avg for stats in grouped_tests.itervalues())

        print '%39s %10s %8s %-10s %10s %10s %0s' % ('name', 'avg', '', 'stdev', 'min', 'max', 'count')
        for key, stats in sorted(grouped_tests.iteritems()):
            s = getattr(stats, name)

            if min_avg:
                increase = (s.avg / min_avg - 1) * 100
                increase_str = ("+%.1f%%" % increase) if increase else ''
            else:
                increase_str = ''

            print '%39s %10.2f %8s %-10.2f %10.2f %10.2f %5d' % (key, s.avg, increase_str, s.std, s.min, s.max, s.count)

        print

def list_tests(args):
    fmt = '%-13s %-6s %-18s %-18s %-19s %-3s %s'

    print fmt % (
        'ID',
        'OS',
        'IMAGE',
        'OS.VERSION',
        'TIME',
        'ERR',
        'THROUGHPUT'
    )

    for test in sorted(get_tests(args), key=attrgetter('datetime')):
        try:
            print fmt % (
                test.id,
                test.properties['guest']['image']['os'],
                test.properties['guest']['image']['name'],
                test.properties['guest']['image'].get('osv.version', ''),
                test.properties['datetime'],
                test.properties['wrk']['errors'],
                test.properties['wrk']['throughput'],
                )
        except:
            print 'Failed to process test id=' + test.id
            raise

def get_field(properties, path):
    value = properties
    for key in path.split('/'):
        if not key in value:
            return None
        value = value[key]
    return str(value)

def print_timeseries(args):
    for test in sorted(get_tests(args), key=attrgetter("datetime")):
        print '\"%-15s\" %-9s %-19s %-6s %-6s %s' % (test.datetime,
            get_field(test.properties, args.field),
            get_field(test.properties, 'wrk/latency/max'),
            test.properties.get('osv.version', ''),
            test.properties['guest']['os'],
            test.id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser('report')
    subparsers = parser.add_subparsers(help="Command")

    _list = subparsers.add_parser('list')
    _list.set_defaults(func=list_tests)

    _stats = subparsers.add_parser('stats')
    _stats.add_argument('-g', '--groupby', default=[], action='append',
        help='Field the tests should be grouped by')
    _stats.set_defaults(func=print_stats)

    _timeseries = subparsers.add_parser('timeseries')
    _timeseries.add_argument('--field', action='store', default='wrk/throughput')
    _timeseries.set_defaults(func=print_timeseries)

    args = parser.parse_args()
    args.func(args)
