"""Verify deterministic log deferral and profile the native R2 backward workload."""

from argparse import ArgumentParser
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import json
import os
from pathlib import Path
from statistics import median
from time import time

import torch

from scripts import diag_p109c_exact_update_cost as base
from scripts.diag_p102a_g4_full_delta_train import state_sha


TAG = "p109c_native_backward_cuda_20261126"
PROFILE = base.reference.EVIDENCE / f"{TAG}_profile.json"
RECORDS = {mode: base.reference.EVIDENCE / f"{TAG}_{mode}" for mode in ("deterministic", "native")}
PREVIOUS_SHA = "63BCF150D53EB45109CC656D9283E9C821C398AE26043BE7898FC8BD3A2E0D63"
ADDRESSES = (31, 1914)
ROUNDS = 4
END = datetime.fromisoformat("2026-11-26T14:20:00+09:00")
WORKSPACE = ":4096:8"
TRACE_PREFIX = "p109c.phase."


def source_profile():
    native = base.integrated.native
    current, bundle, slots, parent, evaluation = base.prepare()
    old = json.loads(native.manifest_bytes(base.PROFILE, PREVIOUS_SHA))
    if current != old:
        raise ValueError("the existing four-address diagnostic no longer matches the sealed input")
    result = dict(addresses=list(ADDRESSES), paired_rounds=ROUNDS, profile_operators=True,
                  baseline_panel_sha256=PREVIOUS_SHA, deterministic_cublas_workspace=WORKSPACE,
                  source_sha256=base.reference.file_sha(Path(__file__)))
    return result, current, bundle, slots, parent, evaluation


def verify_time(deadline):
    if time() >= deadline:
        raise TimeoutError("the native backward comparison reached its approved return time")


def set_mode(deterministic):
    torch.use_deterministic_algorithms(deterministic)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.deterministic = deterministic
    torch.backends.cudnn.benchmark = not deterministic
    torch.backends.cudnn.allow_tf32 = True
    torch.set_float32_matmul_precision("high")


def initialized(model, opt):
    return dict(model=state_sha(model.state_dict()), adam=state_sha(opt[0].state_dict()),
                muon=state_sha(opt[1].state_dict()), cpu_rng=state_sha(torch.get_rng_state()),
                cuda_rng=state_sha(torch.cuda.get_rng_state()))


class TaggedPhases(base.Phases):
    def __init__(self):
        super().__init__()
        self.annotations = []

    def start(self, name):
        annotation = torch.profiler.record_function(TRACE_PREFIX + name)
        annotation.__enter__()
        self.annotations.append(annotation)
        super().start(name)

    def end(self):
        super().end()
        self.annotations.pop().__exit__(None, None, None)

    def close(self):
        while self.annotations:
            self.annotations.pop().__exit__(None, None, None)


def trace_summary(events):
    by_phase = defaultdict(lambda: defaultdict(lambda: [0, 0.]))
    for event in events:
        if (event.device_type != torch.autograd.DeviceType.CPU or event.self_device_time_total <= 0
                or event.name.startswith(TRACE_PREFIX)):
            continue
        parent = event.cpu_parent
        while parent is not None and not parent.name.startswith(TRACE_PREFIX):
            parent = parent.cpu_parent
        phase = "unattributed" if parent is None else parent.name.removeprefix(TRACE_PREFIX)
        counts = by_phase[phase][event.name]
        counts[0] += 1
        counts[1] += event.self_device_time_total
    return {phase: dict(total_self_device_us=sum(us for _, us in operators.values()),
                        top=[dict(operator=name, calls=values[0], self_device_us=values[1]) for name, values in
                             sorted(operators.items(), key=lambda item: item[1][1], reverse=True)[:12]])
            for phase, operators in by_phase.items()}


def profile_baseline(restore, run):
    cuda = torch.profiler.ProfilerActivity.CUDA
    if cuda not in torch.profiler.supported_activities():
        return dict(status="CUDA_TRACE_UNAVAILABLE")
    optimizer = restore()
    phases = TaggedPhases()
    execution_error = None
    try:
        with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU, cuda]) as trace:
            try:
                run("baseline", optimizer, False, phases)
            except Exception as error:
                execution_error = error
                raise
            finally:
                phases.close()
    except RuntimeError as error:
        if execution_error is error:
            raise
        if execution_error is not None:
            raise execution_error from error
        return dict(status="TRACE_FAILED", error=str(error)[:1000])
    measured = trace_summary(trace.events())
    return dict(status="CAPTURED" if measured else "NO_DEVICE_EVENTS", phases=measured)


