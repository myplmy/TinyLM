#!/usr/bin/env python3
"""P076 B3 user-run ag2 parent-init wiring and step-0 band gate.

This is not a learned-quality ranking. It never writes a checkpoint or cache.
Codex may use --check-only, but only the user runs the model path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PARENT = ROOT / "runs/ckpt/m100_ko-en_300M_dense.pt"
CACHE = ROOT / "data_cache/ko-en_600000000"


def fingerprint(module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().contiguous().cpu().numpy().tobytes())
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        print("[CHECK_ONLY] P076 B3 source and launcher contract; parent/cache/model NOT_READ")
        return 0

    import torch
    import torch.nn.functional as F
    from tinylm.config import build_config
    from tinylm.data import Loader
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.init_utils import init_from_dense

    for path in (PARENT, CACHE / "meta.json", CACHE / "val.bin"):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"P076 pinned parent/cache missing or linked: {path.name}")
    if CACHE.is_symlink():
        raise ValueError("P076 cache directory is linked")
    meta = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
    if meta.get("data") != "ko-en" or meta.get("tokens") != 600_000_000:
        raise ValueError("P076 fixed 600M pool metadata differs")
    if not torch.cuda.is_available():
        raise RuntimeError("P076 B3 user-run gate requires CUDA; no CPU model fallback")
    torch.set_num_threads(1)
    loader = Loader("val", 2, 512, "cuda", CACHE, seed=99)
    x, y = loader()
    values = []
    for label, override in (("legacy", None), ("explicit_mean", "mean"),
                            ("attention_norm_mean", "norm_mean")):
        torch.manual_seed(1337)
        cfg = build_config("m100R1c", "tied", 512, False)
        cfg.attn_group = 2
        cfg.cla_group = 2
        if cfg.n_middle % cfg.attn_group:
            raise ValueError("P076 middle layers cannot be grouped by ag2")
        model = TiedMLPTransformer(cfg).cuda()
        init_from_dense(model, PARENT, "cuda", depth_init="prop", group_init="mean",
                        attn_group_init=override)
        model.eval()
        mlp_sha = fingerprint(model.mid_mlps)
        attn_sha = fingerprint(model.mid_attns)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(x)
            ce = F.cross_entropy(logits.float().reshape(-1, cfg.vocab_size),
                                 y.reshape(-1))
        ce_value = float(ce)
        if not math.isfinite(ce_value):
            raise RuntimeError(f"P076 {label} step0 CE is non-finite")
        values.append((label, mlp_sha, attn_sha, ce_value))
        print(f"[MEASURED] {label} mlp_sha={mlp_sha} attn_sha={attn_sha} step0_CE={ce_value:.7f}")
        del model, logits, ce
        torch.cuda.empty_cache()

    legacy, explicit, candidate = values
    if legacy[1:3] != explicit[1:3]:
        raise RuntimeError("explicit mean changed the legacy ag2 initialized weights")
    if len({row[1] for row in values}) != 1:
        raise RuntimeError("attention-only override changed an MLP parent-initialized weight")
    if candidate[2] == legacy[2]:
        raise RuntimeError("attention-only norm_mean did not change shared attention weights")
    if any(not 5.0 <= row[3] <= 9.4 for row in values):
        print("[GATE NEGATIVE] a step0 CE is outside the preregistered 5.0..9.4 init band")
        return 8
    print("[PASS] default/explicit mean identical; MLP invariant; attention-only change; all step0 CE in init band")
    print("[LIMIT] step0 is a binary init gate, not a final-quality ranking or ag2 adoption result")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P076 B3 gate: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
