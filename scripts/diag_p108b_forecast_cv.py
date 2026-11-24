"""Retrospective held-concept/layer forecast audit from completed14-layer data."""
import argparse
import sys
import time
import numpy as np
from scripts import diag_p108c_scope as io
from scripts import p108c_limits as limits
from scripts import p108b_forecast_cv as forecast

OUT=io.ROOT/"handoff/audit/nov16_night_p108c/forecast_cv_v1"
CODE=("scripts/diag_p108b_forecast_cv.py","scripts/p108b_forecast_cv.py",
      "scripts/test_p108b_forecast_cv.py","scripts/p108c_limits.py")


def source():
    data=io.read(io.OLD/"data.json")
    fits={r["id"]:r for r in data["rows"]if r["split"]=="fit"}
    parent=io.read(io.OLD/"geometry/report.json");baseline=parent["baseline"]["objective"]
    if len(fits)!=24 or len(parent["layers"])!=14:raise ValueError("completed14x24 source required")
    references={io.OLD/"data.json",io.OLD/"geometry/report.json"};rows=[];layer_table=[];epsilons=None
    for layer in range(14):
        directory=io.OLD/"geometry"/f"layer{layer:02d}";path=directory/"report.json";record=io.read(path)
        if record["layer"]!=layer or record["status"]!="GLOBAL_SINGLE_LAYER_ACTUAL_COMPLETE":
            raise ValueError("completed physical single-layer row required")
        eps=[float(v["epsilon"])for v in record["finite_difference"]]
        if epsilons is None:epsilons=eps
        if eps!=epsilons:raise ValueError("common existing FD probe depths required")
        answers=io.closed_answers(directory,record["answers_manifest"])
        references.add(path)
        references.update(directory/s["path"]for s in record["answers_manifest"]["shards"])
        for identifier,row in fits.items():
            base=baseline["fit_ce_by_id"][identifier]
            p=baseline["predicted_fit_gain_by_id"][identifier][str(layer)]
            measured=base-record["objective"]["fit_ce_by_id"][identifier]
            fd={}
            for sample in record["finite_difference"]:
                epsilon=float(sample["epsilon"])
                curvature=(sample["plus"]["fit_ce_by_id"][identifier]+sample["minus"]["fit_ce_by_id"][identifier]-2*base)/(epsilon*epsilon)
                fd["FD_QUADRATIC_"+str(epsilon)]=p-.5*curvature
            rows.append(dict(case_id=identifier,fact=row["fact"],semantic_group=forecast.semantic_group(row["fact"]),
                layer=layer,predicted_ce_gain=p,actual_ce_gain=measured,baseline_ce=base,
                generated_exact=answers[identifier]["exact"],small_probe_predictions=fd))
        layer_table.append(dict(layer=layer,predicted_J_gain=record["predicted_gain"],
            actual_J_gain=record["actual_gain"],actual_FIT_ce=record["objective"]["fit_ce"],
            actual_preserve_KL=record["objective"]["preserve_kl"],
            FIT_exact=sum(answers[i]["exact"]is True for i in fits),
            DEV_target_exact=record["dev"]["target"]["exact"],endpoint_transfer=record["transfer"]))
    if len(rows)!=336 or len({r["semantic_group"]for r in rows})!=8:
        raise ValueError("14layers/24phrases/eight semantic concepts required")
    for row in rows:
        if not all(np.isfinite(row[k])for k in ["predicted_ce_gain","actual_ce_gain","baseline_ce"]):
            raise ValueError("finite recorded predictors/outcomes required")
    return rows,layer_table,references,epsilons


