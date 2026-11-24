"""Existing official11 evaluator with three presealed equal-net edited states."""
import argparse
from contextlib import contextmanager
import gc
import json
import os
from pathlib import Path
import shutil
import sysconfig
import time
import unittest
import torch
from scripts import diag_p108e_evaluate as replies
from scripts import p108e_replay as replay
from scripts import p108e_io as native
from scripts import diag_p108c_scope as archive
from scripts import p108c_limits as clock_owner
from scripts import diag_p108_frozen_edit_official as owner
from scripts import diag_p108b_official as history
from scripts import p108b_decode as function_owner
from scripts import interactive_research_infer as manual
from scripts import p106b_official_lm_adapter as lm_owner
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p106b_shards import ShardWriter

BASE=native.BASE/"official_v1"
PROFILE=BASE/"profile.json"
OUTPUT=BASE/"native"
ARMS=[name+"_MATCHED_NET"for name in replies.policy.POLICIES]
CODE=tuple(sorted(set(replies.CODE)|set(owner.CODE)|{
    "scripts/diag_p108e_official.py","scripts/diag_p108b_official.py","scripts/p108b_decode.py"}))


class Budget(clock_owner.Budget):
    def __init__(self,seconds=1800):super().__init__(seconds);self.last_disk=0.

    def check(self,**kwargs):
        result=super().check(**kwargs);now=time.monotonic()
        if now-self.last_disk>5:
            self.last_disk=now
            if shutil.disk_usage(native.ROOT).free<5_000_000_000:
                raise RuntimeError("less than5GB filesystem free;no cleanup authorized")
            if sum(p.stat().st_size for p in native.BASE.rglob("*")if p.is_file())>=1_980_000_000:
                raise RuntimeError("new official phase reached1.98GB owned cap within2GB total")
        return result


def identity():
    files={name:archive.sha(native.ROOT/name)for name in CODE}
    return dict(files=files,sha256=manual.canonical_sha(files))


def prepare():
    Budget(5400).check(admission=True)
    if BASE.exists():raise FileExistsError("preserve new official namespace")
    parent=replies.verify();closed=archive.read(replies.BASE/"actual/report.json")
    if(closed["status"]!="EXACT_STATE_REPLY_COMPARISON_COMPLETE"or not closed["original_core_restored"]
       or closed["cuda_allocated_after_bytes"]or closed["cuda_reserved_after_bytes"]):
        raise ValueError("closed all seven state replies required")
    baseline=history.baseline_reference()
    if baseline["origin"]!=parent["origin"]:raise ValueError("original official lineage differs")
    os.environ.update(owner.official.OFFLINE,HF_EVALUATE_OFFLINE="1")
    tasks,specs,provenance=owner.prepare_tasks()
    if specs!=baseline["task_specs"]or len(tasks)!=11:raise ValueError("official whole task specs differ")
    test=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName("scripts.test_p108b_official"))
    if not test.wasSuccessful()or test.testsRun!=2:raise RuntimeError("existing official/private-function contracts required")
    states={r["name"]:r for r in closed["states"]if r["name"]in ARMS}
    if set(states)!=set(ARMS):raise ValueError("all three declared same-net policies required")
    for row in states.values():
        if abs(row["physical"]["actual_norm"]-native.COMMON_BUDGET)>native.COMMON_BUDGET*2e-5:
            raise ValueError("same total physical norm not met")
    BASE.mkdir()
    with(BASE/"initial_plan.md").open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    refs={replies.PROFILE,replies.BASE/"actual/report.json",replies.BASE/"sealed/report.json",history.BASELINE}
    for r in closed["states"]:
        if r["name"]in ARMS:
            for shard in r["answers_manifest"]["shards"]:refs.add(replies.BASE/"actual"/r["name"]/shard["path"])
    archive.write_new(PROFILE,dict(schema="P108E_MATCHED_OFFICIAL11_V1",authority_directive=142,
        authority_end=clock_owner.AUTHORITY_END.isoformat(),cleanup_seconds=clock_owner.CLEANUP_SECONDS,
        model=parent["model"],origin=parent["origin"],source_identity=identity(),
        references={str(path.relative_to(native.ROOT)):archive.sha(path)for path in sorted(refs)},
        initial_plan_sha256=archive.sha(BASE/"initial_plan.md"),baseline=baseline,arms=ARMS,
        task_specs=specs,framework_provenance=provenance,CPU_contracts=test.testsRun,
        edited_core_sha256={name:states[name]["edited_core_sha256"]for name in ARMS},
        max_seconds_per_arm=1800,owned_raw_cap_bytes=1_980_000_000,total_artifact_cap_bytes=2_000_000_000,
        data_downloads=0,package_installs=0,optimizer_updates=0,checkpoint_writes=0,
        official_labels_used_for_fit=False,reselection_from_official_scores=False,
        scope="THREE_EQUAL_NET_POLICIES_NOT_GENERAL_QUALITY_ADOPTION"))
    if torch.cuda.is_initialized():raise RuntimeError("CPU official preparation initialized CUDA")
    print("[E_OFFICIAL_PREPARED]same11 task specs;three equal-net states;original24526 reused",flush=True)


