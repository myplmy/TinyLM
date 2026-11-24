"""Compare balanced visit counts with the sealed uniform P109C v2 training."""

import argparse
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from hashlib import sha256
from itertools import permutations
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import run_p109c_scratch_mixed as mixed
from tinylm.model import visibility


TAG = "p109c_scratch_mixed_v2_visit_count_v11_chat32_s1337"
PROBE_TAG = "p109c_mixed_visit_count_probe_chat32_v1_20261123"
SCHEMA = "P109C_MIXED_VISIT_COUNT_PLAN_V1"


def source_pins():
    return {path.name: mixed.prep.sha(path) for path in (
        Path(__file__), Path(mixed.__file__), Path(visibility.__file__), Path(mixed.routed.__file__),
        Path(mixed.routed.cla.__file__),
    )}


def update_content(bundle):
    schedule = bundle.schedule
    stats = np.zeros((bundle.steps, 7), dtype=np.int64)
    stats[:, 0] = (schedule[:, :, 0] == -1).sum(1) * mixed.MICRO_TOKENS
    for index, (values, info, lane) in enumerate(zip(bundle.data, bundle.aux, bundle.manifest["lanes"], strict=True)):
        language_offset = 1 if lane["name"].rsplit("_", 2)[1] == "ko" else 2
        lengths = (values[:, :, 2] > 0).sum((1, 2))
        labels = values[:, :, 1] != mixed.prep.IGNORE
        if lane["kind"] == "relation":
            golds = np.array([item["gold"] for item in info])
            labels &= np.arange(mixed.prep.BATCH)[None, :, None] == golds[:, None, None]
        rows, micro = np.nonzero(schedule[:, :, 0] == index)
        chosen = schedule[rows, micro, 1]
        np.add.at(stats[:, language_offset], rows, lengths[chosen])
        np.add.at(stats[:, language_offset + 2], rows, labels.sum((1, 2))[chosen])
        np.add.at(stats[:, 5], rows, int(lane["kind"] == "relation"))
        np.add.at(stats[:, 6], rows, np.array([len(item["decimal"]) for item in info])[chosen])
    return stats


