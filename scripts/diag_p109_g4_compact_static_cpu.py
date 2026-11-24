"""Compare a static link of the same R4 inference source and tensors."""

from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import torch

from scripts import diag_p109_g4_compact_cpu as dynamic


TAG = "p109_g4_compact_cpu_r4_static_v1_20261119"
OUT = dynamic.OUT.with_name(TAG)
MAX_DELTA = 1e-6


def build():
    scratch = Path(tempfile.mkdtemp(prefix="p109_g4_static_", dir="/tmp"))
    obj, binary = scratch / "p014e_lookup.o", scratch / "g4"
    commands = [
        ["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
         "-c", dynamic.C, "-o", str(obj)],
        ["/usr/bin/g++", "-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off",
         "-Wall", "-Wextra", "-Werror", dynamic.CPP, str(obj), "-static", "-o", str(binary)],
    ]
    for command in commands:
        subprocess.run(command, cwd=dynamic.ROOT, timeout=90, check=True)
    elf = subprocess.check_output(["/usr/bin/readelf", "-l", str(binary)], text=True)
    assert "INTERP" not in elf
    dynamic.WRITE(OUT / "compiler.json", dict(
        commands=commands, binary=str(binary), sha256=dynamic.SHA(binary),
        bytes=binary.stat().st_size, interpreter_program_header=False,
    ))
    return binary


@torch.inference_mode()
def run():
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    original_profile = dynamic.READ(dynamic.OUT / "profile.json")
    pins = dynamic.pins()
    assert pins == {k: v for k, v in original_profile.items() if k != "cpu"}
    assert set(os.sched_getaffinity(0)) == {original_profile["cpu"]}
    original = dynamic.READ(dynamic.OUT / "report.json")
    assert original["profile_sha256"] == dynamic.SHA(dynamic.OUT / "profile.json")
    assert original["short"]["numerical_gate_passed"]
    prior_binary = Path(dynamic.READ(dynamic.OUT / "compiler.json")["binary"])
    assert prior_binary.is_relative_to(Path("/tmp"))
    assert not prior_binary.is_symlink() and dynamic.SHA(prior_binary) == original["binary_sha256"]
    OUT.mkdir(exist_ok=False)
    dynamic.WRITE(OUT / "profile.json", dict(
        tag=TAG, original_sha256=dynamic.SHA(dynamic.OUT / "report.json"),
        sources={**pins["sources"], "scripts/diag_p109_g4_compact_static_cpu.py": dynamic.SHA(Path(__file__))},
        max_abs_static_vs_dynamic=MAX_DELTA, dynamic_executable_sha256=original["binary_sha256"],
    ))
    static = build()
    model = dynamic.prior.load_candidate(pins["candidate"])
    fd = dynamic.memfile("g4_compact_static")
    try:
        source = dynamic.model_blob(model, fd, pins["candidate"]["model_tensor_bytes"])
        del model
        assert source == original["artifact"]
        short_ids = original["short"]["short_input_ids"]
        ref, original_scores = dynamic.run_native(prior_binary, fd, short_ids, scores=True)
        short, scores = dynamic.run_native(static, fd, short_ids, scores=True)
        difference = float(np.max(np.abs(scores - original_scores)))
        short.update(max_abs_vs_dynamic=difference,
                     same_ids=short["ids"] == ref["ids"] == original["short"]["reference_ids"],
                     passed=difference <= MAX_DELTA and short["ids"] == ref["ids"])
        dynamic.WRITE(OUT / "short.json", short)
        print("P109_COMPACT_STATIC_41", short["passed"], difference, short["peak_rss_observed_bytes"], flush=True)
        if not (short["same_ids"] and short["passed"]):
            return 8
        inputs = dynamic.READ(dynamic.PROFILE_PATH)["cases"]
        cases = {}
        for name in ("synthetic", "english", "korean"):
            record, _ = dynamic.run_native(static, fd, inputs[name]["ids"])
            baseline = original["cases"][name]
            record["same_ids"] = record["ids"] == baseline["ids"] == baseline["reference_ids"]
            record["original_rss"] = baseline["peak_rss_observed_bytes"]
            assert record["model_bytes"] == baseline["model_bytes"] == source["artifact_bytes"]
            assert record["kv_bytes"] == baseline["kv_bytes"] and record["scratch_bytes"] == baseline["scratch_bytes"]
            dynamic.WRITE(OUT / f"{name}.json", record)
            cases[name] = record
            print("P109_COMPACT_STATIC_1024", name, record["same_ids"], record["peak_rss_observed_bytes"],
                  record["seconds"][0], sum(record["seconds"][1:]), flush=True)
    finally:
        os.close(fd)
    assert not torch.cuda.is_initialized() and dynamic.pins() == pins
    dynamic.WRITE(OUT / "report.json", dict(
        short=short, cases=cases, artifact=source, cuda_initialized=False, checkpoint_writes=0,
        sealed_fd_closed=True, tokenizer_in_native_child=False, profile_sha256=dynamic.SHA(OUT / "profile.json"),
    ))
    return 0 if all(record["same_ids"] for record in cases.values()) else 8


if __name__ == "__main__":
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    if datetime.now(dynamic.prior.ORIGIN.CUTOFF.tzinfo) + timedelta(seconds=1200) >= dynamic.prior.ORIGIN.CUTOFF:
        raise RuntimeError("insufficient time in the authorized window")
    sys.exit(run())
