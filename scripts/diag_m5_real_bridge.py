#!/usr/bin/env python3
"""P104A Stage2B: same real dense checkpoint on Windows and WSL, no retraining.

User-run GPU full fixed-val CE and one in-memory SGD step. The output is a
write-once JSON; no checkpoint, training cache, or tokenizer file is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CKPT = ROOT / "runs" / "ckpt" / "m100s10_ko-en_300M_d14_cla2_norecur_rms4.pt"
CACHE = ROOT / "data_cache" / "ko-en_600000000"
TOKENIZER = ROOT / "data_cache" / "tok-ko-en-32768.json"
CODE_RELATIVE = (
    "tinylm/config.py", "tinylm/model/modules.py",
    "tinylm/model/ternary.py", "tinylm/model/transformer.py",
    "scripts/diag_m5_real_bridge.py",
)
SEQ = 1024
MICRO = 4
STEP_SEQ = 256
STEP_BATCH = 2


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest().upper()


def paths_by_root(root: Path) -> dict[str, Path]:
    return {name: root.joinpath(*name.split("/")) for name in CODE_RELATIVE}


def preflight(platform_name: str, output: Path) -> Path:
    target = (ROOT / output).resolve()
    base = (ROOT / "runs" / "bench").resolve()
    if target.parent != base or target.suffix != ".json":
        raise ValueError("M5 real output must be one JSON directly under runs/bench")
    expected = base / f"p104a_m5_real_{platform_name}.json"
    if target != expected:
        raise ValueError("M5 real platform/output name mismatch")
    if target.exists() or target.is_symlink():
        raise FileExistsError("M5 real output already exists")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("windows", "wsl"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    target = preflight(args.platform, args.out)
    if args.check_only:
        print(f"[CHECK_ONLY] P104A real {args.platform}: output={target.name}, model/GPU/data NOT_RUN")
        return 0
    actual = platform.system()
    if (args.platform == "windows" and actual != "Windows") or (
        args.platform == "wsl" and (actual != "Linux" or "microsoft" not in platform.release().lower())
    ):
        raise RuntimeError(f"M5 platform mismatch {args.platform} != {actual}/{platform.release()}")

    import numpy as np
    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip

    for path in (CKPT, CACHE / "meta.json", CACHE / "val.bin", TOKENIZER):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"M5 real input absent or linked: {path.name}")
    if CACHE.is_symlink():
        raise ValueError("M5 cache directory is linked")
    meta = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
    if meta.get("data") != "ko-en" or meta.get("val") != 3_000_000:
        raise ValueError("M5 real val source differs from fixed ko-en 600M")
    if (CACHE / "val.bin").stat().st_size != 2 * int(meta["val"]):
        raise ValueError("M5 real val uint16 byte count differs")
    if not torch.cuda.is_available():
        raise RuntimeError("M5 real user GPU is unavailable")
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    checkpoint_sha = digest(CKPT)
    cache_sha = digest(CACHE / "val.bin")
    tokenizer_sha = digest(TOKENIZER)
    code_sha = {name: digest(path) for name, path in paths_by_root(ROOT).items()}
    state = torch.load(CKPT, map_location="cpu", weights_only=True)
    if not isinstance(state, dict) or not {"model", "cfg"}.issubset(state):
        raise ValueError("M5 real checkpoint schema differs")
    cfg = TMTConfig(**state["cfg"])
    if cfg.tie_mlp or cfg.dim != 768 or cfg.n_layers != 14 or cfg.cla_group != 2:
        raise ValueError("M5 real d14 CLA2 dense geometry differs")
    model = TiedMLPTransformer(cfg).cuda()
    model.load_state_dict(_strip(state["model"]), strict=True)
    del state
    model.eval()
    val = np.memmap(CACHE / "val.bin", dtype=np.uint16, mode="r",
                    shape=(int(meta["val"]),))
    windows = (len(val) - 1) // SEQ
    if windows < 1000:
        raise ValueError("M5 full fixed-val has too few windows")
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    summed_ce = 0.0
    token_count = 0
    started = time.perf_counter()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for offset in range(0, windows, MICRO):
            blocks = []
            for index in range(offset, min(offset + MICRO, windows)):
                start = index * SEQ
                blocks.append(np.asarray(val[start:start + SEQ + 1],
                                         dtype=np.int64).copy())
            raw = torch.from_numpy(np.stack(blocks)).cuda()
            logits = model(raw[:, :-1])
            loss = F.cross_entropy(logits.float().reshape(-1, cfg.vocab_size),
                                   raw[:, 1:].reshape(-1), reduction="sum")
            summed_ce += float(loss.detach())
            token_count += raw[:, 1:].numel()
    torch.cuda.synchronize()
    eval_wall_sec = time.perf_counter() - started
    eval_ce = summed_ce / token_count
    if not math.isfinite(eval_ce):
        raise RuntimeError("M5 real evaluation CE is non-finite")

    step_raw = np.asarray(val[:STEP_BATCH * (STEP_SEQ + 1)],
                          dtype=np.int64).copy().reshape(STEP_BATCH, STEP_SEQ + 1)
    step_input_sha = hashlib.sha256(step_raw.tobytes()).hexdigest().upper()
    step = torch.from_numpy(step_raw).cuda()
    x, y = step[:, :-1], step[:, 1:]
    model.train()
    optimizer = torch.optim.SGD(model.parameters(), lr=1e-4)
    optimizer.zero_grad(set_to_none=True)
    torch.cuda.synchronize()
    step_started = time.perf_counter()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        step_logits = model(x)
        step_ce = F.cross_entropy(step_logits.float().reshape(-1, cfg.vocab_size),
                                  y.reshape(-1))
    step_ce.backward()
    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    if not bool(torch.isfinite(step_ce)) or not bool(torch.isfinite(grad_norm)):
        raise RuntimeError("M5 real one-step CE or gradient is non-finite")
    probe = None
    for name, parameter in model.named_parameters():
        if parameter.grad is None:
            continue
        flat = parameter.grad.detach().reshape(-1)
        index = int(flat.abs().argmax())
        if float(flat[index].abs()) > 0:
            probe = (name, parameter, index, parameter.detach().reshape(-1)[index].clone())
            break
    if probe is None:
        raise RuntimeError("M5 real one-step gradient changed no parameter")
    optimizer.step()
    torch.cuda.synchronize()
    step_wall_ms = (time.perf_counter() - step_started) * 1000
    probe_name, probe_parameter, probe_index, before = probe
    delta = float((probe_parameter.detach().reshape(-1)[probe_index] - before).abs())
    if not math.isfinite(delta) or delta <= 0:
        raise RuntimeError("M5 real optimizer step is a no-op")
    model.eval()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        post = model(x)
        post_ce = F.cross_entropy(post.float().reshape(-1, cfg.vocab_size),
                                  y.reshape(-1))
    torch.cuda.synchronize()
    result = {
        "schema": "TINYLM_M5_REAL_DENSE_V1",
        "declared_platform": args.platform,
        "runtime": actual, "release": platform.release(),
        "python": platform.python_version(), "torch": torch.__version__,
        "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
        "gpu": torch.cuda.get_device_name(),
        "checkpoint": CKPT.relative_to(ROOT).as_posix(),
        "checkpoint_sha256": checkpoint_sha,
        "input_sha256": cache_sha, "step_input_sha256": step_input_sha,
        "tokenizer_sha256": tokenizer_sha, "code_sha256": code_sha,
        "preset": "m100s10", "data": "ko-en", "arch": "dense",
        "eval_seq": SEQ, "eval_micro_bs": MICRO, "eval_windows": windows,
        "eval_tokens": token_count, "eval_ce": eval_ce,
        "eval_wall_sec": eval_wall_sec,
        "one_step_ce": float(step_ce.detach()),
        "one_step_grad_norm": float(grad_norm.detach()),
        "one_step_param_delta_abs": delta,
        "one_step_probe_name": probe_name, "one_step_probe_flat_index": probe_index,
        "one_step_wall_ms": step_wall_ms,
        "post_step_eval_ce": float(post_ce.detach()),
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "scientific_quality": "SAME_CHECKPOINT_CROSS_OS_FUNCTION_ONLY",
    }
    if target.exists() or target.is_symlink():
        raise FileExistsError("M5 real output appeared during evaluation")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(f"[MEASURED] M5 real {args.platform}: windows={windows} CE={eval_ce:.8f} "
          f"step_CE={float(step_ce.detach()):.8f} post_CE={float(post_ce.detach()):.8f} "
          f"grad={float(grad_norm.detach()):.8f} step_ms={step_wall_ms:.3f}")
    print(f"[EVIDENCE] {target}; compare with the other OS only when checkpoint/code/input SHA match")
    print("[LIMIT] full fixed-val CE and one SGD step are not 300M training reproducibility or OS-only speed attribution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
