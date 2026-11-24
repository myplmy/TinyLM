"""Compare G4 recomputed CE blocks under one fixed native mixed-course workload."""

import argparse
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import monotonic, sleep, time
from unittest.mock import patch

import torch

from scripts import diag_p109c_course_all_axes as axes_fixture
from scripts import diag_p109c_masked_course_resume as base
from scripts.run_p109b_scratch_pair_20261120 import CARD_LIMIT_MIB, file_sha, gpu_status, idle_gpu, publish
from tinylm.train import trainer


ROOT = base.ROOT
SEQ, MICRO, ACCUM, STEPS, MIX_FROM, POOL = 1024, 4, 32, 10, 5, 2**22
WALL, ARM_WALL = 900, 140


@dataclass(frozen=True)
class Experiment:
    output: Path
    tag_prefix: str
    rows: tuple[int, ...]
    compact: bool = False
    raw_methods: tuple[str, ...] = ()


POSITION = Experiment(ROOT / "test_result/evidence/p109c_ce_position_blocks_v1_20261120",
                      "p109c_ce_position_v1", (1024, 2048, 4096, 4096, 2048, 1024))
COMPACT = Experiment(ROOT / "test_result/evidence/p109c_ce_compact_targets_v1_20261120",
                     "p109c_ce_compact_v1", (2048, 2048), compact=True)
RAW = Experiment(ROOT / "test_result/evidence/p109c_raw_ntp_resources_v1_20261120",
                 "p109c_raw_ntp_v1", (0, 0, 1024, 1024, 0, 0),
                 raw_methods=("full_ce", "vocab2048", "wide_checkpoint",
                              "wide_checkpoint", "vocab2048", "full_ce"))


def tag(index, experiment):
    method = experiment.raw_methods[index] if experiment.raw_methods else experiment.rows[index]
    return f"{experiment.tag_prefix}_{index + 1}_{method}"


def command(index, experiment):
    args = axes_fixture.native_args(tag(index, experiment), SEQ, POOL, ACCUM, True)
    for key, value in (("--steps", STEPS), ("--eval-every", STEPS),
                       ("--save-every", STEPS), ("--ce-recompute-rows", experiment.rows[index])):
        args[args.index(key) + 1] = str(value)
    if experiment.raw_methods:
        method = experiment.raw_methods[index]
        if method == "vocab2048":
            args.extend(("--ce-vocab-tile", "2048"))
        elif method == "wide_checkpoint":
            args.remove("--no-ckpt")
            args[args.index("--micro-bs") + 1] = "8"
            args[args.index("--accum") + 1] = "16"
    return args


def read_profile(experiment):
    return json.loads((experiment.output / "profile.json").read_bytes())


def layout():
    plain, axes = axes_fixture.layouts(SEQ, 32768, ACCUM)
    return replace(plain, start_update=MIX_FROM), replace(axes, layout=replace(axes.layout, start_update=MIX_FROM))


def shared_training_settings(args, raw_only):
    changed = ["--tag"]
    if raw_only:
        changed.extend(("--micro-bs", "--accum", "--ce-recompute-rows", "--ce-vocab-tile"))
    comparable = args.copy()
    for flag in changed:
        if flag in comparable:
            index = comparable.index(flag)
            del comparable[index:index + 2]
    if raw_only and "--no-ckpt" in comparable:
        comparable.remove("--no-ckpt")
    return comparable


