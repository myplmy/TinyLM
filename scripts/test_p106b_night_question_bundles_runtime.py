"""Pure source/runtime publication contracts; no real assets or model loading."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_night_question_bundles as d
from scripts.test_p106b_night_question_bundles import distinct,events


class RuntimeTests(unittest.TestCase):
    def test_fixed_ten_labels_no_bare64_or_legacy_completion(self):
        self.assertEqual(len(d.labels()),10);self.assertEqual(len(set(d.labels())),10)
        self.assertFalse(any('base_parent' in x or 'foundation_native' in x for x in d.labels()))
        with patch.object(d.qa.data,'digest',return_value='A'*64):r=d.info()
        self.assertFalse(r['model_loaded']);self.assertFalse(r['new_logits']);self.assertFalse(r['old_bare_full512_gate_credited'])
        self.assertTrue(r['grouping_rule_chosen_after_initial_results'])

    def test_source_metadata_omits_all_individual_alias_records(self):
        r=d.method.census(distinct());small=d.source_summary(r)
        self.assertNotIn('bundles',small);self.assertEqual(small['bundle_set_sha256'],r['bundle_set_sha256'])
        self.assertEqual(small['counts'],r['counts'])

    def test_compact_result_is_bound_to_full_source(self):
        cases=distinct();r=d.method.summarize(events(cases),cases);source=d.method.census(cases)
        small=d.compact_result(r,source);self.assertNotIn('source_census',small)
        self.assertEqual(small['overall'],r['overall'])
        with self.assertRaises(ValueError):d.compact_result(dict(r,source_census={}),source)
        with self.assertRaises(ValueError):d.compact_result(dict(r,source_census_sha256='B'*64),source)

    def test_no_optimizer_model_loading_or_source_revision(self):
        text=(ROOT/'scripts/diag_p106b_night_question_bundles.py').read_text()
        for forbidden in ('load_model(', 'optimizer.step(', 'torch.save(', 'original.prepare(', 'probe.readback('):
            self.assertNotIn(forbidden,text)
        self.assertNotIn('qa.write(original.CORPUS',text)


if __name__=='__main__':unittest.main()
