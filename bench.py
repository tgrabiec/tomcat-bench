#!/usr/bin/env python
import os
import runpy
import argparse
import time
import remote
import subprocess
import pprint
import json
import time
import re
import wrkparse
import traceback
import supervision
import shutil
from random import randrange
from contextlib import contextmanager
from json_utils import *

ENV_IMAGE_REPO = 'BENCH_IMAGE_REPO'
ENV_BASE = 'BENCH_BASE'

bench_base = os.path.dirname(os.path.realpath(__file__))

def get_qemu_version(box):
    return box.eval(['qemu-system-x86_64 -version | sed -r \'s/.*version ([0-9.]+).*/\\1/\''])

def get_box_timestamp(box):
    return box.eval(['date +%s.%N'])

def drop_empty_values(a_dict):
    result = {}
    for key, val in a_dict.iteritems():
        if val:
            result[key] = val
    return result

def get_box(url):
    m = re.match(r'^(?P<username>.*?@)?(?P<hostname>.*?)(:(?P<port>\d+))?$', url)
    if not m:
        raise Exception('Invalid url pattern: ' + url)
    return remote.RemoteShell(**drop_empty_values(m.groupdict()))


def format_dict(data):
    return json.dumps(data, indent=4)

def start_qemu(box, memsize, cpus, image, slave_pid, bridge='virbr0', logfile='qemu.log'):

    cmdline = 'cd %s; export OSV_BRIDGE=%s; qemu-system-x86_64 \
        -m %s -s -smp %d -vnc :1 -device virtio-blk-pci,id=blk0,bootindex=0,drive=hd0,scsi=off \
        -drive file=%s,if=none,id=hd0,aio=native,cache=none \
        -netdev tap,id=hn0,script=./qemu-ifup.sh,vhost=on \
        -device virtio-net-pci,netdev=hn0,id=nic1 -device virtio-rng-pci \
        -enable-kvm -cpu host,+x2apic -chardev stdio,mux=on,id=stdio,signal=off \
        -mon chardev=stdio,mode=readline,default -device isa-serial,chardev=stdio 2>&1 > %s \
         & pid=$!; tail -f $(mktemp) --pid %d; kill $pid' % (
            remote.get_env(box, ENV_BASE), bridge, memsize, cpus, image, logfile, slave_pid)

    print 'Starting guest...'
    print cmdline
    return box.run(sudo_command(cmdline))

class Test(object):
    def __init__(self, bench_base, test_id, test_dir, user_config):
        self.id = test_id
        self.dir = test_dir
        self.bench_base = bench_base
        self.user_config = user_config
        self.properties = {'id': test_id}

def wait_for_server(box, host, port, timeout=30):
    remote.await(remote.when(remote.is_reachable_from, args=(box, host, port), poll_delay=1), timeout=timeout)

def wait_for_ip(box, qemu_log, timeout=10):
    def get_ip():
        ip_line = box.eval(['grep eth0 ' + qemu_log])
        m = re.match(r'eth0: (?P<ip>[\d.]+)', ip_line)
        if m:
            return m.group('ip')

    remote.await(remote.when(get_ip, poll_delay=1), timeout=timeout)
    return get_ip()

def is_qemu_running(box):
    return bool(box.eval(['pidof grep qemu-system-x86_64']))

def get_box_info(box):
    return {
        'hostname': box.eval(['hostname']),
        'uname': box.eval(['uname -a']),
        'cpu': {
            'model': box.eval(['cat /proc/cpuinfo | grep "model name" | head -n 1 | cut -d: -f2']),
            'n_cores': box.eval(['cat /proc/cpuinfo | grep "model name" | wc -l'])
        }
    }

def sudo_command(args):
    return ['sudo bash -c \'', args, '\'']

def sync_bench(box, remote_dir):
    box.rsync(bench_base + '/', remote_dir, excludes=['results'])

class Scope(object):
    def __init__(self):
        self.callbacks = []

    def at_exit(self, callback):
        self.callbacks.append(callback)

    def __enter__(self):
        pass

    def __exit__(self, *args):
        for callback in self.callbacks:
            try:
                callback()
            except:
                traceback.print_exc()

def get_user_config(args):
    if args.config:
        config_file = args.config
    else:
        config_file = os.environ['BENCH_CONFIG']
        if not config_file:
            raise Exception('Config file not specified')

    return runpy.run_path(config_file)

def add_sync_option(parser):
    parser.add_argument('--no-sync', action='store_true', help="do not sync benchmark files")

def add_config_option(parser):
    parser.add_argument('--config', '--conf', action='store', help="use given configuration file")

