import queue
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
