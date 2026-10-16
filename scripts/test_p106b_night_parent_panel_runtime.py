"""Pure namespace, selection and strict scope tests, no actual HF/model IO."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_parent_panel as d


class PanelRuntimeTests(unittest.TestCase):
    def test_namespace_not_old_completion(self):
        self.assertNotEqual(d.EVIDENCE, d.e.EVIDENCE)
        self.assertNotEqual(d.FROZEN, d.e.FROZEN)
        self.assertEqual(len(d.TRAINED), 4)
        self.assertEqual(len(d.BARE), 2)
        self.assertEqual(d.LANES, ('natural', 'public_mc', 'native32', 'native256'))

    def test_unknown_bare_rejected_without_source_access(self):
        with self.assertRaises(ValueError): d.expected_checkpoint('base_qa')

    def test_selection_rejects_incomplete_english_before_writing(self):
        natural = [dict(root=language + str(i), language=language) for language in ('ko', 'en') for i in range(40)]
        with self.assertRaises(ValueError): d.selection(dict(natural=natural, public=[]))

    def test_info_explicit_noncompletion(self):
        with patch.object(d.qa.data, 'digest', return_value='A' * 64), patch.object(d.e, 'info', return_value=dict(original_input_report_sha256='B' * 64)):
            r = d.info()
        self.assertFalse(r['old_six_endpoint_complete'])
        self.assertTrue(r['old_downstream_prerequisites_unchanged'])
        self.assertEqual(r['max_new_natural'], 128)
        self.assertEqual(r['updates'], 0)
        self.assertEqual(r['checkpoints_written'], 0)
        self.assertEqual(r['precision_by_lane']['native32'], 'CUDA_BF16_AUTOCAST_EXISTING_HELPER')
        self.assertEqual(r['precision_by_lane']['native256'], 'FP32_MATH')

    def test_no_old_report_written_or_training_called(self):
        source = (ROOT / 'scripts/diag_p106b_night_parent_panel.py').read_text()
        self.assertNotIn("qa.write(e.EVIDENCE", source)
        self.assertNotIn("optimizer.step(", source)
        self.assertNotIn("torch.save(", source)


if __name__ == '__main__': unittest.main()
