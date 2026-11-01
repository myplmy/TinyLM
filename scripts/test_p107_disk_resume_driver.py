"""CPU-only contracts for the opt-in scheduled disk driver."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import diag_p107_disk_resume as driver


class DiskDriverTests(unittest.TestCase):
    def test_deadline_and_real_io_are_distinct_from_old_memory_diagnostic(self):
        self.assertEqual(driver.DEADLINE.isoformat(),'2026-11-01T06:00:00+00:00')
        self.assertEqual(driver.old.DEADLINE,driver.DEADLINE)
        self.assertIs(driver.old.resume,driver.resume)
        self.assertIn('runs/isolated/',str(driver.SNAPSHOT))

    def test_identity_covers_new_document_schedule_and_io_code(self):
        names=driver.old.identity()['files']
        for name in ['document_source.py','hybrid_session.py','boundary_store.py','anneal_schedule.py']:
            self.assertIn('tinylm/train/'+name,names)

    def test_wrong_action_refused_before_model_load(self):
        value=dict(schema=driver.SCHEMA,tag=driver.TAG,authority_directive=105,
            deadline=driver.DEADLINE.isoformat(),source=driver.old.identity(),
            output=str(driver.OUTPUT.relative_to(driver.ROOT)),snapshot=str(driver.SNAPSHOT.relative_to(driver.ROOT)),
            corpus_training=False)
        args=SimpleNamespace(profile='fixture',profile_sha256='x',mode='cost',max_wall_sec=900)
        with patch.object(driver.old.resource,'read_ref',return_value=value):
            with self.assertRaises(ValueError):driver.validate(args)

    def test_persistent_probe_preserves_bounded_vram_guard(self):
        watch=driver.old.VramWatch()
        self.assertEqual(watch.client.timeout,3.)
        self.assertIsNone(watch.reason)
        self.assertEqual(watch.client.close()['query_errors'],0)


if __name__=='__main__':unittest.main()
