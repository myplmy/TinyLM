"""독립 driver의 자원 감시·서명·종결 검증. 모델·GPU·외부 명령은 실행하지 않는다."""
from pathlib import Path
import signal
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from scripts import diag_p107_adaptive_training as driver


class DriverTests(unittest.TestCase):
    def test_hash_includes_tensor_bits_and_dtype(self):
        first={'a':torch.tensor([1.,2.]),'b':[1,'two']}
        self.assertEqual(driver.tree_sha(first),driver.tree_sha({'b':[1,'two'],'a':first['a'].clone()}))
        other={'a':first['a'].double(),'b':first['b']}
        self.assertNotEqual(driver.tree_sha(first),driver.tree_sha(other))

    def test_lower_allocator_cap_leaves_non_torch_headroom(self):
        self.assertLess(driver.ALLOCATOR_CAP+1_500_000_000,driver.LIMIT)

    def test_vram_query_must_be_single_gpu(self):
        with patch.object(driver.subprocess,'check_output',return_value='100\n200\n'):
            with self.assertRaises(ValueError):driver.VramWatch.used()

    def test_vram_guard_stops_own_pid_only(self):
        watch=driver.VramWatch();watch.proof['baseline_used_bytes']=100
        watch.stop_event=Mock();watch.stop_event.wait.return_value=False
        with patch.object(watch,'used',return_value=driver.LIMIT+101), \
                patch.object(driver.os,'kill') as kill:
            watch.run()
            kill.assert_called_once_with(driver.os.getpid(),signal.SIGTERM)
        self.assertIn('8GB',watch.reason)

    def test_three_bounded_query_failures_stop_worker(self):
        watch=driver.VramWatch();watch.proof['baseline_used_bytes']=100
        watch.stop_event=Mock();watch.stop_event.wait.return_value=False
        with patch.object(watch,'used',side_effect=TimeoutError('fixture query timeout')), \
                patch.object(driver.os,'kill') as kill:
            watch.run()
        self.assertEqual(3,watch.proof['query_errors'])
        self.assertEqual(1,kill.call_count)

    def test_guard_ends_without_signal_when_stopped(self):
        watch=driver.VramWatch();watch.stop_event.set()
        with patch.object(driver.os,'kill') as kill:watch.run()
        kill.assert_not_called()


if __name__=='__main__':
    unittest.main(verbosity=2)
