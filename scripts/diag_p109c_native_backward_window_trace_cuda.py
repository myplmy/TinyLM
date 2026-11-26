"""Rejoin native R2 autograd device events to their CPU launch windows."""

from argparse import ArgumentParser
from bisect import bisect_right
from collections import Counter, defaultdict
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p109c_native_backward_cuda as previous


base = previous.base
native = base.integrated.native
TAG = "p109c_native_backward_window_trace_20261126"
PROFILE = base.reference.EVIDENCE / f"{TAG}_profile.json"
RECORD = base.reference.EVIDENCE / TAG
ORIGINAL_SHA = "092CA3D1C943DE538761C319F756E4F2B27925BC3A037DB1032CB453DEF0691E"
NESTED_PHASE = "raw_head_backward_cuda_ms"
RAW_BACKWARD = "raw_backward_cuda_ms"
COURSE_BACKWARD = "course_backward_cuda_ms"
ATTENTION_BACKWARD = "aten::_flash_attention_backward"


def sealed_profile():
    admitted = json.loads(native.manifest_bytes(previous.PROFILE, ORIGINAL_SHA))
    if admitted["source_sha256"] != base.reference.file_sha(Path(previous.__file__)):
        raise ValueError("the original diagnostic source differs from its sealed profile")
    return dict(tag=TAG, phases="CPU_LAUNCH_WINDOWS", addresses=admitted["addresses"],
                original_profile_sha256=ORIGINAL_SHA, source_sha256=base.reference.file_sha(Path(__file__)))


def phase_index(intervals):
    intervals.sort()
    if any(end <= start for start, end, _ in intervals):
        raise ValueError("an annotation has an empty launch interval")
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
        raise ValueError("parallel phase windows cannot be assigned by containment")
    return [item[0] for item in intervals], intervals


def containing(index, time_range):
    starts, intervals = index
    place = bisect_right(starts, time_range.start) - 1
    if place >= 0:
        _, end, phase = intervals[place]
        if time_range.end <= end:
            return phase
    return None


def summary(events):
    phases = []
    nested = []
    for event in events:
        if event.device_type == torch.autograd.DeviceType.CPU and event.name.startswith(previous.TRACE_PREFIX):
            name = event.name.removeprefix(previous.TRACE_PREFIX)
            windows = nested if name == NESTED_PHASE else phases
            windows.append((event.time_range.start, event.time_range.end, name))
    main_index, nested_index = phase_index(phases), phase_index(nested)
    counts, times = defaultdict(Counter), defaultdict(Counter)
    found_by = defaultdict(Counter)
    disagreements = []
    for event in events:
        if (event.device_type != torch.autograd.DeviceType.CPU or event.self_device_time_total <= 0
                or event.name.startswith(previous.TRACE_PREFIX)):
            continue
        window = containing(nested_index, event.time_range) or containing(main_index, event.time_range)
        parent = event.cpu_parent
        while parent is not None and not parent.name.startswith(previous.TRACE_PREFIX):
            parent = parent.cpu_parent
        tree = parent.name.removeprefix(previous.TRACE_PREFIX) if parent is not None else None
        if tree is not None and window is not None and tree != window:
            disagreements.append((event.name, tree, window))
        phase = tree or window or "unattributed"
        kind = "parent" if tree else "launch_window" if window else "unattributed"
        found_by[phase][kind] += 1
        counts[phase][event.name] += 1
        times[phase][event.name] += event.self_device_time_total
    return dict(window_counts=dict(Counter(phase for _, _, phase in (*phases, *nested))),
                parent_window_disagreements=len(disagreements), first_disagreements=disagreements[:8],
                phases={phase: dict(total_self_device_us=sum(values.values()), event_sources=found_by[phase],
                    flash_backward_calls=counts[phase][ATTENTION_BACKWARD],
                    top=[dict(operator=name, calls=counts[phase][name], self_device_us=elapsed)
                         for name, elapsed in values.most_common(12)])
                        for phase, values in times.items()})


