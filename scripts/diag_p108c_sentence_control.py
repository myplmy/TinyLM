"""Post-result Korean question-grammar control; no model/router reselection."""
import argparse
import gc
import json
import time
import traceback
import torch
import tinylm
from scripts import diag_p108c_scope as io
from scripts import diag_p108c_boundary as boundary
from scripts import p108c_runtime as runtime
from scripts import p108c_limits as limits
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p106b_shards import ShardWriter

BASE=io.BASE
PROFILE=BASE/"sentence_control_profile_v1.json"
INITIAL=BASE/"sentence_control_initial_plan_v1.md"
OUT=BASE/"sentence_control_actual_v1"
QUESTIONS=(
    "대한민국의 수도가 어디인지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
    "프랑스의 수도가 어디인지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
    "물의 화학식이 무엇인지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
    "지구가 어느 별을 공전하는지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
    "독일의 수도가 어디인지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
    "이탈리아의 수도가 어디인지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
    "산소 분자의 화학식이 무엇인지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
    "달이 어느 행성을 공전하는지 주어와 서술어가 있는 완전한 한국어 한 문장으로 답해 주세요.",
)


def prepare():
    limits.Budget(600).check(admission=True);boundary.verify()
    if PROFILE.exists()or INITIAL.exists():raise FileExistsError("preserve grammar-control admission")
    p,_,refs,_=boundary.source()
    from tinylm.chat.serialize import serialize
    tok=manual.local_tokenizer(manual.verify_manifest())
    for q in QUESTIONS:
        text=serialize(dict(messages=manual.prompt_messages(q)),"chatml",add_generation_prompt=True)
        enc=tok.encode(text);runtime.question_indices(text,q,enc.offsets)
        if len(enc.ids)+96>1024:raise ValueError("grammar control would truncate")
        print("[QUESTION_REVIEW]"+q,flush=True)
    refs.update({boundary.PROFILE,boundary.OUT/"report.json"})
    sources={n:io.sha(io.ROOT/n)for n in ("scripts/diag_p108c_sentence_control.py",)+boundary.CODE}
    with INITIAL.open("xb")as f:f.write(io.PLAN.read_bytes())
    io.write_new(PROFILE,dict(schema="P108C_KOREAN_GRAMMAR_CONTROL_V1",authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(),cleanup_seconds=limits.CLEANUP_SECONDS,
        model=p["model"],origin=p["origin"],max_seconds=600,max_new=96,questions=list(QUESTIONS),
        sources=sources,references={str(p.relative_to(io.ROOT)):io.sha(p)for p in sorted(refs)},
        initial_plan_sha256=io.sha(INITIAL),expected_generated_replies=32,
        post_result_control=True,blind_final=False,no_reselection=True,optimizer_updates=0,checkpoint_writes=0))
    if torch.cuda.is_initialized():raise RuntimeError("CPU preparation initialized CUDA")
    print("[GRAMMAR_PREPARED]8 explicitly reviewed native questions;four frozen paths",flush=True)


def verify():
    limits.Budget(600).check();p=io.read(PROFILE)
    if (p["authority_directive"]!=142 or p["authority_end"]!=limits.AUTHORITY_END.isoformat()
        or p["cleanup_seconds"]!=limits.CLEANUP_SECONDS or io.sha(INITIAL)!=p["initial_plan_sha256"]
        or p["questions"]!=list(QUESTIONS)):raise ValueError("exact grammar-control authority/data required")
    for name,sha in {**p["sources"],**p["references"]}.items():
        if io.sha(io.ROOT/name)!=sha:raise ValueError("grammar-control source changed")
    return p


def actual():
    p=verify();budget=limits.Budget(p["max_seconds"]);budget.check(admission=True)
    if OUT.exists():raise FileExistsError("preserve grammar-control run")
    entry=cleanup_owner.resources();OUT.mkdir();started=time.monotonic()
    report=dict(schema=p["schema"],status="STARTED",source_profile_sha256=io.sha(PROFILE),
        entry_resources=entry,optimizer_updates=0,checkpoint_writes=0,post_result_control=True,blind_final=False)
    active=engine=packet=None;failure=None
    try:
        _,configs,_,_=boundary.source();packet=io.load_arrays(io.ARM/"packet.npz")
        torch.set_num_threads(4)
        with manual.selected_runtime(manual.resolve_model(p["model"]))as active:
            try:
                if manual.state_fingerprint(active["model"])!=p["origin"]["core_sha256"]:raise ValueError("original model differs")
                c=configs["DELTA_SCOPE"];engine=runtime.RoutedEdit(active,c["model"],c["threshold"],packet,budget)
                writer=ShardWriter(OUT,"answers",limit=2_000_000)
                for index,q in enumerate(p["questions"]):
                    observation=engine.capture(q,max_new=p["max_new"])
                    for arm in boundary.arm_order(index):
                        c=configs[arm]if arm in configs else configs["DELTA_SCOPE"]
                        engine.router=c["model"];engine.threshold=c["threshold"]
                        engine.feature_layer=c["feature_layer"];engine.feature_view=c["feature_view"]
                        forced=False if arm=="ORIGINAL"else True if arm=="GLOBAL"else None
                        answer,generation,routing=engine.emit(q,max_new=p["max_new"],observation=observation,forced=forced)
                        writer.append(dict(id="grammar:"+str(index),question=q,language="ko",arm=arm,
                            answer=answer,generation=generation,routing=routing,post_result_control=True,blind_final=False))
                manifest=writer.close(lineage=dict(model_core=p["origin"]["core_sha256"],source_profile=io.sha(PROFILE),no_reselection=True))
                if engine.counts["generated_replies"]!=32:raise RuntimeError("grammar-control count differs")
                if manual.state_fingerprint(active["model"])!=p["origin"]["core_sha256"]:raise RuntimeError("original core not restored")
                report.update(status="GRAMMAR_CONTROL_COMPLETE",answers_manifest=manifest,counts=dict(engine.counts),
                    original_core_restored=True,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
            finally:
                if engine is not None:engine.close()
                engine=None
        active=packet=None
    except BaseException as error:
        failure=str(error);report.update(status="GRAMMAR_CONTROL_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        if engine is not None:engine.close()
        active=engine=packet=None;gc.collect();cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None and failure is None:failure=str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;io.write_new(OUT/"report.json",report)
        print("[GRAMMAR_END]"+json.dumps({k:report.get(k)for k in ("status","wall_seconds","cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}),flush=True)
    if failure is not None:raise RuntimeError("preserved grammar-control failure: "+failure)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("phase",choices=("prepare","check","actual"));phase=ap.parse_args().phase
    if phase=="prepare":prepare()
    elif phase=="check":verify();print("[GRAMMAR_CHECK]exact new control;model0",flush=True)
    else:actual()


if __name__=="__main__":main()
