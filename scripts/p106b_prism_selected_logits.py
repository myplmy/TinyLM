"""Read only the continuation positions requested from the pinned Prism decode."""

import ctypes as C
import math

import numpy as np

from scripts.p106b_official_lm_adapter import token_ids
from scripts.p106b_prism_native import log_probabilities


MAX_OUTPUT_ROWS = 64


def batches(length, positions, limit):
    """Bound GPU output rows independently of the context-processing batch."""
    if not 0 < limit <= 512 or not positions or positions != sorted(set(positions)):
        raise ValueError("ordered distinct predictor positions and a bounded native batch required")
    if positions[0] < 0 or positions[-1] >= length:
        raise ValueError("predictor position outside the original input")
    begin = index = 0
    while begin < length:
        end = min(begin+limit,length)
        if len(positions)-index > MAX_OUTPUT_ROWS:
            end = min(end,positions[index+MAX_OUTPUT_ROWS])
        after = index
        while after < len(positions) and positions[after] < end:
            after += 1
        yield begin,end,positions[index:after]
        begin,index = end,after


class SelectedLogits:
    """Keep full precision and reset the original context before every candidate."""

    def __init__(self, native):
        self.native = native
        self.decode_calls = self.candidates = self.positions = self.input_tokens = 0

    def score_plan(self, plan):
        owner = self.native
        src = token_ids(plan.input_ids,owner.vocab_size)
        target = token_ids(plan.continuation_ids,owner.vocab_size)
        first = plan.target_start
        if not 0 <= first < len(src) <= owner.context_limit or len(src)-first != len(target):
            raise ValueError("exact continuation and predictor span required")
        owner.check()
        memory = owner.api.llama_get_memory(owner.context)
        if not memory:
            raise RuntimeError("native context memory cannot be reset")
        owner.api.llama_memory_clear(memory,True)
        owner.api.llama_synchronize(owner.context)
        owner.clears += 1
        logs, greedy = [], []
        for begin,end,selected in batches(len(src),list(range(first,len(src))),owner.batch_limit):
            owner.check()
            flags = (C.c_int8*(end-begin))()
            for index in selected:
                flags[index-begin] = 1
            tokens = (C.c_int32*(end-begin))(*src[begin:end])
            batch = owner.api.llama_batch_get_one(tokens,end-begin)
            batch.logits = flags
            if owner.api.llama_decode(owner.context,batch)!=0:
                raise RuntimeError("native decode with explicit output positions failed")
            owner.api.llama_synchronize(owner.context)
            self.decode_calls += 1
            for index in selected:
                ptr = owner.api.llama_get_logits_ith(owner.context,index-begin)
                if not ptr:
                    raise RuntimeError("missing requested native logit row")
                values = np.ctypeslib.as_array(ptr,shape=(owner.vocab_size,))
                probs = log_probabilities(values)
                logs.append(float(probs[target[index-first]]))
                greedy.append(int(values.argmax()))
        if len(logs)!=len(target):
            raise RuntimeError("continuation position accounting differs")
        self.candidates += 1
        self.positions += len(target)
        self.input_tokens += len(src)
        return dict(response=(math.fsum(logs),tuple(greedy)==target),position_logprob=logs,greedy_ids=greedy)

    def score(self, plans):
        if not 1 <= len(plans) <= 16:
            raise ValueError("one complete bounded official item required")
        return [self.score_plan(plan) for plan in plans]
