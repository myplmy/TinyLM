"""Transport the endpoint predictor to18 native Gemma intervention packets."""
import argparse
import gc
import json
from pathlib import Path
import shutil
import time
import traceback
import unittest
import numpy as np
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import p108f_native as native
from scripts import p108e_endpoint_prediction as secant_owner
from scripts import p108c_limits as clock_owner
from scripts import diag_p108c_scope as archive
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p108b_hf_canary as previous
from scripts import diag_p108b_value_library as cleanup_owner
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as identity
from scripts import p108b_lastlayer_forecast as comparison

ROOT=archive.ROOT
BASE=ROOT/"test_result/evidence/p108f_hf_endpoint_v1_s1337"
PROFILE=BASE/"profile.json"
OLD=archive.OLD
SUFFIX=archive.PM/"hf_suffix_v1"
CODE=("scripts/diag_p108f_hf_endpoint.py","scripts/p108f_native.py","scripts/test_p108f_native.py",
      "scripts/p108e_endpoint_prediction.py","scripts/diag_p108b_hf_canary.py",
      "scripts/p108b_hf_suffix_forecast.py","scripts/p108b_lastlayer_forecast.py",
      "scripts/diag_p106b_external_core6.py","scripts/p108c_limits.py")
PREDICTORS=("ENDPOINT_LINEAR_003","ENDPOINT_LINEAR_001","ENDPOINT_QUADRATIC_003", "ENDPOINT_003_LINEAR_HEAD","ORIGINAL_NO_CHANGE")


class Budget(clock_owner.Budget):
    def __init__(self,seconds=1800):super().__init__(seconds);self.last_disk=0.
    def check(self,**kwargs):
        remaining=super().check(**kwargs);now=time.monotonic()
        if now-self.last_disk>5:
            self.last_disk=now
            if shutil.disk_usage(ROOT).free<5_000_000_000:raise RuntimeError("less than5GB free;no cleanup authorized")
            if BASE.exists()and sum(p.stat().st_size for p in BASE.rglob("*")if p.is_file())>=480_000_000:
                raise RuntimeError("HF predictor reached480MB internal cap within500MB total")
        return remaining


def packet(pin):
    path=ROOT/pin["path"]
    if archive.sha(path)!=pin["sha256"]:raise ValueError("closed HF observation changed")
    return archive.load_arrays(path)


def inputs():
    hf_path=OLD/"hf_canary_profile_v1.json";hf=archive.read(hf_path)
    result_path=OLD/"hf_canary_v1/report.json";closed=archive.read(result_path)
    suffix_profile_path=archive.PM/"hf_suffix_profile_v1.json";suffix=archive.read(suffix_profile_path)
    suffix_result_path=SUFFIX/"report.json";suffix_result=archive.read(suffix_result_path)
    if(closed["status"]!="HF_NATIVE18_TECHNICAL_COMPLETE_NOT_VALUE_POLICY_TRANSFER"or len(closed["layers"])!=18
       or suffix_result["status"]!="HF_SUFFIX_NATIVE36_COMPLETE_NOT_QUALITY"):
        raise ValueError("closed native18 and suffix36 inputs required")
    for name,digest in hf["sources"].items():
        if archive.sha(ROOT/name)!=digest:raise ValueError("original HF canary implementation changed")
    for name,digest in suffix["sources"]["files"].items():
        if archive.sha(ROOT/name)!=digest:raise ValueError("original suffix implementation changed")
    if archive.sha(Path(suffix["model_source_path"]))!=suffix["model_source_sha256"]:
        raise ValueError("original Gemma modeling implementation changed")
    assets=external.asset_identity("gemma270")
    if assets!=hf["assets"]or assets!=suffix["assets"]:raise ValueError("immutable local Gemma assets differ")
    data_path=OLD/"data.json"
    if archive.sha(data_path)!=suffix["calibration_data_sha256"]:raise ValueError("old calibration questions changed")
    refs={hf_path,result_path,suffix_profile_path,suffix_result_path,data_path,
          SUFFIX/"PREDICTIONS_BEFORE_NATIVE_EDITS_v1.json"}
    refs.update(ROOT/r["packet"]["path"]for r in closed["layers"])
    predictions=archive.read(SUFFIX/"PREDICTIONS_BEFORE_NATIVE_EDITS_v1.json")["references"]
    cached={r["index"]:r["packet"]for r in predictions if r["alpha"]==1.}
    cached_actual={r["calibration_index"]:r["actual_packet"]for r in suffix_result["rows"]if r["alpha"]==1.}
    indices=suffix["calibration_indices"]
    if len(indices)!=12 or set(cached)!=set(indices)or set(cached_actual)!=set(indices):
        raise ValueError("same twelve whole original/last17 cases required")
    refs.update(ROOT/pin["path"]for pin in [*cached.values(),*cached_actual.values()])
    questions=archive.read(data_path)["calibration_questions"]
    cases=[dict(index=i,question=questions[i],text="Question: "+questions[i]+chr(10)+"Answer:",
        original=cached[i],cached_last17_actual=cached_actual[i],expected=None)for i in indices]
    return hf,closed,suffix,assets,cases,refs