def verify():
    p=archive.read(PROFILE);replies.verify()
    if(p["authority_directive"]!=142 or p["authority_end"]!=clock_owner.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=clock_owner.CLEANUP_SECONDS or p["source_identity"]!=identity()
       or p["initial_plan_sha256"]!=archive.sha(BASE/"initial_plan.md")):
        raise ValueError("exact official source/authority/initial plan differs")
    for name,digest in p["references"].items():
        if archive.sha(native.ROOT/name)!=digest:raise ValueError("official reference changed: "+name)
    return p


def run_one(name):
    p=verify();budget=Budget(p["max_seconds_per_arm"]);budget.check(admission=True)
    if name not in p["arms"]:raise ValueError("one frozen equal-net policy required")
    sealed=archive.read(replies.BASE/"sealed/report.json")
    state=next(s for s in sealed["states"]if s["name"]==name)
    closed=archive.read(replies.BASE/"actual/report.json")
    previous=next(s for s in closed["states"]if s["name"]==name)
    old_rows=archive.closed_answers(replies.BASE/"actual"/name,previous["answers_manifest"])
    canary_row=next(r for r in old_rows.values()if r["evaluation_panel"]=="FIT")

    @contextmanager
    def runtime(_name,_frozen,_packets,_expected,_target):
        if _name!=name:raise ValueError("private evaluator changed frozen state")
        active=model=physical=lm=after=None;proof=None
        with manual.selected_runtime(manual.resolve_model(p["model"]))as active:
            try:
                model=active["model"];physical=native.modules(active)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise ValueError("native original core differs")
                original={i:m.weight.detach().cpu().numpy().copy()for i,m in physical.items()}
                after=replies.reconstruct(original,state)
                try:
                    with replay.install_after(active,physical,after)as proof:
                        if manual.state_fingerprint(model)!=p["edited_core_sha256"][name]:
                            raise RuntimeError("official edited core does not equal actual-reply model")
                        answer,generation=manual.emit(active,canary_row["question"],max_new=64)
                        if generation["generated_ids"]!=canary_row["generation"]["generated_ids"]:
                            raise RuntimeError("official admission native free-answer canary differs")
                        proof.update(edited_core_sha256=p["edited_core_sha256"][name],origin=p["origin"],
                            native_canary=canary_row["id"],generation_replay_count=1,
                            official_evaluation_does_not_use_chat_generation=True,
                            physical_norm=state["physical"]["actual_norm"],benchmark_used_for_editing=False)
                        lm=lm_owner.create_adapter(active,runtime_root=Path(sysconfig.get_paths()["purelib"]),batch_size=8)
                        try:yield lm,proof
                        finally:
                            if lm is not None:lm.close();lm=None
                finally:
                    restored=manual.state_fingerprint(model)==p["origin"]["core_sha256"]
                    if proof is not None:proof["original_core_restored"]=restored
                    if not restored:raise RuntimeError("official runtime did not restore original core")
            finally:physical=model=after=None
        active=None;gc.collect()

    class GuardedShardWriter(ShardWriter):
        def append(self,row):budget.check();super().append(row)

    def bundle():return {"actual/report.json":dict(origin=p["origin"])},None,None
    frozen_files={"profile.json":archive.sha(PROFILE)}
    evaluator=function_owner.private_function(owner.evaluate,identity=identity,bundle=bundle,
        model_runtime=runtime,OUTPUT=OUTPUT,BASE=BASE,FROZEN=frozen_files,
        ShardWriter=GuardedShardWriter,TAG="p108e_same_net_official11_v1_s1337")
    result=dict(status="STARTED",name=name);failure=None
    try:result=evaluator(name,identity()["sha256"],p["max_seconds_per_arm"])
    except BaseException as error:
        failure=str(error);result.update(status="P108E_OFFICIAL_ERROR",error=failure);error.__traceback__=None
    finally:
        gc.collect();cleanup_error=cleanup_owner.cleanup(result)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        result.update(original_baseline_reused=p["baseline"],source_identity_unchanged=identity()==p["source_identity"])
        archive.write_new(BASE/(name+"_cleanup.json"),result)
    print("[E_OFFICIAL_ARM]"+json.dumps(dict(name=name,status=result["status"],error=failure,
        cuda_allocated_after_bytes=result.get("cuda_allocated_after_bytes"),
        cuda_reserved_after_bytes=result.get("cuda_reserved_after_bytes"))),flush=True)
    return dict(name=name,failed=failure is not None,result=result)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","preflight","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="preflight":
        Budget(5400).check(admission=True);p=replies.verify();baseline=history.baseline_reference()
        if baseline["origin"]!=p["origin"]or torch.cuda.is_initialized():raise ValueError("CPU lineage admission failed")
        print("[E_OFFICIAL_PREFLIGHT]same original baseline and sealed states;no model",flush=True)
    elif args.action=="check":verify();print("[E_OFFICIAL_CHECK]same task/lineage and three frozen edited cores",flush=True)
    else:
        p=verify();Budget(p["max_seconds_per_arm"]*3).check(admission=True)
        results=[run_one(name)for name in ARMS]
        archive.write_new(BASE/"batch_report.json",dict(results=results,independent_arms_continued=True))
        if any(r["failed"]for r in results):raise RuntimeError("one or more official arms failed;raw reports preserved")


if __name__=="__main__":main()
