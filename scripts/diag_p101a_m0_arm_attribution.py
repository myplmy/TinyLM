#!/usr/bin/env python3
"""P101A Stage1Wb: isolate approved M0 migration arms; user-run model gate."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.train.p101a_assets import PARENT, TOKENIZER, verify_m0_assets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--max-abs", type=float, default=1e-5)
    args = ap.parse_args()
    if not 0 < args.max_abs <= 1e-3:
        ap.error("--max-abs must be in (0, 1e-3]")
    run = verify_m0_assets()
    if args.check_only:
        print("[CHECK_ONLY] pinned M0 assets; independent-arm model gate NOT_RUN")
        return 0

    import torch
    import torch.nn.functional as F
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.init_utils import _strip
    from tinylm.train.p101a_contract import (migrate_p101a_state, mtp_loss_components,
                                             mtp_weighted_mean)

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
    source.eval()
    tokens = torch.randint(0, cfg.vocab_size, (1, 9),
                           generator=torch.Generator().manual_seed(7))
    with torch.no_grad():
        baseline = source(tokens).detach()
    source_state = source.state_dict()
    variants = (
        ("e384", replace(cfg, emb_rank=384)),
        ("qk", replace(cfg, qk_gain_learnable=True)),
        ("mtp", replace(cfg, mtp_aux=True)),
    )
    failures = []
    for label, variant_cfg in variants:
        target = TiedMLPTransformer(variant_cfg)
        migrated = migrate_p101a_state(source_state, target.state_dict())
        target.load_state_dict(migrated, strict=True)
        target.eval()
        with torch.no_grad():
            after = target(tokens).detach()
        delta = (baseline.float() - after.float()).abs()
        max_abs = float(delta.amax())
        nrms = float(delta.square().mean().sqrt()
                     / baseline.float().square().mean().sqrt().clamp_min(1e-12))
        top1_changed = int((baseline.argmax(-1) != after.argmax(-1)).sum())
        print(f"[ARM {label}] max_abs={max_abs:.9g} nrms={nrms:.9g} "
              f"top1_changed={top1_changed} tolerance={args.max_abs:.9g}")
        if not bool(torch.isfinite(after).all()) or max_abs > args.max_abs:
            failures.append(label + ":main_logits")
        if label == "mtp":
            payload = target.mtp_deployment_payload()
            deploy = TiedMLPTransformer(TMTConfig(**payload["cfg"]))
            deploy.load_state_dict(payload["model"], strict=True)
            deploy.eval()
            with torch.no_grad():
                deploy_delta = float((after - deploy(tokens)).abs().amax())
            print(f"[ARM mtp] deploy_max_abs={deploy_delta:.9g}")
            if deploy_delta > args.max_abs:
                failures.append("mtp:deploy")
            target.train()
            x, y = tokens[:, :-1], tokens[:, 1:]
            hidden = target(x, return_hidden=True)
            eos_id = Tokenizer.from_file(str(TOKENIZER)).token_to_id("<eos>")
            if eos_id is None:
                raise ValueError("pinned tokenizer lacks EOS")
            parts = mtp_loss_components(hidden, target.emb_up.weight,
                                        target.mtp_up2, target.mtp_up4,
                                        target.emb.weight, x, y, eos_id=eos_id, chunk=256)
            mtp_weighted_mean([parts], 0.2, 0.1).backward()
            if (target.mtp_up2.grad is None or target.mtp_up4.grad is None
                    or target.emb_up.weight.grad is None):
                failures.append("mtp:gradient")
        elif label == "e384":
            target.train()
            x, y = tokens[:, :-1], tokens[:, 1:]
            logits = target(x)
            F.cross_entropy(logits.float().reshape(-1, cfg.vocab_size),
                            y.reshape(-1)).backward()
            grad = target.emb_up.weight.grad
            if grad is None or not float(grad[:, 256:].abs().sum()) > 0:
                failures.append("e384:new_rank_gradient")
        elif label == "qk":
            target.train()
            x, y = tokens[:, :-1], tokens[:, 1:]
            logits = target(x)
            F.cross_entropy(logits.float().reshape(-1, cfg.vocab_size),
                            y.reshape(-1)).backward()
            gains = [p.grad for name, p in target.named_parameters()
                     if name.endswith(".qk_gain_logit")]
            if not gains or not any(g is not None and float(g.abs().sum()) > 0 for g in gains):
                failures.append("qk:gradient")
        del target
    if failures:
        print("[GATE FAIL] approved independent M0 arms: " + ", ".join(failures))
        print("[LIMIT] old combined-arm gate is historical; do not loosen 1e-5 after seeing one result")
        return 1
    print("[PASS] P101A approved E384/QK/MTP independent M0 arms under original 1e-5 gate")
    print("[LIMIT] CPU one-crop function only; GPU training and quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
