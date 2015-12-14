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
import unittest
from unittest.mock import patch

from noticer import runner, STOP, RELOAD


def enqueue(*things):
    tasks = queue.PriorityQueue()
    for i, thing in enumerate(things):
        tasks.put((i, thing))
    return tasks


@patch('subprocess.Popen', autospec=True)
class RunnerTests(unittest.TestCase):
    def test_execution(self, popen):
        test_cmd = 'run_my_thing.sh'
        runner(enqueue(STOP), test_cmd)
        popen.assert_called_with(test_cmd)

    def test_reload(self, popen):
        runner(enqueue(RELOAD, RELOAD, RELOAD, STOP), 'gogo')
        self.assertEqual(popen.call_count, 4)

    def test_short_running_doesnt_get_signal(self, popen):
        proc = popen.return_value
        proc.poll.return_value = True
        runner(enqueue(RELOAD, STOP), 'gogo')
        popen.return_value.send_signal.assert_not_called()

    def test_long_running_but_quick_stopping(self, popen):
        proc = popen.return_value
        proc.poll.return_value = False
        proc.wait.return_value = True
        runner(enqueue(STOP), 'gogo')
        proc.send_signal.assert_called_with(signal.SIGINT)
        self.assertEqual(popen.return_value.send_signal.call_count, 1)

    def test_long_running_slow_stopping(self, popen):
        proc = popen.return_value
        proc.poll.return_value = False
        proc.wait.side_effect = [
            subprocess.TimeoutExpired('gogo', 2), lambda *_: True]
        runner(enqueue(STOP), 'gogo')
        self.assertTrue(proc.kill.called)
