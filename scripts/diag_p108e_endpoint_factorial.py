"""CPU-only factorization of frozen endpoint versus competitor forecast errors."""
import argparse
import time
import unittest
import numpy as np
import torch
from scripts import diag_p108e_endpoint as experiment
from scripts import p108e_endpoint_prediction as secant_owner
from scripts import diag_p108c_scope as archive
from scripts import p108b_lastlayer_forecast as differential
from scripts import diag_p108e_official as resources

BASE=experiment.BASE/"factorial_v1"
CODE=("scripts/diag_p108e_endpoint_factorial.py","scripts/p108b_lastlayer_forecast.py",
      "scripts/p108e_endpoint_prediction.py","scripts/diag_p108e_endpoint.py")


def check():
    resources.Budget(600).check(admission=True);p=experiment.verify()
    closed=archive.read(experiment.BASE/"actual/report.json")
    if(closed["status"]!="ALL14_ENDPOINT_PREDICTION_COMPLETE"or not closed["original_core_restored"]
       or closed["cuda_allocated_after_bytes"]or closed["cuda_reserved_after_bytes"]):
        raise ValueError("complete restored all14 endpoint evidence required")
    if torch.cuda.is_initialized():raise RuntimeError("CPU source check initialized CUDA")
    return p,closed


def actual():
    p,closed=check();budget=resources.Budget(600);started=time.monotonic()
    if BASE.exists():raise FileExistsError("preserve endpoint factorial namespace")
    test=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName("scripts.test_p108b_lastlayer_forecast"))
    if not test.wasSuccessful()or test.testsRun!=5:raise RuntimeError("existing five native RMS/large-step contracts required")
    BASE.mkdir()
    with(BASE/"initial_plan.md").open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    archive.write_new(BASE/"profile.json",dict(schema="P108E_ENDPOINT_ERROR_FACTORIAL_V1",CPU_contracts=5,
        authority_directive=142,authority_end=experiment.native.time_owner.AUTHORITY_END.isoformat(),
        initial_plan_sha256=archive.sha(BASE/"initial_plan.md"),
        sources={name:archive.sha(archive.ROOT/name)for name in CODE},
        endpoint_profile_sha256=archive.sha(experiment.PROFILE),
        endpoint_report_sha256=archive.sha(experiment.BASE/"actual/report.json"),
        native_logit_tolerance=.002,argmax_mismatches_allowed=0,
        ordered_contrasts=["VJP_TO_ENDPOINT_DERIVATIVE","LINEAR_TO_EXACT_FINAL_NORM","FIXED_TO_FULL_COMPETITORS"],
        new_model_loads=0,new_model_forwards=0,new_generated_answers=0))
    capture,arrays,head=experiment.native.origin.captured()
    g=archive.read(experiment.native.GEOMETRY/"report.json")
    r0=experiment.replies.packet(g["baseline_endpoint"])["values"].astype(np.float64)
    original=experiment.replies.packet(g["original_logits_reused"])["logits"].astype(np.float64)
    packed=archive.read(experiment.native.PROFILE)["packed"];layout=experiment.native.target_indices(packed)
    gold=layout["gold"];positions=np.arange(62)
    other=original.copy();other[positions,gold]=-np.inf;rivals=other.argmax(1)
    before_margin=original[positions,gold]-original[positions,rivals]
    predictions=archive.read(experiment.BASE/"actual/ALL14_PREDICTIONS_BEFORE_FULL_STEP.json")["rows"]
    results=[];parity_failed=False
    for observed,predicted in zip(closed["actual_points"],predictions):
        budget.check();layer=observed["layer"]
        if layer!=predicted["layer"]:raise ValueError("all14 candidate order differs")
        fd=next(x for x in predicted["FD"]if x["epsilon"]==.003)
        cached=experiment.replies.packet(fd["packet"])
        d,q=secant_owner.secants(r0,cached["plus"],cached["minus"],fd["plus"]["scalar"],fd["minus"]["scalar"])
        actual_r=experiment.replies.packet(observed["native_endpoint"])["values"].astype(np.float64)
        actual_logits=actual_r@head.T/np.sqrt(np.mean(actual_r**2,axis=1)+capture["norm_eps"])[:,None]
        raw=experiment.replies.packet(observed["native_top8"])
        raw_gold_margin=raw["gold_logits"]-np.max(np.where(raw["ids"]==gold[:,None],-np.inf,raw["logits"]),axis=1)
        top_error=float(np.max(np.abs(np.take_along_axis(actual_logits,raw["ids"],axis=1)-raw["logits"])))
        gold_error=float(np.max(np.abs(actual_logits[positions,gold]-raw["gold_logits"])))
        mismatch=int(np.sum(actual_logits.argmax(1)!=raw["winners"]))
        if max(top_error,gold_error)>.002 or mismatch:parity_failed=True
        changes=np.stack([differential.rms_direction(torch.from_numpy(h),torch.from_numpy(v),capture["norm_eps"]).numpy()
                          for h,v in zip(r0,d)])
        linear_logits=original+changes@head.T
        predicted_r=(r0+d).astype(np.float32).astype(np.float64)
        exact_logits=predicted_r@head.T/np.sqrt(np.mean(predicted_r**2,axis=1)+capture["norm_eps"])[:,None]
        signals={
            "A_ORIGINAL_VJP_FIXED":np.asarray(next(x for x in predicted["predictions"]if x["predictor"]=="CURRENT_RIVAL_LINEAR")["margins"]),
            "B_ENDPOINT_LINEAR_HEAD_FIXED":linear_logits[positions,gold]-linear_logits[positions,rivals],
            "C_ENDPOINT_EXACT_HEAD_FIXED":exact_logits[positions,gold]-exact_logits[positions,rivals]}
        other=exact_logits.copy();other[positions,gold]=-np.inf
        signals["D_ENDPOINT_EXACT_HEAD_FULL"]=exact_logits[positions,gold]-other.max(1)
        actual_fixed=actual_logits[positions,gold]-actual_logits[positions,rivals]
        rows={}
        for name,margin in signals.items():
            rows[name]=dict(score=experiment.replies.policy.mathematics.score(margin,layout["offsets"]),
                actual_fixed_rival_RMSE=float(np.sqrt(np.mean((margin-actual_fixed)**2))),
                actual_full_vocab_RMSE=float(np.sqrt(np.mean((margin-raw_gold_margin)**2))))
        results.append(dict(layer=layer,signals=rows,actual=observed["score"],
            native_top8_reconstruction_max_error=top_error,native_gold_reconstruction_max_error=gold_error,
            argmax_mismatches=mismatch,
            A_to_B_RMSE=float(np.sqrt(np.mean((signals["A_ORIGINAL_VJP_FIXED"]-signals["B_ENDPOINT_LINEAR_HEAD_FIXED"])**2))),
            B_to_C_RMSE=float(np.sqrt(np.mean((signals["B_ENDPOINT_LINEAR_HEAD_FIXED"]-signals["C_ENDPOINT_EXACT_HEAD_FIXED"])**2))),
            C_to_D_RMSE=float(np.sqrt(np.mean((signals["C_ENDPOINT_EXACT_HEAD_FIXED"]-signals["D_ENDPOINT_EXACT_HEAD_FULL"])**2))),
            actual_competitor_switch_margin_RMS=float(np.sqrt(np.mean((actual_fixed-raw_gold_margin)**2)))))
        print("[ENDPOINT_FACTORIAL]layer="+str(layer),flush=True)
    keys=list(results[0]["signals"])
    summary={name:dict(
        mean_full_question_absolute_error=float(np.mean([abs(r["signals"][name]["score"]["questions_all_gold"]-r["actual"]["questions_all_gold"])for r in results])),
        pooled_actual_fixed_rival_RMSE=float(np.sqrt(np.mean([r["signals"][name]["actual_fixed_rival_RMSE"]**2 for r in results]))),
        pooled_actual_full_vocab_RMSE=float(np.sqrt(np.mean([r["signals"][name]["actual_full_vocab_RMSE"]**2 for r in results]))))for name in keys}
    result=dict(schema="P108E_ENDPOINT_ERROR_FACTORIAL_V1",status="NATIVE_PARITY_NEGATIVE"if parity_failed else"ENDPOINT_FACTORIAL_COMPLETE",
        rows=results,summary=summary,wall_seconds=time.monotonic()-started,
        ordering_dependent_algebraic_contrasts_not_unique_causal_percentages=True,
        existing_actual_results_unchanged=True,new_model_loads=0,new_model_forwards=0,new_generated_answers=0)
    archive.write_new(BASE/"report.json",result)
    if torch.cuda.is_initialized():raise RuntimeError("CPU factorial initialized CUDA")
    print("[ENDPOINT_FACTORIAL_END]"+json.dumps(dict(status=result["status"],summary=summary,wall_seconds=result["wall_seconds"])),flush=True)
    return 8 if parity_failed else 0


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("check","actual"));args=parser.parse_args()
    if args.action=="check":check();print("[ENDPOINT_FACTORIAL_CHECK]closed raw endpoint/head only;no model",flush=True);return 0
    return actual()


if __name__=="__main__":raise SystemExit(main())
