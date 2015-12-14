import queue
import unittest
from unittest.mock import patch

from noticer import runner, STOP, RELOAD


@patch('subprocess.Popen', autospec=True)
class RunnerTests(unittest.TestCase):
    def test_execution(self, popen):
        test_cmd = 'run_my_thing.sh'
        tasks = queue.PriorityQueue()
        tasks.put((0, STOP))
        runner(tasks, test_cmd)
        popen.assert_called_with(test_cmd)

    def test_reload(self, popen):
        tasks = queue.PriorityQueue()
        tasks.put((0, RELOAD))
        tasks.put((0, RELOAD))
        tasks.put((0, RELOAD))
        tasks.put((1, STOP))  # lower priority than the RELOADs
        runner(tasks, 'gogo')
        self.assertEqual(popen.call_count, 4)
