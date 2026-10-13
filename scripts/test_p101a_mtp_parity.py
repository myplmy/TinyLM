"""Small CPU weights only; actual checkpoint/GPU parity remains user-owned."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from scripts import diag_p101a_mtp_parity as gate
from scripts.test_p101a_sft_mtp import tiny,Tokens

class ParityTests(unittest.TestCase):
    def test_difference_including_prefix_length(self):
        self.assertIsNone(gate.first_difference([1,2],[1,2]))
        self.assertEqual(gate.first_difference([1,2],[1,3]),1)
        self.assertEqual(gate.first_difference([1],[1,2]),1)
    def test_actual_decode_ids_are_captured_without_reencoding(self):
        tok=gate.CaptureTokens(Tokens());tok.decode([5,6,7])
        self.assertEqual(tok.decoded_ids,[5,6,7])
    def test_same_prefix_paths_and_kv_are_compared(self):
        model,cfg=tiny(True);model.eval()
        with torch.no_grad():
            trace=gate.shadow(model,[1,2],[3,4,5,6],2,'cpu')
        self.assertEqual(trace['same_history_tokens'],4)
        self.assertEqual(trace['pending_query_tokens'],1)
        self.assertEqual(trace['multi_query_tokens'],3)
        self.assertTrue(trace['incremental_vs_multi']['argmax_equal'])
        self.assertTrue(trace['incremental_vs_rebuild']['argmax_equal'])
        self.assertTrue(trace['kv_max_abs_by_owner'])

    def test_shadow_uses_actual_prediction_block(self):
        model,cfg=tiny(True);model.eval()
        for k in (2,4):
            with torch.no_grad():
                trace=gate.shadow(model,[1,2],[3,4,5,6,7,8],2,'cpu',k)
            self.assertEqual(trace['multi_query_tokens'],k)

    def test_profile_label_is_bound_to_row_not_completed_loop(self):
        source=Path(gate.__file__).read_text()
        self.assertIn("total_prediction_tokens=row['k']",source)
        self.assertNotIn('total_prediction_tokens=k,profile=row',source)

if __name__=='__main__':unittest.main(verbosity=2)
