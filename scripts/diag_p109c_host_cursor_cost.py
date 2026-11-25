"""Check CPU-side validation of training draws before materializing the sealed CUDA inputs."""

from argparse import ArgumentParser
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter, time

import numpy as np
import torch

from scripts import diag_p109c_exact_update_cost as update
from tinylm.data.loader import Loader
from tinylm.train import context_curriculum, context_micro_tokens


TAG = "p109c_source_cursor_cost_cuda_20261126"
PROFILE = update.ROOT / "test_result/evidence" / f"{TAG}_profile_v3.json"
OUT = PROFILE.with_name(TAG)
END = datetime.fromisoformat("2026-11-26T09:10:00+09:00")
ARMS = ("native_cuda_validation", "host_validation")
REPEATS = 8


def inputs():
    integrated = update.integrated
    old, bundle, slots, _ = integrated.prepare("original", "capped", "proportional", 0., True)
    plan = context_curriculum.ContextPlan(((bundle.steps, integrated.prep.WIDTH),),
                                         micro_bs=integrated.prep.BATCH, base_accum=integrated.prep.ACCUM)
    sources = (Path(__file__), Path(update.__file__), Path(context_curriculum.__file__),
               Path(context_micro_tokens.__file__), update.ROOT / "tinylm/data/loader.py")
    pins = {str(path.relative_to(update.ROOT)): update.reference.file_sha(path) for path in sources}
    selection = update.reference.completed.read_json(update.PROFILE)
    if (selection["replay_signature"] != old["signature"] or selection["addresses"] != list(update.ADDRESSES)
            or selection["sources"][str(Path(update.__file__).relative_to(update.ROOT))]
            != pins[str(Path(update.__file__).relative_to(update.ROOT))]):
        raise ValueError("the existing actual training input seal differs")
    profile = dict(tag=TAG, native_update_profile_sha256=update.reference.file_sha(update.PROFILE),
                   source_manifest_sha256=bundle.digest, plan=plan.contract(), source_seed=1234, addresses=list(update.ADDRESSES),
                   arms=list(ARMS), sources=pins, cache_sha256=bundle.cache["identity_sha256"], repeats=REPEATS,
                   attribution="Synchronized isolated input preparation, excluding model and optimizer",
                   modules_loaded_on_gpu=0, candidate_scope="same host reads, snapshots, checks, proposals and PCG64 state")
    bundle.unchanged()
    return profile, bundle, plan, slots


def starting_state(plan, source, address, source_sha256):
    generator = np.random.default_rng(1234)
    for _ in range(address * plan.base_accum):
        generator.integers(0, len(source.d) - source.seq - 1, source.bs)
    source.rng.bit_generator.state = generator.bit_generator.state
    cursor = context_micro_tokens.MicroTokensCursor(plan, source, source_sha256=source_sha256)
    empty = cursor.state_dict()
    fixed = empty["cursor"]
    fixed.update(next_update=address, optimizer_updates=address, source_calls=address*plan.base_accum,
                 draw_tokens=address*plan.tokens_per_update, ntp_targets=address*plan.tokens_per_update)
    fixed.pop("state_sha256")
    fixed["state_sha256"] = context_curriculum._sha(fixed)
    empty.pop("state_sha256")
    empty["state_sha256"] = context_micro_tokens._sha(empty)
    return empty


def prepare_update(bundle, slots, address, cursor, *, source_device):
    original = cursor.prepare()
    order = bundle.schedule[address]
    raw = iter(bundle.raw_batch(order[order[:, 0] == -1, 1]))
    ready = []
    for (lane, index), (original_x, original_y) in zip(order, original.batches, strict=True):
        if lane == -1:
            tokens = next(raw)
            x, y = tokens[:, :-1], tokens[:, 1:]
        elif lane >= 0:
            x, y, _ = update.integrated.supervised.course_microbatch(bundle, slots, address, lane, index)
            x, y = x.astype(np.int64), y.astype(np.int64)
        else:
            ready.append((original_x, original_y) if source_device == "cuda" else
                         (original_x.to("cuda"), original_y.to("cuda")))
            continue
        if source_device == "cuda":
            ready.append((original_x.new_tensor(x), original_y.new_tensor(y)))
        else:
            ready.append((torch.tensor(x, device="cuda"), torch.tensor(y, device="cuda")))
    return original, ready


