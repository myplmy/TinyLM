"""Compare two serialized writes with one write plus a file copy on the same G4 state."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from shutil import copyfile
import subprocess
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import perf_counter

import torch

from scripts import diag_p102a_g4_joint_ce_kl_batch8 as sampling
from scripts.diag_p013_g4_packed_cli_resume import END, NAME, OUT as TRAINING_OUT
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.interactive_research_infer import file_sha


ROOT = Path(__file__).resolve().parents[1]
TAG = "p013_g4_packed_checkpoint_pair_v1_20261119"
OUT = TRAINING_OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
SOURCE = TRAINING_OUT / "continuous" / "ckpt" / NAME
SOURCE_SHA = "966577B947DB4631EBF0205DD24586EE46ACB22DC7FC0793F0A33BA54C749157"
PLAN = ROOT / "test_plan/P013_seq-length-warmup-소규모.md"
TEST_LOG = ROOT / "test_result/106_log_20261119_P013_Stage7Wf_PairedPublishTests_CPU.txt"
ORDER = ("double", "copy", "copy", "double")
LIMIT = 210


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(END.tzinfo) + timedelta(seconds=reserve) >= END:
        raise RuntimeError("owned STOP or deadline")


def write(path, report):
    with path.open("x", encoding="utf8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        print(file=stream)


def prepare():
    assert file_sha(SOURCE) == SOURCE_SHA and SOURCE.stat().st_size == 754999419
    assert TEST_LOG.read_text(encoding="utf8").strip().endswith("EXIT 0")
    OUT.mkdir()
    sealed = OUT / "plan_at_execution.md"
    sealed.write_bytes(PLAN.read_bytes())
    paths = (Path(__file__).resolve(), sealed, TEST_LOG, TRAINING_OUT / "report.json",
             ROOT / "tinylm/train/packed_document_training.py", SOURCE)
    write(PROFILE, dict(authority=177, tag=TAG, order=ORDER, source_bytes=SOURCE.stat().st_size,
                        pins={str(path.relative_to(ROOT)): file_sha(path) for path in paths},
                        min_gain_percent=5, training_steps=0, evaluations=0))


def verify(profile):
    assert profile["tag"] == TAG and profile["authority"] == 177 and tuple(profile["order"]) == ORDER
    for name, expected in profile["pins"].items():
        archive = OUT / "execution_sources" / name
        assert file_sha(archive if archive.is_file() else ROOT / name) == expected, name


def save_original(path, state):
    # Stage7We wrote the same state with this function twice.
    with NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
        torch.save(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stream.name, path)


def save_packed_checkpoint(path, state, *, best_path=None):
    """Stage complete, independent files from one serialized training state."""
    if best_path is not None and (best_path.parent != path.parent or best_path == path):
        raise ValueError("paired checkpoints need distinct names in the same directory")
    with TemporaryDirectory(dir=path.parent, prefix=f".{path.name}.") as staging:
        with NamedTemporaryFile(dir=staging, delete=False) as latest:
            torch.save(state, latest)
            latest.flush()
            os.fsync(latest.fileno())
        if best_path is not None:
            with NamedTemporaryFile(dir=staging, delete=False) as best:
                best_name = best.name
            copyfile(latest.name, best_name)
            with open(best_name, "r+b") as best:
                os.fsync(best.fileno())
            # The best file can be ahead of latest, as with an off-cadence eval.
            # Publish latest last so it never records an unpublished best state.
            os.replace(best_name, best_path)
        os.replace(latest.name, path)


def measure(device, profile):
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if device == "cuda":
        assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12500 * 2**20
    # CUDA uses the placement recorded by the actual training save, including its CPU tensors.
    state = torch.load(SOURCE, map_location="cpu" if device == "cpu" else None, weights_only=True)
    assert state["step"] == 4 and {"model", "opt", "context_training_state"} <= state.keys()
    device_model_tensors = sum(tensor.is_cuda for tensor in state["model"].values())
    assert (device_model_tensors > 0) == (device == "cuda")
    rows = []
    for method in ORDER:
        gate()
        with TemporaryDirectory(dir="/tmp", prefix="p013_pair_io_") as temp:
            root = Path(temp)
            assert root.stat().st_dev == SOURCE.stat().st_dev
            latest, best = root / "latest.pt", root / "best.pt"
            start = perf_counter()
            if method == "double":
                save_original(latest, state)
                save_original(best, state)
            else:
                save_packed_checkpoint(latest, state, best_path=best)
            seconds = perf_counter() - start
            assert not os.path.samefile(latest, best)
            same = file_sha(latest)
            assert file_sha(best) == same
            row = dict(method=method, seconds=seconds, bytes=latest.stat().st_size, sha256=same,
                       allocated_file_bytes=512 * (latest.stat().st_blocks + best.stat().st_blocks))
            rows.append(row)
            print("P013_PAIR_SAMPLE", device, len(rows), row, flush=True)
    assert len({row["sha256"] for row in rows}) == len({row["bytes"] for row in rows}) == 1
    gains = [100 * (1 - rows[b]["seconds"] / rows[a]["seconds"]) for a, b in ((0, 1), (3, 2))]
    cuda_cleanup = {}
    del state
    if device == "cuda":
        close_owned_cuda(torch, cuda_cleanup)
    report = dict(device=device, device_model_tensors=device_model_tensors, rows=rows,
                  gains_percent=gains, passes_speed_gate=min(gains) >= profile["min_gain_percent"],
                  cuda_cleanup=cuda_cleanup, source_sha256=SOURCE_SHA)
    write(OUT / f"{device}.json", report)
    print("P013_PAIR_GAINS", device, gains, report["passes_speed_gate"], flush=True)


def run_cuda():
    gate(LIMIT + 10)
    assert idle(), "device has another compute process"
    before = subprocess.check_output(sampling.DEVICE, text=True, timeout=8).strip()
    label = Path(__file__).stem
    write(OUT / "active.json", dict(tag=TAG, pid=os.getpid(), child=label, stage="paired_save"))
    raw = OUT / "device_100ms.csv"
    with raw.open("xb") as samples:
        monitor = subprocess.Popen((*sampling.DEVICE, f"--loop-ms={sampling.INTERVAL_MS}"), stdout=samples)
        try:
            command = (sys.executable, "-B", "-m", f"scripts.{label}", "cuda_worker")
            try:
                code = subprocess.run(command, cwd=ROOT, timeout=LIMIT).returncode
            except subprocess.TimeoutExpired:
                code = 124
                print("P013_PAIR_TIMEOUT", LIMIT, flush=True)
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    after = subprocess.check_output(sampling.DEVICE, text=True, timeout=8).strip()
    device_returned = idle()
    records = sampling.read_samples(raw)
    receipt = dict(exit_code=code, device_returned=device_returned, before=before, after=after,
                   peak=max(records, key=lambda row: row["occupied_mib"]), samples=len(records))
    write(OUT / "device.json", receipt)
    print("P013_PAIR_RELEASE", device_returned, receipt, flush=True)
    if code or not device_returned:
        raise SystemExit(code or 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "cpu", "cuda", "cuda_worker"))
    mode = parser.parse_args().mode
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("0" if mode.startswith("cuda") else "")
    gate()
    if mode == "prepare":
        prepare()
        return
    profile = json.loads(PROFILE.read_text(encoding="utf8"))
    if mode == "cuda_worker":
        measure("cuda", profile)
        return
    verify(profile)
    if mode == "cuda":
        run_cuda()
    else:
        measure("cpu", profile)
    verify(profile)
    print("P013_PAIR_SEALS_OK", len(profile["pins"]), flush=True)


if __name__ == "__main__":
    main()
