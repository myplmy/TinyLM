import unittest
from datetime import datetime, timezone
from scripts import diag_p101a_padding_muon as new
from scripts import diag_p101a_padding_gpu as old
from scripts import diag_p102a_head_muon_trace as trace


class PaddingMuonContracts(unittest.TestCase):
    def test_only_exact_two_policies(self):
        self.assertEqual(tuple(new.validate_policy(x) for x in old.POLICIES),('fixed1024','crop128'))
        for policy in ('crop32','streaming','fixed512',None):
            with self.assertRaises(ValueError):new.validate_policy(policy)

    def test_authority_is_new_and_old_unmodified(self):
        self.assertEqual(new.DEADLINE,datetime(2026,11,13,8,tzinfo=timezone.utc))
        self.assertEqual(old.HARD_STOP,datetime(2026,10,23,7,30,tzinfo=timezone.utc))

    def test_existing_ns_trace_primitives_are_reused(self):
        self.assertIn('PostClipCapture',new.capture_arm.__code__.co_names)
        self.assertIn('private_muon_step',new.capture_arm.__code__.co_names)
        self.assertIn('one_update',new.capture_arm.__code__.co_names)
        self.assertIn('replay_all',new.run.__code__.co_names)
        self.assertNotIn('run_arm',new.run.__code__.co_names)

    def test_original_tolerances_are_not_relaxed(self):
        t=old.literal_tolerances()
        self.assertEqual(t['gradients_and_update'],dict(atol=2e-6,rtol=1e-5))

    def test_phase_budget_rejects_elapsed_time(self):
        b=new.Budget(seconds=-1)
        with self.assertRaises(TimeoutError):b.check('fixture')


if __name__=='__main__':unittest.main()