def capture(ready, device):
    stamp = sha256()
    for x, y in ready:
        for tensor in (x, y):
            if tensor.dtype != torch.long or tensor.device.type != device:
                raise ValueError("the source or model-facing batch dtype or device differs")
            layout = (tuple(tensor.shape), tensor.stride(), tensor.storage_offset())
            stamp.update(repr(layout).encode())
            stamp.update(tensor.cpu().contiguous().numpy().tobytes())
    return stamp.hexdigest().upper()


def run(profile, bundle, plan, slots, record, deadline):
    source = {arm: Loader("train", plan.micro_bs, plan.full_length, device, update.integrated.prep.CACHE, seed=1234)
              for arm, device in zip(ARMS, ("cuda", "cpu"), strict=True)}
    baseline_validation = next(iter(source.values()))
    source_sha = profile["cache_sha256"]
    timings = defaultdict(list)
    metadata = {}
    with (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress:
        for address in update.ADDRESSES:
            fixed = starting_state(plan, baseline_validation, address, source_sha)
            for repeat in range(REPEATS + 1):
                for arm in ARMS if repeat % 2 == 0 else reversed(ARMS):
                    if time() >= deadline:
                        raise TimeoutError("source preparation reached its approved CUDA return time")
                    loader = source[arm]
                    cursor = context_micro_tokens.MicroTokensCursor(plan, loader, source_sha256=source_sha)
                    cursor.load_state_dict(fixed)
                    torch.cuda.synchronize()
                    started = perf_counter()
                    original, actual = prepare_update(bundle, slots, address, cursor, source_device=loader.device)
                    torch.cuda.synchronize()
                    seconds = perf_counter() - started
                    counters = cursor.finish(optimizer_applied=True)
                    if repeat in (0, REPEATS):
                        final = capture(actual, "cuda")
                        source_stamp = cursor.state_dict()["state_sha256"]
                        sizes = {key: counters[key] for key in ("source_calls", "source_snapshot_bytes", "origin_ranges_sha256")}
                        identity = dict(final=final, original_draws=capture(original.batches, loader.device),
                                        source_state=source_stamp, counts=sizes)
                        if address in metadata and metadata[address] != identity:
                            raise ValueError("model-facing tokens, source draws or committed state changed")
                        metadata[address] = identity
                    if repeat:
                        timings[address, arm].append(seconds)
                    if repeat in (0, REPEATS):
                        print(json.dumps(dict(address=address, arm=arm, iteration=repeat, seconds=seconds)), file=progress)
                    del original, actual
    bundle.unchanged()
    result = {}
    for address in update.ADDRESSES:
        native, host = (timings[address, arm] for arm in ARMS)
        result[str(address)] = dict(
            original_s=native, host_s=host, median_difference_s=median(native) - median(host),
            identity=metadata[address])
    update.integrated.native.publish(record / "report.json", dict(status="PREPARE_PROBE_COMPLETE", by_address=result,
                                     profile_sha256=update.reference.file_sha(PROFILE), starts=profile["addresses"]))


def worker(path, expected, _resuming, record, deadline):
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        profile, bundle, plan, slots = inputs()
        if profile != json.loads(update.integrated.native.manifest_bytes(path, expected)) or torch.cuda.device_count() != 1:
            raise ValueError("the preparation profile or single CUDA device differs")
        torch.cuda.set_per_process_memory_fraction(min(.1, 768 * 2**20 / torch.cuda.get_device_properties(0).total_memory))
        run(profile, bundle, plan, slots, record, deadline)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "seal":
        if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by or args.profile_sha256:
            parser.error("sealing uses no CUDA work")
        profile, *_ = inputs()
        update.integrated.native.publish(PROFILE, profile)
        print(update.reference.file_sha(PROFILE), flush=True)
        return 0
    if (args.stop_by is None or args.stop_by.tzinfo is None
            or not datetime.now().astimezone() < args.stop_by <= END or not args.profile_sha256
            or os.sched_getaffinity(0) != update.CPUS or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("use CPU 0–7, the protected device and a bounded isolated sample")
    return update.integrated.supervisor.supervise(worker, PROFILE, args.profile_sha256, OUT, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
