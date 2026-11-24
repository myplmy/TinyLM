"""One sealed extrapolation-distance control on four unused native contexts."""
import argparse
import gc
import json
from pathlib import Path
import time
import traceback
import unittest
import numpy as np
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend
from scripts import diag_p108f_hf_endpoint as old

archive=old.archive
BASE=old.BASE/"large_radius_v1"
PROFILE=BASE/"profile.json"
PREDICTORS=("QUADRATIC_300","LINEAR_003","QUADRATIC_100","LINEAR_100","LINEAR_300","ORIGINAL_NO_CHANGE")
RADII=(.001,.003,.1,.3)
CODE=("scripts/diag_p108f_large_radius.py","scripts/test_p108f_large_radius.py",
      "scripts/diag_p108f_hf_endpoint.py","scripts/p108f_native.py",
      "scripts/p108e_endpoint_prediction.py","scripts/p108c_limits.py")


def select_cases(questions,excluded):
    if len(questions)!=128 or len(set(excluded))!=len(excluded):
        raise ValueError("one128-context pool and unique old indices required")
    seen={questions[i] for i in excluded};result=[]
    for start in range(0,128,32):
        eligible=[i for i in range(start,start+32) if i not in excluded and questions[i] not in seen]
        if not eligible:raise ValueError("each block needs one genuinely unused context")
        index=eligible[0];result.append(index);seen.add(questions[index])
    return result


def summarize(rows):
    result={}
    for name in PREDICTORS:
        points=[r["comparisons"][name] for r in rows]
        gained=sum(p["exact_argmax"] and not r["baseline_exact"] for p,r in zip(points,rows))
        lost=sum(not p["exact_argmax"] and r["baseline_exact"] for p,r in zip(points,rows))
        result[name]=dict(cases=len(rows),argmax_exact=sum(p["exact_argmax"] for p in points),
            pooled_logit_RMSE=float(np.sqrt(np.mean([p["logit_rmse"]**2 for p in points]))),
            mean_response_relative_error=float(np.mean([p["response_relative_error"] for p in points])),
            gained_against_no_change=gained,lost_against_no_change=lost,
            exact_on_changed_cases=sum(p["exact_argmax"] for p,r in zip(points,rows) if not r["baseline_exact"]))
    return result


def prepare():
    old.Budget().check(admission=True)
    if BASE.exists():raise FileExistsError("preserve the one large-radius namespace")
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in(
        "scripts.test_p108f_native","scripts.test_p108f_large_radius"))
    checked=unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful() or checked.testsRun!=7:raise RuntimeError("seven native/new-context contracts required")
    hf,closed,suffix,assets,previous_cases,refs=old.inputs()
    questions=archive.read(archive.OLD/"data.json")["calibration_questions"]
    indices=select_cases(questions,[c["index"] for c in previous_cases])
    if indices!=[4,34,66,98]:raise ValueError("fresh context selection differs from the written plan")
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(assets["declared_directory"],local_files_only=True,trust_remote_code=False)
    cases=[]
    for i in indices:
        text="Question: "+questions[i]+chr(10)+"Answer:";ids=tokenizer.encode(text,add_special_tokens=True)
        if not 1<=len(ids)<=1024:raise ValueError("no truncation admitted")
        cases.append(dict(index=i,question=questions[i],text=text,ids=ids,expected=None))
    refs.update((old.PROFILE,old.BASE/"actual/report.json"))
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb") as stream:stream.write(archive.PLAN.read_bytes())
    archive.write_new(PROFILE,dict(schema="P108F_NEW_CONTEXT_LARGE_RADIUS_V1",authority_directive=142,
        authority_end=old.clock_owner.AUTHORITY_END.isoformat(),cleanup_seconds=old.clock_owner.CLEANUP_SECONDS,
        sources={name:archive.sha(archive.ROOT/name) for name in CODE},
        references={str(path.relative_to(archive.ROOT)):archive.sha(path) for path in sorted(refs)},
        initial_plan_sha256=archive.sha(BASE/"initial_plan.md"),CPU_contracts=checked.testsRun,
        cases=cases,layers=closed["layers"],assets=assets,original_core_sha256=closed["external_runtime_proof"]["initial_core_sha256"],
        model_source_path=suffix["model_source_path"],model_source_sha256=suffix["model_source_sha256"],
        radii=list(RADII),primary_predictor="QUADRATIC_300",predictors=list(PREDICTORS),
        max_seconds=1800,expected_new_backbone_forwards=652,expected_native_points=72,
        native_logit_tolerance=.002,new_generated_answers=0,new_fit=False,new_VJP_calls=0,new_QP_solves=0,
        quality_adoption=False,optimizer_updates=0,checkpoint_writes=0,
        raw_preservation="All native/baseline logits; all endpoint forecasts and forecast-logit SHA/top8; immutable head/source allows reconstruction",
        total_F_cap_bytes=500_000_000,internal_F_cap_bytes=480_000_000))
    if torch.cuda.is_initialized():raise RuntimeError("CPU preparation initialized CUDA")
    print("[LARGE_RADIUS_PREPARED]seven CPU contracts;four unused contexts;no model",flush=True)


