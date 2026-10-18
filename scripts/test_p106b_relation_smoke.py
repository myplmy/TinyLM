import unittest
from unittest.mock import patch
from pathlib import Path
from scripts import p106b_relation_smoke as s


class ScopedSmokeTests(unittest.TestCase):
    def test_all_canonical_actions_retained(self):
        actions, proof = s.adapted_actions(s.DEFAULT_ROOT)
        self.assertEqual(len(actions), proof['canonical_actions'])
        self.assertEqual(proof['adaptations'], ['legacy_handoff_to_codex',
            'contract_reads_fresh_isolated_logs'])
        self.assertFalse(proof['prior_checkpoint_writes'])

    def test_no_legacy_checker_child(self):
        actions, _ = s.adapted_actions(s.DEFAULT_ROOT)
        for item in actions:
            if '--' in item.argv:
                child = item.argv[item.argv.index('--') + 1:]
                self.assertNotIn('scripts/check_handoff.py', child)

    def test_training_arguments_unchanged(self):
        before = s.smoke_module.parse_smoke_module()
        after, _ = s.adapted_actions(s.DEFAULT_ROOT)
        for a,b in zip(before, after):
            if 'run100m.py' in a.argv: self.assertEqual(a, b)

    def test_unsafe_root_rejected(self):
        for path in (s.ROOT, Path('/tmp/out'), s.ROOT/'test_result/evidence/local'):
            with self.assertRaises(ValueError): s.output_root(path)

    def test_changed_canonical_sites_rejected(self):
        with patch.object(s.smoke_module, 'parse_smoke_module', return_value=[]):
            with self.assertRaises(ValueError): s.adapted_actions(s.DEFAULT_ROOT)


if __name__ == '__main__': unittest.main()
