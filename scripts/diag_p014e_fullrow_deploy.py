#!/usr/bin/env python3
"""Whole-output-row packed reference, admitted only after exact shape controls."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import gc
from pathlib import Path
import json
import sys
import time
from types import SimpleNamespace
import weakref

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from scripts import diag_p014e_packed_deploy as prior
from scripts import diag_p014e_tile_shape as shape
from scripts import diag_p106b_resource_matrix as resource

TAG=prior.TAG+"_fullrow_cuda"
SCHEMA="P014E_EXACT_SHAPE_FULLROW_DEPLOYMENT_V1"
OWN=("scripts/diag_p014e_fullrow_deploy.py","scripts/test_p014e_fullrow_deploy.py")
need=resource.need


def identity():
    files=dict(shape.identity()["files"])
    files.update({name:resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files,sha256=resource.sha(files))


def exact_shape_admission(report):
    need(report.get("status")=="CONTROLLED_SHAPES_MEASURED_NOT_ADOPTED" and report.get("exit_code")==0,
         "completed controlled-shape measurement required")
    rows={(row["variant"],row["tile_rows"]):row for row in report["rows"]}
    need(len(rows)==len(report["rows"])==6,"complete distinct2x3 controls required")
    for variant in prior.VARIANTS:
        need(rows[(variant,128)]["original_allclose"] is False,"original128 failure must remain visible")
        full=rows[(variant,4096)]
        need(full["original_allclose"] is True and full["all_exact"] is True
             and full["all_argmax_equal"] is True and len(full["logits"])==16
             and all(v["exact_equal"] is True and v["max_abs"]==0 for v in full["logits"]),
             "full-row exact original criterion required, not argmax-only acceptance")
        for tile in shape.TILES:
            row=rows[(variant,tile)]
            need(row["model_released"] is True,"prior shape model remains held")
            prior.assert_cuda_clean(row["cleanup"])
    return dict(tile_rows=4096,original128_failures_preserved=True,exact_fullrow_positions_per_variant=16)


def pairs_equal(actual,expected):
    for key,gen in (("records","observed"),("answers","generation")):
        need(len(actual[key])==len(expected[key])==4,"same complete four cases required")
        for a,b in zip(actual[key],expected[key]):
            identity_key="workload" if key=="records" else "case"
            need(a[identity_key]==b[identity_key],"case order/input differs")
            need(a[gen]["generated_ids"]==b[gen]["generated_ids"]
                 and a[gen]["metadata"]==b[gen]["metadata"],"full-row IDs or termination differ")
    return True


def validate(profile,args):
    need(profile.get("schema")==SCHEMA and profile.get("tag")==TAG and profile.get("root_approved") is True
         and profile.get("authority_directive")==96 and profile.get("source_sha256")==identity()["sha256"]
         and profile.get("mode")==args.mode=="fullrow-cuda" and profile.get("tile_rows")==4096
         and args.max_wall_sec==profile["max_wall_sec"]==1200,"exact new full-row contract required")
    need(profile.get("deadline")=="2026-10-27T08:00:00+00:00"
         and (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds()>1380,"full phase cannot fit")
    original=resource.read_ref(profile["prior_profile"])
    base,spec=prior.validate(original,SimpleNamespace(mode="deploy-cuda",max_wall_sec=1200))
    original["_file_sha256"]=profile["prior_profile"]["sha256"]
    control=resource.read_ref(profile["shape_report"])
    need(control["source"]==shape.identity(),"shape source changed")
    shape_profile=resource.read_ref(profile["shape_profile"])
    need(control["profile_sha256"]==profile["shape_profile"]["sha256"]
         and control["source_profile"]==shape_profile["prior_profile"]==profile["prior_profile"]
         and shape_profile["prior_export"]==profile["prior_export"]
         and shape_profile["prior_baseline"]==profile["prior_baseline"],"controlled input lineage differs")
    shape.validate(shape_profile,SimpleNamespace(mode="diagnose",max_wall_sec=900))
    admission=exact_shape_admission(control)
    exported,baseline=prior.closed("export",original),prior.closed("baseline-cuda",original)
    need(resource.read_ref(profile["prior_export"] )==exported
         and resource.read_ref(profile["prior_baseline"])==baseline,"original receipt bytes changed")
    need([(v["variant"],v["path"]) for v in exported["payloads"]]
         ==[(v,str((prior.deploy_dir()/(v+".pt")).relative_to(ROOT))) for v in prior.VARIANTS],"payload namespace differs")
    need(baseline["oracle"]["path"]==str((prior.deploy_dir()/"baseline_cuda_oracle.pt").relative_to(ROOT)),"CUDA oracle namespace differs")
    return original,base,exported,baseline,admission


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("fullrow-cuda",),required=True)
    parser.add_argument("--profile",required=True)
    parser.add_argument("--profile-sha256",required=True)
    parser.add_argument("--max-wall-sec",type=int,required=True)
    action=parser.add_mutually_exclusive_group()
    action.add_argument("--execute",action="store_true")
    action.add_argument("--check-only",action="store_true")
    args=parser.parse_args()
    profile=resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    original,base,exported,baseline,admission=validate(profile,args)
    if args.check_only:
        print(json.dumps(dict(status="EXACT_FULLROW_METADATA_ONLY",model_loads=0,gpu_calls=0,admission=admission)))
        return 0
    need(args.execute,"explicit full-row GPU execution required")
    import torch
    from tokenizers import Tokenizer
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    source=identity();budget=resource.Budget(args.max_wall_sec)
    output=resource.safe("test_result/evidence/"+TAG+"/report.json")
    need(not output.exists(),"new full-row evidence required")
    report=dict(schema=SCHEMA,tag=TAG,source=source,profile_sha256=args.profile_sha256,source_profile=profile["prior_profile"],
                shape_report=profile["shape_report"],admission=admission,status="STARTED",quality_claim=False,
                original_checkpoint_loads=0,checkpoint_writes=0,training_updates=0,variants=[],
                started_at=datetime.now(timezone.utc).isoformat())
    model=None;rc=9
    try:
        with resource.wall(args.max_wall_sec):
            from scripts.interactive_research_infer import require_idle_gpu
            from scripts.diag_p102a_logit_margin import memory_point
            report["idle_proof"]=require_idle_gpu();report["memory_before"]=memory_point()
            need(report["memory_before"]["free_mib"]>=2048,"GPU headroom required")
            torch.cuda.init()
            oracle_path=resource.safe(baseline["oracle"]["path"])
            need(resource.digest(oracle_path)==baseline["oracle"]["sha256"],"oracle changed")
            with oracle_path.open('rb') as stream:oracle=torch.load(stream,map_location="cpu",weights_only=True)
            tok=Tokenizer.from_file(str(resource.safe(base["tokenizer"]["path"])))
            for payload in exported["payloads"]:
                budget.check();torch.cuda.reset_peak_memory_stats()
                path=resource.safe(payload["path"])
                need(resource.digest(path)==payload["sha256"],"payload changed")
                row=dict(variant=payload["variant"],tile_rows=4096,result={});report["variants"].append(row)
                ref=None
                execution_error=None;cleanup_errors=[]
                try:
                    started=time.perf_counter();model=prior.packed.load_file(path,device="cuda",tile_rows=4096)
                    ref=weakref.ref(model)
                    row.update(load_seconds=time.perf_counter()-started,storage_after_load=resource.model_storage(model))
                    result,tensors=prior.measured_suite(model,model.cfg,tok,base,original,"cuda",budget,
                                                         oracle=oracle[payload["variant"]],progress=row["result"])
                    if result["status"]=="FULL_TECHNICAL_SUITE_NOT_QUALITY":
                        expected=next(v["result"] for v in baseline["variants"] if v["variant"]==payload["variant"])
                        row["same_device_ids_and_stops_equal"]=pairs_equal(result,expected)
                        row["numeric_recheck"]=[dict(workload=work["id"],step=i,**shape.difference(actual,wanted))
                            for work,reference in zip(tensors,oracle[payload["variant"]])
                            for i,(actual,wanted) in enumerate(zip(work["logits"],reference["logits"]))]
                        need(len(row["numeric_recheck"])==16,"complete full-row numeric recheck required")
                        row["all_exact"]=all(v["exact_equal"] for v in row["numeric_recheck"])
                    del tensors
                    row.update(cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved())
                except BaseException as exc:
                    # Keep the original failure without retaining its model/KV traceback.
                    execution_error=dict(type=type(exc).__name__,message=str(exc)[:2000])
                    row["execution_error"]=execution_error
                finally:
                    if model is not None:
                        try:model.to("cpu")
                        except BaseException as exc:
                            cleanup_errors.append(dict(stage="model_to_cpu",type=type(exc).__name__,message=str(exc)[:1000]))
                        model=None
                    gc.collect()
                    row["model_released"]=None if ref is None else ref() is None
                    try:
                        row["cleanup"]=resource.close_cuda(torch)
                        prior.assert_cuda_clean(row["cleanup"])
                    except BaseException as exc:
                        cleanup_errors.append(dict(stage="cuda_cleanup",type=type(exc).__name__,message=str(exc)[:1000]))
                    row["cleanup_errors"]=cleanup_errors
                need(execution_error is None,"full-row execution failed; original failure is preserved in variant.execution_error")
                need(not cleanup_errors,"full-row cleanup failed; all attempted cleanup failures are preserved")
                need(row["model_released"],"full-row model remains held")
                need(resource.digest(path)==payload["sha256"],"payload changed during full-row execution")
                if row["result"]["status"]!="FULL_TECHNICAL_SUITE_NOT_QUALITY":rc=8;break
            else:rc=0
            need(identity()==source,"full-row source changed")
            report["status"]="TECHNICAL_COMPLETE_NOT_QUALITY" if rc==0 else "BUDGET_HOLD_NOT_FULL_SUITE"
    except BaseException as exc:
        report["status"]= "ERROR_NOT_COMPLETE";rc=9
        report["error"]=dict(type=type(exc).__name__,message=str(exc)[:2000])
    finally:
        if model is not None:
            try:
                model.to("cpu");model=None;gc.collect()
            except BaseException as exc:
                report["model_cleanup_error"]=dict(type=type(exc).__name__,message=str(exc)[:1000])
                rc=9;report["status"]="ERROR_NOT_COMPLETE"
        if torch.cuda.is_initialized():
            try:
                report["final_cuda_cleanup"]=resource.close_cuda(torch);prior.assert_cuda_clean(report["final_cuda_cleanup"])
            except Exception as exc:
                report["cleanup_error"]=dict(type=type(exc).__name__,message=str(exc)[:1000]);rc=9;report["status"]="ERROR_NOT_COMPLETE"
        report.update(exit_code=rc,seconds=time.monotonic()-budget.started,ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output,report);print(json.dumps(dict(status=report["status"],exit_code=rc,seconds=report["seconds"])))
    return rc


if __name__=="__main__":raise SystemExit(main())
