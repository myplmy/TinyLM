"""CPU fixtures only; no model, tokenizer, or dataset."""
import unittest
import sys
from pathlib import Path
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import torch
from scripts.diag_p102a_muon_sensitivity import trace_pair, synthetic_report, main


class SensitivityTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_identical_and_no_input_mutation(self):
        g = torch.tensor([[.4, -.3], [.2, .1]])
        original = g.clone()
        result = trace_pair(g, g)
        self.assertTrue(torch.equal(g, original))
        for field in ('input_gradient', 'ns_input', 'bf16_input', 'ns_output',
                      'momentum_buffer', 'updated_weight', 'linear_sgd_control'):
            self.assertTrue(result[field]['close'], field)

    def test_rounding_boundary_is_not_causal_proof(self):
        with patch('torch.cuda._lazy_init', side_effect=AssertionError('CUDA forbidden')):
            result = synthetic_report()
        case = result['cases']['bf16_boundary']
        self.assertTrue(case['input_gradient']['close'])
        self.assertFalse(case['bf16_input']['close'])
        self.assertFalse(case['ns_output']['close'])
        self.assertTrue(case['linear_sgd_control']['close'])
        self.assertFalse(result['actual_tinylm_cause_proven'])
        self.assertEqual(result['model_calls'], 0)

    def test_rng_and_default_optimizer_unchanged(self):
        from tinylm.train.muon import _newton_schulz
        rng = torch.get_rng_state().clone()
        synthetic_report()
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))
        from tinylm.train.muon import _newton_schulz as after
        self.assertIs(after, _newton_schulz)

    def test_reject_bad_inputs(self):
        g = torch.zeros(2, 3)
        for bad in (torch.zeros(2, 2), torch.zeros(2, 3, dtype=torch.float64),
                    torch.full((2, 3), float('nan'))):
            with self.assertRaises(ValueError):
                trace_pair(g, bad)
        with self.assertRaises(ValueError):
            trace_pair(g, g, lr=-1)

    def test_cli_does_not_offer_model_or_gpu_flags(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as exit:
            main(['--device', 'cuda'])
        self.assertEqual(exit.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
