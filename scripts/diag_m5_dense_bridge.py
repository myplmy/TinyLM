#!/usr/bin/env python3
"""P104A user-run small dense Windows/WSL bridge, not a full M5 quality verdict."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CKPT = ROOT / "runs" / "ckpt" / "tiny_synthetic_2M_dense.pt"
CODE = (
    ROOT / "tinylm" / "config.py",
    ROOT / "tinylm" / "model" / "modules.py",
    ROOT / "tinylm" / "model" / "ternary.py",
    ROOT / "tinylm" / "model" / "transformer.py",
    Path(__file__),
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", choices=("windows", "wsl"), default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    args.platform = args.platform or ("windows" if platform.system() == "Windows" else "wsl")
    args.out = args.out or Path(f"runs/bench/p104a_m5_{args.platform}.json")
    target = (ROOT / args.out).resolve()
    base = (ROOT / "runs" / "bench").resolve()
    if target.parent != base or target.suffix != ".json":
        ap.error("output must be a JSON directly under runs/bench")
    if target.exists() or target.is_symlink():
        ap.error(f"output already exists: {target}")
    if args.check_only:
        print(f"[CHECK_ONLY] M5 {args.platform} output={target}; checkpoint/model/GPU NOT_RUN")
        return 0

    actual = platform.system()
    if (args.platform == "windows" and actual != "Windows") or (
        args.platform == "wsl" and (actual != "Linux" or "microsoft" not in platform.release().lower())
    ):
        raise RuntimeError(f"platform mismatch: declared={args.platform} actual={actual}/{platform.release()}")
    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip

    if not torch.cuda.is_available() or not CKPT.is_file():
        raise RuntimeError("CUDA and the exact shared tiny dense checkpoint are required")
    ckpt_sha = digest(CKPT)
    code_sha = {p.relative_to(ROOT).as_posix(): digest(p) for p in CODE}
    state = torch.load(CKPT, map_location="cpu", weights_only=True)
    cfg = TMTConfig(**state["cfg"])
    if cfg.tie_mlp:
        raise RuntimeError("M5 small control must be an untied dense checkpoint")
    model = TiedMLPTransformer(cfg).cuda()
    model.load_state_dict(_strip(state["model"]), strict=True)
    model.eval()
    rng = torch.Generator(device="cpu").manual_seed(104)
    raw = torch.randint(3, cfg.vocab_size, (2, 33), generator=rng, dtype=torch.long)
    x, y = raw[:, :-1].cuda(), raw[:, 1:].cuda()
    token_sha = hashlib.sha256(raw.numpy().tobytes()).hexdigest().upper()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    start = time.perf_counter()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        logits = model(x)
        eval_ce = F.cross_entropy(logits.reshape(-1, cfg.vocab_size).float(), y.reshape(-1))
    torch.cuda.synchronize()
    eval_ms = (time.perf_counter() - start) * 1000
    if not bool(torch.isfinite(eval_ce)):
        raise RuntimeError("non-finite evaluation CE")

    model.train()
    optimizer = torch.optim.SGD(model.parameters(), lr=1e-4)
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        train_logits = model(x)
        loss = F.cross_entropy(train_logits.reshape(-1, cfg.vocab_size).float(), y.reshape(-1))
    loss.backward()
    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(grad_norm)):
        raise RuntimeError("non-finite one-step loss/gradient")
    probe = None
    for name, param in model.named_parameters():
        if param.grad is None:
            continue
        flat_grad = param.grad.detach().reshape(-1)
        flat_index = int(flat_grad.abs().argmax())
        if float(flat_grad[flat_index].abs()) > 0:
            probe = (name, param, flat_index,
                     param.detach().reshape(-1)[flat_index].clone())
            break
    if probe is None:
        raise RuntimeError("one-step gradient changed no parameter")
    optimizer.step()
    probe_name, probe_param, probe_index, before_update = probe
    probe_delta = float(
        (probe_param.detach().reshape(-1)[probe_index] - before_update).abs()
    )
    if not math.isfinite(probe_delta) or probe_delta <= 0:
        raise RuntimeError("optimizer step changed no observed parameter")
    model.eval()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        post_logits = model(x)
        post_ce = F.cross_entropy(
            post_logits.reshape(-1, cfg.vocab_size).float(), y.reshape(-1)
        )
    torch.cuda.synchronize()
    result = {
        "schema": "TINYLM_M5_SMALL_DENSE_V2",
        "declared_platform": args.platform,
        "runtime": actual,
        "release": platform.release(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "gpu": torch.cuda.get_device_name(),
        "checkpoint": CKPT.relative_to(ROOT).as_posix(),
        "checkpoint_sha256": ckpt_sha,
        "code_sha256": code_sha,
        "input_sha256": token_sha,
        "eval_ce": float(eval_ce),
        "one_step_ce": float(loss),
        "one_step_grad_norm": float(grad_norm),
        "one_step_param_delta_abs": probe_delta,
        "one_step_probe_name": probe_name,
        "one_step_probe_flat_index": probe_index,
        "post_step_eval_ce": float(post_ce),
        "eval_wall_ms": eval_ms,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "scientific_quality": "NOT_RUN",
    }
    if not all(math.isfinite(result[k]) for k in
               ("eval_ce", "one_step_ce", "one_step_grad_norm",
                "one_step_param_delta_abs", "post_step_eval_ce")):
        raise RuntimeError("non-finite bridge value")
    base.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(f"[PASS] small dense functional bridge {args.platform}: eval_ce={result['eval_ce']:.6f} "
          f"one_step_ce={result['one_step_ce']:.6f} "
          f"post_step_eval_ce={result['post_step_eval_ce']:.6f} "
          f"param_delta={probe_delta:.8g} peak_reserved={result['peak_reserved_bytes']}")
    print(f"[EVIDENCE] {target}; full M5 real-checkpoint quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
