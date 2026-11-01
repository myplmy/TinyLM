"""Preflight for a new process replay; CPU metadata only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import diag_p107_process_resume as driver


class ProcessResumeTests(unittest.TestCase):
    def test_only_old_default_hook_changed(self):
        previous,report=driver.check_historical_contract()
        self.assertFalse(report['causal_kd'])
        self.assertEqual(report['resume_equivalence'],'EXACT')
        self.assertEqual(driver.base.resource.digest(driver.ARCHIVED_DEFAULT),
            previous['source']['files']['tinylm/train/adaptive_training.py'])

    def test_new_action_is_bounded_resume(self):
        self.assertIs(driver.base.resume,driver.resume)
        self.assertEqual(driver.DEADLINE.isoformat(),'2026-11-01T06:00:00+00:00')
        self.assertIn('process_resume',driver.TAG)

    def test_bad_contract_rejected_before_model(self):
        args=SimpleNamespace(profile='fixture',profile_sha256='x',mode='resume',max_wall_sec=300)
        with patch.object(driver.base.resource,'read_ref',return_value=dict(schema='bad')):
            with self.assertRaises(ValueError):driver.validate(args)


if __name__=='__main__':unittest.main()
