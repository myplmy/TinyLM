#!/usr/bin/env python3
"""P103A Stage1bW user-run write-once M0 2M fixed-window boundary builder.

It writes only a new runs/bench namespace after pinned parent/cache checks.
Codex may run --self-test/--check-only, never the model/build path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "runs" / "bench" / "p103a_stage1bw_m0_fixed2m"
SOURCE_TOKENS = 2_000_000
SEQ = 1024
DIM = 768
SPLIT = 12
GROUP = 64


def digest_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


def sha_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest().upper()


def code_digest() -> str:
    sha = hashlib.sha256()
    for name in ("tinylm/train/p103a_model_boundary.py",
                 "tinylm/model/transformer.py", "tinylm/model/modules.py",
                 "tinylm/model/ternary.py"):
        sha.update(name.encode("utf-8"))
        sha.update((ROOT / name).read_bytes())
    return sha.hexdigest().upper()


def manifest(precision: str, source_sha: str, backend: str):
    from tinylm.train.p103a_contract import (
        fixed_window_cache_budget, validate_window_cache_manifest,
    )
    from tinylm.train.p101a_assets import CACHE, EXPECTED, PARENT, TOKENIZER
    layout = fixed_window_cache_budget(SOURCE_TOKENS, SEQ, DIM, group=GROUP)
    data = {
        "schema": "P103A_FIXED_WINDOW_CACHE_V1",
        "parent_sha256": EXPECTED[PARENT],
        "tokenizer_sha256": EXPECTED[TOKENIZER],
        "source_cache_meta_sha256": EXPECTED[CACHE / "meta.json"],
        "source_window_sha256": source_sha,
        "lower_function_sha256": code_digest(),
        "context_policy": "fixed_window_causal_start0_v1",
        "tokenizer_lineage": "legacy32",
        "backend_signature": backend,
        "split_layer": SPLIT,
        "precision": precision,
        "source_tokens": SOURCE_TOKENS,
        "seq": SEQ,
        "dim": DIM,
        "group": GROUP,
        "windows": layout["windows"],
        "boundary_tokens": layout["boundary_tokens"],
        "payload_bytes": (layout["exact_payload_bytes"] if precision == "fp32"
                          else layout["int8_per64_payload_bytes"]),
        "unused_source_tokens": layout["unused_source_tokens"],
    }
    validate_window_cache_manifest(data)
    return data


def self_test() -> None:
    from tinylm.train.p103a_contract import fixed_window_cache_budget
    budget = fixed_window_cache_budget(SOURCE_TOKENS, SEQ, DIM, group=GROUP)
    assert budget["windows"] == 1953 and budget["boundary_tokens"] == 1_999_872
    assert budget["exact_payload_bytes"] == 6_143_606_784
    assert budget["int8_per64_payload_bytes"] == 1_631_895_552
    print("[PASS] P103A 2M fixed-window exact/INT8 byte and 127-token-tail contract; model NOT_RUN")


def check_only() -> None:
    self_test()
    print("[CHECK_ONLY] P103A target write-once runs/bench/p103a_stage1bw_m0_fixed2m; pinned parent/cache/model NOT_READ")


def build(batch_windows: int) -> int:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("write-once P103A output already exists")
    if shutil.disk_usage(ROOT).free < 12 * 2**30:
        raise OSError("P103A needs at least 12 GiB free for exact/INT8 files and staging")
    import numpy as np
    import torch
    import torch.nn.functional as F
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.init_utils import _strip
    from tinylm.train.p101a_assets import CACHE, EXPECTED, PARENT, verify_m0_assets
    from tinylm.train.p103a_contract import (
        fixed_window_cache_budget, fixed_window_starts, gather_fixed_window_xy,
        quantize_boundary_int8, dequantize_boundary_int8,
    )
    from tinylm.train.p103a_model_boundary import (
        freeze_lower_dependency, frozen_prefix_boundary, tail_logits_from_boundary,
    )

    verify_m0_assets()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA user-run build required; no CPU fallback")
    torch.set_num_threads(1)
    state = torch.load(PARENT, map_location="cpu", weights_only=True)
    if not isinstance(state, dict) or not {"model", "cfg", "step"}.issubset(state):
        raise ValueError("M0 parent checkpoint schema differs")
    cfg = TMTConfig(**state["cfg"])
    if (cfg.n_layers != 16 or cfg.cla_group != 2 or cfg.dim != DIM
            or cfg.tie_mlp or cfg.max_seq_len < SEQ):
        raise ValueError("M0 12/4 geometry differs")
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(_strip(state["model"]), strict=True)
    del state
    freeze_lower_dependency(model, SPLIT)
    model = model.to("cuda").eval()
    meta = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
    source = np.memmap(CACHE / "train.bin", dtype=np.uint16, mode="r",
                       shape=(int(meta["train"]),))[:SOURCE_TOKENS]
    layout = fixed_window_cache_budget(SOURCE_TOKENS, SEQ, DIM, group=GROUP)
    source_sha = digest_bytes(source[:layout["boundary_tokens"] + 1].tobytes())
    starts = fixed_window_starts(SOURCE_TOKENS, SEQ)
    windows = int(starts.numel())
    first = torch.from_numpy(np.asarray(source[:SEQ + 1], dtype=np.int64).copy())
    first_x, first_y = gather_fixed_window_xy(first, torch.tensor([0]), SEQ)
    first_x, first_y = first_x.cuda(), first_y.cuda()
    with torch.no_grad():
        first_boundary = frozen_prefix_boundary(model, first_x, SPLIT)
        full_logits = model(first_x).float()
        split_logits = tail_logits_from_boundary(model, first_boundary, SPLIT).float()
        first_delta = float((full_logits - split_logits).abs().amax())
        full_loss = F.cross_entropy(full_logits.reshape(-1, cfg.vocab_size),
                                    first_y.reshape(-1))
        split_loss = F.cross_entropy(split_logits.reshape(-1, cfg.vocab_size),
                                     first_y.reshape(-1))
        first_loss_delta = float((full_loss - split_loss).abs())
    if max(first_delta, first_loss_delta) > 5e-5:
        raise ValueError(f"first actual 1024-token M0 boundary differs: logits={first_delta}, loss={first_loss_delta}")
    del first_x, first_y, first_boundary, full_logits, split_logits
    torch.cuda.empty_cache()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".p103a_stage1bw_", dir=OUTPUT.parent))
    exact_path = temporary / "exact.fp32.bin"
    code_path = temporary / "codes.int8.bin"
    scale_path = temporary / "scales.fp32.bin"
    exact = np.memmap(exact_path, dtype=np.float32, mode="w+",
                      shape=(windows, SEQ, DIM))
    codes = np.memmap(code_path, dtype=np.int8, mode="w+",
                      shape=(windows, SEQ, DIM))
    scales = np.memmap(scale_path, dtype=np.float32, mode="w+",
                       shape=(windows, SEQ, DIM // GROUP))
    window_hashes = []
    worst_int8_nrms = 0.0
    started = time.perf_counter()
    with torch.no_grad():
        for offset in range(0, windows, batch_windows):
            end = min(offset + batch_windows, windows)
            blocks = []
            for index in range(offset, end):
                start = index * SEQ
                block = np.asarray(source[start:start + SEQ + 1],
                                   dtype=np.int64).copy()
                if block.size != SEQ + 1:
                    raise ValueError("fixed source window was truncated")
                blocks.append(block)
                window_hashes.append(digest_bytes(block[:-1].tobytes()))
            raw = torch.from_numpy(np.stack(blocks))
            x = raw[:, :-1].cuda()
            hidden = frozen_prefix_boundary(model, x, SPLIT).detach().float()
            values = hidden.cpu().numpy()
            exact[offset:end] = values
            flat = hidden.reshape(-1, DIM)
            q, scale = quantize_boundary_int8(flat, group=GROUP)
            approx = dequantize_boundary_int8(q, scale, group=GROUP)
            error = (approx - flat).square().mean().sqrt() / flat.square().mean().sqrt().clamp_min(1e-12)
            worst_int8_nrms = max(worst_int8_nrms, float(error))
            codes[offset:end] = q.cpu().numpy().reshape(end - offset, SEQ, DIM)
            scales[offset:end] = scale.cpu().numpy().reshape(end - offset, SEQ, DIM // GROUP)
            if end == windows or end % 128 < batch_windows:
                print(f"[P103A] windows={end}/{windows} int8_nrms_max={worst_int8_nrms:.7g}", flush=True)
    exact.flush(); codes.flush(); scales.flush()
    del exact, codes, scales
    expected_sizes = {
        exact_path: layout["exact_payload_bytes"],
        code_path: layout["boundary_tokens"] * DIM,
        scale_path: layout["boundary_tokens"] * (DIM // GROUP) * 4,
    }
    for path, expected in expected_sizes.items():
        if path.stat().st_size != expected:
            raise ValueError(f"P103A payload bytes differ: {path.name}")
    backend = f"torch={torch.__version__};cuda={torch.version.cuda};device={torch.cuda.get_device_name(0)}"
    extra = {
        "window_hashes_sha256": digest_bytes(
            b"".join(bytes.fromhex(value) for value in window_hashes)),
        "file_sha256": {path.name: sha_file(path) for path in expected_sizes},
        "first_window_exact_logit_max_abs": first_delta,
        "first_window_exact_loss_abs": first_loss_delta,
        "int8_boundary_nrms_max": worst_int8_nrms,
        "build_wall_sec": time.perf_counter() - started,
        "window_count": windows,
        "warning": "cache build is not training speed, RSS or language quality",
    }
    (temporary / "window_hashes.json").write_text(
        json.dumps(window_hashes, ensure_ascii=False), encoding="utf-8")
    for precision, filename in (("fp32", "manifest_exact.json"),
                                ("int8_per64", "manifest_int8.json")):
        data = manifest(precision, source_sha, backend)
        data.update(extra)
        (temporary / filename).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("P103A final output appeared during build; temporary files kept for review")
    os.rename(temporary, OUTPUT)
    print(f"[PASS] P103A fixed2M write-once files={OUTPUT.relative_to(ROOT)} windows={windows} "
          f"exact_bytes={layout['exact_payload_bytes']} int8_bytes={layout['int8_per64_payload_bytes']}")
    print(f"[LIMIT] first-window exact logits={first_delta:.7g} loss={first_loss_delta:.7g}; "
          f"INT8 NRMS max={worst_int8_nrms:.7g}; GPU whole-step/quality/RSS NOT_RUN")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--batch", type=int, default=2)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.check_only:
        check_only()
        return 0
    if not 1 <= args.batch <= 8:
        parser.error("--batch must be 1..8")
    try:
        return build(args.batch)
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"[FAIL] P103A build: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[LIMIT] partial temporary output, if any, is left untouched for user review")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
