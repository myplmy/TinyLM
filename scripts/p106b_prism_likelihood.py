"""Full continuation likelihood using the qualified Prism CAPI last-logit path."""

from collections import defaultdict
import math

import numpy as np

from scripts.p106b_official_lm_adapter import plan_tokens, token_ids
from scripts.p106b_prism_native import log_probabilities


class PrismLikelihood:
    """Use the original causal pair encoder and evaluate each predictor prefix."""

    backend = 'causal'

    def __init__(self, native, template, prefix_token_id, *, check=None):
        self.native = native
        self.template = template
        self.vocab = native.vocab_size
        self.context_limit = native.context_limit
        self.prefix_token_id = token_ids([prefix_token_id], self.vocab)[0]
        self.check = check or (lambda: None)

    def tok_encode(self, text, add_special_tokens=None):
        if not isinstance(text, str) or add_special_tokens not in (None, False):
            raise ValueError('causal likelihood requires explicitly untemplated native text')
        if not text:
            return []
        return self.native.tokenize(text, add_special=False)

    def plan(self, context, target):
        if not isinstance(context, str) or not isinstance(target, str) or not target:
            raise ValueError('nonempty original target and explicit context required')
        if context:
            context_ids, target_ids = self.template._encode_pair(self, context, target)
            if self.tok_encode(context+target) != context_ids+target_ids:
                raise ValueError('joint native encoding changes the already encoded predictor prefix')
        else:
            encoded = self.tok_encode(target, add_special_tokens=False)
            if not encoded:
                raise ValueError('empty-context target requires native tokens')
            if encoded[0] == self.prefix_token_id:
                context_ids, target_ids = encoded[:1], encoded[1:]
            else:
                context_ids, target_ids = [self.prefix_token_id], encoded
        return plan_tokens(context_ids, target_ids, self.vocab, self.context_limit)

    @staticmethod
    def prefix(plan, target_index):
        return plan.input_ids[:plan.target_start+target_index+1]

    def score(self, plans):
        """Share only exact predictor prefixes of candidates in this call."""
        if not 1 <= len(plans) <= 16:
            raise ValueError('one bounded official item of plans required')
        jobs = defaultdict(list)
        outputs = []
        for index, plan in enumerate(plans):
            token_ids(plan.input_ids, self.vocab)
            targets = token_ids(plan.continuation_ids, self.vocab)
            if (plan.target_start < 0 or plan.target_start + len(targets) != len(plan.input_ids)
                    or len(plan.input_ids) > self.context_limit):
                raise ValueError('every original continuation position must have a predictor')
            outputs.append([None]*len(targets))
            for position, target in enumerate(targets):
                jobs[self.prefix(plan, position)].append((index, position, target))

        for prefix, sites in jobs.items():
            self.check()
            logits = self.native.logits(prefix)
            if logits.shape != (self.vocab,):
                raise ValueError('full native vocabulary logits required')
            logp = log_probabilities(logits)
            greedy_id = int(np.argmax(logits))
            for index, position, target in sites:
                outputs[index][position] = (float(logp[target]), greedy_id)

        return [dict(response=(math.fsum(p for p, _ in sites),
                              all(greedy == token for (_, greedy), token in zip(sites,plan.continuation_ids))),
                     position_logprob=[p for p, _ in sites],
                     greedy_ids=[greedy for _, greedy in sites])
                for plan, sites in zip(plans, outputs)]
