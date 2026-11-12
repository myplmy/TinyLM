"""Synthetic metadata tests: no actual restricted payload is accessed."""
from pathlib import Path
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import active_guard_v6_preflight_v1 as guard


class ExactGuard6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard.activate()
        cls.contract = guard.checked_contract()

    def context(self, ident='expanded_train:1', sha='A'*64):
        return dict(source_id=ident, original=dict(sha256=sha), candidate=dict(sha256=sha))

    def test_known_metadata_contract(self):
        self.assertEqual(len(self.contract['trusted_metadata']), 21)
        self.assertFalse(self.contract['actual_filter_metadata_hold']['body_admission_approved'])

    def test_original_id(self):
        with self.assertRaises(ValueError):
            guard.require_payload_context(self.context(guard.NEW_ID), self.contract)

    def test_parent_id_alias(self):
        with self.assertRaises(ValueError):
            guard.require_payload_context(self.context(guard.NEW_ALIAS), self.contract)

    def test_arbitrary_id_same_original_sha(self):
        sha = self.contract['actual_filter_metadata_hold']['original']['sha256']
        with self.assertRaises(ValueError):
            guard.require_payload_context(self.context(sha=sha), self.contract)

    def test_candidate_only_alias(self):
        row = self.context()
        row['candidate']['sha256'] = self.contract['actual_filter_metadata_hold']['original']['sha256']
        with self.assertRaises(ValueError):
            guard.require_payload_context(row, self.contract)

    def test_all_old_hashes_stay_restricted(self):
        for sha in self.contract['restricted_hashes']:
            with self.assertRaises(ValueError):
                guard.require_payload_context(self.context(sha=sha), self.contract)

    def test_normal_document(self):
        guard.require_payload_context(self.context(), self.contract)

    def test_no_payload_attempts(self):
        guard.assert_no_protected_opens()


if __name__ == '__main__':
    unittest.main()
