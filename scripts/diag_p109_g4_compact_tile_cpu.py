"""Isolate the eight-token workspace on the verified static R4 runner."""

from datetime import datetime, timedelta
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import torch

from scripts import diag_p109_g4_compact_static_cpu as static


dynamic = static.dynamic
TAG = "p109_g4_compact_cpu_r4_tile8_v1_20261119"
OUT = static.OUT.with_name(TAG)
ORIGINAL = b"constexpr int Group = 128, PackedGroup = 26, Tile = 32;"
CHANGED = b"constexpr int Group = 128, PackedGroup = 26, Tile = 8;"


def build():
    canonical = (dynamic.ROOT / dynamic.CPP).read_bytes()
    assert canonical.count(ORIGINAL) == 1
    source = canonical.replace(ORIGINAL, CHANGED, 1)
    scratch = Path(tempfile.mkdtemp(prefix="p109_g4_tile8_", dir="/tmp"))
    obj, binary = scratch / "p014e_lookup.o", scratch / "g4"
    commands = [
        ["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
         "-c", dynamic.C, "-o", str(obj)],
        ["/usr/bin/g++", "-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off",
         "-Wall", "-Wextra", "-Werror", "-x", "c++", "-", "-x", "none", str(obj), "-static", "-o", str(binary)],
    ]
    subprocess.run(commands[0], cwd=dynamic.ROOT, timeout=90, check=True)
    subprocess.run(commands[1], cwd=dynamic.ROOT, timeout=90, input=source, check=True)
    assert "INTERP" not in subprocess.check_output(["/usr/bin/readelf", "-l", str(binary)], text=True)
    dynamic.WRITE(OUT / "compiler.json", dict(
        commands=commands, binary=str(binary), sha256=dynamic.SHA(binary), bytes=binary.stat().st_size,
        source_sha256=sha256(source).hexdigest().upper(), source_change=[32, 8],
    ))
    return binary


@torch.inference_mode()
def run():
    orig = dynamic.READ(dynamic.OUT / "report.json")
    previous = dynamic.READ(static.OUT / "report.json")
    original_profile = dynamic.READ(dynamic.OUT / "profile.json")
    pins = dynamic.pins()
    assert pins == {k: v for k, v in original_profile.items() if k != "cpu"}
    assert previous["profile_sha256"] == dynamic.SHA(static.OUT / "profile.json")
    assert previous["sealed_fd_closed"] and previous["short"]["passed"] and orig["short"]["numerical_gate_passed"]
    assert previous["artifact"] == orig["artifact"]
    previous_binary = dynamic.READ(static.OUT / "compiler.json")
    binary32 = Path(previous_binary["binary"])
    assert binary32.is_relative_to(Path("/tmp")) and not binary32.is_symlink()
    assert dynamic.SHA(binary32) == previous_binary["sha256"]
    os.sched_setaffinity(0, {original_profile["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    dynamic.WRITE(OUT / "profile.json", dict(
        tag=TAG, pins=pins, source=dynamic.SHA(Path(__file__)), tile_tokens=8,
        reference_report_sha256=dynamic.SHA(static.OUT / "report.json"), reference_elf=previous_binary["sha256"],
        max_logit_difference=static.MAX_DELTA,
    ))
    binary8 = build()
    model = dynamic.prior.load_candidate(pins["candidate"])
    fd = dynamic.memfile("g4_compact_tile8")
    try:
        artifact = dynamic.model_blob(model, fd, pins["candidate"]["model_tensor_bytes"])
        assert artifact == previous["artifact"]
        del model
        tokens = orig["short"]["short_input_ids"]
        ref, left = dynamic.run_native(binary32, fd, tokens, scores=True)
        short, right = dynamic.run_native(binary8, fd, tokens, scores=True)
        delta = float(np.max(np.abs(left - right)))
        short.update(max_abs_vs_static32=delta, same_ids=short["ids"] == ref["ids"], passed=delta <= static.MAX_DELTA)
        assert ref["ids"] == orig["short"]["reference_ids"]
        dynamic.WRITE(OUT / "short.json", short)
        print("P109_COMPACT_TILE8_41", short["same_ids"], delta, short["scratch_bytes"], flush=True)
        if not (short["same_ids"] and short["passed"]):
            return 8
        cases = {}
        for case, item in dynamic.READ(dynamic.PROFILE_PATH)["cases"].items():
            row, _ = dynamic.run_native(binary8, fd, item["ids"])
            old = previous["cases"][case]
            row["same_ids"] = row["ids"] == old["ids"] == orig["cases"][case]["reference_ids"]
            assert row["model_bytes"] == old["model_bytes"] and row["kv_bytes"] == old["kv_bytes"]
            assert old["scratch_bytes"] - row["scratch_bytes"] == 688128
            dynamic.WRITE(OUT / f"{case}.json", row)
            cases[case] = row
            print("P109_COMPACT_TILE8_1024", case, row["same_ids"], row["peak_rss_observed_bytes"],
                  row["seconds"][0], sum(row["seconds"][1:]), flush=True)
    finally:
        os.close(fd)
    assert not torch.cuda.is_initialized() and dynamic.pins() == pins
    dynamic.WRITE(OUT / "report.json", dict(
        short=short, cases=cases, artifact=artifact, cuda_initialized=False, checkpoint_writes=0,
        sealed_fd_closed=True, tokenizer_in_native_child=False, profile_sha256=dynamic.SHA(OUT / "profile.json"),
    ))
    return 0 if all(record["same_ids"] for record in cases.values()) else 8


if __name__ == "__main__":
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    if datetime.now(dynamic.prior.ORIGIN.CUTOFF.tzinfo) + timedelta(seconds=1200) >= dynamic.prior.ORIGIN.CUTOFF:
        raise RuntimeError("insufficient time in the authorized window")
    sys.exit(run())