def add_repo_option(parser):
    parser.add_argument('--repo', action='store', required=False)

def sync(args):
    user_config = get_user_config(args)
    tomcat_box = get_box(user_config['tomcat']['ssh'])
    tomcat_bench_base = remote.get_env(tomcat_box, ENV_BASE)
    load_driver_box = get_box(user_config['load_driver']['ssh'])
    load_driver_bench_base = remote.get_env(load_driver_box, ENV_BASE)

    print 'Syncing load-driver ...'
    sync_bench(load_driver_box, load_driver_bench_base)

    print 'Syncing tomcat ...'
    sync_bench(tomcat_box, tomcat_bench_base)

def make_image(args):
    user_config = get_user_config(args)
    tomcat_box = get_box(user_config['tomcat']['ssh'])
    tomcat_bench_base = remote.get_env(tomcat_box, ENV_BASE)
    src_base = args.src
    name = args.name[0]

    if not args.no_sync:
        sync_bench(tomcat_box, tomcat_bench_base)

    make_command = 'SRC_BASE=' + src_base

    if args.osv_rev:
        make_command += ' OSV_VERSION_REF=' + args.osv_rev

    make_command += ' ./setup-host.sh'
    
    tomcat_box.shell([make_command], cwd=tomcat_bench_base)
    tomcat_box.shell(['${%s}/bench.py push -f %s' % (ENV_BASE, name)], cwd=os.path.join(src_base, 'osv'))

def get_image_cache_dir(args):
    if args.repo:
        return repo
    env = 'BENCH_IMAGE_REPO'
    try:
        return os.environ[env]
    except KeyError:
        raise Exception('Please set the \'%s\' environment variable' % env)

def trim(s):
    return s.rstrip('\n')

def push_image(args):
    name = args.name[0]
    image_dir = os.path.join(get_image_cache_dir(args), name)
    if os.path.exists(image_dir):
        if args.force:
            shutil.rmtree(image_dir)
        else:
            raise Exception('Image directory already exists: ' + image_dir + ', use -f to force')
    os.mkdir(image_dir)
    shutil.copyfile('build/release/usr.img', os.path.join(image_dir, 'usr.img'))
    shutil.copyfile('build/release/loader.elf', os.path.join(image_dir, 'loader.elf'))

    manifest = {
        'os': 'osv',
        'osv.version': trim(subprocess.check_output(['scripts/osv-version.sh'])),
        'osv.sha1': trim(subprocess.check_output(['git', 'rev-parse', 'HEAD'])),
        'apps.version': trim(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd='apps')),
        'webapp.version': trim(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd='../FrameworkBenchmarks')),
    }

    print('Pushed \'%s\' as: ' % name)
    print(format_dict(manifest))
    save_json(manifest, os.path.join(image_dir, 'manifest.json'))

def drop_page_cache(box):
    print 'Dropping page cache'
    box.shell(sudo_command('echo 3 > /proc/sys/vm/drop_caches'))

