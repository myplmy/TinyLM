"""Compare a continuous packed CLI run with a fresh CUDA-process resume."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p013_g4_document_context as earlier
from scripts import test_p013_packed_document_cli as probe
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p107_hybrid_mntp import close_owned_cuda


ROOT, END = earlier.ROOT, earlier.END
TAG = "p013_packed_document_cli_cuda_v1_20261119"
OUT = earlier.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
PLAN = OUT / "plan_at_execution.md"
PHASES = ("continuous", "prefix", "resume")
LIMIT = 30
CPU_LOG = ROOT / "test_result/106_log_20261119_P013_Stage7Wc_PackedCLIReadback_CPU.txt"
SOURCES = (
    "scripts/test_p013_packed_document_cli.py", "tinylm/cli.py", "tinylm/config.py",
    "tinylm/train/trainer.py", "tinylm/train/context_training_state.py",
    "tinylm/train/context_curriculum.py", "tinylm/train/packed_document_training.py",
    "tinylm/train/indexed_document_source.py", "tinylm/train/document_input.py",
    "tinylm/train/document_context_curriculum.py", "tinylm/train/hybrid_mntp.py",
    "tinylm/model/transformer.py", "tinylm/model/visibility.py", "tinylm/model/modules.py",
)


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(END.tzinfo) + timedelta(seconds=reserve) >= END:
        raise RuntimeError("owned STOP or deadline")


def verify(profile):
    assert profile["tag"] == TAG and profile["authority"] == 177
    for path, wanted in profile["pins"].items():
        assert earlier.manual.file_sha(Path(path)) == wanted, path


def prepare():
    raw = CPU_LOG.read_text(encoding="utf-8")
    assert "Ran 82 tests" in raw and "PACKED_CLI_PROOF 231 84" in raw and raw.splitlines()[-1] == "EXIT 0"
    assert not torch.cuda.is_initialized()
    sections = earlier.PLAN.read_text(encoding="utf-8").split("### Stage7Wd ", 1)
    assert len(sections) == 2 and TAG in sections[1]
    fixture = probe.InputFixture()
    paths = [fixture.profile_path, *sorted((fixture.root / "inputs").iterdir())]
    OUT.mkdir(exist_ok=False)
    PLAN.write_text("### Stage7Wd " + sections[1], encoding="utf-8")
    paths.extend([Path(__file__), CPU_LOG, PLAN, *(ROOT / name for name in SOURCES)])
    profile = dict(tag=TAG, authority=177, fixture=str(fixture.profile_path),
                   pins={str(p): earlier.manual.file_sha(p) for p in paths})
    verify(profile)
    earlier.write(PROFILE, profile)
    print("PACKED_CUDA_PREPARE", len(paths), flush=True)


def worker(profile, phase):
    assert torch.cuda.device_count() == 1
    torch.use_deterministic_algorithms(True)
    probe.TAG = TAG
    directory = OUT / ("continuous" if phase == "continuous" else "restart")
    with sdpa_kernel(SDPBackend.MATH):
        probe.worker(Path(profile["fixture"]), directory, phase)
    cleanup = {}
    close_owned_cuda(torch, cleanup)
    earlier.write(OUT / f"cleanup_{phase}.json", cleanup)
    print("PACKED_CUDA_WORKER_COMPLETE", phase, flush=True)


def load_result(group):
    name = f"tiny_synthetic_256_{TAG}"
    base = OUT / group
    state = torch.load(base / "ckpt" / f"{name}.pt", weights_only=True, map_location="cpu")
    result = json.loads((base / "logs" / f"{name}.json").read_bytes())
    return state, result


def check_continuation(prefix):
    assert prefix["step"] == 1
    a, ar = load_result("continuous")
    b, br = load_result("restart")
    key = probe.trainer.CONTEXT_STATE_KEY
    assert a["step"] == b["step"] == 4 and br["context_resume_start_step"] == 1
    same = {field: probe.state_sha(a[field]) == probe.state_sha(b[field]) for field in ("model", "opt", key)}
    assert all(same.values()) and ar["final"] == br["final"]
    state = b[key]
    assert state["cpu_rng"].numel() and state["cuda_rng"].numel() and state["binding"]["runtime"]["device"] == "cuda"
    assert state["cursor"]["optimizer_updates"] == 4 and state["cursor"]["valid_targets"] == 231
    assert state["control"]["history"][-1]["val_valid_targets"] == 84
    return dict(exact=same, cpu_rng_bytes=state["cpu_rng"].numel(), cuda_rng_bytes=state["cuda_rng"].numel(),
                model_sha256=probe.state_sha(b["model"]), adamw_sha256=probe.state_sha(b["opt"]),
                context_sha256=probe.state_sha(state), train_valid_targets=state["cursor"]["valid_targets"],
                validation=br["final"], resume_from=br["context_resume_start_step"], updates_per_arm=b["step"])


def run(profile):
    sampler = earlier.sampling
    assert idle(), "GPU has another compute process"
    before = subprocess.check_output(sampler.DEVICE, text=True, timeout=8).strip()
    raw = OUT / "device_100ms.csv"
    exits, prefix = {}, None
    with raw.open("xb") as stream:
        monitor = subprocess.Popen((*sampler.DEVICE, f"--loop-ms={sampler.INTERVAL_MS}"), stdout=stream)
        try:
            for phase in PHASES:
                gate(LIMIT + 5)
                if phase == "resume" and exits.get("prefix") != 0:
                    break
                assert idle(), "GPU not returned before next phase"
                cmd = ["timeout", "--kill-after=5s", f"{LIMIT}s", sys.executable, "-B", "-u",
                       "-m", __spec__.name, "worker", phase]
                exits[phase] = subprocess.run(cmd, cwd=ROOT, check=False).returncode
                if phase == "prefix" and exits[phase] == 0:
                    path = OUT / "restart" / "ckpt" / f"tiny_synthetic_256_{TAG}.pt"
                    prefix = torch.load(path, weights_only=True, map_location="cpu")
                print("PACKED_CUDA_EXIT", phase, exits[phase], flush=True)
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    after = subprocess.check_output(sampler.DEVICE, text=True, timeout=8).strip()
    samples = sampler.read_samples(raw)
    returned = idle()
    verify(profile)
    exact = check_continuation(prefix) if exits == dict.fromkeys(PHASES, 0) else None
    earlier.write(OUT / "report.json", dict(tag=TAG, exits=exits, continuation=exact, before=before, after=after,
        device_returned=returned, samples=len(samples), device_peak=max(samples, key=lambda row: row["occupied_mib"]),
        source_preserved=True, profile_sha256=earlier.manual.file_sha(PROFILE)))
    print("PACKED_CUDA_RESULT", exact, returned, after, flush=True)
    if exact is None or not returned:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "worker"))
    parser.add_argument("phase", nargs="?", choices=PHASES)
    args = parser.parse_args()
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.mode == "prepare" else "0")
    gate(3 * (LIMIT + 5) if args.mode == "run" else 0)
    if args.mode == "prepare":
        prepare()
    else:
        profile = earlier.read(PROFILE)
        if args.mode == "run":
            verify(profile)
            run(profile)
        else:
            worker(profile, args.phase)


if __name__ == "__main__":
    main()
