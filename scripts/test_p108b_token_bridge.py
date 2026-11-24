"""Token CE is separated from termination, without model loading."""
import unittest
import torch
from scripts import diag_p108b_token_bridge as d


class TokenBridgeTests(unittest.TestCase):
    def test_answer_and_eot_scores_are_separate_and_first_rank_is_exact(self):
        logits=torch.zeros(3,8);logits[0,1]=2;logits[0,3]=3;logits[1,2]=1;logits[2,4]=4
        result=d.token_statistics(logits,torch.tensor([1,2,4]))
        self.assertEqual(result['first_gold_rank'],2);self.assertEqual(result['first_top_id'],3)
        self.assertEqual(result['answer_token_count'],2)
        self.assertAlmostEqual(result['mean_ce'],(2*result['answer_ce']+result['eot_ce'])/3)
        self.assertGreater(result['eot_probability_after_gold'],.8)

    def test_missing_or_wrong_eot_contract_is_rejected(self):
        with self.assertRaises(ValueError):d.token_statistics(torch.zeros(1,8),torch.tensor([4]))
        with self.assertRaises(ValueError):d.token_statistics(torch.zeros(2,8),torch.tensor([1,2]))


if __name__=='__main__':unittest.main()
