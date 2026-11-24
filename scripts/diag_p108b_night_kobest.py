"""Current-authority Qwen0.6 baseline on already local official KoBEST tasks."""
import argparse
import gc
import json
import math
from pathlib import Path
import time
import traceback
from scripts.prepare_p106b_official_eval import configure_hf_cache

CACHE_POLICY=configure_hf_cache()
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p108b_external_kobest as tasks_owner
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p106b_orpo_official as official
from scripts import diag_p108b_value_library as cleanup_owner
from scripts import interactive_research_infer as manual
from scripts import diag_p108c_scope as io
from scripts import p108c_limits as limits
from scripts.p106b_shards import ShardWriter,verify as verify_shards

ROOT=io.ROOT;BASE=io.BASE
PROFILE=BASE/"external_qwen06_kobest_profile_v1.json"
INITIAL=BASE/"external_qwen06_kobest_initial_plan_v1.md"
OUT=BASE/"external_qwen06_kobest_v1"
MODEL="qwen06"
CODE=("scripts/diag_p108b_night_kobest.py","scripts/diag_p108b_external_kobest.py",
      "scripts/diag_p106b_external_core6.py","scripts/diag_p106b_orpo_official.py",
      "scripts/diag_p106b_official_core6.py","scripts/prepare_p106b_kobest_official_eval.py",
      "scripts/prepare_p106b_official_eval.py","scripts/p106b_official_lm_adapter.py",
      "scripts/p106b_official_tasks.py","scripts/p106b_shards.py","scripts/p108c_limits.py")


def prepare():
    limits.Budget(1800).check(admission=True)
    if PROFILE.exists()or INITIAL.exists():raise FileExistsError("preserve earlier KoBEST admission")
    tasks,specs,provenance=tasks_owner.tasks();assets=external.asset_identity(MODEL)
    from lm_eval.evaluator import simple_evaluate
    if not callable(simple_evaluate)or torch.cuda.is_initialized():raise ValueError("CPU official entry without model/CUDA required")
    with INITIAL.open("xb")as f:f.write(io.PLAN.read_bytes())
    io.write_new(PROFILE,dict(schema="P108B_NIGHT_QWEN06_KOBEST_V1",authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(),cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=1800,model=MODEL,sources={n:io.sha(ROOT/n)for n in CODE},
        assets=assets,task_specs=specs,framework=provenance,
        actual_counts={n:len(t.eval_docs)for n,t in tasks.items()},initial_plan_sha256=io.sha(INITIAL),
        cache_policy=CACHE_POLICY,policy=dict(num_fewshot=0,apply_chat_template=False,batch_size=1,
            max_length=1024,precision="FP32_MATH_TF32_OFF",use_cache=False,bootstrap_iters=0,seed=1337),
        model_loads=0,training=False,optimizer_updates=0,checkpoint_writes=0,
        new_downloads=0,new_packages=0,new_environment=False))
    print("[NIGHT_KOBEST_PREPARED]qwen06;official5/test4561;existing assets/environment;model0",flush=True)


def verify():
    limits.Budget(1800).check();p=io.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=limits.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=limits.CLEANUP_SECONDS or p["model"]!=MODEL
       or p["initial_plan_sha256"]!=io.sha(INITIAL)):
        raise ValueError("current night authority/model/initial plan differs")
    for name,expected in p["sources"].items():
        if io.sha(ROOT/name)!=expected:raise ValueError("frozen evaluator source changed: "+name)
    if external.asset_identity(MODEL)!=p["assets"]:raise ValueError("native existing assets changed")
    tasks,specs,provenance=tasks_owner.tasks()
    if specs!=p["task_specs"]or provenance!=p["framework"]:
        raise ValueError("exact official tasks/framework differ")
    return p,tasks,provenance


