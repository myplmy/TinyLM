"""No model/assets: synthetic label declaration, CPU budget and RNG state tests."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import torch
from scripts import diag_p107_adaptive_masking as d

torch.set_num_threads(1)


class DriverContract(unittest.TestCase):
    def test_fixture_is_explicit_synthetic_groups_and_only_trailing_pad(self):
        tokens,docs,groups=d.fixture(32768,1)
        self.assertEqual(tokens.shape,(8,1025));self.assertEqual(set(groups),{'all','fixture_ko_label','fixture_en_label','fixture_digit_label','fixture_rare_label'})
        self.assertTrue(bool((docs[0,-17:]==-1).all()));self.assertTrue(bool((tokens[docs>=0]>=35).all()))

    def test_invalid_profile_is_rejected_before_reference_read(self):
        with patch.object(d.resource,'digest',side_effect=AssertionError('no asset')):
            with self.assertRaises(ValueError):d.validate({'schema':'WRONG'},SimpleNamespace(max_wall_sec=300))

    def test_fake_predictions_are_not_labeled_model_accuracy(self):
        tokens,docs,_=d.fixture(32768,1)
        selected=d.h.uniform_mntp_selection(tokens,docs,vocab_size=32768,probability=.15,generator=torch.Generator().manual_seed(3))
        batch=d.h.mntp_batch(tokens,docs,selected,vocab_size=32768)
        pred=d.synthetic_predictions(batch)
        valid=batch.targets!=-100
        self.assertTrue(torch.equal(pred[valid]==batch.targets[valid],batch.targets[valid]%3==0))


if __name__=='__main__':unittest.main()
