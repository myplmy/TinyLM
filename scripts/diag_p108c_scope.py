"""Offline edit-scope diagnosis from sealed prior numeric artifacts only.

No torch import, checkpoint loading, language-model inference, or final/test
reading. Cached answer joins are explicitly not fresh native model results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time

import tinylm
import numpy as np

from scripts import p108c_scope as scope
from scripts import p108c_limits as limits

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "test_result/evidence/p108b_layer_transfer_v2_s1337"
PM = ROOT / "test_result/evidence/p108b_layer_transfer_v3_s1337"
BASE = ROOT / "test_result/evidence/p108c_night_v1_s1337"
PROFILE = BASE / "scope_profile_v1.json"
OUT = BASE / "scope_offline_v1"
PLAN = ROOT / "test_plan/P108_직접가중치-방향수리와-학습개입.md"
ARM = PM / "norm_sweep_v1/PER_TARGET_PROTECT_S2p0"
FORECAST = PM / "lastlayer_forecast_v1"
CODE = ("scripts/p108c_scope.py", "scripts/p108c_limits.py",
        "scripts/diag_p108c_scope.py", "scripts/test_p108c_scope.py")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value):
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True,
                          indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(payload) >= 20_000_000:
        raise ValueError("split result before the20MB limit")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path), bytes=len(payload))


def load_arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        result = {key: archive[key].copy() for key in archive.files}
    if any(x.dtype.kind not in "fiub" or not np.isfinite(x).all() for x in result.values()):
        raise ValueError("finite numeric non-pickle source arrays required")
    return result


def save_arrays(path, **arrays):
    if sum(x.nbytes for x in arrays.values()) >= 18_000_000:
        raise ValueError("split arrays before20MB")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    if path.stat().st_size >= 20_000_000:
        raise RuntimeError("result unexpectedly exceeds20MB")
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path), bytes=path.stat().st_size)


def closed_answers(directory, manifest):
    result = {}
    for shard in manifest["shards"]:
        path = directory / shard["path"]
        if sha(path) != shard["sha256"].upper():
            raise ValueError("closed answer shard changed")
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["id"] in result:
                raise ValueError("duplicate cached-answer ID")
            result[row["id"]] = row
    if len(result) != manifest["rows"]:
        raise ValueError("cached-answer count differs")
    return result


def inputs():
    parent_profile = read(PM/"norm_profile_v1.json")
    forecast_profile = read(PM/"lastlayer_forecast_profile_v1.json")
    for parent in (parent_profile, forecast_profile):
        for relative, expected in parent["references"].items():
            if sha(ROOT/relative) != expected.upper():
                raise ValueError("closed parent reference changed: " + relative)
    norm_closed = read(PM/"norm_sweep_v1/report.json")
    if (not norm_closed["status"].startswith("NORM_SWEEP_COMPLETE") or
            not norm_closed["original_core_restored"] or
            norm_closed["cuda_allocated_after_bytes"] or norm_closed["cuda_reserved_after_bytes"]):
        raise ValueError("closed global edit and cleanup proof required")
    data = read(OLD / "data.json")
    fits = [r for r in data["rows"] if r["split"] == "fit"]
    dev = read(OLD / "select_dev.json")["rows"]
    if len(fits) != 24 or len(dev) != 96 or sum(r["family"] == "target" for r in dev) != 48:
        raise ValueError("sealed FIT24 and SELECT-DEV96 required")
    forecasts = read(FORECAST / "PREDICTIONS_BEFORE_EDITED_FORWARD_v1.json")
    closed = read(FORECAST / "report.json")
    if (not closed["original_core_restored"] or closed["cuda_allocated_after_bytes"] or
            closed["cuda_reserved_after_bytes"] or not closed["prediction_sealed_before_actual"]):
        raise ValueError("closed native source with exact original-key identity required")
    if not all(row["input_key_exact"] for row in closed["rows"]):
        raise ValueError("last-layer source input changed")
    keys, refs = {}, set()
    for item in forecasts["pins"]:
        if item["position"] != 0:
            continue
        spec = item["packet"]
        path = ROOT / spec["path"]
        if sha(path) != spec["sha256"].upper():
            raise ValueError("original feature packet changed")
        if item["id"] in keys:
            raise ValueError("duplicate prefix-only feature ID")
        keys[item["id"]] = load_arrays(path)["original_key"]
        refs.add(path)
    guard_ids = [i for i in keys if i.startswith("preserve:")]
    if len(guard_ids) != 7 or len(keys) != 103 or not all(r["id"] in keys for r in dev):
        raise ValueError("exact103 prefix-only native features required")
    weighted_path = PM / "norm_sweep_v1/PER_TARGET_full_solution.npz"
    full_solution = load_arrays(weighted_path)
    weighted = full_solution["weighted_keys"]
    fit_keys, cursor, horizons = [], 0, {}
    for row in fits:
        path = OLD / ("target_values_v1/values/PER_TARGET_layer13_" + row["fact"] + ".json")
        value = read(path)
        if value["fact"] != row["fact"] or value["layer"] != 13 or value["mode"] != "PER_TARGET":
            raise ValueError("same native target-value row required")
        count = len(value["target_values"])
        if not count or cursor + count > weighted.shape[1]:
            raise ValueError("target-window columns are truncated")
        fit_keys.append((weighted[:, cursor] * math.sqrt(count)).astype(np.float32))
        horizons[row["id"]] = count
        cursor += count
        refs.add(path)
    if weighted.shape != (2048, cursor) or cursor != 62:
        raise ValueError("all62 question-weighted target columns must be accounted")
    calibration_path = OLD / "geometry/layer13_calibration.npz"
    raw_cal = load_arrays(calibration_path)["keys"]
    questions = data["calibration_questions"]
    if len(questions) != 128 or raw_cal.shape != (1024, 2048):
        raise ValueError("128 prompts with native last8 calibration keys required")
    cal_keys = raw_cal.reshape(128, 8, 2048)[:, -1]
    related = "What is the capital of France?"
    excluded = [i for i, q in enumerate(questions) if q == related]
    if excluded != [75]:
        raise ValueError("ROOT-reviewed CAL related-family annotation differs")
    selected_cal = [i for i in range(128) if i not in excluded]
    def negative_group(i):
        return ("cal_task:" + str(i//8) if i < 64 else
                "user_case:" + str(i) if i < 80 else "role_query_template")
    train_meta = [dict(id=r["id"], question=r["question"], role="FIT_SCOPE_POSITIVE",
                       label=1, group="fact:" + r["fact"]) for r in fits]
    train_meta += [dict(id="cal:" + str(i), question=questions[i], role="CAL_SCOPE_NEGATIVE",
                        label=0, group=negative_group(i)) for i in selected_cal]
    train_x = np.concatenate([np.stack(fit_keys), cal_keys[selected_cal]], axis=0)
    dev_x = np.stack([keys[r["id"]] for r in dev])
    guard_x = np.stack([keys[i] for i in guard_ids])
    packet_path = ARM / "packet.npz"
    arm_record = read(ARM/"report.json")
    if sha(packet_path) != arm_record["packet"]["sha256"].upper():
        raise ValueError("closed global edit packet changed")
    delta = load_arrays(packet_path)["requested"]
    if not np.array_equal(delta, (full_solution["full"] * 2).astype(np.float32)):
        raise ValueError("the reused full solution does not reproduce the fixed global edit")
    if delta.shape != (768, 2048):
        raise ValueError("fixed joint last-layer requested delta required")
    refs.update({OLD/"data.json", OLD/"select_dev.json", weighted_path, calibration_path,
                 packet_path, ARM/"report.json", FORECAST/"report.json",
                 FORECAST/"PREDICTIONS_BEFORE_EDITED_FORWARD_v1.json",
                 PM/"norm_profile_v1.json", PM/"lastlayer_forecast_profile_v1.json",
                 PM/"norm_sweep_v1/report.json", OLD/"geometry/report.json"})
    original_manifest = read(OLD/"geometry/report.json")["baseline"]["answers_manifest"]
    edited_manifest = read(ARM/"report.json")["answers_manifest"]
    for directory, manifest in ((OLD/"geometry", original_manifest), (ARM, edited_manifest)):
        for spec in manifest["shards"]:
            refs.add(directory/spec["path"])
    return dict(train_x=train_x, train_meta=train_meta, fits=fits, horizons=horizons,
        dev_x=dev_x, dev=dev, guard_x=guard_x, guard_ids=guard_ids,
        delta=delta, refs=refs, original_manifest=original_manifest,
        edited_manifest=edited_manifest,
        exclusions=[dict(id="cal:75", role="RELATED_UNLABELLED_NOT_NEGATIVE", question=related)],
        feature_provenance="FIT: first target-window key restored from per-question weighting; CAL: last of8; DEV/guard: original prefix-only native")


def prepare():
    limits.Budget(900).check(admission=True)
    if BASE.exists():
        raise FileExistsError("fresh night namespace required; preserve any previous attempt")
    source = inputs()
    parent = read(PM/"norm_profile_v1.json")
    plan = PLAN.read_bytes()
    if b"p108c-scoped-edit" not in plan:
        raise ValueError("P108C plan must precede the experiment")
    profile = dict(schema="P108C_SCOPE_OFFLINE_V1", authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(), cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=900, model=parent["parent_model"], origin=parent["origin"], layer=13,
        code={name:sha(ROOT/name) for name in CODE},
        references={str(path.relative_to(ROOT)):sha(path) for path in sorted(source["refs"])},
        initial_plan_sha256=hashlib.sha256(plan).hexdigest().upper(),
        numpy_version=np.__version__, python_version=platform.python_version(),
        initial_feature_counts=dict(train=len(source["train_x"]), positive=24, negative=127, dev=96, guard=7),
        feature_provenance=source["feature_provenance"], exclusions=source["exclusions"],
        full_model_or_checkpoint_loads=0, gpu_calls=0, generated_answers=0,
        final_or_official_consumed=False, ridge_values=[1e-4, 1e-2, 1.])
    BASE.mkdir()
    with (BASE/"scope_initial_plan_v1.md").open("xb") as stream:
        stream.write(plan)
    write_new(PROFILE, profile)
    print("[SCOPE_PREPARED] reused raw features; model0; TRAIN151/DEV96/guard7", flush=True)


def verify():
    limits.Budget(900).check()
    p = read(PROFILE)
    if (p["authority_directive"] != 142 or p["authority_end"] != limits.AUTHORITY_END.isoformat() or
            p["code"] != {name:sha(ROOT/name) for name in CODE} or
            p["numpy_version"] != np.__version__ or
            sha(BASE/"scope_initial_plan_v1.md") != p["initial_plan_sha256"]):
        raise ValueError("new night authority, exact code/runtime and initial plan required")
    for path, expected in p["references"].items():
        if sha(ROOT/path) != expected:
            raise ValueError("frozen numeric source changed: " + path)
    return p


def save_model(model):
    arrays = {k:v for k, v in model.items() if isinstance(v, np.ndarray)}
    metadata = {k:v for k, v in model.items() if not isinstance(v, np.ndarray)}
    if arrays:
        metadata["arrays"] = save_arrays(OUT/"models"/(model["name"]+".npz"), **arrays)
    metadata["model_array_names"] = sorted(arrays)
    return metadata


def offline():
    p = verify()
    budget = limits.Budget(p["max_seconds"])
    budget.check(admission=True)
    if OUT.exists():
        raise FileExistsError("preserve prior offline fit and selection")
    source = inputs()
    OUT.mkdir()
    started = time.monotonic()
    x, dev, guard = [source[k] for k in ("train_x", "dev_x", "guard_x")]
    y = [r["label"] for r in source["train_meta"]]
    dev_y = [int(r["family"] == "target") for r in source["dev"]]
    models, fitting = scope.fit_models(x, y, [r["group"] for r in source["train_meta"]],
                                      source["delta"], ridge_values=tuple(p["ridge_values"]))
    budget.check()
    model, selection = scope.select(models, x, y, dev, dev_y, guard)
    chosen = selection["selected"]
    pins = {m["name"]:save_model(m) for m in models}
    if model["name"] not in pins:
        pins[model["name"]] = save_model(model)
    input_pin = save_arrays(OUT/"reused_features.npz", train=x, dev=dev, guard=guard)
    write_new(OUT/"inputs.json", dict(train=source["train_meta"], dev=source["dev"],
        guard_ids=source["guard_ids"], horizons=source["horizons"], exclusions=source["exclusions"],
        feature_provenance=source["feature_provenance"], feature_packet=input_pin))
    write_new(OUT/"frozen_router_v1.json", dict(model=pins[model["name"]], threshold=chosen["threshold"],
        profile_sha256=sha(PROFILE), selection_rule=selection["selection_rule"],
        selected_before_any_new_native_run=True, final_or_official_consumed=False))
    write_new(OUT/"selection.json", selection)
    original = closed_answers(OLD/"geometry", source["original_manifest"])
    edited = closed_answers(ARM, source["edited_manifest"])
    joined = {}
    for name, features, rows in (("FIT", x[:24], source["fits"]),
                                  ("DEV", dev, source["dev"])):
        decisions = scope.route(model, features, chosen["threshold"])
        values = []
        for row, decision in zip(rows, decisions):
            a, b = original[row["id"]], edited[row["id"]]
            selected = b if decision else a
            values.append(dict(id=row["id"], gated_on=bool(decision),
                original_exact=a["exact"], global_edit_exact=b["exact"],
                cache_join_exact=selected["exact"],
                family=row.get("family"), language=row.get("language")))
        joined[name] = dict(rows=values, original_exact=sum(r["original_exact"] is True for r in values),
            global_edit_exact=sum(r["global_edit_exact"] is True for r in values),
            cache_join_exact=sum(r["cache_join_exact"] is True for r in values),
            caveat="OFFLINE_CACHE_JOIN_ONLY_NOT_NEW_NATIVE_INFERENCE")
    scores = dict(train={m["name"]:scope.score(m, x).tolist() for m in models},
                  dev={m["name"]:scope.score(m, dev).tolist() for m in models},
                  guard={m["name"]:scope.score(m, guard).tolist() for m in models})
    write_new(OUT/"scores.json", scores)
    write_new(OUT/"cached_answer_join.json", joined)
    budget.check()
    report = dict(schema=p["schema"], status="SCOPE_OFFLINE_COMPLETE_NATIVE_NOT_RUN",
        selected=chosen, candidate_models=len(models), threshold_trials=len(selection["candidates"]),
        fitting=fitting, feature_provenance=source["feature_provenance"],
        original_numeric_sources_verified=True, input_packet=input_pin,
        new_model_loads=0, gpu_calls=0, generated_answers=0,
        body_optimizer_updates=0, value_optimizer_updates=0,
        router_training="weighted closed-form ridge and fixed prototype/statistic candidates",
        wall_seconds=time.monotonic()-started, source_profile_sha256=sha(PROFILE),
        final_or_official_consumed=False,
        next_gate="NATIVE_FEATURE_AND_BRANCH_REPLAY_BEFORE_NEW_QUALITY_CLAIM")
    write_new(OUT/"report.json", report)
    print("[SCOPE_OFFLINE_END] " + json.dumps({k:report[k] for k in
        ("status", "selected", "candidate_models", "threshold_trials", "wall_seconds")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("preflight", "prepare", "check", "offline"))
    phase = parser.parse_args().phase
    if phase == "preflight":
        limits.Budget(900).check(admission=True)
        source = inputs()
        print("[SCOPE_PREFLIGHT] TRAIN151/DEV96/guard7; source identity; no writes/model/CUDA",
              flush=True)
    elif phase == "prepare":
        prepare()
    elif phase == "check":
        verify()
        print("[SCOPE_CHECK] exact source/authority; no model or CUDA", flush=True)
    else:
        offline()


if __name__ == "__main__":
    main()
