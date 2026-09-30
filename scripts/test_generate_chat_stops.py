#!/usr/bin/env python3
"""CPU fixture for opt-in ChatML stop IDs, including legacy multi-token markers."""
from pathlib import Path
import sys
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tinylm.infer.generate import sample


class Tokenizer:
    def encode(self, _text):
        return type("Encoding", (), {"ids": [1, 2]})()
    def token_to_id(self, _text):
        return None
    def decode(self, ids):
        return " ".join(map(str, ids))


class Model:
    def __init__(self, ids):
        self.ids, self.index = ids, 0
    def __call__(self, x, **_kwargs):
        logits = torch.zeros(1, 1, 8)
        logits[..., self.ids[min(self.index, len(self.ids)-1)]] = 5
        self.index += 1
        return logits


def main():
    cfg = type("Config", (), {"max_seq_len": 16})()
    def run(ids, stops=None):
        return sample(Model(ids), cfg, Tokenizer(), "prompt", max_new=4,
                      temperature=0, device="cpu", use_cache=False,
                      return_metadata=True, stop_token_sequences=stops)
    text, meta = run([3, 4, 5], [[3, 4]])
    assert text.endswith("3 4") and meta["generated_tokens"] == 2
    assert meta["finish_reason"] == "STOP_SEQUENCE"
    assert run([4, 5], [[4]])[1]["generated_tokens"] == 1
    # A marker prefix in the prompt must not count as generated output.
    assert run([3, 3, 3], [[2, 3]])[1]["generated_tokens"] == 4
    assert run([3, 4], None) == run([3, 4], [])
    assert "stop_token_sequences" not in run([3, 4], None)[1]
    try:
        run([3], [[]])
    except ValueError:
        pass
    else:
        raise AssertionError("empty stop sequence accepted")
    print("[PASS] opt-in single/multi-token ChatML stops; default path unchanged; GPU NOT_RUN")


if __name__ == "__main__":
    main()