def completed_baseline(profile, experiment):
    prior = read_profile(POSITION)
    report_path = POSITION.output / "report.json"
    reference = json.loads(report_path.read_bytes())
    prior_path = POSITION.output / "profile.json"
    if (not reference["complete"] or not reference["matched_initialization"]
            or reference["profile_sha256"] != file_sha(prior_path)):
        raise ValueError("the complete sealed position-block report is required")
    fixed_fields = ("pool", "input_slots_per_arm", "input_slots_per_step", "phase_boundary", "card_limit_mib")
    if any(profile[key] != prior[key] for key in fixed_fields):
        raise ValueError("the resource workload differs from the completed baseline")
    if any(profile["pins"][key] != prior["pins"][key] for key in ("fixture/meta.json", "fixture/train.bin", "fixture/val.bin")):
        raise ValueError("the baseline fixture changed")
    if (profile["course"]["course_rows_sha256"] != prior["course"]["course_rows_sha256"]
            or profile["relation_course"]["layout"]["course_rows_sha256"]
            != prior["relation_course"]["layout"]["course_rows_sha256"]
            or profile["relation_course"]["gold_by_question"] != prior["relation_course"]["gold_by_question"]):
        raise ValueError("the baseline course inputs changed")
    reference_rows = 2048 if experiment.compact else 1024
    init = set()
    pairs = 0
    for index, arm in enumerate(reference["arms"]):
        if arm["rows"] != reference_rows:
            continue
        result = POSITION.output / arm["tag"] / "result.json"
        args = shared_training_settings(prior["commands"][index], bool(experiment.raw_methods))
        if (any(shared_training_settings(candidate, bool(experiment.raw_methods)) != args
                for candidate in profile["commands"]) or file_sha(result) != arm["result_sha256"]):
            raise ValueError("baseline arm identity or settings changed")
        init.add(arm["initialization_sha256"])
        pairs += 1
    if len(init) != 1 or pairs != 2:
        raise ValueError("two comparable position-block references are required")
    return dict(path=str(report_path.relative_to(ROOT)), sha256=file_sha(report_path),
                initialization_sha256=init.pop(), recompute_rows=reference_rows)


def make_profile(plain, axes, experiment):
    pins = base.mixed.routed.source_pins()
    for path in map(Path, (__file__, base.__file__, base.mixed.__file__, axes_fixture.__file__)):
        pins[str(path.relative_to(ROOT))] = file_sha(path)
    for name in ("meta.json", "train.bin", "val.bin"):
        pins[f"fixture/{name}"] = file_sha(POSITION.output / "synthetic" / name)
    profile = dict(approval="WIP191", ledger_item=180, workload="owned synthetic", pool=POOL,
                   input_slots_per_arm=SEQ * MICRO * ACCUM * STEPS, input_slots_per_step=SEQ * MICRO * ACCUM,
                   phase_boundary=MIX_FROM, card_limit_mib=CARD_LIMIT_MIB, cutoff_epoch=base.CUTOFF,
                   ce_rows=list(experiment.rows), commands=[command(index, experiment) for index in range(len(experiment.rows))],
                   course=plain.binding(), relation_course=axes.binding(), pins=pins)
    if experiment.compact or experiment.raw_methods:
        profile.update(compact_course_ce=experiment.compact, raw_methods=list(experiment.raw_methods),
                       baseline=completed_baseline(profile, experiment))
    return profile


def verify_profile(plain, axes, experiment):
    observed = make_profile(plain, axes, experiment)
    if observed != read_profile(experiment):
        raise ValueError("sealed course, fixture or launch condition changed")
    return observed


