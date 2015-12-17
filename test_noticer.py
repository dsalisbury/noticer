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

import queue
import signal
import subprocess
import threading
import unittest
from unittest.mock import MagicMock, patch

from noticer import task_loop, runner, STOP, RELOAD, RED, GREEN, RESET


def enqueue(*things):
    tasks = queue.PriorityQueue()
    for i, thing in enumerate(things):
        tasks.put((i, thing))
    return tasks


def make_popen_mock(returncode=0):
    mock = MagicMock(spec=subprocess.Popen)
    mock.return_value.returncode = returncode
    return mock


@patch('noticer.time.sleep')
@patch('noticer.subprocess.Popen', new_callable=make_popen_mock)
class TaskLoopTests(unittest.TestCase):
    def test_execution(self, popen, sleep):
        test_cmd = 'run_my_thing.sh'
        task_loop(enqueue(STOP), test_cmd)
        popen.assert_called_with(test_cmd)

    def test_reload(self, popen, sleep):
        task_loop(enqueue(RELOAD, RELOAD, RELOAD, STOP), 'gogo')
        self.assertEqual(popen.call_count, 4)

    def test_short_running_doesnt_get_signal(self, popen, sleep):
        proc = popen.return_value
        proc.poll.return_value = 0
        task_loop(enqueue(RELOAD, STOP), 'gogo')
        popen.return_value.send_signal.assert_not_called()

    def test_long_running_but_quick_stopping(self, popen, sleep):
        proc = popen.return_value
        proc.poll.return_value = None
        proc.wait.return_value = 0
        task_loop(enqueue(STOP), 'gogo')
        proc.send_signal.assert_called_with(signal.SIGINT)
        self.assertEqual(popen.return_value.send_signal.call_count, 1)

    def test_long_running_slow_stopping(self, popen, sleep):
        proc = popen.return_value
        proc.poll.return_value = None
        proc.wait.side_effect = [
            subprocess.TimeoutExpired('gogo', 2), lambda *_: True]
        task_loop(enqueue(STOP), 'gogo')
        self.assertTrue(proc.kill.called)

    def test_not_crash_when_popen_fails(self, popen, sleep):
        proc = popen.return_value
        rte = RuntimeError('Bang!')
        popen.side_effect = [rte, proc, rte, rte, proc]
        task_loop(enqueue(RELOAD, RELOAD, RELOAD, RELOAD, STOP), 'gogo')
        self.assertEqual(popen.call_count, 5)

    def test_not_crash_when_given_junk_task(self, popen, sleep):
        messages = []
        task_loop(enqueue('ping', 'pong', STOP), 'gogo', log=messages.append)
        self.assertIn("Bogus task: 'ping'", messages)
        self.assertIn("Bogus task: 'pong'", messages)


@patch('noticer.time.sleep')
@patch('noticer.subprocess.Popen', new_callable=make_popen_mock)
class RunnerTests(unittest.TestCase):
    def _thing(self, popen, returncode):
        proc = popen.return_value
        proc.poll.return_value = True  # command completed
        proc.returncode = returncode
        stop = threading.Event()
        lines = []
        runner('gogo', stop_event=stop, log=lines.append)
        return lines

    def test_failing_short_command(self, popen, sleep):
        out = self._thing(popen=popen, returncode=1)
        self.assertEqual(out[-1], RED + 'COMMAND FAILED' + RESET)

    def test_successful_short_command(self, popen, sleep):
        out = self._thing(popen=popen, returncode=0)
        self.assertEqual(out[-1], GREEN + 'COMMAND SUCCEEDED' + RESET)

    def test_long_command_no_status_output(self, popen, sleep):
        proc = popen.return_value
        proc.returncode = 1  # FIXME: what's the real exit code for a SIGKILL?
        proc.poll.return_value = False  # command not completed
        proc.wait.side_effect = [
            subprocess.TimeoutExpired('gogo', 2), lambda *_: True]
        log_mock = MagicMock()
        stop = threading.Event()
        stop.set()
        runner('gogo', stop_event=stop, log=log_mock)
        self.assertEqual(log_mock.call_count, 4)
