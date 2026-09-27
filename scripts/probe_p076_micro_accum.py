#!/usr/bin/env python3
"""Bounded synthetic P076 B3 memory/throughput probe, never a quality result.

No parent checkpoint, dataset, HF file, cache, or output checkpoint is read or
written.  The eight synthetic sequences are identical across arms; changing
micro-batch only changes how they are split across one optimizer update.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def micro_indices(micro_bs: int, accum: int) -> tuple[tuple[int, ...], ...]:
    if micro_bs not in (4, 8) or micro_bs * accum != 128:
        raise ValueError("P076 fixed effective batch requires 8x16 or 4x32")
    return tuple(tuple(range((i * micro_bs) % 8,
                             (i * micro_bs) % 8 + micro_bs))
                 for i in range(accum))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--micro-bs", type=int, choices=(4, 8), required=True)
    parser.add_argument("--accum", type=int, required=True)
    parser.add_argument("--no-ckpt", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        indices = micro_indices(args.micro_bs, args.accum)
    except ValueError as exc:
        parser.error(str(exc))
    counts = {i: sum(i in group for group in indices) for i in range(8)}
    assert set(counts.values()) == {16}, counts
    contract = {
        "schema": "P076_MICRO_ACCUM_V1", "micro_bs": args.micro_bs,
        "accum": args.accum, "seq": 1024, "effective_tokens": 131_072,
        "activation_checkpoint": not args.no_ckpt,
        "same_eight_sequences_each_seen": 16,
        "compiled": False, "parent_init": "RANDOM_NOT_P076_PARENT",
        "data": "SYNTHETIC_IN_MEMORY", "checkpoint_write": False,
    }
    if args.check_only:
        print(json.dumps(contract, sort_keys=True))
        print("[CHECK_ONLY] contract and partition PASS; model/GPU/cache NOT_RUN")
        return 0

    import torch

    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.trainer import _ce_chunked

    if not torch.cuda.is_available():
        print("[HOLD] CUDA unavailable; no model started")
        return 8
    free_bytes, total_bytes = torch.cuda.mem_get_info()
    if free_bytes < 12_000 * 2**20:
        print(f"[HOLD] CUDA free {free_bytes // 2**20}MiB < 12000MiB; no model started")
        return 8
    torch.set_num_threads(1)
    torch.manual_seed(1337)
    cfg = build_config("m100R1c", "tied", 1024, not args.no_ckpt)
    cfg.attn_group = cfg.cla_group = 2
    model = TiedMLPTransformer(cfg).cuda()
    matrices, _ = split_params(model)
    matrix_ids = {id(param) for param in matrices}
    groups = []
    for group in model.param_groups(1e-3):
        parameters = [p for p in group["params"] if id(p) not in matrix_ids]
        if parameters:
            groups.append(dict(group, params=parameters))
    adamw = torch.optim.AdamW(groups, betas=(0.9, 0.95), eps=1e-8)
    muon = Muon(matrices, lr=4e-3, scale_mode="rms", weight_decay=0)
    # Shifted targets create a next-token workload.  They are random text and
    # are NEVER an absolute CE/quality measurement.
    tokens = torch.randint(0, cfg.vocab_size, (8, 1025), device="cuda")
    x_all, y_all = tokens[:, :-1], tokens[:, 1:]
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    try:
        for group in indices:
            start, end = group[0], group[-1] + 1
            x, y = x_all[start:end], y_all[start:end]
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(x)
                ce = _ce_chunked(logits.reshape(-1, cfg.vocab_size),
                                 y.reshape(-1), 2048)
                loss = ce / args.accum
            loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        if not math.isfinite(float(grad_norm)):
            print("[FAIL] synthetic gradient norm nonfinite")
            return 9
        adamw.step()
        muon.step()
        torch.cuda.synchronize()
    except torch.cuda.OutOfMemoryError as exc:
        print(f"[GATE NEGATIVE] synthetic update OOM: {exc}")
        return 8
    elapsed = time.monotonic() - started
    contract.update({
        "step_count": 1, "wall_sec": round(elapsed, 3),
        "effective_tokens_per_sec": round(131_072 / elapsed, 1),
        "peak_allocated_mib": torch.cuda.max_memory_allocated() // 2**20,
        "peak_reserved_mib": torch.cuda.max_memory_reserved() // 2**20,
        "initial_cuda_free_mib": free_bytes // 2**20,
        "gpu_total_mib": total_bytes // 2**20,
        "finite_gradient": True,
        "limit": "one eager synthetic update; no compile/parent/dataset/teacher; not 300M training quality or stable wall",
    })
    print(json.dumps(contract, sort_keys=True))
    print("[PASS] synthetic one-update VRAM/time only; real trainer quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