def balance(stats):
    """Match exposure by pairing R1 and R3 within each four-update block."""
    pairs = np.array(list(permutations(range(4), 2)))
    depths = np.full(len(stats), 2, dtype=np.int16)
    rng = np.random.default_rng(1337)
    carry = np.zeros(stats.shape[1])
    scale = np.maximum(stats.mean(0), 1.)
    for first in range(0, len(stats) // 4 * 4, 4):
        group = stats[first:first + 4]
        differences = (group[pairs[:, 1]] - group[pairs[:, 0]]) / scale
        costs = np.abs(carry + differences).sum(1) + .05 * np.abs(differences).sum(1)
        selected = rng.choice(np.flatnonzero(np.isclose(costs, costs.min(), rtol=1e-10, atol=1e-10)))
        low, high = pairs[selected]
        depths[[first + low, first + high]] = [1, 3]
        carry += differences[selected]
    return depths


def make_profile(bundle):
    stats = update_content(bundle)
    depths = balance(stats)
    visits = 4 + 12 * depths.astype(np.int64)
    assert (depths.sum() == 2 * bundle.steps)
    return dict(schema=SCHEMA, manifest_sha256=bundle.digest, steps=bundle.steps, repeats=depths.tolist(),
                layer_token_visits=int(visits.sum()) * mixed.MICRO_TOKENS * mixed.prep.ACCUM,
                effective_visits_delta=((visits - 28)[:, None] * stats).sum(0).tolist(),
                visits_sha256=sha256(visits.astype("<i2").tobytes()).hexdigest(), sources=source_pins())


def read_profile(path, sha, manifest_sha):
    profile = json.loads(mixed.native.manifest_bytes(path, sha))
    repeats = profile["repeats"]
    if (profile["schema"] != SCHEMA or profile["manifest_sha256"] != manifest_sha
            or profile["sources"] != source_pins() or len(repeats) != profile["steps"]
            or any(type(depth) is not int for depth in repeats)
            or any(sorted(repeats[i:i + 4]) != [1, 2, 2, 3] for i in range(0, len(repeats) // 4 * 4, 4))
            or any(depth != 2 for depth in repeats[len(repeats) // 4 * 4:])):
        raise ValueError("the sealed, exposure-matched visit plan differs")
    return profile


def admits_r3(original, cfg, visits):
    middle = list(range(2, 14))
    fixed_r2 = [0, 1, *middle, *middle, 14, 15]
    fixed_r3 = [0, 1, *middle, *middle, *middle, 14, 15]
    return original(cfg, visits) or (visits == fixed_r3 and original(cfg, fixed_r2))


@contextmanager
def visit_count_route(profile, plan_sha, probe):
    repeats = [1, 2, 3] if probe else profile["repeats"]
    original_binding = mixed.context_training_state.make_binding
    original_native = mixed.routed.run_native
    acceptance = visibility._fixed_g4_r2
    observed = []

    def route(cfg, owners, policy, seed, index, steps):
        if policy != "balanced_count" or seed != 1337 or steps != profile["steps"] or not 0 <= index < steps:
            raise ValueError("the native route request differs from the sealed visit counts")
        if probe and index == len(repeats):
            raise mixed.ProbeComplete()
        visits = tuple(mixed.routed.cla.schedule(cfg, owners, "uniform", repeats[index]))
        observed.append(len(visits))
        return visits

    def binding(plan, recipe, cache, device):
        return original_binding(plan, dict(recipe, p109c_visit_count_profile=plan_sha), cache, device)

    def train(_policy, argv, *, build_model):
        return original_native("balanced_count", argv, build_model=build_model)

    with (patch.object(mixed.routed, "route_for", route),
          patch.object(mixed.routed, "run_native", train),
          patch.object(mixed.context_training_state, "make_binding", binding),
          patch.object(visibility, "_fixed_g4_r2", partial(admits_r3, acceptance)),
          patch.object(mixed, "TAG", TAG), patch.object(mixed, "PROBE_TAG", PROBE_TAG)):
        yield observed


def worker(plan_path, plan_sha, probe, path, manifest_sha, resume, record, cutoff):
    if resume:
        raise ValueError("the paired visit run starts from scratch")
    profile = read_profile(plan_path, plan_sha, mixed.native.digest(manifest_sha))
    mixed.native.publish(record / "visit_plan.json", dict(sha256=plan_sha, probe=probe, profile=profile))
    with visit_count_route(profile, plan_sha, probe) as observed:
        mixed.worker(True, .25, .02, None, probe, profile["sources"][Path(mixed.__file__).name],
                     path, manifest_sha, False, record, cutoff)
    if observed != ([16, 28, 40] if probe else [4 + 12 * repeat for repeat in profile["repeats"]]):
        raise ValueError("actual native route selections did not close the sealed visit schedule")
    mixed.native.publish(record / "visit_execution.json", dict(sha256=plan_sha, probe=probe,
                         counts={visits: observed.count(visits) for visits in (16, 28, 40)},
                         actual_visits_sha256=sha256(np.array(observed, dtype="<i2").tobytes()).hexdigest()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "check", "probe", "run"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--visit-plan", required=True, type=Path)
    parser.add_argument("--visit-plan-sha256")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    manifest = args.manifest.absolute()
    manifest_sha = mixed.native.digest(args.manifest_sha256)
    visit_plan = args.visit_plan.absolute()
    if args.mode == "prepare":
        result = make_profile(mixed.Bundle(manifest, manifest_sha))
        with visit_plan.open("x", encoding="utf-8") as output:
            print(json.dumps(result, indent=2), file=output)
        print("P109_VISIT_COUNT_PLAN", visit_plan, mixed.prep.sha(visit_plan), result["visits_sha256"], flush=True)
        return 0
    if not args.visit_plan_sha256:
        parser.error("the owned visit plan requires its SHA-256")
    plan_sha = mixed.native.digest(args.visit_plan_sha256)
    result = read_profile(visit_plan, plan_sha, manifest_sha)
    if args.mode == "check":
        print("P109_VISIT_COUNT_CHECK", plan_sha, result["steps"], result["layer_token_visits"], flush=True)
        return 0
    if not args.record or not args.stop_by or args.stop_by.tzinfo is None:
        parser.error("GPU operation requires a fresh record and a timezone-aware cutoff")
    record = args.record.absolute()
    with (patch.object(mixed.native, "gpu_worker", partial(worker, visit_plan, plan_sha, args.mode == "probe")),
          patch.object(mixed.native, "gpu_status", partial(mixed.telemetry.gpu_status, record))):
        return mixed.native.supervise(manifest, manifest_sha, False, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
