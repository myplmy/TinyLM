"""Verify actual owned child exit/reaping without corpus or model execution."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_versioned_guarded_cache_v2 import owned_stop, write_new


class OwnedWorkerTests(unittest.TestCase):
    def test_completed_child_keeps_observed_exit_code(self):
        process = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'raise SystemExit(7)'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.assertEqual(process.wait(timeout=5), 7)
        self.assertEqual(owned_stop(process), 7)

    def test_live_owned_group_is_terminated_and_reaped(self):
        process = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time; time.sleep(20)'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.assertLess(owned_stop(process), 0)
        self.assertIsNotNone(process.returncode)

    def test_receipt_never_overwrites_existing_evidence(self):
        directory = Path(tempfile.mkdtemp(prefix='hold_owned_worker_fixture_'))
        path = directory/'receipt.json'
        write_new(path, {'status': 'fixture'})
        with self.assertRaises(FileExistsError): write_new(path, {'status': 'changed'})
        self.assertEqual(json.loads(path.read_text()), {'status': 'fixture'})


if __name__ == '__main__': unittest.main(verbosity=2)
