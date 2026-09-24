#!/usr/bin/env python3
"""P101A Stage1Wc: user-run pinned-M0 E384 roundoff attribution, not an adoption gate."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _max_abs(a, b) -> float:
    return float((a.double() - b.double()).abs().amax())


def _factorized_input(w, up, tokens):
    import torch.nn.functional as F
    return F.linear(F.embedding(tokens, w), up)


def _factorized_head(w, up, hidden):
    import torch.nn.functional as F
    return F.linear(F.linear(hidden, up.T), w)


def _state_contract(old_w, old_up, new_w, new_up) -> None:
    import torch
    rank = old_w.shape[1]
    if (old_w.dtype != torch.float32 or old_up.dtype != torch.float32
            or new_w.shape[1] <= rank or new_up.shape[1] != new_w.shape[1]
            or not torch.equal(old_w, new_w[:, :rank])
            or not torch.equal(old_up, new_up[:, :rank])
            or torch.count_nonzero(new_up[:, rank:]).item() != 0):
        raise RuntimeError("E384 migration changed old blocks or new projection is not zero")


def _tensor_self_test() -> int:
    import torch
    from tinylm.train.p101a_contract import expand_factorized
    generator = torch.Generator().manual_seed(101)
    w = torch.randn(64, 8, generator=generator)
    up = torch.randn(16, 8, generator=generator)
    new_w, new_up = expand_factorized(w, up, 4, generator=generator)
    _state_contract(w, up, new_w, new_up)
    tokens = torch.tensor([[1, 3, 5]], dtype=torch.long)
    hidden = torch.randn(1, 3, 16, generator=generator)
    input64 = _max_abs(
        _factorized_input(w.double(), up.double(), tokens),
        _factorized_input(new_w.double(), new_up.double(), tokens))
    head64 = _max_abs(
        _factorized_head(w.double(), up.double(), hidden.double()),
        _factorized_head(new_w.double(), new_up.double(), hidden.double()))
    if input64 > 1e-12 or head64 > 1e-12:
        raise RuntimeError(f"E384 real-valued map changed: input={input64} head={head64}")
    print(f"[PASS] E384 tensor-only old-block/zero-new-U contract; "
          f"FP64 input={input64:.9g} head={head64:.9g}; M0 model NOT_RUN")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--max-abs", type=float, default=1e-5,
                    help="report historical Stage1Wb threshold without changing it")
    args = ap.parse_args()
    if not 0 < args.max_abs <= 1e-3:
        ap.error("--max-abs must be in (0, 1e-3]")
    if args.self_test:
        return _tensor_self_test()

    from tinylm.train.p101a_assets import PARENT, verify_m0_assets
    run = verify_m0_assets()
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.init_utils import _strip
    from tinylm.train.p101a_contract import migrate_p101a_state

    torch.set_num_threads(1)
    state = torch.load(PARENT, map_location="cpu", weights_only=True)
    if (not isinstance(state, dict) or not {"model", "cfg", "step"}.issubset(state)
            or state["step"] != run["steps"]):
        raise ValueError("pinned M0 checkpoint schema/step differs")
    cfg = TMTConfig(**state["cfg"])
    if (cfg.n_layers != 16 or cfg.dim != 768 or cfg.emb_rank != 256
            or cfg.vocab_size != 32768):
        raise ValueError("pinned M0 geometry differs")
    torch.manual_seed(101)
    source = TiedMLPTransformer(cfg)
    source.load_state_dict(_strip(state["model"]), strict=True)
    del state
    target = TiedMLPTransformer(replace(cfg, emb_rank=384))
    target.load_state_dict(
        migrate_p101a_state(source.state_dict(), target.state_dict()), strict=True)
    source.eval()
    target.eval()
    _state_contract(source.emb.weight, source.emb_up.weight,
                    target.emb.weight, target.emb_up.weight)
    print("[STATE] old E256 blocks bit-identical; E384 new projection columns zero")
    any_historical_fail = False
    for seed in (7, 17, 31):
        tokens = torch.randint(0, cfg.vocab_size, (1, 9),
                               generator=torch.Generator().manual_seed(seed))
        with torch.no_grad():
            old_input = _factorized_input(source.emb.weight, source.emb_up.weight, tokens)
            new_input = _factorized_input(target.emb.weight, target.emb_up.weight, tokens)
            old_hidden = source(tokens, return_hidden=True)
            new_hidden = target(tokens, return_hidden=True)
            old_logits = source._head_logits(old_hidden)
            same_hidden_new_head = target._head_logits(old_hidden)
            new_logits = target._head_logits(new_hidden)
            old_direct = source(tokens)
            new_direct = target(tokens)
            input64 = _max_abs(
                _factorized_input(source.emb.weight.double(),
                                  source.emb_up.weight.double(), tokens),
                _factorized_input(target.emb.weight.double(),
                                  target.emb_up.weight.double(), tokens))
            head64 = _max_abs(
                _factorized_head(source.emb.weight.double(),
                                 source.emb_up.weight.double(), old_hidden.double()),
                _factorized_head(target.emb.weight.double(),
                                 target.emb_up.weight.double(), old_hidden.double()))
        input32 = _max_abs(old_input, new_input)
        body32 = _max_abs(old_hidden, new_hidden)
        head32 = _max_abs(old_logits, same_hidden_new_head)
        path_delta = max(_max_abs(old_direct, old_logits),
                         _max_abs(new_direct, new_logits))
        if path_delta > 1e-6:
            raise RuntimeError(f"hidden/head reconstruction differs from direct forward: {path_delta}")
        full32 = _max_abs(old_direct, new_direct)
        nrms = float((old_logits.double() - new_logits.double()).square().mean().sqrt()
                     / old_logits.double().square().mean().sqrt().clamp_min(1e-12))
        changed = int((old_logits.argmax(-1) != new_logits.argmax(-1)).sum())
        if not all(torch.isfinite(x).all() for x in
                   (old_input, new_input, old_hidden, new_hidden,
                    old_logits, same_hidden_new_head, new_logits)):
            raise RuntimeError("non-finite E384 attribution tensor")
        any_historical_fail |= full32 > args.max_abs
        print(f"[SEED {seed}] input32={input32:.9g} body32={body32:.9g} "
              f"head32_common_hidden={head32:.9g} full32={full32:.9g} "
              f"nrms={nrms:.9g} top1_changed={changed} "
              f"input64={input64:.9g} head64_common_hidden={head64:.9g}")
    print(f"[DIAGNOSTIC COMPLETE] historical_threshold={args.max_abs:.9g} "
          f"exceeded_on_panel={int(any_historical_fail)}")
    print("[LIMIT] measurement completion is not an E384 function PASS; "
          "Stage1Wb FAIL and E384 training HOLD remain until a separately approved remedy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
