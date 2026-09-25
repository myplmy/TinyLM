#!/usr/bin/env python3
"""P014E G0: model-free fixed-Hadamard / g128 ternary math and byte contract.

This deliberately does not load a checkpoint, GPU backend, or protected data.
Numeric ternary errors and theoretical code bytes are diagnostic, not adoption.
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np


K = 768
GROUP = 128
THRESHOLD = 0.7
SEEDS = (1337, 2024, 31415)
FP64_MAX_ABS = 1e-10
FP32_NRMS = 1e-5


def fwht(values: np.ndarray, block: int) -> np.ndarray:
    """Normalized block-diagonal Walsh-Hadamard transform along the last axis."""
    if block <= 0 or block & (block - 1) or values.shape[-1] % block:
        raise ValueError("block must be a power of two dividing the final width")
    out = np.array(values, copy=True)
    for start in range(0, out.shape[-1], block):
        sub = out[..., start:start + block]
        width = 1
        while width < block:
            pair = sub.reshape(*sub.shape[:-1], block // (2 * width), 2, width)
            left = pair[..., 0, :].copy()
            right = pair[..., 1, :].copy()
            pair[..., 0, :] = left + right
            pair[..., 1, :] = left - right
            width *= 2
        sub /= math.sqrt(block)
    return out


def rotate(values: np.ndarray, block: int, signs: np.ndarray) -> np.ndarray:
    return fwht(values * signs, block)


def inverse_rotate(values: np.ndarray, block: int, signs: np.ndarray) -> np.ndarray:
    return fwht(values, block) * signs


def ternary_g128(weight: np.ndarray) -> np.ndarray:
    """Forward-only mirror of tinylm/model/ternary.py default g128, not STE."""
    if weight.ndim != 2 or weight.shape[1] % GROUP:
        raise ValueError("g128 requires a matrix with width divisible by 128")
    groups = weight.reshape(weight.shape[0], -1, GROUP)
    magnitude = np.abs(groups)
    mask = magnitude >= THRESHOLD * magnitude.mean(axis=-1, keepdims=True)
    count = np.maximum(mask.sum(axis=-1, keepdims=True), 1)
    alpha = (magnitude * mask).sum(axis=-1, keepdims=True) / count
    return (np.sign(groups) * mask * alpha).reshape(weight.shape)


def nrms(actual: np.ndarray, reference: np.ndarray) -> float:
    ref = reference.astype(np.float64)
    delta = actual.astype(np.float64) - ref
    return float(np.sqrt(np.mean(delta * delta)) / max(np.sqrt(np.mean(ref * ref)), 1e-12))


def theoretical_bytes(rows: int, width: int) -> int:
    """2-bit codes plus fp32 g128 scales only; not physical packed/runtime/RSS."""
    return math.ceil(rows * width * 2 / 8) + rows * (width // GROUP) * 4


def self_test() -> dict:
    rng = np.random.default_rng(20260925)
    weight64 = rng.normal(0, 0.04, size=(8, K)).astype(np.float64)
    input64 = rng.normal(0, 1.0, size=(4, K)).astype(np.float64)
    records = []
    for seed in SEEDS:
        for mode, width, block in (("three_256", K, 256), ("pad_1024", 1024, 1024)):
            local = np.random.default_rng(seed)
            signs = local.choice(np.array([-1, 1], dtype=np.int8), size=width)
            for dtype in (np.float64, np.float32):
                x = np.pad(input64.astype(dtype), ((0, 0), (0, width - K)))
                w = np.pad(weight64.astype(dtype), ((0, 0), (0, width - K)))
                s = signs.astype(dtype)
                xr, wr = rotate(x, block, s), rotate(w, block, s)
                reference = x @ w.T
                transformed = xr @ wr.T
                inverse_error = nrms(inverse_rotate(xr, block, s), x)
                identity_max = float(np.max(np.abs(transformed - reference)))
                identity_nrms = nrms(transformed, reference)
                if dtype == np.float64 and identity_max > FP64_MAX_ABS:
                    raise AssertionError(f"{mode}/{seed}: FP64 rotation identity failed")
                if dtype == np.float32 and identity_nrms > FP32_NRMS:
                    raise AssertionError(f"{mode}/{seed}: FP32 rotation identity failed")
                if inverse_error > (FP64_MAX_ABS if dtype == np.float64 else FP32_NRMS):
                    raise AssertionError(f"{mode}/{seed}: inverse rotation failed")
                quantized = xr @ ternary_g128(wr).T
                records.append({"mode": mode, "seed": seed, "dtype": np.dtype(dtype).name,
                                "width": width, "identity_max_abs": identity_max,
                                "identity_nrms": identity_nrms, "inverse_nrms": inverse_error,
                                "ternary_vs_float_nrms": nrms(quantized, reference),
                                "theoretical_code_scale_bytes": theoretical_bytes(w.shape[0], width)})
    if len(records) != 12:
        raise AssertionError("expected 3 seeds x 2 rotations x 2 precisions")
    for invalid in (0, 192, 2048):
        try:
            fwht(np.zeros((1, K)), invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid block {invalid} was accepted")
    return {"schema": "P014E_G0_ROTATION_CONTRACT_V1", "status": "SYNTHETIC_PASS",
            "source": "independent NumPy mirror of TLinear g128 threshold/alpha; no checkpoint",
            "threshold": {"fp64_max_abs": FP64_MAX_ABS, "fp32_nrms": FP32_NRMS},
            "records": records,
            "byte_accounting": "2-bit code + fp32 group scale only; excludes seed, runtime, RSS, KV and online rotation",
            "not_run": ["checkpoint_sensitivity", "actual_packed_bytes", "cpu_wall", "gpu_whole_step",
                        "full_val", "korean_english_quality", "learnable_rotation"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", required=True)
    parser.parse_args()
    result = self_test()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("[PASS] P014E G0 synthetic rotation identity/g128 byte contract; model quality and speed NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
