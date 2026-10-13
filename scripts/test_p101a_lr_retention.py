"""CPU-only exposure and optimizer scale contracts; no model weights opened."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p101a_lr_retention as gate

class LRTests(unittest.TestCase):
    def test_both_optimizers_scale_with_constant_rms4_ratio(self):
        optimizers=(SimpleNamespace(param_groups=[{'lr':1e-4}]),
                    SimpleNamespace(param_groups=[{'lr':4e-4}]))
        result=gate.scale_optimizers(lambda model:optimizers,None,.1)
        self.assertAlmostEqual(result[0].param_groups[0]['lr'],1e-5)
        self.assertAlmostEqual(result[1].param_groups[0]['lr'],4e-5)
    def test_default_four_pass_and_explicit_one_pass_use_same_counts(self):
        import inspect
        text=inspect.getsource(gate.prior.train_arm)
        self.assertIn('epochs=4',text)
        self.assertIn('expected_steps=epochs*math.ceil',text)
        self.assertIn('processed!=epochs*report',text)
        self.assertIn('range(epochs)',text)
    def test_frozen_source_is_not_the_new_evidence_namespace(self):
        for tag in gate.TAGS.values():
            self.assertNotEqual(tag,gate.SOURCE_TAG)
        self.assertEqual(len(gate.SOURCE_SHA),64)

if __name__=='__main__':unittest.main(verbosity=2)