def collect(previous_profile, bundle, slots, parent, evaluation, record, deadline, addresses):
    state = torch.load(parent, map_location="cpu", mmap=True, weights_only=True)
    context = base.export.check_training_state(state, bundle.steps)
    archived = torch.load(evaluation, map_location="cpu", mmap=True, weights_only=True)
    if (context["binding"]["recipe"]["p109c_bilingual_mixed"] != previous_profile["integrated_training_signature"]
            or previous.state_sha(base.export.evaluation_payload(state)) != previous.state_sha(archived)):
        raise ValueError("the archive and the actual training body must agree")
    del archived
    cfg = base.TMTConfig(**state["cfg"])
    model = base.integrated.supervised.SupervisedG4(cfg).to("cuda").train()
    previous.set_mode(False)
    results = {}
    with patch.object(previous, "trace_summary", summary):
        for address in addresses:
            panel = previous_profile["panels"][str(address)]
            batches = base.device_batches(bundle, slots, address)
            counters = {}

            def restore():
                previous.verify_time(deadline)
                return base.restore(model, state, context, address, panel, bundle.steps)

            def run(arm, optimizer, _capture, phases):
                counters.update(base.run_update(model, bundle, batches, panel, optimizer, arm, phases))

            trace = previous.profile_baseline(restore, run)
            trace_data = trace.get("phases", {})
            by_phase = trace_data.get("phases", {})
            expected = {RAW_BACKWARD: 28 * sum(lane == -1 for lane, *_ in batches),
                        COURSE_BACKWARD: 28 * sum(lane >= 0 for lane, *_ in batches)}
            observed = {name: by_phase.get(name, {}).get("flash_backward_calls", 0) for name in expected}
            linked = (trace["status"] == "CAPTURED" and expected == observed
                      and trace_data["parent_window_disagreements"] == 0)
            result = dict(trace=trace, independently_timed_cuda_ms=counters.get("phase_events", {}),
                          expected_flash_backward_calls=expected, observed_flash_backward_calls=observed,
                          backward_phase_link_valid=linked)
            native.publish(record / f"{address}_trace.json", result)
            results[str(address)] = result
            del batches
    bundle.unchanged()
    if base.reference.file_sha(parent) != previous_profile["parent_sha256"]:
        raise ValueError("the read-only parent changed during tracing")
    return results


def worker(path, digest, _resuming, record, deadline):
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as out, redirect_stdout(out), redirect_stderr(out):
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        profile = sealed_profile()
        before, context, bundle, slots, parent, evaluation = previous.source_profile()
        if (profile != json.loads(native.manifest_bytes(path, digest))
                or before != json.loads(native.manifest_bytes(previous.PROFILE, ORIGINAL_SHA))
                or torch.cuda.device_count() != 1 or not torch.cuda.is_bf16_supported()):
            raise ValueError("the unchanged probe inputs and single CUDA device are required")
        free, total = torch.cuda.mem_get_info()
        available = (context["card_limit_mib"] - 384) * 2**20 - (total - free)
        if not 0 < available <= total:
            raise ValueError("insufficient whole-card headroom")
        torch.cuda.set_per_process_memory_fraction(available / total)
        torch.manual_seed(1337)
        results = collect(context, bundle, slots, parent, evaluation, record, deadline, profile["addresses"])
        native.publish(record / "report.json", dict(tag=TAG, profile_sha256=digest, addresses=results,
            status="BACKWARD_WINDOWS_VERIFIED" if all(x["backward_phase_link_valid"] for x in results.values())
            else "BACKWARD_WINDOWS_INCOMPLETE"))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("seal", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    mask = os.environ.get("CUDA_VISIBLE_DEVICES")
    if args.mode == "seal":
        if mask != "" or args.profile_sha256 or args.stop_by or PROFILE.exists() or RECORD.exists():
            parser.error("seal in CPU-only mode before creating a record")
        native.publish(PROFILE, sealed_profile())
        print(PROFILE, base.reference.file_sha(PROFILE))
        return 0
    if (args.stop_by is None or args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= previous.END
            or not args.profile_sha256 or os.sched_getaffinity(0) != base.CPUS or mask != "0"
            or "CUBLAS_WORKSPACE_CONFIG" in os.environ or RECORD.exists()):
        parser.error("use a new sealed record, CPU 0–7, CUDA 0, normal workspace and an authorized cutoff")
    return base.integrated.supervisor.supervise(worker, PROFILE, args.profile_sha256, RECORD, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
