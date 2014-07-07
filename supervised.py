import sys
import threading
import remote
import os
import time
import subprocess

refresh_period = 1

class Master(object):
    def __init__(self, box, bench_base):
        self.proc = box.run(['stdbuf -i0 -o0 python -u', os.path.join(bench_base, 'supervised.py')],
            stdout=subprocess.PIPE)
        self.remote_pid = int(self.proc.stdout.readline())

    def close(self):
        self.proc.kill()

def open_link(box, bench_base):
    return Master(box, bench_base)

if __name__ == "__main__":
    print os.getpid()

    while True:
        try:
            sys.stdout.write('\n')
        except IOError:
            break
        time.sleep(refresh_period)

    sys.stderr.write('Done\n')
