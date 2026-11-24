"""Raw probability contracts; tests open no socket and load no model."""
import copy
import math
import unittest

from scripts.p106b_prism_http import (PrismHTTP,ProtocolHold,completion_request,
    completion_probabilities,full_distribution,compare_forced_to_full)


def example_reply():
    return dict(tokens_predicted=1,truncated=False,completion_probabilities=[dict(
        id=2,logprob=math.log(.6),top_logprobs=[dict(id=i,logprob=math.log(p)) for i,p in ((2,.6),(0,.3),(1,.1))])])


class PrismProbabilityContracts(unittest.TestCase):
    def test_nonlocal_proxy_or_redirect_target_is_not_an_endpoint(self):
        for base in ('https://127.0.0.1:8080','http://localhost:8080','http://example.com:8080',
                     'http://user@127.0.0.1:8080','http://127.0.0.1:8080/remote'):
            with self.subTest(base=base),self.assertRaises(ProtocolHold):PrismHTTP(base)

    def test_forcing_preserves_explicit_raw_and_uncached_contract(self):
        request=completion_request([4,5],forced_token=7)
        self.assertEqual(request['logit_bias'],[[7,1_000_000.]])
        self.assertFalse(request['post_sampling_probs'])
        self.assertFalse(request['cache_prompt'])
        self.assertEqual(request['n_probs'],1)
        self.assertEqual(request['repeat_penalty'],1.)

    def test_full_denominator_uses_native_ids_not_rank_indices(self):
        full=full_distribution(example_reply(),vocab_size=3)
        self.assertAlmostEqual(full['mass'],1.)
        self.assertEqual(full['by_id'][0],math.log(.3))
        self.assertEqual(full['greedy_token'],2)

    def test_biased_non_greedy_target_is_compared_with_original_full_distribution(self):
        reply=example_reply();full=full_distribution(reply,vocab_size=3)
        forced=copy.deepcopy(reply)
        forced['completion_probabilities'][0].update(id=1,logprob=math.log(.1),top_logprobs=reply['completion_probabilities'][0]['top_logprobs'][:1])
        self.assertTrue(compare_forced_to_full(forced,full,target=1,vocab_size=3)['passed'])
        forced['completion_probabilities'][0]['logprob']=0.
        self.assertFalse(compare_forced_to_full(forced,full,target=1,vocab_size=3)['passed'])

    def test_duplicate_full_ids_are_refused(self):
        reply=example_reply();reply['completion_probabilities'][0]['top_logprobs'][2]['id']=0
        with self.assertRaisesRegex(ProtocolHold,'duplicate'):full_distribution(reply,vocab_size=3)

    def test_selected_sampler_probability_cannot_replace_original_greedy_probability(self):
        reply=example_reply();reply['completion_probabilities'][0]['logprob']=0.
        with self.assertRaisesRegex(ProtocolHold,'greedy maximum'):full_distribution(reply,vocab_size=3)

    def test_unsorted_full_array_is_not_used_as_a_rank_selector(self):
        reply=example_reply();reply['completion_probabilities'][0]['top_logprobs'].reverse()
        with self.assertRaisesRegex(ProtocolHold,'sorted'):full_distribution(reply,vocab_size=3)

    def test_zero_probability_finite_sentinel_is_not_a_valid_selected_likelihood(self):
        reply=example_reply();reply['completion_probabilities'][0]['logprob']=-3.402823466e38
        with self.assertRaisesRegex(ProtocolHold,'sentinel'):
            completion_probabilities(reply,vocab_size=3,expected_top=3)

    def test_topk_renormalized_partial_output_does_not_pass_full_vocabulary_gate(self):
        reply=example_reply();reply['completion_probabilities'][0]['top_logprobs']=reply['completion_probabilities'][0]['top_logprobs'][:1]
        with self.assertRaisesRegex(ProtocolHold,'response count'):full_distribution(reply,vocab_size=3)

    def test_truncation_or_wrong_forced_token_is_refused(self):
        reply=example_reply();reply['truncated']=True
        with self.assertRaises(ProtocolHold):full_distribution(reply,vocab_size=3)
        reply=example_reply()
        with self.assertRaisesRegex(ProtocolHold,'selected native token'):
            completion_probabilities(reply,vocab_size=3,expected_token=1,expected_top=3)


if __name__=='__main__':unittest.main()
