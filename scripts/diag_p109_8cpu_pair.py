"""Counterbalanced 96-update diagnostic with an actual temporary checkpoint round trip."""

from argparse import ArgumentParser
from dataclasses import asdict, replace
from datetime import datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import sys
import time

from scripts import diag_p109_full_train_throughput as throughput


TAG = "p109_full_train_6gib_20261124_8cpu_paired96_retry3"
WORKER_MODULE = "scripts.diag_p109_8cpu_pair"
RECORD = throughput.EVIDENCE / TAG
SCOPE = throughput.EVIDENCE / "p109_full_train_6gib_20261124_budget.json"
AUTHORIZED_END = datetime.fromisoformat("2026-11-25T01:00:00+09:00")
CPU_SET = set(range(8))
CONTROL = "mix_r2"
CHALLENGER = "mix_r1_to_r2_70"
ORDER = (CONTROL, CHALLENGER, CHALLENGER, CONTROL)
STEPS = 96
ALLOCATOR_MARGIN_MIB = 512
ALLOCATOR_LIMIT_MIB = 3712
RAW_CE_ROWS = 512
COURSE_CE_ROWS = 512
QUALITY_MARGIN_NATS = .02
R2_CHECKPOINT_VISITS = 16
COURSE_CHECKPOINT_VISITS = 24


def read(path):
    return json.loads(path.read_bytes())


def own_sha():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def approved_arm(label):
    raw_checkpoints = R2_CHECKPOINT_VISITS if label == CONTROL else 0
    return replace(throughput.ARMS[label], checkpoint_visits=raw_checkpoints,
                   r2_ckpt=R2_CHECKPOINT_VISITS, course_ckpt=COURSE_CHECKPOINT_VISITS)


def equal_tree(expected, restored, torch):
    if isinstance(expected, torch.Tensor):
        return (isinstance(restored, torch.Tensor) and expected.dtype == restored.dtype
                and torch.equal(expected, restored.detach().cpu()))
    if isinstance(expected, dict):
        return expected.keys() == restored.keys() and all(equal_tree(value, restored[key], torch)
                                                          for key, value in expected.items())
    if isinstance(expected, (list, tuple)):
        return len(expected) == len(restored) and all(equal_tree(a, b, torch)
                                                       for a, b in zip(expected, restored, strict=True))
    return expected == restored


