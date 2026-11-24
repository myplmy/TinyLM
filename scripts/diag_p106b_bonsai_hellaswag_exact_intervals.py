"""Preserve official HellaSwag rows from the qualified Bonsai prefix route."""

import argparse
import json
import os
from pathlib import Path
import signal
import sysconfig
import time

import numpy as np

from scripts import diag_p013_native_matched_training as io
from scripts import diag_p106b_bonsai_hellaswag_remaining as held
from scripts import diag_p106b_bonsai_native_core6 as core


TAG = "p106b_bonsai_hellaswag_exact_prefix_intervals_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
TASK = "hellaswag"
RANGES = ((0, 256), (256, 512), (512, 768))
CAP = 880
PARENT = core.OUT / "actual/report.json"
HELD_RESULT = held.OUT / "actual/report.json"
WITNESS = core.PRISM.OUT / "actual/A0_logits_fp32.npy"
SOURCES = ("scripts/diag_p106b_bonsai_hellaswag_exact_intervals.py",
    "scripts/diag_p106b_bonsai_hellaswag_remaining.py", "scripts/diag_p013_native_matched_training.py",
    "scripts/p106b_shards.py", "scripts/p106b_prism_native.py")


def fingerprint():
    profile, native = core.verify()
    prior = core.PRISM.read(PARENT)
    negative = core.PRISM.read(HELD_RESULT)
    assert prior["exit"] == negative["exit"] == 8
    assert prior["tasks"][TASK]["status"] == "COST_HOLD" and prior["tasks"][TASK]["rows"] == 0
    assert negative["task"] == TASK and negative["single_batch_oracle"]["eligible"] is False
    assert prior["profile_sha256"] == io.digest(core.PROFILE) == held.PARENT_SHA
    done = {name: row["manifest"]["concat_sha256"] for name, row in prior["tasks"].items()
            if row["status"] == "COMPLETE"}
    assert len(done) == 5
    bound = {str(path.relative_to(io.ROOT)): io.digest(path)
        for path in (PARENT, HELD_RESULT, core.PROFILE, WITNESS, *(io.ROOT/p for p in SOURCES))}
    return dict(tag=TAG, sources=bound, previous_tasks_reused=done, ranges=[list(pair) for pair in RANGES],
        rows_total=10042, worker_interval_cap_s=CAP, route="QUALIFIED_LAST_LOGIT_PREFIXES",
        for_evaluation_only=True, full_task_score=False, official=profile["tasks"]["items"][TASK],
        cutoff_KST="2026-11-18 16:30", original_held_task_rows=0), profile, native


def prepare():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    p, _, _ = fingerprint()
    assert len({i for first, end in RANGES for i in range(first, end)}) == sum(end-first for first,end in RANGES)
    assert all(0 <= first < end <= p["rows_total"] for first, end in RANGES)
    OUT.mkdir()
    io.write(PROFILE, p)
    print("BONSAI_HELLASWAG_EXACT_READY", io.digest(PROFILE), p["ranges"], flush=True)


def read_interval(directory, expected):
    manifest = core.PRISM.read(directory / (TASK + "_shards_manifest.json"))
    core.verify_shards(directory, manifest)
    assert manifest["lineage"]["route"] == "QUALIFIED_LAST_LOGIT_PREFIXES"
    rows = []
    for shard in manifest["shards"]:
        with (directory / shard["path"]).open(encoding="utf-8") as stream:
            rows.extend(json.loads(line) for line in stream)
    assert len(rows) == manifest["rows"] <= len(expected)
    for row, item in zip(rows, expected[:len(rows)], strict=True):
        assert all(row[k] == value for k, value in item.items())
        assert len(row["token_proof"]) == len(row["responses"]) == len(item["arguments"]) == 4
    return dict(rows=len(rows), manifest=manifest,
        source_prefix_matches=True, complete_interval=len(rows)==len(expected) and manifest["lineage"]["complete"])


