"""One shared held-fact calibrator ranks all layers; no native model work."""
import argparse
import json
import sys
import time
import numpy as np
from scripts import diag_p108c_scope as io
from scripts import p108c_limits as limits
from scripts import p108b_forecast_cv as forecast

SOURCE=io.ROOT/"handoff/audit/nov16_night_p108c/forecast_cv_v1/source_rows.json"
OUT=io.ROOT/"handoff/audit/nov16_night_p108c/forecast_common_v1"
CODE=("scripts/diag_p108b_forecast_common.py","scripts/p108b_forecast_cv.py","scripts/p108c_limits.py")


def source():
    rows=io.read(SOURCE)["rows"]
    if len(rows)!=336 or len({r["layer"]for r in rows})!=14 or len({r["semantic_group"]for r in rows})!=8:
        raise ValueError("closed14 layers/eight facts/336 outcomes required")
    return rows


def actual():
    budget=limits.Budget(600);budget.check(admission=True)
    if OUT.exists():raise FileExistsError("preserve common-calibrator analysis")
    rows=source();OUT.mkdir();started=time.monotonic()
    with (OUT/"initial_plan.md").open("xb")as stream:stream.write(io.PLAN.read_bytes())
    io.write_new(OUT/"admission.json",dict(authority_directive=142,authority_end=limits.AUTHORITY_END.isoformat(),
        sources={n:io.sha(io.ROOT/n)for n in CODE},source_rows_sha256=io.sha(SOURCE),
        original_edit_saw_all_FIT=True,model_or_GPU=False,final_or_official_used=False,
        initial_plan_sha256=io.sha(OUT/"initial_plan.md")))
    predicted=np.array([r["predicted_ce_gain"]for r in rows]);actual=np.array([r["actual_ce_gain"]for r in rows])
    depth=np.array([r["layer"]for r in rows]);groups=np.array([r["semantic_group"]for r in rows])
    predictions={};folds=[];metrics={}
    for regime,held_values in (("FACT_ONLY",sorted(set(groups))),("LAYER_ONLY",list(range(14)))):
        values={name:np.full(len(rows),np.nan)for name in forecast.METHODS}
        for held in held_values:
            budget.check()
            test=(groups==held)if regime=="FACT_ONLY"else(depth==held);train=~test
            weights=forecast.group_weights(groups[train]);models={}
            for name in forecast.METHODS:
                guess,model=forecast.predict(name,predicted[train],depth[train],actual[train],weights,
                                             predicted[test],depth[test])
                values[name][test]=guess;models[name]=model
            folds.append(dict(regime=regime,held=str(held),training_indices=np.where(train)[0].tolist(),
                              test_indices=np.where(test)[0].tolist(),models=models))
        if any(not np.isfinite(v).all()for v in values.values()):raise RuntimeError("incomplete OOF predictions")
        if regime=="FACT_ONLY":
            for field in rows[0]["small_probe_predictions"]:
                values[field]=np.array([r["small_probe_predictions"][field]for r in rows])
        scores={name:forecast.evaluate(rows,value)for name,value in values.items()}
        if regime=="LAYER_ONLY":
            allowed=("semantic_weighted_rmse","semantic_weighted_mae","sign_accuracy","generated_exact_auc")
            scores={name:{k:s[k]for k in allowed}for name,s in scores.items()}
        predictions.update({regime+"__"+name:value for name,value in values.items()});metrics[regime]=scores
    for case in {r["case_id"]for r in rows}:
        indices={i for i,r in enumerate(rows)if r["case_id"]==case}
        covering=[f for f in folds if f["regime"]=="FACT_ONLY"and indices.intersection(f["test_indices"])]
        if len(covering)!=1 or len(indices)!=14 or not indices.issubset(set(covering[0]["test_indices"])):
            raise RuntimeError("every ranked14-layer set must share one frozen calibrator")
    io.save_arrays(OUT/"predictions.npz",**predictions)
    io.write_new(OUT/"folds.json",dict(folds=folds))
    if "torch"in sys.modules and sys.modules["torch"].cuda.is_initialized():raise RuntimeError("CPU audit initialized CUDA")
    report=dict(status="COMMON_CALIBRATOR_CPU_COMPLETE",rows=336,fact_folds=8,layer_folds=14,metrics=metrics,
        all_ranked_candidates_share_one_calibrator=True,layer_only_ranking_intentionally_not_reported=True,
        prior_edit_target_training_holdout=False,new_model_loads=0,new_forwards=0,new_generations=0,
        checkpoint_writes=0,wall_seconds=time.monotonic()-started)
    io.write_new(OUT/"report.json",report)
    print("[FORECAST_COMMON_END]"+json.dumps(dict(status=report["status"],wall_seconds=report["wall_seconds"],
        fact_only_regret={name:m["mean_case_regret"]for name,m in metrics["FACT_ONLY"].items()})),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("phase",choices=("check","actual"))
    if parser.parse_args().phase=="check":
        limits.Budget(600).check(admission=True);source();print("[FORECAST_COMMON_CHECK]closed336;model0",flush=True)
    else:actual()


if __name__=="__main__":main()
