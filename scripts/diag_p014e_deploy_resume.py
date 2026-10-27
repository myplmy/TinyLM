#!/usr/bin/env python3
"""Explicit CPU budget continuation; old source/profile/HOLD stay immutable."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p014e_packed_deploy as prior
from scripts import diag_p106b_resource_matrix as resource

TAG = prior.TAG + "_cpu_budget5400"
SCHEMA = "P014E_EXPLICIT_CPU_BUDGET_CONTINUATION_V1"
OWN = ("scripts/diag_p014e_deploy_resume.py", "scripts/test_p014e_deploy_resume.py")
need = resource.need


def identity():
    files = dict(prior.identity()["files"])
    files.update({name: resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def admission(hold, seconds, remaining):
    need(hold.get("phase") == "deploy-cpu" and hold.get("exit_code") == 8
         and hold.get("status") == "BUDGET_HOLD_NOT_FULL_SUITE"
         and hold.get("cuda_initialized") is False, "actual previous CPU budget HOLD8 required")
    variants = hold.get("variants", [])
    need(len(variants) == 1 and variants[0].get("variant") == "fp32_unchanged"
         and variants[0].get("model_released") is True, "previous partial model must be released")
    result = variants[0]["result"]
    need(result.get("status") == "BUDGET_HOLD_NOT_FULL_SUITE" and result.get("records") == []
         and result.get("answers") == [] and len(result.get("cost_probes", [])) == 2,
         "previous full suite must not have run")
    estimate = result["conservative_seconds"]
    need(type(estimate) in (int, float) and math.isfinite(estimate) and estimate > 0
         and type(seconds) is int and seconds == 5400 and remaining > seconds + 180,
         "exact current CPU window with closure reserve required")
    whole = 2 * estimate + 600
    need(whole <= seconds, "both complete variants cannot fit conservative continuation budget")
    return dict(previous_one_variant_seconds=estimate, two_variants_plus_closure_seconds=whole,
                current_phase_cap_seconds=seconds, remaining_authority_seconds=remaining,
                previous_phase_cap_seconds=1200, fixed_workload_unchanged=True)


def validate(profile, args):
    source = identity()
    need(profile.get("schema") == SCHEMA and profile.get("tag") == TAG
         and profile.get("root_approved") is True and profile.get("authority_directive") == 96
         and profile.get("source_sha256") == source["sha256"] and args.max_wall_sec == profile["max_wall_sec"],
         "explicit source-bound continuation authority required")
    need(profile.get("deadline") == "2026-10-27T08:00:00+00:00"
         and profile.get("mode") == args.mode == "deploy-cpu" and profile.get("training_updates") == 0,
         "CPU-only no-training continuation required")
    original = resource.read_ref(profile["prior_profile"])
    # Validate the original contract as metadata only. The actual larger wall
    # belongs to this separately signed continuation, not the old1200s profile.
    base, spec = prior.validate(original, SimpleNamespace(mode="deploy-cpu", max_wall_sec=1200))
    original["_file_sha256"] = profile["prior_profile"]["sha256"]
    need(original["source_sha256"] == prior.identity()["sha256"], "prior runtime source changed")
    hold = resource.read_ref(profile["prior_hold"])
    need(profile["prior_hold"]["path"] == str(prior.record_path("deploy-cpu").relative_to(ROOT)),
         "exact original HOLD namespace required")
    need(hold.get("source") == prior.identity()
         and hold.get("profile_sha256") == original["_file_sha256"], "prior HOLD lineage differs")
    for mode, key in (("export", "prior_export"), ("baseline-cpu", "prior_baseline")):
        need(profile[key]["path"] == str(prior.record_path(mode).relative_to(ROOT)),
             "exact original source receipt namespace required")
        need(resource.read_ref(profile[key]) == prior.closed(mode, original), "original receipt byte identity differs")
    remaining = (resource.DEADLINE - datetime.now(timezone.utc)).total_seconds()
    budget = admission(hold, args.max_wall_sec, remaining)
    return original, base, spec, source, budget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("deploy-cpu",), required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--max-wall-sec", type=int, required=True)
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument("--execute", action="store_true")
    execution.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    profile = resource.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    original, base, spec, source, admission_proof = validate(profile, args)
    if args.check_only:
        print(json.dumps(dict(status="CONTINUATION_METADATA_ONLY", admission=admission_proof,
                              model_loads=0, gpu_calls=0)))
        return 0
    need(args.execute, "explicit CPU execution required")
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    need(not torch.cuda.is_initialized(), "CPU continuation must not initialize CUDA")
    output = resource.safe("test_result/evidence/" + TAG + "/report.json")
    need(not output.exists(), "new continuation evidence required")
    budget = resource.Budget(args.max_wall_sec)
    report = dict(schema=SCHEMA, tag=TAG, phase="deploy-cpu-resume", source=source,
                  prior_runtime_source=prior.identity(), profile_sha256=args.profile_sha256,
                  previous_profile=profile["prior_profile"], previous_hold=profile["prior_hold"],
                  admission=admission_proof, training_updates=0, checkpoint_writes=0,
                  quality_claim=False, status="STARTED", started_at=datetime.now(timezone.utc).isoformat(),
                  pid=__import__("os").getpid(), cpu_threads=torch.get_num_threads(),
                  cpu_affinity="OS_SCHEDULED_SHARED_HOST", original_checkpoint_loads=0)
    rc = 9
    try:
        with resource.wall(args.max_wall_sec):
            rc = prior.deploy(base, spec, original, budget, report, "cpu")
            need(identity() == source and not torch.cuda.is_initialized(), "continuation source/device changed")
            report["status"] = "TECHNICAL_COMPLETE_NOT_QUALITY" if rc == 0 else "BUDGET_HOLD_NOT_FULL_SUITE"
    except BaseException as exc:
        report["status"], rc = "ERROR_NOT_COMPLETE", 9
        report["error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
    finally:
        report.update(exit_code=rc, seconds=time.monotonic() - budget.started,
                      ended_at=datetime.now(timezone.utc).isoformat(), cuda_initialized=torch.cuda.is_initialized())
        resource.write_new(output, report)
        print(json.dumps(dict(status=report["status"], exit_code=rc, seconds=report["seconds"])))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