def worker(index, experiment):
    plain, axes = layout()
    profile = verify_profile(plain, axes, experiment)
    if not torch.cuda.is_available():
        raise RuntimeError("selected CUDA device is unavailable")
    total, background, _ = gpu_status()
    if background >= CARD_LIMIT_MIB - 512:
        raise RuntimeError("the card has no safe allocation headroom")
    torch.cuda.set_per_process_memory_fraction((CARD_LIMIT_MIB - background - 512) / total)
    torch.cuda.reset_peak_memory_stats()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    arm = experiment.output / tag(index, experiment)
    meta = json.loads((POSITION.output / "synthetic/meta.json").read_bytes())
    native_eval = trainer.evaluate
    native_time_stats = trainer._step_stats
    native_model_init = base.mixed.routed.RoutedG4.__init__
    initial = []
    step_ms = []
    final_checkpoint_steps = []

    def evaluate(model, loader, _count, device, **kwargs):
        return native_eval(model, loader, 2, device, **kwargs)

    def step_stats(times, *args, **kwargs):
        step_ms[:] = times
        return native_time_stats(times, *args, **kwargs)

    def observe_initial(model, cfg):
        native_model_init(model, cfg)
        initial.append(base.fixture.state_sha(model.state_dict()))

    def observe_final(blob, _target):
        # The timed path ends before saving. Keep its final step, without retaining synthetic weights.
        final_checkpoint_steps.append(blob["step"])

    started = monotonic()
    with (patch.object(trainer, "CKPT", arm / "ckpt"), patch.object(trainer, "LOGS", arm / "logs"),
          patch.object(trainer, "prepare", return_value=meta), patch.object(trainer, "evaluate", evaluate),
          patch.object(trainer, "_step_stats", step_stats),
          patch.object(base.mixed.routed.RoutedG4, "__init__", observe_initial),
          patch.object(torch, "save", observe_final)):
        if experiment.raw_methods:
            receipt = base.mixed.routed.run_native("uniform_r2", command(index, experiment))
        else:
            receipt = base.mixed.run_native(plain, command(index, experiment), all_axes=axes,
                                            compact_course_ce=experiment.compact)
    torch.cuda.synchronize()
    elapsed = monotonic() - started
    (native_path,) = (arm / "logs").glob("*.json")
    native = json.loads(native_path.read_bytes())
    updates = receipt["updates"]
    stable_original = step_ms[1:MIX_FROM]
    if (len(initial) != 1 or len(step_ms) != STEPS or native.get("ce_recompute_rows", 0) != experiment.rows[index]
            or native["n_skip"] != 0 or final_checkpoint_steps.count(STEPS) < 1
            or len(updates) != STEPS or any(not step["optimizer_applied"] or step["visits"] != 28 for step in updates)
            or any(step["draw_tokens"] != SEQ * MICRO * ACCUM for step in updates)):
        raise RuntimeError("the required visits and update accounting did not close")
    if experiment.raw_methods:
        method = experiment.raw_methods[index]
        if (native["grad_ckpt"] != (method == "wide_checkpoint")
                or native.get("ce_vocab_tile", 0) != (2048 if method == "vocab2048" else 0)):
            raise RuntimeError("the native NTP execution did not use the declared resource method")
    else:
        expected_positions = 152 if experiment.compact else 32768
        if ([step["course_input_slots"] for step in updates] != [0] * MIX_FROM + [32768] * (STEPS-MIX_FROM)
                or any(step["course_supervised_targets"] != 98 or step["course_head_positions"] != expected_positions
                       for step in updates[MIX_FROM:])):
            raise RuntimeError("the declared course accounting did not close")
    if "baseline" in profile and initial[0] != profile["baseline"]["initialization_sha256"]:
        raise RuntimeError("the new run and the completed baseline started with different weights")
    verify_profile(plain, axes, experiment)
    publish(arm / "result.json", dict(
        tag=tag(index, experiment), recompute_rows=experiment.rows[index], initialization_sha256=initial[0],
        original_step_median_ms=median(stable_original),
        mixed_step_median_ms=None if experiment.raw_methods else median(step_ms[MIX_FROM+1:]),
        step_ms=step_ms, native_seconds=elapsed, final_validation=native["history"][-1],
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        skips=native["n_skip"], retained_checkpoint=False, native_log_sha256=file_sha(native_path), receipt=receipt))


