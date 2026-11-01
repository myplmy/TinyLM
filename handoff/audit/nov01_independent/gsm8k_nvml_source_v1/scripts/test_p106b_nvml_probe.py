"""NVML IPC의 CPU fixture 검사. 실제 GPU/NVML library를 열지 않는다."""
import json
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from scripts.p106b_nvml_probe import NvmlClient


def command(body):
    ready = json.dumps(dict(ready=True, backend='PERSISTENT_NVML_C_API'))
    return [sys.executable, '-B', '-u', '-c', 'import sys,json,time;print(' + repr(ready) + ',flush=True)' + chr(10) + body]


class ProbeContract(unittest.TestCase):
    def test_process_reused_and_closed(self):
        program = 'for line in sys.stdin:' + chr(10) + ' if line.strip()=="quit":break' + chr(10) + ' print(json.dumps(dict(used_bytes=5,reserved_bytes=3,free_bytes=12,total_bytes=20)),flush=True)'
        client = NvmlClient(command=command(program))
        self.addCleanup(client.close)
        self.assertEqual(client.memory()['used_bytes'], 5)
        self.assertEqual(client.memory()['reserved_bytes'], 3)
        self.assertEqual(client.memory()['used_bytes'], 5)
        self.assertEqual(client.stats['launches'], 1)
        self.assertTrue(client.close()['closed'])
        self.assertIsNone(client.process)

    def test_timeout_kills_only_owned_helper(self):
        client = NvmlClient(timeout=.1, command=command('time.sleep(10)'))
        self.addCleanup(client.close)
        started = time.monotonic()
        with self.assertRaises(TimeoutError): client.memory()
        self.assertLess(time.monotonic()-started, 1)
        self.assertIsNone(client.process)
        self.assertEqual(client.stats['query_errors'], 1)
        self.assertEqual(client.pending, [])

    def test_timeout_respects_existing_three_second_cap(self):
        for timeout in [0, -1, 4]:
            with self.subTest(timeout=timeout), self.assertRaises(ValueError): NvmlClient(timeout=timeout)

    def test_bad_handshake_rejected(self):
        client = NvmlClient(command=[sys.executable,'-u','-c','print("{}",flush=True)'])
        self.addCleanup(client.close)
        with self.assertRaises(ValueError): client.memory()
        self.assertIsNone(client.process)

    def test_malformed_or_out_of_range_memory_rejected(self):
        for payload in [{}, dict(used_bytes=30,reserved_bytes=0,free_bytes=1,total_bytes=20),
                        dict(used_bytes=True,reserved_bytes=0,free_bytes=1,total_bytes=20),
                        dict(used_bytes=5,reserved_bytes=21,free_bytes=1,total_bytes=20)]:
            body = 'for line in sys.stdin:' + chr(10) + ' print(' + repr(json.dumps(payload)) + ',flush=True)'
            client = NvmlClient(command=command(body))
            with self.subTest(payload=payload), self.assertRaises(ValueError): client.memory()
            client.close()
            self.assertIsNone(client.process)

    def test_early_eof_rejected(self):
        client = NvmlClient(command=command('pass'))
        self.addCleanup(client.close)
        with self.assertRaises((RuntimeError, BrokenPipeError)): client.memory()

    def test_closed_client_cannot_restart(self):
        client = NvmlClient(command=command('pass'))
        client.close()
        with self.assertRaises(RuntimeError): client.memory()
        self.assertEqual(client.stats['launches'], 0)

    def test_original_three_consecutive_failure_policy_is_inherited(self):
        from scripts.p106b_nvml_probe import watcher_class
        from scripts.diag_p107_adaptive_training import VramWatch
        cls = watcher_class()
        self.assertIs(cls.run, VramWatch.run)
        watcher = cls()
        watcher.proof['baseline_used_bytes'] = 0
        watcher.stop_event = SimpleNamespace(wait=lambda _:False)
        watcher.client = SimpleNamespace(memory=lambda:(_ for _ in ()).throw(TimeoutError('fixture')))
        with patch('scripts.diag_p107_adaptive_training.os.kill') as kill:
            watcher.run()
        self.assertEqual(watcher.proof['query_errors'], 3)
        kill.assert_called_once()
        self.assertIsNotNone(watcher.reason)


if __name__ == '__main__':
    unittest.main()