def run(args):
    user_config = get_user_config(args)

    test_id = str(time.time())
    results_dir = os.path.join(bench_base, 'results')
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)
    test_dir = os.path.join(results_dir, test_id)
    os.mkdir(test_dir)

    test = Test(bench_base, test_id, test_dir, user_config)
    print 'Starting test, id=%s, dir=%s' % (test.id, test.dir)

    load_driver_box = get_box(user_config['load_driver']['ssh'])
    tomcat_box = get_box(user_config['tomcat']['ssh'])
    tomcat_bench_base = remote.get_env(tomcat_box, ENV_BASE)
    load_driver_bench_base = remote.get_env(load_driver_box, ENV_BASE)

    print "Using %s as load driver" % (str(load_driver_box))
    print "Using %s as tomcat host" % (str(tomcat_box))

    if not args.no_sync:
        sync(args)

    load_driver_box.shell(['sudo ./setup.sh'], cwd=load_driver_bench_base)

    test.properties.update({
        'qemu.version': get_qemu_version(tomcat_box),
        'load_driver': get_box_info(load_driver_box),
        'tomcat': get_box_info(tomcat_box),
        'datetime': remote.localhost.eval(['date \'+%Y.%m.%d %H:%M:%S\'']),
        'bench.version': remote.localhost.eval(['git rev-parse HEAD'], cwd=bench_base),
    })

    if is_qemu_running(tomcat_box):
        time.sleep(supervision.refresh_period)
        if is_qemu_running(tomcat_box):
            raise Exception('Qemu already running on ' + str(tomcat_box))

    print 'Copying image file...'
    guest_image = args.image
    image_dir = os.path.join(remote.get_env(tomcat_box, ENV_IMAGE_REPO), guest_image)
    image_src = os.path.join(image_dir, 'usr.img')
    tmp_image_path = os.path.join(user_config['tomcat']['image_run_dir'], 'tmp.img')
    tomcat_box.shell(['cp', image_src, tmp_image_path])

    memsize = user_config.get('memsize', '4g')
    cpus = int(args.cpus or user_config.get('cpus', '1'))
    bridge = user_config.get('bridge', 'virbr0')

    image_properties = json.loads(tomcat_box.eval(['cat ' + os.path.join(image_dir, 'manifest.json')]))
    image_properties['name'] = guest_image

    test.properties['guest'] = {
        'image': image_properties,
        'memsize': memsize,
        'cpus': cpus,
        'bridge': bridge,
    }

    supervisor = supervision.start_master(tomcat_box, tomcat_bench_base)
    slave_pid = supervisor.slave_pid
    print 'Started remote supervisor, pid=%d' % (slave_pid)

    qemu_log = os.path.join(tomcat_bench_base, 'qemu.log')
    start_qemu(tomcat_box, memsize, cpus, tmp_image_path, slave_pid, bridge, qemu_log)

    guest_ip = wait_for_ip(tomcat_box, qemu_log)
    print "Guest IP is " + guest_ip

    tomcat_port = 8081
    print 'Waiting for Tomcat (%s:%d) ...' % (guest_ip, tomcat_port)
    wait_for_server(tomcat_box, guest_ip, tomcat_port)

    test.properties['ping'] = load_driver_box.eval(['ping -i 0.2 -c 3 %s | tail -n 1' % guest_ip])

    drop_page_cache(tomcat_box)

    url = 'http://%s:%d/servlet/json' % (guest_ip, tomcat_port)

    print 'Warmup'
    warmup_duration = user_config.get('warmup_duration', '1m')
    test.properties['warmup_start'] = get_box_timestamp(load_driver_box)
    load_driver_box.shell(['wrk -t4 -c16 -d%s %s' % (warmup_duration, url)])

    print 'Main test'
    test_duration = user_config.get('test_duration', '1m')

    wrk_file = 'wrk.' + test_id
    wrk_cmdline = 'wrk --latency -t4 -c%s -d%s %s' % (str(args.connections), test_duration, url)
    test.properties['start'] = get_box_timestamp(load_driver_box)
    load_driver_box.shell([wrk_cmdline, '>', wrk_file], cwd=load_driver_bench_base)

    test.properties['end'] = get_box_timestamp(load_driver_box)
    print 'Test finished'

    load_driver_box.download(os.path.join(load_driver_bench_base, wrk_file), test_dir)
    wrk = wrkparse.read(os.path.join(test_dir, wrk_file))
    test.properties['wrk'] = {
       'cmdline': wrk_cmdline,
       'throughput': wrk.requests_per_second,
       'errors': wrk.error_count,
       'latency': {
           'unit': 'ms',
           'max': wrk.latency_max / 1e6,
       },
       'duration': wrk.test_duration,
       'nr_threads': wrk.nr_threads,
       'nr_connections': wrk.nr_connections,
    }

    tomcat_box.download(qemu_log, test_dir)

    print 'Test attributes:', format_dict(test.properties)
    save_json(test.properties, os.path.join(test_dir, 'properties.json'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser('Tomcat benchmark')
    subparsers = parser.add_subparsers(help="Command")

    _sync = subparsers.add_parser('sync')
    add_config_option(_sync)
    _sync.set_defaults(func=sync)

    _make_img = subparsers.add_parser('make-img')
    add_config_option(_make_img)
    add_sync_option(_make_img)
    add_repo_option(_make_img)
    _make_img.add_argument('--src', action='store', required=True)
    _make_img.add_argument('--osv-rev', action='store', required=False)
    _make_img.add_argument('name', nargs=1)
    _make_img.set_defaults(func=make_image)

    _push = subparsers.add_parser('push')
    _push.add_argument('name', nargs=1)
    _push.add_argument('--force', '-f', action='store_true', default=False)
    add_repo_option(_push)
    _push.set_defaults(func=push_image)

    _run = subparsers.add_parser('run')
    add_config_option(_run)
    add_sync_option(_run)
    add_repo_option(_run)
    _run.add_argument('--image', action='store', required=True)
    _run.add_argument('--cpus', '-c', action='store', default='4')
    _run.add_argument('--connections', '--conn', action='store', default='128')
    _run.set_defaults(func=run)

    args = parser.parse_args()
    args.func(args)