def prepare():
    Budget().check(admission=True)
    if BASE.exists():raise FileExistsError("preserve HF predictor namespace")
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n)for n in(
        "scripts.test_p108f_native","scripts.test_p108b_hf_suffix_forecast"))
    checked=unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful()or checked.testsRun!=8:raise RuntimeError("eight native after/head contracts required")
    hf,closed,suffix,assets,cases,refs=inputs()
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(assets["declared_directory"],local_files_only=True,trust_remote_code=False)
    for case in cases:
        case["ids"]=tokenizer.encode(case["text"],add_special_tokens=True)
        if not 1<=len(case["ids"])<=1024:raise ValueError("native no-truncation case exceeds1024")
    BASE.mkdir()
    with(BASE/"initial_plan.md").open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    archive.write_new(PROFILE,dict(schema="P108F_GEMMA18_ENDPOINT_PREDICTOR_V1",authority_directive=142,
        authority_end=clock_owner.AUTHORITY_END.isoformat(),cleanup_seconds=clock_owner.CLEANUP_SECONDS,
        sources={name:archive.sha(ROOT/name)for name in CODE},
        references={str(path.relative_to(ROOT)):archive.sha(path)for path in sorted(refs)},
        initial_plan_sha256=archive.sha(BASE/"initial_plan.md"),CPU_contracts=checked.testsRun,
        assets=assets,original_core_sha256=closed["external_runtime_proof"]["initial_core_sha256"],
        model_source_path=suffix["model_source_path"],model_source_sha256=suffix["model_source_sha256"],
        cases=cases,layers=closed["layers"],original_common_norm=closed["common_absolute_norm"],
        epsilons=[.001,.003],primary_predictor="ENDPOINT_LINEAR_003",predictors=list(PREDICTORS),
        native_logit_tolerance=.002,argmax_mismatches_allowed=0,max_seconds=1800,
        expected_new_backbone_forwards=1069,cached_last_layer_actual_forwards_reused=12,
        full_primary_prediction_packets=216,new_full_actual_packets=204,
        owned_raw_cap_bytes=480_000_000,total_artifact_cap_bytes=500_000_000,
        source_training_labels=False,new_fit=False,new_VJP_calls=0,new_QP_solves=0,
        new_generated_answers=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU native predictor preparation initialized CUDA")
    print("[HF_ENDPOINT_PREPARED]eight CPU contracts;18 old packets/12 old observations;no model",flush=True)


def verify():
    p=archive.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=clock_owner.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=clock_owner.CLEANUP_SECONDS
       or p["initial_plan_sha256"]!=archive.sha(BASE/"initial_plan.md")):
        raise ValueError("exact HF predictor clock/authority/initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if archive.sha(ROOT/name)!=digest:raise ValueError("HF predictor source changed: "+name)
    if external.asset_identity("gemma270")!=p["assets"]:
        raise ValueError("strict original HF asset bytes changed")
    if archive.sha(Path(p["model_source_path"]))!=p["model_source_sha256"]:
        raise ValueError("actual Gemma modeling implementation changed")
    return p


def observe(body,cases,budget,counts):
    residuals=[];logits=[]
    for case in cases:
        budget.check();captured=[]
        def retain(_module,args):captured.append(args[0][0,-1].detach().cpu().numpy().copy())
        hook=body.model.norm.register_forward_pre_hook(retain)
        ids=torch.tensor([case["ids"]],device="cuda")
        try:result=body(input_ids=ids,use_cache=False,logits_to_keep=1).logits[0,-1]
        finally:hook.remove()
        if len(captured)!=1:raise RuntimeError("one native final norm visit required")
        residuals.append(captured[0]);logits.append(result.detach().cpu().numpy().copy())
        counts["new_backbone_forwards"]+=1;ids=result=None
    return np.stack(residuals),np.stack(logits)


def actual():
    p=verify();budget=Budget();budget.check(admission=True)
    out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve previous HF endpoint actual")
    out.mkdir();started=time.monotonic();counts=dict(new_backbone_forwards=0,head_only_calls=0,new_generated_answers=0)
    report=dict(schema=p["schema"],status="STARTED",layers=[],cases=p["cases"],counts=counts,
        source_profile_sha256=archive.sha(PROFILE),external_runtime_proof={},entry_resources=cleanup_owner.resources(),
        new_fit=False,new_VJP_calls=0,optimizer_updates=0,checkpoint_writes=0,quality_adoption=False)
    body=lm=downs=module=None;failure=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with external.model_runtime("gemma270",torch,p["assets"],proof=report["external_runtime_proof"])as(lm,_):
            body=lm.model;downs=previous.modules(body)
            if(len(downs)!=18 or manual.state_fingerprint(body)!=p["original_core_sha256"]
               or type(body.model.norm).__name__!="Gemma3RMSNorm"or body.lm_head.bias is not None):
                raise ValueError("same native Gemma18 float original and verified head required")
            previous.validate_config(body.config.to_dict());cases=p["cases"];last=body.model.layers[-1]
            baseline=[];r0=[];directions={};originals={}
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                for case in cases:
                    if lm.tokenizer.encode(case["text"],add_special_tokens=True)!=case["ids"]:
                        raise ValueError("exact old literal native prompt tokenization differs")
                    cached=packet(case["original"]);baseline.append(cached["original"])
                    h=torch.from_numpy(cached["original_residual"]).to("cuda")
                    y=torch.from_numpy(cached["original_down"]).to("cuda")
                    r0.append((h+last.post_feedforward_layernorm(y)).cpu().numpy().copy());h=y=None
                r0=np.stack(r0);baseline=np.stack(baseline)
                report["baseline_endpoint"]=archive.save_arrays(out/"baseline_endpoint.npz",values=r0)
                rr,gg=observe(body,cases[:1],budget,counts)
                if not np.array_equal(gg,baseline[:1]):raise RuntimeError("native original cached full-vocab canary differs")
                canary_error=0.;canary_mismatches=0
                for case,h,g0 in zip(cases,r0,baseline):
                    composed=native.gemma_head(body,h).cpu().numpy();counts["head_only_calls"]+=1
                    canary_error=max(canary_error,float(np.max(np.abs(composed-g0))))
                    canary_mismatches+=int(composed.argmax()!=g0.argmax());composed=None
                report.update(native_original_canary_bitexact=True,original_endpoint_max_error=float(np.max(np.abs(rr-r0[:1]))),
                    head_canary_maximum_error=canary_error,head_canary_argmax_mismatches=canary_mismatches)
                rr=gg=None
                if canary_error>p["native_logit_tolerance"]or canary_mismatches:
                    raise RuntimeError("native Gemma final norm/head canary differs")
                predictions=[]
                for row in p["layers"]:
                    budget.check();layer=row["layer"];module=downs[layer]
                    if identity.tensor_sha(module.weight)!=row["before_weight_sha256"]:
                        raise ValueError("native physical owner differs from old18 packet")
                    arrays=packet(row["packet"]);before=module.weight.detach().cpu().numpy().copy();after=arrays["after"]
                    if identity.tensor_sha(torch.from_numpy(after))!=row["after_weight_sha256"]:
                        raise ValueError("old actual after matrix differs")
                    delta=after.astype(np.float64)-before.astype(np.float64)
                    originals[layer]=before;directions[layer]=after;fd={};fd_meta=[]
                    directory=out/("layer"+str(layer).zfill(2));directory.mkdir()
                    for epsilon in p["epsilons"]:
                        observed={};coordinates={}
                        for sign in(1,-1):
                            small=(before.astype(np.float64)+sign*epsilon*delta).astype(np.float32)
                            coordinates[sign]=secant_owner.physical_coordinate(before,small,delta)
                            with native.temporary_after(module,small):observed[sign],unused=observe(body,cases,budget,counts)
                            unused=None
                        d,q=secant_owner.secants(r0,observed[1],observed[-1],coordinates[1]["scalar"],coordinates[-1]["scalar"])
                        fd[epsilon]=dict(d=d,q=q)
                        pin=archive.save_arrays(directory/("fd_"+str(int(epsilon*1000)).zfill(3)+".npz"),plus=observed[1],minus=observed[-1])
                        fd_meta.append(dict(epsilon=epsilon,plus=coordinates[1],minus=coordinates[-1],packet=pin))
                    full_predictions=[];metadata=[]
                    for i,case in enumerate(cases):
                        endpoint_estimates=(r0[i]+fd[.003]["d"][i],r0[i]+fd[.001]["d"][i],
                            r0[i]+fd[.003]["d"][i]+fd[.003]["q"][i])
                        values=[native.gemma_head(body,x).cpu().numpy().copy()for x in endpoint_estimates]
                        values.append(native.gemma_linear_head(body,r0[i],fd[.003]["d"][i]).cpu().numpy().copy())
                        values.append(baseline[i])
                        counts["head_only_calls"]+=4
                        if any(not np.isfinite(x).all()for x in values):raise RuntimeError("nonfinite native head forecast")
                        pin=archive.save_arrays(directory/("primary_case"+str(case["index"]).zfill(3)+".npz"),logits=values[0])
                        metadata.append(dict(index=case["index"],primary_packet=pin,
                            secondary_logit_sha256={name:identity.tensor_sha(torch.from_numpy(v))for name,v in zip(PREDICTORS[1:],values[1:])}))
                        full_predictions.append(values)
                    predictions.append(dict(layer=layer,values=full_predictions,FD=fd_meta,metadata=metadata,
                        linear_epsilon_relative_disagreement=float(np.linalg.norm(fd[.001]["d"]-fd[.003]["d"])/max(np.linalg.norm(fd[.003]["d"]),1e-30)),
                        quadratic_epsilon_relative_disagreement=float(np.linalg.norm(fd[.001]["q"]-fd[.003]["q"])/max(np.linalg.norm(fd[.003]["q"]),1e-30))))
                    print("[HF_ENDPOINT_PREDICTION_CLOSED]layer="+str(layer),flush=True)
                archive.write_new(out/"ALL18_PREDICTIONS_BEFORE_NEW_FULL_EDITS.json",dict(rows=[
                    {k:v for k,v in row.items()if k!="values"}for row in predictions],
                    all_new_full_step_forwards=0,primary=p["primary_predictor"],quality_labels_used=False))
                for row,predicted in zip(p["layers"],predictions):
                    budget.check();layer=row["layer"];directory=out/("layer"+str(layer).zfill(2));module=downs[layer]
                    native_rows=[]
                    if layer==17:
                        actuals=np.stack([packet(c["cached_last17_actual"])["logits"]for c in cases]);actual_pins=[c["cached_last17_actual"]for c in cases]
                        actual_endpoint=None;reused=12
                    else:
                        with native.temporary_after(module,directions[layer]):actual_endpoint,actuals=observe(body,cases,budget,counts)
                        endpoint_pin=archive.save_arrays(directory/"actual_endpoint.npz",values=actual_endpoint)
                        actual_pins=[archive.save_arrays(directory/("actual_case"+str(c["index"]).zfill(3)+".npz"),logits=v)
                            for c,v in zip(cases,actuals)];reused=0
                    for i,(case,values)in enumerate(zip(cases,predicted["values"])):
                        metrics={name:comparison.compare(torch.from_numpy(baseline[i]),torch.from_numpy(actuals[i]),torch.from_numpy(v))
                            for name,v in zip(PREDICTORS,values)}
                        native_rows.append(dict(index=case["index"],question=case["question"],comparisons=metrics,
                            actual_packet=actual_pins[i],primary_packet=predicted["metadata"][i]["primary_packet"],
                            actual_original_argmax_equal=bool(actuals[i].argmax()==baseline[i].argmax()),
                            actual_logit_change_norm=float(np.linalg.norm(actuals[i].astype(np.float64)-baseline[i].astype(np.float64)))))
                    layer_report=dict(layer=layer,rows=native_rows,FD=predicted["FD"],cached_native_actual_reused=reused,
                        actual_endpoint=None if layer==17 else endpoint_pin,
                        same_old_after_weight_sha256=row["after_weight_sha256"],actual_norm=row["actual_norm"],
                        original_weight_restored=identity.tensor_sha(module.weight)==row["before_weight_sha256"])
                    if not layer_report["original_weight_restored"]:raise RuntimeError("native weight not restored")
                    archive.write_new(directory/"report.json",layer_report);report["layers"].append(layer_report)
                    print("[HF_ENDPOINT_FULL_LAYER]layer="+str(layer)+" cached="+str(reused),flush=True)
                summaries={}
                for name in PREDICTORS:
                    points=[r["comparisons"][name]for layer in report["layers"]for r in layer["rows"]]
                    summaries[name]=dict(cases=len(points),argmax_exact=sum(x["exact_argmax"]for x in points),
                        pooled_logit_RMSE=float(np.sqrt(np.mean([x["logit_rmse"]**2 for x in points]))),
                        mean_response_relative_error=float(np.mean([x["response_relative_error"]for x in points])),
                        maximum_absolute_logit_error=max(x["max_absolute_logit_error"]for x in points),
                        actual_argmax_changed_cases=sum(not r["actual_original_argmax_equal"]for layer in report["layers"]for r in layer["rows"]),
                        argmax_exact_on_changed_cases=sum(r["comparisons"][name]["exact_argmax"]for layer in report["layers"]for r in layer["rows"]if not r["actual_original_argmax_equal"]),
                        zero_actual_logit_change_cases=sum(r["actual_logit_change_norm"]==0 for layer in report["layers"]for r in layer["rows"]))
                if counts["new_backbone_forwards"]!=p["expected_new_backbone_forwards"]:
                    raise RuntimeError("native model-call budget accounting differs")
                report.update(status="GEMMA18_ENDPOINT_PREDICTION_COMPLETE_NOT_QUALITY",summary=summaries,
                    cached_native_actual_reused=12,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                predictions=baseline=r0=originals=directions=module=downs=body=lm=last=h=y=None
    except BaseException as error:
        failure=str(error);report.update(status="GEMMA18_ENDPOINT_PREDICTION_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        predictions=baseline=r0=originals=directions=module=downs=body=lm=last=h=y=None;gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;archive.write_new(out/"report.json",report)
    print("[HF_ENDPOINT_END]"+json.dumps(dict(status=report["status"],counts=counts,error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","preflight","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="preflight":
        Budget().check(admission=True);inputs()
        if torch.cuda.is_initialized():raise RuntimeError("CPU native preflight initialized CUDA")
        print("[HF_ENDPOINT_PREFLIGHT]existing18 packets/12 contexts and local assets;no model",flush=True)
    elif args.action=="check":verify();print("[HF_ENDPOINT_CHECK]frozen18 packet/12 cached inputs/new clock",flush=True)
    else:actual()


if __name__=="__main__":main()