def actual():
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    p, previous, native = fingerprint()
    assert p == core.PRISM.read(PROFILE) and os.environ["LD_LIBRARY_PATH"] == native["bundle"]
    assert not any(key.startswith(("LLAMA_ARG_", "GGML_")) for key in os.environ)
    assert time.time() + CAP + 95 < core.CUTOFF
    entry = io.reserve_device()
    history = []
    error = None
    stop_at = core.CUTOFF - 30
    engine = None
    runtime = io.ROOT / "data_cache/p106b_official_eval_runtime/core6_env_20261023"
    assert Path(sysconfig.get_paths()["purelib"]).is_relative_to(runtime)

    def remaining():
        return min(stop_at, core.CUTOFF - 30) - time.time()

    def check():
        if remaining() <= 0 or (OUT / "STOP").exists():
            raise core.mc.lambada.Hold("owned interval budget or STOP")

    def interrupt(*_):
        raise core.mc.lambada.Hold("owned interrupt")

    old_handler = signal.signal(signal.SIGINT, interrupt)
    try:
        tasks, inputs, meta = core.inputs()
        assert core.canonical(meta) == core.canonical(previous["tasks"])
        official_inputs = inputs[TASK]
        assert len(official_inputs) == p["rows_total"]
        template, _ = core.prepare_harness(runtime_root=Path(sysconfig.get_paths()["purelib"]))
        with core.PRISM.native.NativeModel(native["bundle"], io.ROOT / native["model"], check=check) as engine:
            exact = engine.logits(native["prompts"]["A"]["native_ids"])
            assert np.array_equal(np.load(WITNESS, allow_pickle=False).view(np.uint32), exact.view(np.uint32))
            assert engine.piece(core.mc.lambada.EOT) == b"<|im_end|>"
            reference = core.PrismLikelihood(engine, template, core.mc.lambada.EOT, check=check)
            total = [0]
            for first, end in RANGES:
                if (OUT / "STOP").exists() or time.time() + CAP + 50 >= core.CUTOFF:
                    break
                directory = OUT / f"rows_{first:05}_{end:05}"
                directory.mkdir()
                stop_at = time.time() + CAP
                print("BONSAI_HELLASWAG_INTERVAL_START", first, end, "pid="+str(os.getpid()), flush=True)
                rows = official_inputs[first:end]
                try:
                    result = core.evaluate(reference, None, TASK, tasks[TASK], rows, check,
                                           remaining, directory, total)
                except core.mc.lambada.Hold as exc:
                    result = dict(status="PARTIAL_HOLD", reason=str(exc))
                # The subset has no standalone official score.
                evidence = {k: result[k] for k in ("status", "route", "cost", "seconds", "reason") if k in result}
                manifest_path = directory / (TASK + "_shards_manifest.json")
                if manifest_path.is_file():
                    evidence.update(read_interval(directory, rows))
                else:
                    evidence.update(rows=0, complete_interval=False)
                record = dict(first=first, end_exclusive=end, **evidence,
                    profile_sha256=io.digest(PROFILE), official_full_task_score=None)
                io.write(directory / "interval.json", record)
                history.append(record)
                print("BONSAI_HELLASWAG_INTERVAL_DONE", first, end, record["rows"], record["status"], flush=True)
                if not record["complete_interval"]:
                    break
                stop_at = core.CUTOFF - 30
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:1400])
    finally:
        signal.signal(signal.SIGINT, old_handler)
        handles_closed = engine is None or not (engine.context or engine.model or engine.backend)
        release = io.reserve_device()
        done = error is None and len(history)==len(RANGES) and handles_closed and all(
            record["complete_interval"] for record in history)
        sealed, _, _ = fingerprint()
        assert sealed == p
        io.write(OUT / "terminal.json", dict(complete_intervals=done, exit=0 if done else 8, error=error,
            entry=entry, release=release, handles_closed=handles_closed, intervals=history,
            exact_rows=sum(record["rows"] for record in history), official_full_task_score=None,
            previous_tasks_unchanged=len(p["previous_tasks_reused"]), profile_sha256=io.digest(PROFILE)))
    return 0 if done else 8


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "actual"))
    raise SystemExit(actual() if parser.parse_args().action == "actual" else prepare())
