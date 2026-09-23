#!/usr/bin/env python3
"""P092 Stage3Wb user-run resident-memory and inference-speed diagnosis."""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARMS = (
    ("p092_s2_dense100", "none", 1.0),
    ("p092_s2_static50", "static", 0.5),
    ("p092_s2_dynamic50", "dynamic", 0.5),
)
PREFIX = "m100s10_ko-en_300M_"


def check_inputs(output):
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output already exists: {output}")
    if not output.resolve().is_relative_to((ROOT / "runs/bench").resolve()):
        raise ValueError("output must be under runs/bench")
    rows = []
    for tag, mode, density in ARMS:
        stem = PREFIX + tag
        log = ROOT / "runs/logs" / f"{stem}.json"
        ckpt = ROOT / "runs/ckpt" / f"{stem}.pt"
        if not log.is_file() or not ckpt.is_file():
            raise FileNotFoundError(f"paired JSON/checkpoint missing: {stem}")
        meta = json.loads(log.read_text(encoding="utf-8"))
        expected = dict(tag=stem, preset="m100s10", data="ko-en",
                        arch="dense", steps=763, seed=1337,
                        connectivity_mode=mode, connectivity_density=density,
                        n_skip=0)
        for key, value in expected.items():
            if meta.get(key) != value:
                raise ValueError(f"{stem}: {key}={meta.get(key)!r}, expected {value!r}")
        if "final" not in meta:
            raise ValueError(f"{stem}: final result missing")
        rows.append(dict(tag=tag, mode=mode, density=density, checkpoint=ckpt,
                         checkpoint_bytes=ckpt.stat().st_size,
                         train_ms_step=meta["ms_step_median"],
                         reported_runtime_mib=meta["runtime_mb"],
                         reported_packed_mib=meta["packed_mb"],
                         ternary_params=meta["mem_params"]["ternary"]))
    return rows


def held_tensor_bytes(model):
    seen = set()
    totals = dict(parameters=0, buffers=0, dequant=0, mask=0)
    for tensor in model.parameters():
        if id(tensor) not in seen:
            seen.add(id(tensor))
            totals["parameters"] += tensor.numel() * tensor.element_size()
    for name, tensor in model.named_buffers():
        if tensor is not None and id(tensor) not in seen:
            seen.add(id(tensor))
            size = tensor.numel() * tensor.element_size()
            totals["buffers"] += size
            if name.endswith("connectivity_mask"):
                totals["mask"] += size
    for module in model.modules():
        tensor = getattr(module, "_wq", None)
        if tensor is not None and id(tensor) not in seen:
            seen.add(id(tensor))
            totals["dequant"] += tensor.numel() * tensor.element_size()
    totals["held_total"] = sum(totals[k] for k in ("parameters", "buffers", "dequant"))
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-new", type=int, default=32)
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()
    if args.max_new < 4 or args.reps < 2:
        parser.error("max-new >=4 and reps >=2 are required")
    output = ROOT / args.out
    inputs = check_inputs(output)
    for row in inputs:
        print(f"[INPUT] {row['tag']} checkpoint_bytes={row['checkpoint_bytes']} "
              f"training_ms_step={row['train_ms_step']:.2f}")
    if args.check_only:
        print("[PASS] metadata/checkpoint/output contract; model/GPU NOT_RUN")
        return 0
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("P092 Stage3Wb requires user-run CUDA")
    from scripts.bench_infer import PROMPT, bench_one
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model

    tok = load_tokenizer("ko-en")
    results = []
    for pass_no, order in enumerate((inputs, list(reversed(inputs))), 1):
        for row in order:
            gc.collect()
            torch.cuda.empty_cache()
            before = torch.cuda.memory_allocated()
            model, cfg, device = load_model("dense", str(row["checkpoint"]), device="cuda")
            torch.cuda.synchronize()
            held = held_tensor_bytes(model)
            allocated = torch.cuda.memory_allocated() - before
            masks = [v for name, v in model.named_buffers()
                     if name.endswith("connectivity_mask")]
            mask_n = sum(v.numel() for v in masks)
            mask_active = sum(int(v.sum().item()) for v in masks)
            if row["mode"] == "none" and mask_n:
                raise RuntimeError("dense control unexpectedly has connectivity mask")
            if row["mode"] != "none":
                if mask_n != row["ternary_params"]:
                    raise RuntimeError("mask does not cover every ternary weight")
                if abs(mask_active / mask_n - row["density"]) > 0.002:
                    raise RuntimeError("loaded mask density mismatch")
            tok_s, ttft_ms, _ = bench_one(
                model, cfg, tok, PROMPT, args.max_new, device, args.reps,
                use_cache=True, logits_last_only=True)
            results.append(dict(tag=row["tag"], pass_no=pass_no,
                                checkpoint_bytes=row["checkpoint_bytes"],
                                train_ms_step=row["train_ms_step"],
                                reported_runtime_mib=row["reported_runtime_mib"],
                                reported_packed_mib=row["reported_packed_mib"],
                                held_tensor_bytes=held,
                                cuda_allocated_model_delta_bytes=allocated,
                                mask_elements=mask_n, mask_active=mask_active,
                                ttft_ms=ttft_ms, decode_tok_s=tok_s))
            print(f"[MEASURE] pass={pass_no} {row['tag']} "
                  f"held_mib={held['held_total']/1048576:.2f} "
                  f"mask_mib={held['mask']/1048576:.2f} "
                  f"ttft_ms={ttft_ms:.2f} tok_s={tok_s:.2f}", flush=True)
            del model
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(dict(schema="TINYLM_P092_STAGE3WB_DIAGNOSTIC_V1",
                       status="DIAGNOSTIC_ONLY", device="cuda", runs=results,
                       limitations=["single seed 100M; no quality conclusion",
                                    "decode includes Python dispatch, not pure GEMM",
                                    "allocated delta is not RSS or peak",
                                    "historical training ms/step is not inference tok/s"]),
                  stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(f"[PASS] wrote {output.relative_to(ROOT)}; quality/adoption NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
