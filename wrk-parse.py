#!/usr/bin/env python
import re
import sys
import operator

def text_to_nanos(text):
    if text.endswith('ms'):
        return float(text.rstrip('ms')) * 1e6
    if text.endswith('us'):
        return float(text.rstrip('us')) * 1e3
    if text.endswith('ns'):
        return float(text.rstrip('ns'))
    if text.endswith('s'):
        return float(text.rstrip('s')) * 1e9
    return float(text)

class wrk_output:
    pattern = r"""Running (?P<test_duration>.+?) test @ (?P<url>.+)
  (?P<nr_threads>\d+) threads and (?P<nr_connections>\d+) connections\s*
  Thread Stats   Avg      Stdev     Max   \+/- Stdev
    Latency\s+([^ ]+)\s+([^ ]+)\s+(?P<latency_max>[^ ]+)\s+([^ ]+?)
    Req/Sec\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)\s+([^ ]+?)(
  Latency Distribution
     50%\s*(?P<latency_p50>.*?)
     75%\s*(?P<latency_p75>.*?)
     90%\s*(?P<latency_p90>.*?)
     99%\s*(?P<latency_p99>.*?))?
  (?P<total_requests>\d+) requests in (?P<total_duration>.+?), (?P<total_read>.+?) read(
  Socket errors: connect (?P<err_connect>\d+), read (?P<err_read>\d+), write (?P<err_write>\d+), timeout (?P<err_timeout>\d+))?(
  Non-2xx or 3xx responses: (?P<bad_responses>\d+))?
Requests/sec\:\s*(?P<req_per_sec>.+?)
Transfer/sec\:\s*(?P<transfer>.*?)\s*"""

    def __init__(self, text):
        self.m = re.match(self.pattern, text, re.MULTILINE)
        if not self.m:
            raise Exception('Input does not match')

    @property
    def requests_per_second(self):
        return self.m.group('req_per_sec')

    @property
    def error_count(self):
        return sum(map(int, [
            self.m.group('err_timeout') or '0',
            self.m.group('err_connect') or '0',
            self.m.group('err_write') or '0',
            self.m.group('err_read') or '0',
            self.m.group('bad_responses') or '0'
        ]))

    @property
    def latency_max(self):
        return text_to_nanos(self.m.group('latency_max'))


def print_table(header_value_pairs):
    formats = []

    for header, value in data:
        formats.append('%%%ds' % (max(len(str(value)), len(header))))

    format = ' '.join(formats)

    print format % tuple(map(operator.itemgetter(0), data))
    print format % tuple(map(str, map(operator.itemgetter(1), data)))

if __name__ == "__main__":
    with open(sys.argv[1]) as file:
        summary = wrk_output(file.read())

        data = [
            ('Req/s', summary.requests_per_second),
            ('Errors', summary.error_count),
            ('Latency-max [ns]', summary.latency_max),
        ]

        print_table(data)