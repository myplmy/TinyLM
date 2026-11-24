"""Verify ordered source exposure with the exact fixed and curriculum training plans."""

import hashlib
import os
from pathlib import Path

import numpy as np
import torch

from scripts import diag_p013_native_matched_training as design


OUT = design.ROOT / "test_result/evidence/p013_native_synthetic_source_cpu_v1_20261118"
TAG = OUT.name


def covered_positions(starts, width):
    stop = -1
    total = 0
    for start in sorted(starts):
        end = start + width
        total += max(0, end - max(start, stop))
        stop = max(end, stop)
    return total


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    assert os.environ.get("TINYLM_DIR") == str(OUT) and os.environ.get("TINYLM_HF") == str(OUT / "HF")
    if OUT.exists():
        raise FileExistsError(f"Preserve existing run {TAG}")
    profile = design.verify()
    profile_sha = design.digest(design.PROFILE)
    source_sha = design.digest(Path(__file__))
    torch.set_num_threads(1)
    from tinylm.data.loader import Loader
    from tinylm.data.prepare import prepare
    from tinylm.train.context_micro_tokens import MicroTokensCursor, parse_context_plan
    from tinylm.train.context_training_state import cache_identity

    meta = prepare("synthetic", design.POOL, exact=True)
    cache_dir = Path(meta["dir"])
    assert cache_dir.parent == OUT / "data_cache" and (meta["train"], meta["val"]) == (4_975_000, 25_000)
    assert meta["token_dtype"] == "uint16" and meta["vocab"] == 32768
    proof = cache_identity(cache_dir)
    source = np.memmap(cache_dir / "train.bin", dtype="uint16", mode="r")
    assert len(source) == meta["train"]
    ladder = {}
    for name in ("fixed", "curriculum"):
        plan = parse_context_plan(design.ARMS[name][0], micro_bs=design.MICRO, accum=design.ACCUM,
                                  seq=design.SEQ, steps=design.STEPS)
        loader = Loader("train", design.MICRO, design.SEQ, "cpu", cache_dir, seed=1234)
        ladder[name] = MicroTokensCursor(plan, loader, source_sha256=proof["identity_sha256"])

    rng = np.random.default_rng(1234)
    offsets = np.arange(design.SEQ + 1)
    visited = []
    digests = [hashlib.sha256(), hashlib.sha256()]
    updates = []
    for ordinal in range(design.STEPS):
        fixed = ladder["fixed"].prepare()
        curriculum = ladder["curriculum"].prepare()
        assert fixed.update == curriculum.update == ordinal
        assert len(fixed.batches) == len(curriculum.batches) == design.ACCUM
        for a, b in zip(fixed.batches, curriculum.batches, strict=True):
            starts = rng.integers(0, len(source) - design.SEQ - 1, design.MICRO)
            visited.extend(int(i) for i in starts)
            window = source[starts[:, None] + offsets[None, :]].astype(np.int64)
            assert tuple(b[0].shape) == (design.MICRO * design.SEQ // curriculum.length, curriculum.length)
            for side, expected in enumerate((window[:, :-1], window[:, 1:])):
                reference = expected.flatten()
                assert np.array_equal(a[side].numpy().flatten(), reference)
                assert np.array_equal(b[side].numpy().flatten(), reference)
                digests[side].update(reference.astype("<u2").tobytes())
        updates.append(ladder["curriculum"].finish(optimizer_applied=False))
        ladder["fixed"].finish(optimizer_applied=False)

    terminal = {name: cursor.state_dict()["cursor"] for name, cursor in ladder.items()}
    assert all(row["next_update"] == 18 and row["optimizer_updates"] == 0 and row["source_calls"] == 288
               and row["ntp_targets"] == row["draw_tokens"] == profile["exact_draw"]
               and row["rng"] == rng.bit_generator.state for row in terminal.values())
    assert len(visited) == 2304 and cache_identity(cache_dir) == proof and not torch.cuda.is_initialized()
    assert design.verify() == profile and design.digest(design.PROFILE) == profile_sha
    result = dict(schema="P013_NATIVE_SYNTHETIC_SOURCE_CPU_V1", tag=TAG,
        source_script_sha256=source_sha, training_profile_sha256=profile_sha, generated_pool=design.POOL,
        cache=proof, source_rng=terminal["fixed"]["rng"], matched_updates=len(updates), full_window_starts=len(visited),
        unique_window_starts=len(set(visited)), drawn_targets=profile["exact_draw"],
        unique_target_source_positions=covered_positions([start + 1 for start in visited], design.SEQ),
        ordered_x_sha256=digests[0].hexdigest().upper(), ordered_y_sha256=digests[1].hexdigest().upper(),
        ordered_xy_exact=True, case_updates=updates, gpu_runs=0, model_loads=0, optimizer_updates=0)
    design.write(OUT / "report.json", result)
    print("P013_NATIVE_SOURCE_MATCH", result["drawn_targets"], result["unique_target_source_positions"],
          result["ordered_y_sha256"], flush=True)


if __name__ == "__main__":
    main()
