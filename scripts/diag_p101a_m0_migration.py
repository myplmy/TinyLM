#!/usr/bin/env python3
"""P101A pinned M0 checkpoint migration gate; full model path is user-run only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.train.p101a_assets import PARENT, STEM, TOKENIZER, verify_m0_assets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-abs", type=float, default=1e-5)
    args = parser.parse_args()
    run = verify_m0_assets()
    if args.check_only:
        print(f"[PASS] pinned M0 metadata/hash/cache: {STEM}; model NOT_RUN")
        return 0
    if args.max_abs <= 0:
        parser.error("--max-abs must be positive")

    import torch
    from tokenizers import Tokenizer
    from dataclasses import replace
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.init_utils import _strip
    from tinylm.train.p101a_contract import migrate_p101a_state, mtp_loss_components, mtp_weighted_mean

    saved = torch.load(PARENT, map_location="cpu", weights_only=True)
    if not isinstance(saved, dict) or not {"model", "cfg", "step"}.issubset(saved):
        raise ValueError("M0 checkpoint schema is incomplete")
    if saved["step"] != run["steps"]:
        raise ValueError("M0 checkpoint step and run JSON differ")
    cfg = TMTConfig(**saved["cfg"])
    if cfg.n_layers != 16 or cfg.dim != 768 or cfg.emb_rank != 256 or cfg.vocab_size != 32768:
        raise ValueError("M0 checkpoint architecture differs")
    torch.manual_seed(101)
    source = TiedMLPTransformer(cfg)
    source.load_state_dict(_strip(saved["model"]), strict=True)
    target_cfg = replace(cfg, emb_rank=384, qk_gain_learnable=True, mtp_aux=True)
    target = TiedMLPTransformer(target_cfg)
    migrated = migrate_p101a_state(source.state_dict(), target.state_dict())
    target.load_state_dict(migrated, strict=True)
    source.eval()
    target.eval()
    tokens = torch.randint(0, cfg.vocab_size, (1, 9),
                           generator=torch.Generator().manual_seed(7))
    with torch.no_grad():
        before, after = source(tokens), target(tokens)
    max_abs = float((before - after).abs().amax())
    if max_abs > args.max_abs:
        print(f"[GATE FAIL] M0 function drift max_abs={max_abs:.8g}")
        return 1
    payload = target.mtp_deployment_payload()
    deploy = TiedMLPTransformer(TMTConfig(**payload["cfg"]))
    deploy.load_state_dict(payload["model"], strict=True)
    deploy.eval()
    with torch.no_grad():
        if not torch.allclose(after, deploy(tokens), atol=args.max_abs, rtol=0):
            raise RuntimeError("auxiliary-head export changed main logits")
    target.train()
    x, y = tokens[:, :-1], tokens[:, 1:]
    hidden = target(x, return_hidden=True)
    eos_id = Tokenizer.from_file(str(TOKENIZER)).token_to_id("<eos>")
    if eos_id is None:
        raise ValueError("pinned M0 tokenizer has no EOS ID")
    parts = mtp_loss_components(hidden, target.emb_up.weight,
                                target.mtp_up2, target.mtp_up4,
                                target.emb.weight, x, y, eos_id=eos_id, chunk=256)
    mtp_weighted_mean([parts], 0.2, 0.1).backward()
    if (target.mtp_up2.grad is None or target.mtp_up4.grad is None
            or target.emb_up.weight.grad is None
            or not float(target.emb_up.weight.grad[:, 256:].abs().sum()) > 0):
        raise RuntimeError("M0 migrated MTP/new-rank gradient is missing")
    print(f"[PASS] P101A real M0 strict migration max_abs={max_abs:.8g}; aux/export/new-rank gradients")
    print("[LIMIT] CPU one-crop gate; continued trainer, GPU wall and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
