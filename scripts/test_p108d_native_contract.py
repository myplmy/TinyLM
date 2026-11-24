"""Guard the native head-window shape that caused the preserved v1 failure."""
import unittest
import torch
from scripts.diag_p108d_winner import canonical_head_logits


class NativeWindowContracts(unittest.TestCase):
    def test_prompt_positions_never_reach_the_head(self):
        class Recorder:
            def _head_logits(self,hidden):
                self.seen=hidden.clone()
                return hidden.sum(-1,keepdim=True)
        model=Recorder()
        hidden=torch.arange(24,dtype=torch.float32).reshape(1,6,4)
        observed=canonical_head_logits(model,hidden,3,3)
        self.assertEqual(tuple(model.seen.shape),(1,3,4))
        torch.testing.assert_close(observed,hidden[:,3:].sum(-1,keepdim=True),rtol=0,atol=0)

    def test_truncated_suffix_is_rejected(self):
        with self.assertRaises(ValueError):
            canonical_head_logits(object(),torch.zeros(1,6,4),3,2)


if __name__=="__main__":unittest.main()