def begin_gpu(experiment):
    verify_profile(*layout(), experiment)
    _, initial_used = idle_gpu()
    deadline = min(time() + WALL, base.CUTOFF)
    records = []
    failed = set()
    for index, rows in enumerate(experiment.rows):
        label = tag(index, experiment)
        condition = experiment.raw_methods[index] if experiment.raw_methods else rows
        if (experiment.output / "STOP").exists():
            records.append(dict(tag=label, rows=rows, status="OWNER_STOP"))
            break
        if condition in failed:
            records.append(dict(tag=label, rows=rows, status="HELD_AFTER_CONDITION_FAILURE"))
            continue
        if time() + ARM_WALL > deadline:
            records.append(dict(tag=label, rows=rows, status="INSUFFICIENT_REMAINING_WINDOW"))
            break
        _, idle_used = idle_gpu()
        arm = experiment.output / label
        arm.mkdir()
        print("P109C_CE_BLOCK_START", index + 1, rows, flush=True)
        begin = monotonic()
        peak = idle_used
        stop_reason = None
        with (arm / "stdout.txt").open("x", encoding="utf-8") as log:
            args = [sys.executable, "-B", "-u", "-m", "scripts.diag_p109c_ce_position_blocks", "worker", str(index)]
            if experiment.compact:
                args.append("--compact-course-ce")
            if experiment.raw_methods:
                args.append("--raw-ntp")
            child = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            try:
                while child.poll() is None:
                    if (experiment.output / "STOP").exists():
                        stop_reason = "OWNER_STOP"
                        break
                    _, used, _ = gpu_status()
                    peak = max(peak, used)
                    if used > CARD_LIMIT_MIB:
                        stop_reason = "CARD_LIMIT"
                        break
                    if monotonic() - begin >= ARM_WALL or time() >= deadline:
                        stop_reason = "ARM_TIME_LIMIT"
                        break
                    sleep(0.4)
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        child.kill()
                code = child.wait()
        _, after = idle_gpu()
        record = dict(tag=label, rows=rows, exit=code, reason=stop_reason, sampled_card_peak_mib=peak,
                      sampled_card_before_mib=idle_used, idle_after_mib=after, wall_seconds=monotonic()-begin)
        if code != 0:
            failed.add(condition)
        else:
            measured = json.loads((arm / "result.json").read_bytes())
            record.update(result_sha256=file_sha(arm / "result.json"),
                          initialization_sha256=measured["initialization_sha256"],
                          original_step_median_ms=measured["original_step_median_ms"],
                          mixed_step_median_ms=measured["mixed_step_median_ms"])
        records.append(record)
        print("P109C_CE_BLOCK_EXIT", index + 1, code, peak, stop_reason, flush=True)
        if stop_reason == "OWNER_STOP":
            break
    complete = len(records) == len(experiment.rows) and all(row.get("exit") == 0 for row in records)
    matched_init = len({row["initialization_sha256"] for row in records if "initialization_sha256" in row}) == 1
    total, final_used = idle_gpu()
    publish(experiment.output / "report.json",
            dict(complete=complete, matched_initialization=matched_init, arms=records,
                 gpu_return=dict(free_mib=total-final_used, compute_pids=0,
                                 baseline_used_mib=initial_used, final_used_mib=final_used),
                 profile_sha256=file_sha(experiment.output / "profile.json")))
    print("P109C_CE_BLOCKS_COMPLETE", complete, matched_init, total-final_used, flush=True)
    return 0 if complete and matched_init else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "gpu", "worker"))
    parser.add_argument("index", nargs="?", type=int)
    variants = parser.add_mutually_exclusive_group()
    variants.add_argument("--compact-course-ce", action="store_true")
    variants.add_argument("--raw-ntp", action="store_true")
    args = parser.parse_args()
    experiment = COMPACT if args.compact_course_ce else RAW if args.raw_ntp else POSITION
    expected = "" if args.mode == "prepare" else "0"
    reserve = ARM_WALL if args.mode == "worker" else WALL
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected or time() + reserve >= base.CUTOFF:
        raise RuntimeError("the scoped device or remaining window does not match the experiment")
    if args.mode == "worker":
        if args.index is None or not 0 <= args.index < len(experiment.rows):
            parser.error("worker requires a sealed arm index")
        worker(args.index, experiment)
        return 0
    if args.mode == "prepare":
        experiment.output.mkdir(exist_ok=False)
        if experiment == POSITION:
            base.source(experiment.output, SEQ, 32768, POOL)
        publish(experiment.output / "profile.json", make_profile(*layout(), experiment))
        print("P109C_CE_BLOCKS_SEALED", STEPS, list(experiment.rows), experiment.compact, flush=True)
        return 0
    return begin_gpu(experiment)


if __name__ == "__main__":
    raise SystemExit(main())
