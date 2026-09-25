#!/usr/bin/env python3
"""CPU-only contract: production sampling requests last-position logits."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from tinylm.infer.generate import sample


class _Encoding:
    ids = [1, 2]


class _Tokenizer:
    def encode(self, _text):
        return _Encoding()

    def decode(self, ids):
        return " ".join(map(str, ids))

    def token_to_id(self, _token):
        return None


class _Cfg:
    max_seq_len = 16


class _Model:
    def __init__(self):
        self.flags = []

    def __call__(self, x, *, past_kv=None, use_cache=False, logits_last_only=False):
        self.flags.append(bool(logits_last_only))
        logits = torch.zeros(x.shape[0], 1 if logits_last_only else x.shape[1], 8)
        logits[..., 3] = 1.0
        if not use_cache:
            return logits
        length = x.shape[1]
        kv = {0: (torch.zeros(1, 1, length, 1), torch.zeros(1, 1, length, 1))}
        return logits, kv


def main() -> int:
    model = _Model()
    sample(model, _Cfg(), _Tokenizer(), "x", max_new=2, temperature=0.0,
           device="cpu", use_cache=True, stop_at_eos=False, logits_last_only=True)
    assert model.flags and all(model.flags), model.flags
    text, missing = sample(model, _Cfg(), _Tokenizer(), "x", max_new=2,
                           temperature=0.0, device="cpu", return_metadata=True,
                           logits_last_only=True)
    assert text and missing["finish_reason"] == "EOS_UNAVAILABLE"
    assert missing["generated_tokens"] == 2 and not missing["stop_at_eos_effective"]

    class _EosTokenizer(_Tokenizer):
        def token_to_id(self, _token):
            return 3

    text, stopped = sample(model, _Cfg(), _EosTokenizer(), "x", max_new=2,
                           temperature=0.0, device="cpu", return_metadata=True,
                           logits_last_only=True)
    assert text and stopped["finish_reason"] == "EOS"
    assert stopped["generated_tokens"] == 1 and stopped["stop_at_eos_effective"]
    _, limit = sample(model, _Cfg(), _EosTokenizer(), "x", max_new=2,
                      temperature=0.0, device="cpu", stop_at_eos=False,
                      return_metadata=True, logits_last_only=True)
    assert limit["finish_reason"] == "MAX_NEW_EOS_DISABLED" and limit["generated_tokens"] == 2
    print("[PASS] generation sampling requests logits_last_only on prefill and decode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
