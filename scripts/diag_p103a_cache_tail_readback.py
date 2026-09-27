#!/usr/bin/env python3
"""P103A Stage1cWa: user-run read-only actual-cache tail-function gate.

Three pinned 1024-token windows are loaded from the existing 2M exact/INT8
files without rewriting them. Uncached full forward is compared to exact and
INT8 tail forward/backward on the same frozen M0 parent. This is not a 2M
whole-wall training or language-quality result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_p103a_fixed2m import (  # noqa: E402
    OUTPUT as CACHE_DIR, SEQ, DIM, SPLIT, GROUP, code_digest,
)
from tinylm.train.p101a_assets import CACHE, EXPECTED, PARENT, verify_m0_assets  # noqa: E402
from tinylm.train.p103a_contract import validate_window_cache_manifest  # noqa: E402

WINDOW_IDS = (0, 976, 1952)
MAX_ABS = 5e-5


def regular(path: Path) -> bool:
    return not path.is_symlink() and path.is_file()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def preflight() -> dict:
    if CACHE_DIR.is_symlink() or not CACHE_DIR.is_dir():
        raise FileNotFoundError("P103A pinned Stage1bW cache directory absent or linked")
    exact_path = CACHE_DIR / "manifest_exact.json"
    int8_path = CACHE_DIR / "manifest_int8.json"
    if not regular(exact_path) or not regular(int8_path):
        raise FileNotFoundError("P103A exact/INT8 cache manifests absent or linked")
    exact = json.loads(exact_path.read_text(encoding="utf-8"))
    int8 = json.loads(int8_path.read_text(encoding="utf-8"))
    validate_window_cache_manifest(exact)
    validate_window_cache_manifest(int8)
    shared = ("parent_sha256", "tokenizer_sha256", "source_cache_meta_sha256",
              "source_window_sha256", "lower_function_sha256", "context_policy",
              "tokenizer_lineage", "backend_signature", "split_layer",
              "source_tokens", "seq", "dim", "group", "windows",
              "boundary_tokens", "window_hashes_sha256")
    if (exact.get("precision") != "fp32" or int8.get("precision") != "int8_per64"
            or any(exact.get(key) != int8.get(key) for key in shared)
            or exact.get("parent_sha256") != EXPECTED[PARENT]
            or exact.get("tokenizer_sha256") != EXPECTED[ROOT / "data_cache/tok-ko-en-32768.json"]
            or exact.get("source_cache_meta_sha256") != EXPECTED[CACHE / "meta.json"]
            or exact.get("lower_function_sha256") != code_digest()
            or exact.get("seq") != SEQ or exact.get("dim") != DIM
            or exact.get("group") != GROUP or exact.get("split_layer") != SPLIT
            or exact.get("windows") != 1953):
        raise ValueError("P103A exact/INT8 provenance, model code or geometry differs")
    sizes = {"exact.fp32.bin": exact["payload_bytes"],
             "codes.int8.bin": exact["boundary_tokens"] * DIM,
             "scales.fp32.bin": exact["boundary_tokens"] * (DIM // GROUP) * 4}
    sizes["exact.fp32.bin"] = exact["payload_bytes"]
    if sizes["codes.int8.bin"] + sizes["scales.fp32.bin"] != int8["payload_bytes"]:
        raise ValueError("INT8 value/scale byte sum differs")
    for name, expected in sizes.items():
        path = CACHE_DIR / name
        if not regular(path) or path.stat().st_size != expected:
            raise ValueError(f"P103A cached payload absent, linked or byte count differs: {name}")
    hashes = CACHE_DIR / "window_hashes.json"
    if not regular(hashes):
        raise FileNotFoundError("per-window source hash index absent or linked")
    refs = json.loads(hashes.read_text(encoding="utf-8"))
    if not isinstance(refs, list) or len(refs) != exact["windows"]:
        raise ValueError("per-window source hash index count differs")
    return {"schema": "P103A_STAGE1CWA_PREFLIGHT_V1",
            "source": "same pinned M0 Stage1bW source/cache/window contract",
            "window_ids": list(WINDOW_IDS), "manifest_exact_sha256": file_sha(exact_path),
            "manifest_int8_sha256": file_sha(int8_path),
            "parent_sha256_expected": EXPECTED[PARENT],
            "source_window_sha256": exact["source_window_sha256"],
            "payload_sizes": sizes,
            "full_payload_hashes": "NOT_RUN_IN_CHECK_ONLY",
            "model_gpu": "NOT_RUN"}


def execute() -> int:
    import numpy as np
    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.init_utils import _strip
    from tinylm.train.p103a_contract import dequantize_boundary_int8
    from tinylm.train.p103a_model_boundary import freeze_lower_dependency, tail_logits_from_boundary

    report = preflight()
    verify_m0_assets()
    if not torch.cuda.is_available():
        raise RuntimeError("P103A Stage1cWa requires user-run CUDA")
    torch.set_num_threads(1)
    state = torch.load(PARENT, map_location="cpu", weights_only=True)
    cfg = TMTConfig(**state["cfg"])
    if (cfg.n_layers != 16 or cfg.cla_group != 2 or cfg.dim != DIM
            or cfg.tie_mlp or cfg.max_seq_len < SEQ):
        raise ValueError("actual M0 12/4 parent geometry differs")
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(_strip(state["model"]), strict=True)
    del state
    freeze_lower_dependency(model, SPLIT)
    model = model.cuda().train()
    metadata = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
    source = np.memmap(CACHE / "train.bin", dtype=np.uint16, mode="r",
                       shape=(int(metadata["train"]),))
    shape = (1953, SEQ, DIM)
    exact = np.memmap(CACHE_DIR / "exact.fp32.bin", dtype=np.float32,
                      mode="r", shape=shape)
    codes = np.memmap(CACHE_DIR / "codes.int8.bin", dtype=np.int8,
                      mode="r", shape=shape)
    scales = np.memmap(CACHE_DIR / "scales.fp32.bin", dtype=np.float32,
                       mode="r", shape=(1953, SEQ, DIM // GROUP))
    refs = json.loads((CACHE_DIR / "window_hashes.json").read_text(encoding="utf-8"))
    outputs = []
    for index in WINDOW_IDS:
        block = np.asarray(source[index * SEQ:index * SEQ + SEQ + 1], dtype=np.int64).copy()
        if block.size != SEQ + 1 or hashlib.sha256(block[:-1].tobytes()).hexdigest().upper() != refs[index]:
            raise ValueError(f"source window {index} no longer matches cached identity")
        x = torch.from_numpy(block[:-1].copy()).long().unsqueeze(0).cuda()
        y = torch.from_numpy(block[1:].copy()).long().unsqueeze(0).cuda()
        saved_exact = torch.from_numpy(np.asarray(exact[index]).copy()).unsqueeze(0).cuda()
        flat_codes = torch.from_numpy(np.asarray(codes[index]).copy()).reshape(-1, DIM).cuda()
        flat_scales = torch.from_numpy(np.asarray(scales[index]).copy()).reshape(-1, DIM // GROUP).cuda()
        saved_int8 = dequantize_boundary_int8(flat_codes, flat_scales, group=GROUP).reshape(1, SEQ, DIM)
        base_grad = None
        base_logits = None
        base_loss = None
        for arm in ("uncached", "exact", "int8"):
            model.zero_grad(set_to_none=True)
            torch.cuda.synchronize()
            started = time.perf_counter()
            if arm == "uncached":
                logits = model(x).float()
            else:
                logits = tail_logits_from_boundary(model, saved_exact if arm == "exact" else saved_int8,
                                                   SPLIT).float()
            loss = F.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1))
            loss.backward()
            torch.cuda.synchronize()
            wall = time.perf_counter() - started
            grad = {name: p.grad.detach().clone() for name, p in model.named_parameters()
                    if p.grad is not None}
            if arm == "uncached":
                base_grad, base_logits, base_loss = grad, logits.detach(), loss.detach()
                logit_delta = loss_delta = grad_delta = 0.0
            else:
                if set(grad) != set(base_grad):
                    raise RuntimeError(f"{arm} trainable gradient presence differs")
                logit_delta = float((logits.detach() - base_logits).abs().amax())
                loss_delta = float((loss.detach() - base_loss).abs())
                grad_delta = max(float((grad[name] - base_grad[name]).abs().amax())
                                 for name in grad)
            row = {"window": index, "arm": arm, "loss": round(float(loss.detach()), 8),
                   "logit_max_abs_vs_uncached": logit_delta,
                   "loss_abs_vs_uncached": loss_delta,
                   "grad_max_abs_vs_uncached": grad_delta,
                   "forward_backward_wall_sec": round(wall, 4),
                   "rss_max_mib_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                   "torch_reserved_mib": torch.cuda.max_memory_reserved() / 2**20}
            outputs.append(row)
            print("[P103A_TAIL] " + json.dumps(row, sort_keys=True), flush=True)
    exact_bad = [row for row in outputs if row["arm"] == "exact" and max(
        row["logit_max_abs_vs_uncached"], row["loss_abs_vs_uncached"],
        row["grad_max_abs_vs_uncached"]) > MAX_ABS]
    print(json.dumps({"schema": "P103A_STAGE1CWA_READBACK_V1",
                      "preflight": report, "rows": outputs,
                      "exact_failures": len(exact_bad),
                      "full2m_whole_wall": "NOT_RUN", "language_quality": "NOT_RUN"},
                     sort_keys=True), flush=True)
    if exact_bad:
        print("[GATE NEGATIVE] persisted exact cache differs from same fixed-window full model")
        return 8
    print("[PASS] sampled persisted exact tail forward/backward; INT8 cost is report-only")
    return 0


def self_test() -> None:
    assert WINDOW_IDS == (0, 976, 1952) and 1952 < 1953
    assert SEQ == 1024 and DIM == 768 and GROUP == 64 and SPLIT == 12
    print("[PASS] P103A fixed window0/mid/last and exact/INT8 readback geometry; model/GPU NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        if args.check_only:
            print(json.dumps(preflight(), sort_keys=True))
            print("[CHECK_ONLY] exact/INT8 provenance/size/index PASS; payload/model/GPU NOT_RUN")
            return 0
        return execute()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"[FAIL] P103A Stage1cWa {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
