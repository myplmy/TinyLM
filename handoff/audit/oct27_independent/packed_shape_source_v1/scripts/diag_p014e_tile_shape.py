#!/usr/bin/env python3
"""Same payload/oracle; output-row shape intervention, no threshold relaxation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p014e_packed_deploy as prior
from scripts import diag_p106b_resource_matrix as resource

SCHEMA = "P014E_SAME_PAYLOAD_ROW_SHAPE_DIAGNOSIS_V1"
TAG = prior.TAG + "_tile_shape"
TILES = (128, 512, 4096)
OWN = ("scripts/diag_p014e_tile_shape.py", "scripts/test_p014e_tile_shape.py")
need = resource.need


def identity():
    files = dict(prior.identity()["files"])
    files.update({name: resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def difference(actual, expected):
    import torch
    need(actual.shape == expected.shape and actual.dtype == expected.dtype == torch.float32
         and bool(torch.isfinite(actual).all()) and bool(torch.isfinite(expected).all()), "finite matched FP32 logits required")
    delta = actual - expected
    return dict(max_abs=float(delta.abs().max()), mean_abs=float(delta.abs().mean()),
                relative_l2=float(delta.norm() / expected.norm().clamp_min(1e-30)),
                outside_original_tolerance=int((~torch.isclose(actual,expected,rtol=2e-5,atol=2e-6)).sum()),
                original_allclose=bool(torch.allclose(actual, expected, rtol=2e-5, atol=2e-6)),
                exact_equal=torch.equal(actual, expected),
                argmax_equal=torch.equal(actual.argmax(-1), expected.argmax(-1)),
                tolerance_unchanged=dict(rtol=2e-5, atol=2e-6))


def validate(profile, args):
    need(profile.get("schema") == SCHEMA and profile.get("tag") == TAG
         and profile.get("root_approved") is True and profile.get("authority_directive") == 96
         and profile.get("source_sha256") == identity()["sha256"]
         and profile.get("tiles") == list(TILES) and args.max_wall_sec == profile["max_wall_sec"] == 900,
         "fixed source-bound shape experiment required")
    need(profile.get("deadline") == "2026-10-27T08:00:00+00:00"
         and profile.get("mode") == args.mode == "diagnose"
         and (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds() > 1080,
         "current whole experiment and closure must fit")
    original = resource.read_ref(profile["prior_profile"])
    base, spec = prior.validate(original, SimpleNamespace(mode="deploy-cuda", max_wall_sec=1200))
    original["_file_sha256"] = profile["prior_profile"]["sha256"]
    baseline = prior.closed("baseline-cuda", original)
    exported = prior.closed("export", original)
    error = resource.read_ref(profile["prior_error"])
    need(error["phase"] == "deploy-cuda" and error["exit_code"] == 9
         and error["profile_sha256"] == original["_file_sha256"] and error["source"] == prior.identity()
         and error["error"]["message"] == "same-device row-tile logits exceed declared tolerance",
         "exact retained numeric error required")
    prior.assert_cuda_clean(error["final_cuda_cleanup"])
    for receipt, key in ((baseline, "prior_baseline"), (exported, "prior_export")):
        need(resource.read_ref(profile[key]) == receipt, "exact prior receipt bytes required")
    need([(row["variant"],row["path"]) for row in exported["payloads"]]
         == [(v,str((prior.deploy_dir()/(v+".pt")).relative_to(ROOT))) for v in prior.VARIANTS], "exact payload namespace required")
    need(baseline["oracle"]["path"] == str((prior.deploy_dir()/"baseline_cuda_oracle.pt").relative_to(ROOT)),
         "exact CUDA oracle namespace required")
    return original, base, baseline, exported


def observe(model, oracle, budget):
    import torch
    forward = resource.FP32Forward(model, "cuda")
    errors = []
    with torch.no_grad():
        for row in oracle:
            budget.check()
            logits, kv = forward(torch.tensor([row["ids"]], device="cuda"), use_cache=True, logits_last_only=True)
            for step, expected in enumerate(row["logits"]):
                errors.append(dict(workload=row["id"], step=step,
                                   **difference(logits.detach().cpu(), expected)))
                if step < len(row["logits"]) - 1:
                    logits, kv = forward(torch.tensor([[row["teacher_ids"][step]]], device="cuda"),
                                         past_kv=kv, use_cache=True, logits_last_only=True)
            del logits, kv
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("diagnose",), required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--max-wall-sec", type=int, required=True)
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument("--execute", action="store_true")
    execution.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    profile = resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    original, base, baseline, exported = validate(profile, args)
    if args.check_only:
        print(json.dumps(dict(status="ROW_SHAPE_METADATA_ONLY",model_loads=0,gpu_calls=0)))
        return 0
    need(args.execute, "explicit GPU shape diagnosis required")
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    source, budget = identity(),resource.Budget(args.max_wall_sec)
    output = resource.safe("test_result/evidence/"+TAG+"/report.json")
    need(not output.exists(),"new diagnosis output required")
    report = dict(schema=SCHEMA,tag=TAG,source=source,profile_sha256=args.profile_sha256,
                  previous_error=profile["prior_error"],source_profile=profile["prior_profile"],
                  status="STARTED",training_updates=0,original_checkpoint_loads=0,checkpoint_writes=0,
                  quality_claim=False,rows=[],started_at=datetime.now(timezone.utc).isoformat())
    model = None
    rc = 9
    try:
        with resource.wall(args.max_wall_sec):
            from scripts.interactive_research_infer import require_idle_gpu
            from scripts.diag_p102a_logit_margin import memory_point
            report["idle_proof"] = require_idle_gpu()
            report["memory_before"] = memory_point()
            need(report["memory_before"]["free_mib"] >= 2048,"insufficient GPU headroom")
            torch.cuda.init()
            oracle_path = resource.safe(baseline["oracle"]["path"])
            need(resource.digest(oracle_path) == baseline["oracle"]["sha256"],"oracle changed")
            with oracle_path.open("rb") as stream:
                oracle = torch.load(stream,map_location="cpu",weights_only=True)
            for payload in exported["payloads"]:
                path = resource.safe(payload["path"])
                need(resource.digest(path) == payload["sha256"],"same payload changed")
                for tile in TILES:
                    budget.check()
                    torch.cuda.reset_peak_memory_stats()
                    row = dict(variant=payload["variant"],tile_rows=tile,started_at=datetime.now(timezone.utc).isoformat())
                    report["rows"].append(row)
                    started = time.perf_counter()
                    model = prior.packed.load_file(path,device="cuda",tile_rows=tile)
                    ref = weakref.ref(model)
                    try:
                        row["logits"] = observe(model,oracle[payload["variant"]],budget)
                        row.update(original_allclose=all(x["original_allclose"] for x in row["logits"]),
                                   all_exact=all(x["exact_equal"] for x in row["logits"]),
                                   all_argmax_equal=all(x["argmax_equal"] for x in row["logits"]),
                                   storage=resource.model_storage(model),
                                   cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                                   cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved())
                    finally:
                        model.to("cpu")
                        model = None
                        gc.collect()
                        row["model_released"] = ref() is None
                        row["cleanup"] = resource.close_cuda(torch)
                        prior.assert_cuda_clean(row["cleanup"])
                    need(row["model_released"],"diagnosis model remains held")
                    row["seconds"] = time.perf_counter()-started
                    print(json.dumps(dict(variant=row["variant"],tile_rows=tile,
                                          original_allclose=row["original_allclose"],all_exact=row["all_exact"])),flush=True)
            need(identity()==source,"shape diagnosis source changed")
            need(len(report["rows"])==6 and all(len(row["logits"])==16 for row in report["rows"]),"complete2x3x16 diagnosis required")
            report["status"]="CONTROLLED_SHAPES_MEASURED_NOT_ADOPTED"
            rc = 0
    except BaseException as exc:
        report["status"]="ERROR_NOT_COMPLETE"
        report["error"]=dict(type=type(exc).__name__,message=str(exc)[:2000])
    finally:
        if model is not None:
            model.to("cpu")
            model=None
            gc.collect()
        if torch.cuda.is_initialized():
            try:
                report["final_cuda_cleanup"]=resource.close_cuda(torch)
                prior.assert_cuda_clean(report["final_cuda_cleanup"])
            except Exception as exc:
                report["cleanup_error"]=dict(type=type(exc).__name__,message=str(exc)[:1000])
                report["status"],rc="ERROR_NOT_COMPLETE",9
        report.update(exit_code=rc,seconds=time.monotonic()-budget.started,ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output,report)
        print(json.dumps(dict(status=report["status"],exit_code=rc,seconds=report["seconds"])))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
