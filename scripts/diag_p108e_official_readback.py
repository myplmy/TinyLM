"""Recount all official samples with matched prompts and a33-test family."""
import json
import os
from scripts import diag_p108e_official as experiment
from scripts import diag_p108_frozen_edit_official as owner
from scripts import diag_p108b_official_readback as common
from scripts import diag_p108c_scope as archive
from scripts import p106b_shards as shards
from scripts import eval_bench_suite as statistics

PRIMARY={"piqa":"acc","arc_easy":"acc_norm","arc_challenge":"acc_norm",
         "hellaswag":"acc_norm","winogrande":"acc","boolq":"acc"}


def run():
    from sklearn.metrics import f1_score
    p=experiment.verify()
    batch=archive.read(experiment.BASE/"batch_report.json")
    if len(batch["results"])!=3 or any(r["failed"]for r in batch["results"]):
        raise ValueError("three complete official states required")
    os.environ.update(owner.official.OFFLINE,HF_EVALUATE_OFFLINE="1")
    tasks,specs,provenance=owner.prepare_tasks()
    paths={"original":experiment.history.BASELINE,
           **{name:experiment.OUTPUT/name/"report.json"for name in experiment.ARMS}}
    inputs={};vectors={};identities={};metrics={};signatures={}
    for name,path in paths.items():
        report=archive.read(path)
        if(report["status"]!="OFFICIAL_ELEVEN_TASKS_COMPLETE"or report["returncode"]!=0
           or report["task_specs"]!=specs or report["policy"]!=owner.official.policy()
           or report["frozen_model_origin"]!=p["origin"]):
            raise ValueError("complete same official contract and lineage required")
        if name!="original":
            if(report["model_proof"]["edited_core_sha256"]!=p["edited_core_sha256"][name]
               or not report["model_proof"]["original_core_restored"]):
                raise ValueError("edited core or original recovery differs")
            cleanup=archive.read(experiment.BASE/(name+"_cleanup.json"))
            if cleanup["cuda_allocated_after_bytes"]or cleanup["cuda_reserved_after_bytes"]:
                raise ValueError("final GPU allocation remains")
        inputs[name]=dict(path=str(path.relative_to(archive.ROOT)),sha256=archive.sha(path))
        vectors[name]={};identities[name]={};metrics[name]={};signatures[name]={}
        for taskname,task in tasks.items():
            manifest=report["sample_manifests"][taskname];shards.verify(path.parent,manifest);rows=[]
            for part in manifest["shards"]:
                rows.extend(json.loads(line)for line in(path.parent/part["path"]).read_text().splitlines())
            audit=owner.official.plain(owner.suite.audit_task(task,rows,len(task.eval_docs)))
            if audit!=report["independent_audits"][taskname]:raise ValueError("independent raw audit differs")
            vector=common.recount_vectors(task,rows);vectors[name][taskname]=vector
            values=report["official_results"][taskname]["results"][taskname]
            for metric in ("acc","acc_norm"):
                if metric+",none"in values:
                    if abs(sum(vector[metric])/len(rows)-values[metric+",none"])>1e-12:
                        raise ValueError("raw official accuracy differs")
            if taskname.startswith("kobest_"):
                f1=float(f1_score(vector["gold"],vector["pred"],average="macro"))
                if abs(f1-values["f1,none"])>1e-12:raise ValueError("raw official macroF1 differs")
            identities[name][taskname]=experiment.manual.canonical_sha([
                {key:r[key]for key in("doc_id","doc_hash","prompt_hash","target_hash","arguments")}for r in rows])
            primary=PRIMARY.get(taskname,"f1")
            metrics[name][taskname]=dict(n=len(rows),primary_metric=primary,primary=values[primary+",none"],
                acc=values["acc,none"],acc_norm=values.get("acc_norm,none"),f1=values.get("f1,none"),
                diagnostic_baselines=audit)
            signatures[name][taskname]=dict(rows=len(rows),sample_concat_sha256=manifest["concat_sha256"])
        if name!="original"and identities[name]!=identities["original"]:
            raise ValueError("official source/order/questions/targets/rendered options differ")
    tests=[]
    for name in experiment.ARMS:
        for taskname in tasks:
            metric=PRIMARY.get(taskname,"acc");left=vectors["original"][taskname][metric];right=vectors[name][taskname][metric]
            lost=sum(bool(a)and not b for a,b in zip(left,right));gained=sum(bool(b)and not a for a,b in zip(left,right))
            tests.append(dict(arm=name,task=taskname,accuracy_metric=metric,n=len(left),
                original_correct=sum(left),edited_correct=sum(right),gained=gained,lost=lost,
                delta_pp=100*(gained-lost)/len(left),p_unadjusted=statistics.mcnemar_exact_p(lost,gained),
                scope="ITEM_ACCURACY_ONLY_NOT_MACRO_F1_SIGNIFICANCE"))
    if len(tests)!=33:raise ValueError("one predeclared33-test family required")
    common.corrected_p(tests)
    summary={name:dict(core6_project_primary_mean=sum(row[t]["primary"]for t in PRIMARY)/6,
        kobest_task_mean_macro_f1=sum(row[t]["f1"]for t in row if t.startswith("kobest_"))/5)
        for name,row in metrics.items()}
    result=dict(schema="P108E_OFFICIAL11_PAIRED_RAW_READBACK_V1",inputs=inputs,
        primary_metric_map=PRIMARY,task_specs=specs,metrics=metrics,summary=summary,
        paired_accuracy_tests=tests,statistical_family=33,holm_significant_count=sum(t["p_holm"]<.05 for t in tests),
        exact_original_prompt_and_choices=identities["original"],sample_signatures=signatures,
        actual_rows_per_model=sum(r["n"]for r in metrics["original"].values()),
        statistical_limits="No macroF1 significance test;item clustering and one parent/one seed remain",
        benchmark_used_for_training_editing_or_reselection=False,new_model_calls=0,
        quality_adoption=False,root_open_language_review="ROOT_REVIEW.md separately")
    path=archive.ROOT/"handoff/audit/nov16_night_p108c/P108E_OFFICIAL11_READBACK_v1.json"
    archive.write_new(path,owner.official.plain(result))
    print(json.dumps(dict(summary=summary,Holm_significant=result["holm_significant_count"],
        paired_rows_per_model=result["actual_rows_per_model"],new_model_calls=0),ensure_ascii=False),flush=True)


if __name__=="__main__":run()
