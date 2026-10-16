"""Pure fixed-scope/reference identity tests; no actual HF/model reads."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_reference_extension as d


class ExtensionTests(unittest.TestCase):
    def test_exact_new_labels_and_no_old_completion_credit(self):
        with patch.object(d.qa.data, 'digest', return_value='A' * 64): r = d.info()
        self.assertEqual(len(r['labels']), 4); self.assertFalse(r['new_logits'])
        self.assertFalse(r['model_loaded']); self.assertTrue(r['old17_unavailable_are_not_completed'])
        self.assertTrue(r['natural64_not_natural512']); self.assertEqual(r['updates'], 0)

    def test_same_checkpoint_two_labels_is_one_group(self):
        reports = {label:dict(checkpoint_sha256='A' * 64) for label in d.LABELS}
        self.assertEqual(len(d.grouped_checkpoints(reports)), 1)
        self.assertEqual(len(d.grouped_checkpoints(reports)['A' * 64]), 4)

    def test_missing_or_extra_label_and_missing_checkpoint_hash_rejected(self):
        reports = {label:dict(checkpoint_sha256='A' * 64) for label in d.LABELS}
        reports.pop(d.LABELS[0])
        with self.assertRaises(ValueError): d.grouped_checkpoints(reports)
        reports[d.LABELS[0]] = {}
        with self.assertRaises(ValueError): d.grouped_checkpoints(reports)

    def test_bare_checkpoint_path_and_source_body_are_exact(self):
        cp = ROOT / 'runs/ckpt/synthetic.pt'; sha = 'A' * 64
        r = dict(status='BOUNDED_PARENT_EVAL_COMPLETE', endpoint='base_parent', code_sha256={},
            body_unchanged=True, initial_core_sha256=sha, checkpoint=str(cp.relative_to(ROOT)),
            checkpoint_sha256=sha, input_report_sha256=sha,
            directory=str((d.panel.LOCAL / 'base_parent').relative_to(ROOT)),
            outputs=dict.fromkeys(d.panel.LANES), receipt_sha256=dict.fromkeys(d.panel.LANES))
        with patch.object(d.panel, 'info', return_value=dict(code_sha256={})):
            d.bare_contract(r, 'base_parent', cp, sha, sha, sha)
            for key, value in [('checkpoint', 'runs/ckpt/wrong.pt'), ('body_unchanged', False),
                               ('input_report_sha256', 'B' * 64), ('outputs', {})]:
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.bare_contract(dict(r, **{key:value}), 'base_parent', cp, sha, sha, sha)

    def test_no_new_model_or_legacy_report_writes(self):
        source = (ROOT / 'scripts/diag_p106b_night_reference_extension.py').read_text()
        for expression in ('load_model(', 'optimizer.step(', 'torch.save(', 'reference.run(', 'panel.readback('):
            self.assertNotIn(expression, source)
        self.assertNotIn('qa.write(reference.EVIDENCE', source)


if __name__ == '__main__': unittest.main()
