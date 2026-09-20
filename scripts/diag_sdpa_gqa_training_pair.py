#!/usr/bin/env python3
"""P060B Stage1W: judge an off/on 250-step pair from training JSON only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "runs" / "logs"
MATCHED = (
    "preset", "arch", "data", "tokens", "pool_tokens", "steps", "micro_bs",
    "accum", "seq", "seed", "optimizer", "muon_scale", "muon_lr_mult",
    "matrix_weight_decay_effective", "cla_group", "grad_ckpt",
)


def _load(raw_tag: str):
    hits = sorted(LOGS.glob(f"*_{raw_tag}.json"))
    if len(hits) != 1:
        raise ValueError(f"tag {raw_tag!r} expected one JSON, found {len(hits)}")
    return hits[0], json.loads(hits[0].read_text(encoding="utf-8"))


def _contract_errors(off, on):
    errors = []
    for field in MATCHED:
        if off.get(field) != on.get(field):
            errors.append(f"{field}: off={off.get(field)!r} on={on.get(field)!r}")
    if bool(off.get("sdpa_gqa")):
        errors.append("off arm recorded sdpa_gqa=true")
    if not bool(on.get("sdpa_gqa")):
        errors.append("on arm did not record sdpa_gqa=true")
    if int(off.get("steps") or 0) != 250:
        errors.append(f"expected 250-step probe, got {off.get('steps')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off-tag", default="p060b_s1w_off250")
    parser.add_argument("--on-tag", default="p060b_s1w_on250")
    parser.add_argument("--max-speed-ratio", type=float, default=1.05)
    parser.add_argument("--min-memory-reduction", type=float, default=0.10)
    args = parser.parse_args()
    try:
        off_path, off = _load(args.off_tag)
        on_path, on = _load(args.on_tag)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[GATE FAIL artifacts] {type(exc).__name__}: {exc}")
        return 2

    errors = _contract_errors(off, on)
    if errors:
        for error in errors:
            print(f"[GATE FAIL contract] {error}")
        return 3
    off_ms = float(off.get("ms_step_median") or math.nan)
    on_ms = float(on.get("ms_step_median") or math.nan)
    off_vram = float(off.get("vram_reserved_gb") or math.nan)
    on_vram = float(on.get("vram_reserved_gb") or math.nan)
    if not all(math.isfinite(value) and value > 0 for value in (off_ms, on_ms, off_vram, on_vram)):
        print("[GATE FAIL metrics] ms_step_median/vram_reserved_gb missing or non-finite")
        return 4
    if int(off.get("n_skip") or 0) or int(on.get("n_skip") or 0):
        print(f"[GATE FAIL stability] skip off={off.get('n_skip')} on={on.get('n_skip')}")
        return 4

    speed_ratio = on_ms / off_ms
    memory_reduction = 1.0 - on_vram / off_vram
    print(f"off={off_path.name} ms_step_median={off_ms:.3f} vram_reserved_gb={off_vram:.3f}")
    print(f"on={on_path.name} ms_step_median={on_ms:.3f} vram_reserved_gb={on_vram:.3f}")
    print(f"on/off speed_ratio={speed_ratio:.4f} memory_reduction={memory_reduction:.3%}")
    print("[LIMIT] 250-step/32.768M probe judges speed and training memory only; quality NOT_RUN")
    if speed_ratio > args.max_speed_ratio or memory_reduction < args.min_memory_reduction:
        print(f"[GATE NEGATIVE] requires speed<=+{args.max_speed_ratio - 1:.0%} and "
              f"reserved-memory reduction>={args.min_memory_reduction:.0%}")
        return 8
    print("[GATE CANDIDATE] training speed/memory contract passed; full quality remains NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
