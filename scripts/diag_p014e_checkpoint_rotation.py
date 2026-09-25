#!/usr/bin/env python3
"""P014E Stage1Wa: CPU actual-checkpoint weight/rotation micro attribution.

The checkpoint is user-loaded only. Synthetic activations isolate one TLinear
projection; these measurements do not establish whole-model quality or RSS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diag_p014e_rotation_contract import K, nrms, rotate, ternary_g128, theoretical_bytes

MODES = (("no_rotation", K, 0), ("three_256", K, 256), ("pad_1024", 1024, 1024))
LABELS = {
    "m100s10_ko-en_300M_d14_cla2_norecur_rms4": ("A", "dense"),
    "m100R1c_ko-en_300M_mC_initonly_s2": ("B", "tied"),
    "m100s8_ko-en_300M_d12_cla2_r20": ("C", "dense"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def regular_checkpoint(raw: str) -> Path:
    candidate = ROOT / raw
    path = candidate.resolve()
    if not path.is_relative_to((ROOT / "runs" / "ckpt").resolve()):
        raise ValueError("checkpoint must be under runs/ckpt")
    if candidate.is_symlink() or not path.is_file():
        raise ValueError("checkpoint absent or linked")
    return path


def preflight(raw: str, arch: str) -> dict:
    path = regular_checkpoint(raw)
    selected = LABELS.get(path.stem)
    if selected is None or selected[1] != arch:
        raise ValueError("checkpoint/arch is outside the approved A/B/C panel")
    meta_path = ROOT / "runs" / "logs" / (path.stem + ".json")
    if meta_path.is_symlink() or not meta_path.is_file():
        raise ValueError("same-stem training JSON absent or linked")
    record = json.loads(meta_path.read_text(encoding="utf-8"))
    if (record.get("arch") != arch or record.get("data") != "ko-en"
            or record.get("micro_group") != 128 or record.get("sparse34") is not False
            or record.get("tokens") != 300023808):
        raise ValueError("checkpoint is not the preregistered ko-en 300M g128 non-sparse lineage")
    return {"checkpoint": str(path.relative_to(ROOT)), "json": str(meta_path.relative_to(ROOT)),
            "arch": arch, "label": selected[0], "seed": record.get("seed"), "preset": record.get("preset"),
            "train_repeat": record.get("train_repeat"), "checkpoint_bytes": path.stat().st_size}


def _timing_ms(fn, warmup: int, iters: int) -> tuple[float, float]:
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(iters):
        started = time.perf_counter_ns()
        fn()
        times.append((time.perf_counter_ns() - started) / 1e6)
    ordered = sorted(times)
    return statistics.median(ordered), ordered[math.ceil(0.95 * len(ordered)) - 1]


def compare_weight(weight: np.ndarray, inputs: np.ndarray, seed: int,
                   warmup: int, iters: int) -> list[dict]:
    if weight.ndim != 2 or inputs.ndim != 2 or weight.shape[1] != K or inputs.shape[1] != K:
        raise ValueError("Stage1Wa requires weight [out,768] and input [batch,768]")
    if weight.dtype != np.float32 or inputs.dtype != np.float32:
        raise ValueError("Stage1Wa fixes float32 input and checkpoint weight")
    reference = inputs @ weight.T
    rows = []
    for mode, width, block in MODES:
        w = np.pad(weight, ((0, 0), (0, width - K)))
        x = np.pad(inputs, ((0, 0), (0, width - K)))
        signs = None
        if block:
            signs = np.random.default_rng(seed).choice(
                np.array([-1.0, 1.0], dtype=np.float32), size=width
            )
        started = time.perf_counter_ns()
        rotated_w = rotate(w, block, signs) if block else w
        quantized_w = ternary_g128(rotated_w)
        pack_ms = (time.perf_counter_ns() - started) / 1e6

        def call() -> np.ndarray:
            actual_x = rotate(x, block, signs) if block else x
            return actual_x @ quantized_w.T

        transformed_x = rotate(x, block, signs) if block else x
        identity = transformed_x @ rotated_w.T
        identity_error = nrms(identity, reference)
        if identity_error > 1e-5:
            raise AssertionError(f"{mode} float identity nrms={identity_error}")
        output = call()
        p50_ms, p95_ms = _timing_ms(call, warmup, iters)
        rows.append({
            "mode": mode, "width": width, "rows": int(weight.shape[0]),
            "batch": int(inputs.shape[0]), "seed": seed,
            "identity_nrms": identity_error,
            "ternary_vs_float_nrms": nrms(output, reference),
            "pack_ms": pack_ms,
            "projection_plus_online_rotation_p50_ms": p50_ms,
            "projection_plus_online_rotation_p95_ms": p95_ms,
            "theoretical_code_scale_bytes": theoretical_bytes(weight.shape[0], width),
            "actual_fp32_weight_bytes": int(quantized_w.nbytes),
        })
    return rows


def select_modules(model) -> list[tuple[str, object]]:
    from tinylm.model.ternary import TLinear
    gates = [(name, module) for name, module in model.named_modules()
             if isinstance(module, TLinear) and name.endswith("gate_proj")
             and tuple(module.weight.shape)[1] == K]
    if not gates:
        raise ValueError("no actual TLinear gate_proj with width 768")
    indices = sorted({0, len(gates) // 2, len(gates) - 1})
    return [gates[index] for index in indices]


def self_test() -> None:
    rng = np.random.default_rng(20260926)
    weight = rng.normal(0, 0.03, size=(8, K)).astype(np.float32)
    inputs = rng.normal(0, 1.0, size=(4, K)).astype(np.float32)
    rows = compare_weight(weight, inputs, 1337, 1, 2)
    assert [row["mode"] for row in rows] == [entry[0] for entry in MODES]
    assert all(math.isfinite(row["ternary_vs_float_nrms"]) for row in rows)
    assert rows[2]["theoretical_code_scale_bytes"] > rows[0]["theoretical_code_scale_bytes"]
    for broken in (weight[:, :512], weight.astype(np.float64)):
        try:
            compare_weight(broken, inputs, 1337, 1, 2)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid checkpoint mirror accepted")
    print("[PASS] P014E Stage1Wa synthetic math/timing contract; checkpoint/model NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--ckpt")
    parser.add_argument("--arch", choices=("dense", "tied"))
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--iters", type=int, default=7)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.ckpt or not args.arch:
        parser.error("--ckpt and --arch are required outside --self-test")
    if min(args.batch, args.warmup, args.iters) < 1:
        parser.error("batch, warmup and iters must be positive")
    try:
        evidence = preflight(args.ckpt, args.arch)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P014E checkpoint preflight: {type(exc).__name__}: {exc}")
        return 2
    if args.check_only:
        print(json.dumps(dict(evidence, status="STATIC_ONLY"), ensure_ascii=False, sort_keys=True))
        return 0

    import torch
    from tinylm.infer.generate import load_model
    torch.set_num_threads(1)
    started = time.perf_counter()
    model, cfg, _ = load_model(args.arch, str(ROOT / evidence["checkpoint"]), "cpu")
    load_sec = time.perf_counter() - started
    if (cfg.dim != K or cfg.micro_group != 128 or cfg.sparse34
            or not math.isclose(cfg.twn_thr_ratio, 0.7, abs_tol=1e-12)):
        print("[FAIL] P014E actual model config does not match g128/threshold0.7/non-sparse mirror")
        return 2
    print(json.dumps(dict(evidence,
                          checkpoint_sha256=sha256_file(ROOT / evidence["checkpoint"]),
                          model_load_sec=load_sec,
                          selected_count=len(select_modules(model))),
                     ensure_ascii=False, sort_keys=True))
    for name, module in select_modules(model):
        weight = np.asarray(module._w().detach().cpu(), dtype=np.float32)
        inputs = np.random.default_rng(args.seed).normal(
            0, 1, size=(args.batch, K)
        ).astype(np.float32)
        rows = compare_weight(weight, inputs, args.seed, args.warmup, args.iters)
        for row in rows:
            print(json.dumps(dict(row, module=name, label=evidence["label"]),
                             ensure_ascii=False, sort_keys=True))
    print("[MEASURED_NO_ADOPTION] actual checkpoint weights, synthetic activations and one-thread projection micro wall only")
    print("[NOT_RUN] whole-model CPU decode p95, physical 2-bit packing/RSS, GPU whole-step and full-val quality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
