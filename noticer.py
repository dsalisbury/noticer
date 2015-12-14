#!/usr/bin/env python

# Copyright (c) 2015 David Salisbury
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import subprocess
import pyinotify
import sys
import queue
import threading
import signal
import argparse
from functools import partial

# Sentinels to signal that we need to restart the process or abort altogether
RELOAD = object()
STOP = object()

log_err = partial(print, file=sys.stderr)


class EventHandler(pyinotify.ProcessEvent):
    def my_init(self, directory, extensions, task_queue):
        self.directory = directory
        self.extensions = extensions
        self.task_queue = task_queue

    def generic_processor(self, event):
        for ext in self.extensions:
            if event.pathname.endswith(ext):
                print('Handling {!r}'.format(event))
                self.task_queue.put((100, RELOAD))
                break

    process_IN_MODIFY = generic_processor
    process_IN_CREATE = generic_processor


def runner(tasks, command, log=log_err):
    while True:
        log('Starting')
        proc = subprocess.Popen(command)
        _, task = tasks.get()
        if task is STOP or task is RELOAD:
            log('Stopping')
            # No point signalling a stopped process
            if not proc.poll():
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(5)

            if task is STOP:
                break
        else:
            log('Bogus task: {!r}'.format(task))


def watcher(directory, extensions, command, log=log_err):
    task_queue = queue.PriorityQueue()
    run_thread = threading.Thread(
        target=runner, kwargs={'tasks': task_queue, 'command': command})
    run_thread.start()

    # Plumbing between inotify and worker thread's task queue
    handler = EventHandler(
        directory=directory, extensions=extensions, task_queue=task_queue)

    manager = pyinotify.WatchManager()
    manager.add_watch(directory, pyinotify.ALL_EVENTS, rec=True, auto_add=True)
    notifier = pyinotify.Notifier(manager, default_proc_fun=handler)
    try:
        notifier.loop()
    except KeyboardInterrupt:
        log('Stopping normally')
    finally:
        task_queue.put((0, STOP))
    log('Waiting on runner to stop')
    run_thread.join()


def _parse_args(arg_list):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d', '--directory', dest='directory', help='Directory to monitor',
        default='.')
    parser.add_argument(
        '-e', '--extension', dest='extensions', help='Extensions to monitor',
        nargs='*')
    parser.add_argument('command')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    return parser.parse_args(arg_list)


def _main():
    args = _parse_args(sys.argv[1:])
    command = [args.command] + args.args
    watcher(args.directory, args.extensions, command)


if __name__ == '__main__':
    _main()