def actual():
    p,tasks,provenance=verify();budget=limits.Budget(p["max_seconds"]);budget.check(admission=True)
    entry=cleanup_owner.resources()
    if OUT.exists():raise FileExistsError("preserve previous whole/partial external task run")
    OUT.mkdir();torch.set_num_threads(4);torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    from scripts.p106b_gate_runtime import wall_limit
    report=dict(schema=p["schema"],model=MODEL,status="STARTED",source_profile_sha256=io.sha(PROFILE),
        policy=p["policy"],framework=provenance,entry_resources=entry,actual_counts={},official_results={},
        independent_audits={},sample_manifests={},training=False,optimizer_updates=0,checkpoint_writes=0,
        metrics_scope="EXTERNAL_BASELINE_NOT_TINYLM_IMPROVEMENT_OR_FREE_DIALOGUE")
    started=time.monotonic();failure=None;lengths=ShardWriter(OUT,"token_lengths",limit=2_000_000)
    lm=None
    try:
        with wall_limit(p["max_seconds"]),sdpa_kernel(SDPBackend.MATH),torch.no_grad():
            proof={}
            with external.model_runtime(MODEL,torch,p["assets"],proof=proof)as(lm,_proof):
                report["model_proof"]=proof
                report["native_full_softmax_canary"]=external.numerical_canary(lm,torch)
                if lm.batch_size!=1 or lm.max_length!=1024:raise ValueError("fixed native HF batch/length differs")
                torch.cuda.reset_peak_memory_stats();manager=TaskManager()
                with tasks_owner.core.length_observer(lm,lengths)as observed:
                    for name,task in tasks.items():
                        budget.check();tick=time.monotonic()
                        raw=simple_evaluate(model=lm,tasks=[task],num_fewshot=0,task_manager=manager,
                            batch_size=1,device="cuda",use_cache=None,cache_requests=False,limit=None,
                            bootstrap_iters=0,log_samples=True,apply_chat_template=False,fewshot_as_multiturn=False,
                            random_seed=1337,numpy_random_seed=1337,torch_random_seed=1337,fewshot_random_seed=1337)
                        samples=raw.pop("samples")[name];audit=official.audit_task(task,samples,len(task.eval_docs))
                        for metric,key in (("acc","correct"),("acc_norm","correct_norm")):
                            score=raw["results"][name].get(metric+",none")
                            if score is not None and not math.isclose(score,audit[key]/len(samples),abs_tol=1e-12):
                                raise ValueError("official accuracy differs from raw choices")
                        f1=task.aggregation()["f1"]([r["f1"]for r in samples])
                        if not math.isclose(f1,raw["results"][name]["f1,none"],abs_tol=1e-12):
                            raise ValueError("official macroF1 differs from raw labels")
                        writer=ShardWriter(OUT,name+"_samples",limit=2_000_000)
                        for row in samples:writer.append(tasks_owner.core.plain(row))
                        manifest=writer.close(lineage=dict(model=MODEL,task=name,framework_commit=official.adapter.COMMIT))
                        verify_shards(OUT,manifest)
                        report["sample_manifests"][name]=manifest;report["actual_counts"][name]=len(samples)
                        report["independent_audits"][name]=audit;report["official_results"][name]=tasks_owner.core.plain(raw)
                        print("[NIGHT_KOBEST_TASK]"+json.dumps(dict(task=name,n=len(samples),seconds=time.monotonic()-tick)),flush=True)
                report.update(token_lengths_summary=observed,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,peak_scope="POST_LOAD_CANARY_THROUGH_TASKS_ONLY")
            lm=None
            if report["actual_counts"]!=p["actual_counts"]:raise ValueError("exact4561 denominator differs")
            report["status"]="OFFICIAL_KOBEST_QWEN06_FIVE_COMPLETE"
    except BaseException as error:
        failure=str(error);report.update(status="NIGHT_KOBEST_ERROR",error_type=type(error).__name__,error=failure,traceback=traceback.format_exc())
        error.__traceback__=None
    finally:
        lm=None
        if lengths._total_rows:
            report["lengths_manifest"]=lengths.close(lineage=dict(model=MODEL));verify_shards(OUT,report["lengths_manifest"])
        gc.collect();cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None and failure is None:failure=str(cleanup_error)
        report.update(wall_seconds=time.monotonic()-started,
            source_files_unchanged=all(io.sha(ROOT/n)==s for n,s in p["sources"].items()))
        io.write_new(OUT/"report.json",report)
        print("[NIGHT_KOBEST_END]"+json.dumps({k:report.get(k)for k in("status","wall_seconds","actual_counts","cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}),flush=True)
    if failure is not None:raise RuntimeError("preserved official Qwen KoBEST failure: "+failure)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("phase",choices=("prepare","check","actual"));phase=ap.parse_args().phase
    if phase=="prepare":prepare()
    elif phase=="check":verify();print("[NIGHT_KOBEST_CHECK]exact local framework/assets/current authority;model0",flush=True)
    else:actual()


if __name__=="__main__":main()