def roundtrip(directory, model, adamw, muon, position):
    import torch

    destination = directory / "boundary_checkpoint.pt"
    before = time.perf_counter()
    payload = dict(model=model.state_dict(), adamw=adamw.state_dict(), muon=muon.state_dict(), position=position,
                   cpu_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state())
    with destination.open("xb") as stream:
        torch.save(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
    saved = time.perf_counter()
    del payload
    # Next update starts with zero gradients. Rebuild optimizer buffers from the file within the same worker.
    adamw.zero_grad(set_to_none=True)
    muon.zero_grad(set_to_none=True)
    adamw.state.clear()
    muon.state.clear()
    torch.cuda.empty_cache()
    restored = torch.load(destination, map_location="cpu", weights_only=True, mmap=True)
    model.load_state_dict(restored["model"], strict=True)
    adamw.load_state_dict(restored["adamw"])
    muon.load_state_dict(restored["muon"])
    torch.set_rng_state(restored["cpu_rng"])
    torch.cuda.set_rng_state(restored["cuda_rng"])
    torch.cuda.synchronize()
    applied = time.perf_counter()
    checks = dict(model=equal_tree(restored["model"], model.state_dict(), torch),
                  adamw=equal_tree(restored["adamw"], adamw.state_dict(), torch),
                  muon=equal_tree(restored["muon"], muon.state_dict(), torch),
                  rng=torch.equal(restored["cpu_rng"], torch.get_rng_state())
                      and torch.equal(restored["cuda_rng"], torch.cuda.get_rng_state()),
                  next_input=restored["position"] == position)
    if not all(checks.values()):
        raise ValueError(f"the loaded boundary checkpoint differs: {checks}")
    torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info()
    used = (total-free) / 2**20
    if used >= throughput.CARD_MIB - 64:
        raise RuntimeError("checkpoint restoration approached the card guard")
    return dict(position=restored["position"], checks=checks, mode="same_worker_state_reload",
                file=destination.name, bytes=destination.stat().st_size, save_seconds=saved-before,
                load_seconds=applied-saved, check_seconds=time.perf_counter()-applied,
                card_boundary_mib=used, cpu_affinity=sorted(os.sched_getaffinity(0)))


def read_arm(index, label):
    directory = RECORD / f"{index:02d}_{label}"
    supervisor = read(directory / "supervisor.json")
    worker = read(directory / "worker.json")
    binding = read(directory / "mix_binding.json")
    checkpoint = read(directory / "checkpoint_roundtrip.json")
    rows = [json.loads(line) for line in (directory / "steps.jsonl").read_text(encoding="utf-8").splitlines()]
    position = checkpoint["position"]
    if (supervisor["returncode"] != 0 or supervisor["stop_reason"] is not None
            or not supervisor["samples"] or supervisor["card_after_exit"].get("compute_pids") != []
            or len(rows) != STEPS or worker["updates"] != STEPS
            or any(row["step"] != step for step, row in enumerate(rows)) or not all(checkpoint["checks"].values())
            or supervisor["allocator_mib"] != ALLOCATOR_LIMIT_MIB
            or (binding["raw_ce_rows"], binding["course_ce_rows"]) != (RAW_CE_ROWS, COURSE_CE_ROWS)
            or checkpoint["cpu_affinity"] != sorted(CPU_SET) or position["next_update"] != round(STEPS*.70)
            or rows[position["next_update"]]["course_source"] != position["next_course_source"]):
        raise ValueError(f"{directory.name} did not close with the sealed round-trip and return")
    peak = max(supervisor["peak_card_mib"], checkpoint["card_boundary_mib"],
               *(row["cuda_global_used_mib"] for row in rows))
    if peak > throughput.CARD_MIB:
        raise ValueError(f"{directory.name} exceeded the approved card cap")
    steady = rows[1:]
    raw_rates = {str(phase["repeat"]): phase["raw_tokens"] / phase["raw_seconds"] for phase in worker["phases"]}
    course_seconds = sum(r["course_sec"] for r in steady) / sum(r["course_batches"] for r in steady)
    fixed_seconds = sum(r["sec"] - r["raw_sec"] - r["course_sec"] for r in steady) / len(steady)
    wall = supervisor["end"] - supervisor["start"]
    seen_raw_r1 = sum(row["raw_targets"] for row in rows if row["raw_repeat"] == 1)
    if (label == CONTROL and seen_raw_r1 != 0) or (label == CHALLENGER and not .67 <= seen_raw_r1/worker["seen_raw"] <= .73):
        raise ValueError("the realized route does not describe the admitted raw target fraction")
    identity = dict(raw_order=worker["raw_window_order_sha256"], val=binding["val_starts_sha256"],
                    course=binding["actual_course_source_addresses"], initial_val=worker["initial_val_r2"],
                    input_rows=[(r["raw_targets"], r["course_tokens"], r["course_answers"], r["bilingual_pairs"],
                                 r["relations"], r["decimals"]) for r in rows])
    result = dict(arm=label, record=directory.name, actual_updates=STEPS, card_peak_mib=peak,
                  nvml_peak_mib=supervisor["peak_card_mib"], telemetry_misses=supervisor["missed"],
                  allocator_mib=supervisor["allocator_mib"], wall_seconds=wall,
                  update_seconds=worker["update_seconds"], outside_updates_sec=wall-worker["update_seconds"],
                  startup_seconds=binding["startup_seconds"], validation_seconds=sum(r["seconds"] for r in worker["val_curve"]),
                  checkpoint=checkpoint, seen_raw=worker["seen_raw"], seen_raw_r1=seen_raw_r1,
                  seen_course=worker["seen_course"], supervised_answers=[sum(r["course_answers"][i] for r in rows) for i in range(3)],
                  bilingual_pairs=sum(r["bilingual_pairs"] for r in rows), relations=sum(r["relations"] for r in rows),
                  decimals=sum(r["decimals"] for r in rows), raw_rates=raw_rates, mix_rate=worker["tokens_per_s"],
                  course_seconds_per_batch=course_seconds, fixed_seconds_per_update=fixed_seconds,
                  val_final_r2=worker["final_val_r2"], val_windows_final=worker["val_curve"][-1]["window_nll"],
                  v3_comparable_quality="NOT_RUN")
    return result, identity


def full_projection(records, scope, fraction):
    rates1 = [r["raw_rates"]["1"] for r in records] if fraction else []
    rates2 = [r["raw_rates"]["2"] for r in records]
    price_raw = fraction/min(rates1) if fraction else 0
    price_raw += (1-fraction)/min(rates2)
    raw = scope["raw_scored_targets"] * price_raw
    course = scope["course_microbatches"] * max(r["course_seconds_per_batch"] for r in records)
    fixed = scope["steps"] * max(r["fixed_seconds_per_update"] for r in records)
    reserve = max(900., max(r["outside_updates_sec"] for r in records))
    return dict(raw_sec=raw, course_sec=course, fixed_sec=fixed, reserve_sec=reserve,
                total_sec=raw+course+fixed+reserve, budget_sec=scope["twice_wall_seconds"],
                margin_sec=scope["twice_wall_seconds"]-raw-course-fixed-reserve)


def conclude():
    records = [read_arm(index, label) for index, label in enumerate(ORDER)]
    arms = [result for result, _ in records]
    if any(other != records[0][1] for _, other in records):
        raise ValueError("the four arms did not consume exactly the same sealed exposure")
    baselines = [a for a in arms if a["arm"] == CONTROL]
    challengers = [a for a in arms if a["arm"] == CHALLENGER]
    scope = read(SCOPE)
    budget = full_projection(challengers, scope, .70)
    deltas = [challenger["val_final_r2"]-control["val_final_r2"]
              for challenger, control in zip(challengers, baselines, strict=True)]
    disposition = "RETAIN_FOR_FURTHER_REVIEW" if budget["margin_sec"] >= 0 and max(deltas) <= QUALITY_MARGIN_NATS else "HOLD"
    identity = sha256(json.dumps(records[0][1], sort_keys=True).encode()).hexdigest()
    throughput.publish(RECORD / "paired_result.json", dict(tag=TAG, arms=arms, paired_input_sha256=identity,
                       projection_baseline=full_projection(baselines, scope, 0.), projection_challenger=budget,
                       paired_val_deltas_r2=deltas, val_margin_nats=QUALITY_MARGIN_NATS, disposition=disposition,
                       projection_method="Slower observed rate in each phase, including a 900 s overhead reserve.",
                       actual_full_training="NOT_RUN"))
    print(f"PAIRED_COMPLETE {disposition} projection={budget['total_sec']:.2f}s margin={budget['margin_sec']:.2f}s", flush=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--worker", choices=(CONTROL, CHALLENGER))
    parser.add_argument("--record", type=Path)
    parser.add_argument("--steps", type=int, default=STEPS)
    parser.add_argument("--fraction", type=float)
    args = parser.parse_args()
    if (os.sched_getaffinity(0) != CPU_SET or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"
            or args.steps != STEPS):
        parser.error("pin CPU 0–7, one device and the admitted 96 updates")
    if args.worker:
        if (args.record is None or args.record.parent != RECORD or not 0 < (args.fraction or 0) < .31
                or read(RECORD / "profile.json")["approved_driver_sha256"] != own_sha()):
            parser.error("the paired worker needs the bounded supervisor and its exact source pin")
        args.raw_ce_rows = RAW_CE_ROWS
        args.course_ce_rows = COURSE_CE_ROWS
        return throughput.worker(args, checkpoint_roundtrip=roundtrip, arm_override=approved_arm(args.worker))
    if (args.stop_by is None or args.stop_by.tzinfo is None or args.stop_by > AUTHORIZED_END
            or args.stop_by.timestamp() - time.time() < 1200):
        parser.error("allow at least 20 minutes inside the explicit approval window")
    args.allocator_margin = ALLOCATOR_MARGIN_MIB
    deadline = args.stop_by.timestamp() - 35
    lock = os.open(throughput.ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        throughput.idle_gpu()
        RECORD.mkdir()
        for source in (Path(__file__), Path(throughput.__file__), *throughput.EXPERIMENT_SOURCES):
            with (RECORD / source.name).open("xb") as saved:
                saved.write(source.read_bytes())
        throughput.publish(RECORD / "profile.json", dict(pins=throughput.pin_inputs(), approved_driver_sha256=own_sha(),
                           steps=STEPS, arms=[(label, asdict(approved_arm(label))) for label in ORDER],
                           cutoff=deadline, card_ceiling_mib=throughput.CARD_MIB,
                           fixed_allocator_margin_mib=ALLOCATOR_MARGIN_MIB, allocator_limit_mib=ALLOCATOR_LIMIT_MIB,
                           raw_ce_rows=RAW_CE_ROWS, course_ce_rows=COURSE_CE_ROWS,
                           cpu_affinity=sorted(CPU_SET)))

        def stop(signum, _frame):
            raise KeyboardInterrupt(signal.Signals(signum).name)

        signal.signal(signal.SIGTERM, stop)
        for index, label in enumerate(ORDER):
            if time.time()+30 >= deadline or (RECORD / "STOP").exists():
                raise TimeoutError("the authorized experiment must stop before all four arms")
            destination = RECORD / f"{index:02d}_{label}"
            reason = throughput.run_arm(args, destination, label, deadline, worker_module=WORKER_MODULE,
                                        allocator_limit_mib=ALLOCATOR_LIMIT_MIB)
            if reason is not None or read(destination / "supervisor.json")["returncode"] != 0:
                raise RuntimeError(f"{destination.name} stopped; see the preserved worker and supervisor logs")
        conclude()
    finally:
        os.close(lock)
    return 0


if __name__ == "__main__":
    sys.exit(main())
