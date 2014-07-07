import os
import subprocess
import threading
import socket
import time
import atexit
import re
from contextlib import contextmanager

def is_endpoint_reachable(host, port):
    s = socket.socket()
    try:
        s.connect((host, port))
        s.close()
        return True
    except socket.error:
        return False

def is_port_open(box, port):
    return bool(box.eval(['lsof -i :' + str(port)]))

def is_reachable_from(box, host, port):
    return 'Escape character is \'^]\'.' in box.iter_lines(['telnet', host, str(port), '<', '/dev/null'])

def when(predicate, args=[], poll_delay=0.2):
    event = threading.Event()

    def poll():
        while True:
            if predicate(*args):
                event.set()
                return
            time.sleep(poll_delay)

    thread = threading.Thread(target=poll)
    thread.setDaemon(True)
    thread.start()
    return event

def await(event, timeout=None):
    event.wait(timeout)
    if not event.is_set():
        raise Exception('timeout')

def when_reachable(host, port):
    return when(is_endpoint_reachable, args=(host, port))

def get_env(box, name, optional=False):
    value = box.eval(['echo ${%s}' % name])
    if not optional and not value:
        raise Exception('Variable %s not set on %s' % (name, box))

class RemoteShell(object):
    def __init__(self, hostname, port=None, username=os.environ['USER']):
        self.hostname = hostname
        self.port = port
        self.username = username

    def run(self, args, cwd=None, terminal=False, bufzie=0, **kwargs):
        if isinstance(args, basestring):
            raise Exception('args should be a list not a string')

        if cwd:
            args = ['cd', cwd, ';'] + args

        cmdline = ['ssh',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'CheckHostIP=no',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'LogLevel=QUIET']

        if terminal:
            cmdline.append('-t')

        if self.port:
            cmdline.extend(['-p', str(self.port)])

        cmdline.extend([self.username + '@' + self.hostname])
        cmdline.extend(args)
        return subprocess.Popen(cmdline, **kwargs)

    def shell(self, args, **kwargs):
        if self.run(args, **kwargs).wait():
            raise Exception('command failed: ' + ' '.join(args))

    def sudo(args, **kwargs):
        self.shell('sudo bash -c \'' + ' '.join(args) + '\'', **kwargs) 

    def iter_lines(self, args, **kwargs):
        proc = self.run(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, **kwargs)
        for line in proc.stdout:
            yield line.rstrip()

    def eval(self, args, **kwargs):
        return '\n'.join(self.iter_lines(args, **kwargs))

    def rsync(self, local_dir, remote_dir, excludes=[]):
        args = ['rsync', '-e', 'ssh -C -o UserKnownHostsFile=/dev/null -o CheckHostIP=no -o StrictHostKeyChecking=no -o LogLevel=QUIET',
            '-r', '-a', local_dir, self.hostname + ':' + remote_dir]

        for dir in excludes:
            args.extend(['--exclude', dir])

        print ' '.join(args)
        if subprocess.call(args):
            raise Exception('rsync failed')

    def download(self, remote_path, local_path):
        args = ['scp', '-C']

        if self.port:
            args.extend(['-P', str(self.port)])

        args.append(self.username + '@' + self.hostname + ':' + remote_path)
        args.append(local_path)

        if subprocess.call(args):
            raise Exception('scp failed')

    def __repr__(self):
        if self.port:
            port_part = ':' + str(self.port)
        else:
            port_part = ''
        return 'RemoteShell(' + self.username + '@' + self.hostname + port_part + ')'

localhost = RemoteShell('localhost')