def actual():
    budget=limits.Budget(600);budget.check(admission=True)
    if OUT.exists():raise FileExistsError("preserve previous retrospective calibration")
    rows,layers,refs,epsilons=source();OUT.mkdir();started=time.monotonic()
    with (OUT/"initial_plan.md").open("xb")as f:f.write(io.PLAN.read_bytes())
    io.write_new(OUT/"admission.json",dict(authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(),cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=600,code={p:io.sha(io.ROOT/p)for p in CODE},
        sources={str(p.relative_to(io.ROOT)):io.sha(p)for p in sorted(refs)},
        initial_plan_sha256=io.sha(OUT/"initial_plan.md"),cases=336,semantic_groups=8,physical_layers=14,
        calibrators=list(forecast.METHODS),fd_epsilons=epsilons,
        inference="RETROSPECTIVE_CALIBRATOR_HOLDOUT_NOT_EDIT_TARGET_HOLDOUT",
        original_edit_training_already_saw_all_FIT=True,new_model_or_gpu=False))
    io.write_new(OUT/"source_rows.json",dict(rows=rows,layers=layers))
    p=np.array([r["predicted_ce_gain"]for r in rows]);y=np.array([r["actual_ce_gain"]for r in rows])
    depth=np.array([r["layer"]for r in rows]);groups=np.array([r["semantic_group"]for r in rows])
    predictions={name:np.full(len(rows),np.nan)for name in forecast.METHODS};folds=[]
    for layer in range(14):
        for group in sorted(set(groups)):
            budget.check();train,test=forecast.fold_indices(depth,groups,layer,group)
            w=forecast.group_weights(groups[train]);models={}
            for name in forecast.METHODS:
                values,model=forecast.predict(name,p[train],depth[train],y[train],w,p[test],depth[test])
                predictions[name][test]=values;models[name]=model
            folds.append(dict(held_layer=layer,held_semantic_group=str(group),
                training_indices=np.where(train)[0].tolist(),test_indices=np.where(test)[0].tolist(),models=models))
    if len(folds)!=112 or any(not np.isfinite(v).all()for v in predictions.values()):
        raise ValueError("each of336 outcomes must have one separated prediction")
    for name in sorted(rows[0]["small_probe_predictions"]):
        predictions[name]=np.array([r["small_probe_predictions"][name]for r in rows])
    metrics={name:forecast.evaluate(rows,values)for name,values in predictions.items()}
    io.write_new(OUT/"folds.json",dict(folds=folds))
    io.save_arrays(OUT/"predictions.npz",**predictions)
    io.write_new(OUT/"case_predictions.json",dict(rows=[dict(r,predictions={k:float(v[i])for k,v in predictions.items()})for i,r in enumerate(rows)]))
    if "torch"in sys.modules and sys.modules["torch"].cuda.is_initialized():
        raise RuntimeError("CPU forecast analysis initialized CUDA")
    report=dict(schema="P108B_FORECAST_CROSSCHECK_V1",status="RETROSPECTIVE_CPU_ANALYSIS_COMPLETE",
        rows=336,held_cells=112,physical_layers=14,semantic_groups=8,calibration_holdout_only=True,
        edit_target_training_holdout=False,metrics=metrics,layer_table=layers,
        FD_methods_use_same_case_small_actual_probes=True,FD_previous_model_forwards_per_layer=4*152,
        loss_improved_but_generated_wrong=sum(r["actual_ce_gain"]>0 and not r["generated_exact"]for r in rows),
        loss_improved=sum(r["actual_ce_gain"]>0 for r in rows),generated_exact=sum(r["generated_exact"]for r in rows),
        baseline_difficulty_generated_exact_auc=forecast.auc(-np.array([r["baseline_ce"]for r in rows]),[r["generated_exact"]for r in rows]),
        new_model_loads=0,new_GPU=0,new_generations=0,new_optimizer_updates=0,checkpoint_writes=0,
        cross_model_transfer="NOT_RUN",general_or_language_quality="NOT_ESTABLISHED_BY_LOSS_FORECAST",
        wall_seconds=time.monotonic()-started,source_admission_sha256=io.sha(OUT/"admission.json"))
    io.write_new(OUT/"report.json",report)
    print("[FORECAST_CV_END]"+__import__("json").dumps(dict(status=report["status"],rows=336,held_cells=112,
        weighted_RMSE={n:m["semantic_weighted_rmse"]for n,m in metrics.items()},wall_seconds=report["wall_seconds"])),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("phase",choices=("check","actual"));phase=ap.parse_args().phase
    if phase=="check":
        limits.Budget(600).check(admission=True);source();print("[FORECAST_CV_CHECK]completed14x24 and eight concepts;model0",flush=True)
    else:actual()


if __name__=="__main__":main()