def verify():
    old.Budget().check(admission=True);p=archive.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=old.clock_owner.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=old.clock_owner.CLEANUP_SECONDS
       or p["initial_plan_sha256"]!=archive.sha(BASE/"initial_plan.md")):
        raise ValueError("exact authority, clock and initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if archive.sha(archive.ROOT/name)!=digest:raise ValueError("closed input changed: "+name)
    if old.external.asset_identity("gemma270")!=p["assets"]:raise ValueError("native assets changed")
    if archive.sha(Path(p["model_source_path"]))!=p["model_source_sha256"]:raise ValueError("native implementation changed")
    return p


def actual():
    p=verify();budget=old.Budget();budget.check(admission=True)
    out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve large-radius actual")
    out.mkdir();started=time.monotonic();counts=dict(new_backbone_forwards=0,head_only_calls=0,new_generated_answers=0)
    report=dict(schema=p["schema"],status="STARTED",rows=[],counts=counts,source_profile_sha256=archive.sha(PROFILE),
        external_runtime_proof={},entry_resources=old.cleanup_owner.resources(),quality_adoption=False,
        new_fit=False,new_VJP_calls=0,new_QP_solves=0,optimizer_updates=0,checkpoint_writes=0)
    body=lm=downs=module=forecasts=baseline=r0=None;failure=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with old.external.model_runtime("gemma270",torch,p["assets"],proof=report["external_runtime_proof"]) as (lm,_):
            body=lm.model;downs=old.previous.modules(body);cases=p["cases"]
            if len(downs)!=18 or old.manual.state_fingerprint(body)!=p["original_core_sha256"]:
                raise ValueError("same original18 native owners required")
            old.previous.validate_config(body.config.to_dict())
            if any(lm.tokenizer.encode(c["text"],add_special_tokens=True)!=c["ids"] for c in cases):
                raise ValueError("native literal prompt tokens changed")
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                r0,baseline=old.observe(body,cases,budget,counts)
                baseline_pins=[archive.save_arrays(out/("baseline_"+str(c["index"])+".npz"),logits=v)
                               for c,v in zip(cases,baseline)]
                archive.save_arrays(out/"baseline_endpoint.npz",values=r0)
                canary_error=0.;canary_mismatches=0
                for h,g in zip(r0,baseline):
                    value=old.native.gemma_head(body,h).cpu().numpy();counts["head_only_calls"]+=1
                    canary_error=max(canary_error,float(np.max(np.abs(value-g))))
                    canary_mismatches+=int(value.argmax()!=g.argmax())
                if canary_error>p["native_logit_tolerance"] or canary_mismatches:
                    raise RuntimeError("native head reconstruction failed")
                report.update(head_canary_maximum_error=canary_error,head_canary_argmax_mismatches=canary_mismatches)
                forecasts=[]
                for row in p["layers"]:
                    budget.check();layer=row["layer"];module=downs[layer]
                    before=module.weight.detach().cpu().numpy().copy();after=old.packet(row["packet"])["after"]
                    if(old.identity.tensor_sha(module.weight)!=row["before_weight_sha256"]
                       or old.identity.tensor_sha(torch.from_numpy(after))!=row["after_weight_sha256"]):
                        raise ValueError("old18 physical packet changed")
                    delta=after.astype(np.float64)-before.astype(np.float64);fd={};fd_meta=[]
                    directory=out/("layer"+str(layer).zfill(2));directory.mkdir()
                    for radius in RADII:
                        observed={};coordinates={}
                        for sign in (1,-1):
                            small=(before.astype(np.float64)+sign*radius*delta).astype(np.float32)
                            coordinates[sign]=old.secant_owner.physical_coordinate(before,small,delta)
                            with old.native.temporary_after(module,small):
                                observed[sign],discard=old.observe(body,cases,budget,counts)
                            discard=None
                        d,q=old.secant_owner.secants(r0,observed[1],observed[-1],coordinates[1]["scalar"],coordinates[-1]["scalar"])
                        fd[radius]=dict(d=d,q=q)
                        pin=archive.save_arrays(directory/("fd_"+str(int(radius*1000)).zfill(3)+".npz"),
                                                plus=observed[1],minus=observed[-1])
                        fd_meta.append(dict(radius=radius,plus=coordinates[1],minus=coordinates[-1],packet=pin))
                    endpoints=np.stack((r0+fd[.3]["d"]+fd[.3]["q"],r0+fd[.003]["d"],
                                        r0+fd[.1]["d"]+fd[.1]["q"],r0+fd[.1]["d"],r0+fd[.3]["d"]),axis=1)
                    endpoint_pin=archive.save_arrays(directory/"predicted_endpoints.npz",values=endpoints)
                    values=[];meta=[]
                    for i,c in enumerate(cases):
                        vectors=[old.native.gemma_head(body,h).cpu().numpy().copy() for h in endpoints[i]]+[baseline[i]]
                        counts["head_only_calls"]+=5
                        if any(not np.isfinite(v).all() for v in vectors):raise RuntimeError("nonfinite forecast")
                        values.append(vectors);meta.append(dict(index=c["index"],predictors={name:dict(
                            sha256=old.identity.tensor_sha(torch.from_numpy(v)),argmax=int(v.argmax()),
                            top8_indices=np.argsort(v)[-8:][::-1].tolist()) for name,v in zip(PREDICTORS,vectors)}))
                    forecasts.append(dict(layer=layer,values=values,metadata=meta,FD=fd_meta,predicted_endpoints=endpoint_pin))
                    print("[LARGE_RADIUS_PREDICTION_CLOSED]layer="+str(layer),flush=True)
                archive.write_new(out/"ALL72_PREDICTIONS_BEFORE_FULL_EDITS.json",dict(
                    rows=[{k:v for k,v in row.items() if k!="values"} for row in forecasts],
                    primary=p["primary_predictor"],new_full_step_forwards=0,quality_labels_used=False))
                for old_row,predicted in zip(p["layers"],forecasts):
                    budget.check();layer=old_row["layer"];module=downs[layer];directory=out/("layer"+str(layer).zfill(2))
                    after=old.packet(old_row["packet"])["after"]
                    with old.native.temporary_after(module,after):actual_endpoint,actuals=old.observe(body,cases,budget,counts)
                    endpoint_pin=archive.save_arrays(directory/"actual_endpoints.npz",values=actual_endpoint)
                    layer_rows=[]
                    for i,c in enumerate(cases):
                        actual_pin=archive.save_arrays(directory/("actual_"+str(c["index"])+".npz"),logits=actuals[i])
                        comparisons={name:old.comparison.compare(torch.from_numpy(baseline[i]),torch.from_numpy(actuals[i]),torch.from_numpy(v))
                                     for name,v in zip(PREDICTORS,predicted["values"][i])}
                        layer_rows.append(dict(layer=layer,index=c["index"],question=c["question"],comparisons=comparisons,
                            actual_packet=actual_pin,baseline_packet=baseline_pins[i],
                            baseline_exact=bool(actuals[i].argmax()==baseline[i].argmax())))
                    restored=old.identity.tensor_sha(module.weight)==old_row["before_weight_sha256"]
                    if not restored:raise RuntimeError("native original after-state not restored")
                    archive.write_new(directory/"report.json",dict(layer=layer,rows=layer_rows,actual_endpoint=endpoint_pin,
                        original_weight_restored=restored,same_old_after_weight_sha256=old_row["after_weight_sha256"]))
                    report["rows"].extend(layer_rows)
                    print("[LARGE_RADIUS_NATIVE_LAYER]layer="+str(layer),flush=True)
                if counts["new_backbone_forwards"]!=652 or len(report["rows"])!=72:
                    raise RuntimeError("sealed forward or sample count differs")
                report.update(status="LARGE_RADIUS72_NATIVE_COMPLETE_NOT_QUALITY",summary=summarize(report["rows"]),
                    actual_argmax_changed_cases=sum(not r["baseline_exact"] for r in report["rows"]),
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                body=lm=downs=module=forecasts=baseline=r0=None
    except BaseException as error:
        failure=str(error);report.update(status="LARGE_RADIUS_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        body=lm=downs=module=forecasts=baseline=r0=None;gc.collect()
        cleanup_error=old.cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;archive.write_new(out/"report.json",report)
    print("[LARGE_RADIUS_END]"+json.dumps(dict(status=report["status"],counts=counts,error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="check":verify();print("[LARGE_RADIUS_CHECK]frozen new contexts,old18 packets and clock",flush=True)
    else:actual()


if __name__=="__main__":main()
