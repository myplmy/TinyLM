"""Ensure automatic rule work never invents individual human reading credit."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from record_hold_stages_v6 import reconcile


class StageSeparationTests(unittest.TestCase):
    def counts(self,**changes):
        args=dict(human={'A':3,'B':4},rule={'B':4,'C':5},root_ids={'A','C'},
            official_hold=96,expected_hold=92,initial=100,prior_hold=2,initial_unique=20)
        args.update(changes);return reconcile(**args)

    def test_rule_does_not_inflate_human_full_read(self):
        x=self.counts();self.assertEqual((x['fresh_first_review_unique'],x['fresh_first_review_positions']),(2,7))

    def test_overlap_counted_once(self):
        x=self.counts();self.assertEqual(x['processed_by_human_or_approved_rule_positions'],12)

    def test_rule_only_reading_is_explicit(self):
        x=self.counts();self.assertEqual(x['rule_processed_without_individual_human_full_read_unique'],1)
        self.assertEqual(x['rule_processed_without_individual_human_full_read_positions'],5)

    def test_official_cache_partition_still_closes(self):
        x=self.counts();self.assertEqual(sum(x['official_stage_partition'].values()),96)
        self.assertEqual(x['official_stage_partition']['ROOT_admitted_cache_pending'],4)

    def test_unread_is_distinct_from_unprocessed(self):
        x=self.counts();self.assertEqual(x['still_first_unreviewed_positions'],91)
        self.assertEqual(x['unprocessed_by_both_positions'],86)

    def test_conflicting_multiplicity_rejected(self):
        with self.assertRaises(AssertionError):self.counts(rule={'B':9,'C':5})

    def test_admission_without_any_processing_rejected(self):
        with self.assertRaises(AssertionError):self.counts(root_ids={'A','Z'})

    def test_cache_ahead_of_selection_rejected(self):
        with self.assertRaises(AssertionError):self.counts(official_hold=90)

    def test_wrong_root_denominator_rejected(self):
        with self.assertRaises(AssertionError):self.counts(expected_hold=93)

    def test_negative_source_weight_rejected(self):
        with self.assertRaises(AssertionError):self.counts(rule={'B':4,'C':-5})


if __name__=='__main__':unittest.main()