def diagnose(profile, native_profile, bundle, slots, parent, evaluation, record, deadline, mode):
    state = torch.load(parent, map_location="cpu", mmap=True, weights_only=True)
    context = base.export.check_training_state(state, bundle.steps)
    archived = torch.load(evaluation, map_location="cpu", mmap=True, weights_only=True)
    if (context["binding"]["recipe"]["p109c_bilingual_mixed"] != native_profile["integrated_training_signature"]
            or state_sha(base.export.evaluation_payload(state)) != state_sha(archived)):
        raise ValueError("the original native state must export the archived v3 checkpoint")
    del archived
    cfg = base.TMTConfig(**state["cfg"])
    model = base.integrated.supervised.SupervisedG4(cfg).to("cuda").train()
    deterministic = mode == "deterministic"
    set_mode(deterministic)
    comparisons = {}
    with (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as log:
        for address in profile["addresses"]:
            panel = native_profile["panels"][str(address)]
            batches = base.device_batches(bundle, slots, address)

            def restore():
                verify_time(deadline)
                return base.restore(model, state, context, address, panel, bundle.steps)

            def run(label, optimizer, capture, phases=None):
                statistics = base.run_update(model, bundle, batches, panel, optimizer, label, phases)
                if capture:
                    statistics.update(gradients=state_sha({name: param.grad for name, param in model.named_parameters()}),
                                      updated=state_sha(model.state_dict()), adam=state_sha(optimizer[0].state_dict()),
                                      muon=state_sha(optimizer[1].state_dict()))
                print(json.dumps(dict(address=address, arm=label, traced=phases is not None,
                                      deterministic=deterministic, **statistics)), file=log)
                return statistics

            if deterministic:
                comparisons[str(address)] = identity_trials(model, restore, run)
            else:
                measurements = speed_trials(profile, restore, run)
                base.integrated.native.publish(record / f"{address}_timing.json", measurements)
                comparisons[str(address)] = dict(measurements, operators=profile_baseline(restore, run))
            del batches
    bundle.unchanged()
    if base.reference.file_sha(parent) != native_profile["parent_sha256"]:
        raise ValueError("the read-only parent changed during measurement")
    report = dict(mode=mode, addresses=comparisons)
    if deterministic:
        report["exact"] = all(item["initial_exact"] and not item["baseline_repeat_difference"] and not item["deferred_difference"]
                              for item in comparisons.values())
    else:
        report["wall_median_reduction"] = median(p["reduction"] for item in comparisons.values() for p in item["times"])
        report["both_addresses_reduce"] = all(item["median_reduction"] > 0 for item in comparisons.values())
    base.integrated.native.publish(record / "report.json", dict(status="NATIVE_BACKWARD_ATTRIBUTION_COMPLETE",
        profile_sha256=base.reference.file_sha(PROFILE), **report))


def identity_trials(model, restore, run):
    states, measured = [], []
    for arm in ("baseline", "deferred", "baseline"):
        optimizer = restore()
        states.append(initialized(model, optimizer))
        measured.append(run(arm, optimizer, True))
    return dict(initial_exact=states[0] == states[1] == states[2], initial=states,
                baseline_repeat_difference=base.check_identity(measured[2], measured[0]),
                deferred_difference=base.check_identity(measured[1], measured[0]))


def speed_trials(profile, restore, run):
    run("baseline", restore(), False)
    times = []
    for order in range(profile["paired_rounds"]):
        arms = ("baseline", "deferred")
        seconds = {arm: run(arm, restore(), False)["seconds"]
                   for arm in (arms if order % 2 == 0 else arms[::-1])}
        times.append(dict(seconds, reduction=1. - seconds["deferred"]/seconds["baseline"]))
    return dict(times=times, median_reduction=median(row["reduction"] for row in times))


def worker(path, digest, _resuming, record, deadline, *, mode):
    native = base.integrated.native
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as output, redirect_stdout(output), redirect_stderr(output):
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        profile, old, bundle, slots, parent, evaluation = source_profile()
        if (profile != json.loads(native.manifest_bytes(path, digest)) or torch.cuda.device_count() != 1
                or not torch.cuda.is_bf16_supported()):
            raise ValueError("the sealed case or CUDA device differs")
        free, total = torch.cuda.mem_get_info()
        budget = (old["card_limit_mib"] - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("insufficient whole-card allocation headroom")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        torch.manual_seed(1337)
        diagnose(profile, old, bundle, slots, parent, evaluation, record, deadline, mode)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("seal", *RECORDS))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    mask = os.environ.get("CUDA_VISIBLE_DEVICES")
    if args.mode == "seal":
        if mask != "" or args.profile_sha256 or args.stop_by or PROFILE.exists() or any(p.exists() for p in RECORDS.values()):
            parser.error("the frozen comparison requires an unused output and CPU-only preparation")
        profile, *_ = source_profile()
        base.integrated.native.publish(PROFILE, profile)
        print(PROFILE, base.reference.file_sha(PROFILE), flush=True)
        return 0
    expected_workspace = WORKSPACE if args.mode == "deterministic" else None
    record = RECORDS[args.mode]
    if (args.stop_by is None or args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or not args.profile_sha256 or os.sched_getaffinity(0) != base.CPUS or mask != "0"
            or os.environ.get("CUBLAS_WORKSPACE_CONFIG") != expected_workspace or record.exists()):
        parser.error("use one CUDA device, CPU 0–7, the matching workspace, and the exact time and source seal")
    return base.integrated.supervisor.supervise(partial(worker, mode=args.mode), PROFILE, args.profile_sha256, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
