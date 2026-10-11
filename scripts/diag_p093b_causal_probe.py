#!/usr/bin/env python3
"""P093B controlled repetition-history, MLP, activation and precision interventions."""
from __future__ import annotations
import argparse
from contextlib import nullcontext, contextmanager
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p093b_generation_attribution as saved
from scripts import diag_p093b_native_repair as old
from scripts import diag_p093b_live_trace as live

TAG="p093b_causal_v1_s1337"
LIVE=ROOT/"test_result/evidence/p093b_live_trace_v1_s1337/live_trace"
LIVE_SHA="D50DF5EF024D02A41FE18F3CF5E699C3306224201C225341F5DA46CD114EA98A"
CODE=("scripts/diag_p093b_causal_probe.py","scripts/p093b_causal_probe.py",
      "scripts/test_p093b_causal_probe.py",*live.CODE)
TRAIN=ROOT/"runs/logs/m100s12_ko-en_300M_d16_cla2_norecur_rms4.json"
TRAIN_SHA="C3256FD47A7CC3F6F848B58240A8424B04A962E3476518C0DAFECC5930F11243"


def directory(tag, mode):
    return old.directory(tag,"causal_"+mode)


@contextmanager
def budget(seconds):
    previous=signal.getsignal(signal.SIGALRM)
    def alarm(*_):
        raise TimeoutError("owned causal diagnostic budget expired; partial preserved")
    signal.signal(signal.SIGALRM,alarm)
    signal.setitimer(signal.ITIMER_REAL,seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)


def source_rows():
    from scripts.p106b_shards import verify
    if old.digest(LIVE/"report.json")!=LIVE_SHA:
        raise ValueError("exact prior completed native trace differs")
    source=json.loads((LIVE/"report.json").read_text())
    if source.get("completed_native_sequences")!=24:
        raise ValueError("actual24 native answers required")
    verify(LIVE,source["answer_manifest"])
    rows=[json.loads(line) for sh in source["answer_manifest"]["shards"]
          for line in (LIVE/sh["path"]).open(encoding="utf-8")]
    return rows


def cases(rows,tok):
    mapping={(r["subject"],r["id"]):r for r in rows}
    result=[]
    specs=(("question_copy","parent","ko_context"),("single_word","shared","ko_context"),
           ("numbered_listing","rank64","ko_math"),("english_question","parent","en_math"))
    for ident,subject,question in specs:
        row=mapping[(subject,question)]
        ids=row["generated_token_ids"]
        prompt=tok.encode(row["prompt"]).ids
        if ident=="numbered_listing":
            if len(ids)<72 or any(ids[i*9:(i+1)*9][:3]!=ids[:3] for i in range(8)):
                raise ValueError("exact existing9-token varying-number listing required")
            leading=[]; block=ids[:9]; first=0
            bodies={n:ids[:9*n] for n in (1,3,8)}
        else:
            event=min(row["loop_candidates"],key=lambda e:(e["onset_token"],e["period"]))
            first=event["first_block_token"]-1
            leading=ids[:first]; block=event["block_ids"]
            bodies={n:block*n for n in (1,3,8)}
            if ids[first:first+3*len(block)]!=block*3:
                raise ValueError("exact block source differs")
        result.append({"case":ident,"source_subject":subject,"question_id":question,
            "question":row["prompt"],"anchor":prompt+leading,"bodies":bodies,
            "focus":block[0],"block":block,"source_first_token":first+1})
    return result


def execute(info,out,args):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model,sample
    from scripts import p093b_causal_probe as core
    from scripts import p093b_native_repair as native
    from scripts import diag_p093b_calibration_recovery as recovery
    from scripts.p106b_education_followup import ARMS
    from scripts.p106b_gate_runtime import idle_before_gpu
    from scripts.p106b_shards import ShardWriter,verify
    from scripts.p093b_live_trace import pair_change
    start=time.perf_counter()
    source=saved.source(); info["factor_pin"]=live.verify_factor_pin(source)
    spec=ARMS["a"]; tokpath=ROOT/spec["tokenizer"]
    if old.digest(old.PARENT)!=recovery.PARENT_SHA or old.digest(tokpath)!=spec["tok_sha"]:
        raise ValueError("exact parent/tokenizer changed")
    if old.digest(TRAIN)!=TRAIN_SHA:
        raise ValueError("exact training metadata changed")
    train=json.loads(TRAIN.read_text())
    info["training_metadata"]={k:train.get(k) for k in
        ("arch","n_layers","train_repeat","repeat_mode","reuse_attn_on_dup","init_from","init_from_src","tokens")}
    initializer=ROOT/"runs/logs/m100_ko-en_300M_dense.json"
    if old.regular(initializer):
        d=json.loads(initializer.read_text())
        info["initializer_metadata"]={"sha256":old.digest(initializer),**{k:d.get(k) for k in
            ("arch","train_repeat","n_layers","init_from","init_from_src","tokens")}}
    idle_before_gpu()
    model,cfg,device=load_model("dense",str(old.PARENT),"cuda")
    if cfg.n_layers!=16 or cfg.tie_mlp or cfg.n_modes!=1 or cfg.train_repeat!=1. or cfg.wq_dtype!="fp32" or model.visit_schedule()!=list(range(16)):
        raise ValueError("pinned independent-MLP single-visit R1-trained parent required")
    info.update(model_loading="MEASURED",parent_sha256=recovery.PARENT_SHA,tokenizer_sha256=spec["tok_sha"],
        cfg={k:getattr(cfg,k) for k in ("train_repeat","infer_repeat","repeat_mode","repeat_where",
        "reuse_attn_on_dup","repeat_kv_reuse","tie_mlp","cla_group","n_modes","n_middle","n_prelude","n_coda")},
        native_visit_schedule=model.visit_schedule(),
        bf16_reduced_precision_reduction=torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction)
    group=source["input"]["group_layers"]
    originals=[model.layers[i].mlp[0] for i in group]
    original_refs=[id(m) for m in originals]
    shared=native.shared_native(originals,cfg)
    adapters=old.load_adapters(saved.BASE,"rank64",shared,cfg,source["input"])
    tok=Tokenizer.from_file(str(tokpath)); eos=tok.token_to_id("<eos>")
    rows=source_rows(); panel=cases(rows,tok)
    writer=ShardWriter(out,"causal_rows")
    summaries=[]; noop_diffs=[]; actual_generations=0
    def append(row):
        writer.append(row)
        brief={k:v for k,v in row.items() if k not in ("capture_vectors","states","input_ids")}
        if row["kind"] in ("BASELINE","NATIVE_SAMPLE","PRECISION_PAIR"):
            print("[CAUSAL_RESULT] "+json.dumps(brief,ensure_ascii=False),flush=True)
    try:
        with torch.no_grad():
            for subject in ("parent","shared","rank64"):
                context=nullcontext() if subject=="parent" else native.patched_group(
                    model,group,shared,adapters if subject=="rank64" else None)
                with context:
                    for case in panel:
                        baselines={}
                        for n in (1,3,8):
                            body=case["bodies"][n]
                            prefixes=core.history_controls(case["anchor"],body,seed=1337+n)
                            for variant,prefix in prefixes.items():
                                if len(prefix)>256: raise ValueError("bounded no-crop prefix required")
                                x,states,visits=core.controlled_forward(model,prefix)
                                metrics=core.output_metrics(x,case["focus"],eos,tok.decode)
                                baselines[(n,variant)]=(metrics,states,prefix)
                                row={"kind":"BASELINE","subject":subject,"case":case["case"],
                                    "question":case["question"],"repetitions_or_chunks":n,"variant":variant,
                                    "prefix_tokens":len(prefix),"input_ids":prefix,"prefix_text":tok.decode(prefix),
                                    "last_token_id":prefix[-1],"actual_visits":visits,"metrics":metrics,
                                    "order_control_identical":prefixes["observed"]==prefixes["order_shuffle"],
                                    "causal_scope":"history intervention; controls may change syntax/meaning and are not guaranteed in-distribution"}
                                if n==8:
                                    row["capture_vectors"]={str(i):states[(i,0)].tolist() for i in range(16)}
                                append(row)
                        receiver,state_receiver,prefix=baselines[(8,"observed")]
                        no_op,_,_=core.controlled_forward(model,prefix,
                            patches={i:state_receiver[(i,0)] for i in range(16)})
                        ref,_,_=core.controlled_forward(model,prefix)
                        difference=float((no_op-ref).abs().max()); noop_diffs.append(difference)
                        append({"kind":"NOOP_PATCH","subject":subject,"case":case["case"],"max_abs":difference})
                        for donor_name in ("order_shuffle","prompt_cycle"):
                            donor,states_donor,_=baselines[(8,donor_name)]
                            for layer in range(16):
                                x,_,_=core.controlled_forward(model,prefix,patches={layer:states_donor[(layer,0)]})
                                metric=core.output_metrics(x,case["focus"],eos,tok.decode)
                                append({"kind":"ACTIVATION_PATCH","subject":subject,"case":case["case"],
                                    "donor":donor_name,"layer":layer,"position":"last same token in same-length prefix",
                                    "metrics":metric,"effect":core.patch_effect(metric,receiver,donor)})
                        for n in (1,8):
                            prefix=baselines[(n,"observed")][2]
                            with core.recurrence(model,2.):
                                x,_,visits=core.controlled_forward(model,prefix)
                                append({"kind":"INFERENCE_R2_ON_R1_TRAINED","subject":subject,"case":case["case"],
                                    "chunks":n,"actual_visits":visits,
                                    "metrics":core.output_metrics(x,case["focus"],eos,tok.decode),
                                    "training_distribution_mismatch":True})
                        summaries.append({"subject":subject,"case":case["case"],
                            "baselines":[{"chunks":n,"variant":v,"metrics":b[0]} for (n,v),b in baselines.items()]})
                    targets={"shared":{"ko_reason":[36,39,58],"en_reason":[6]},
                             "rank64":{"ko_reason":[14,30]}}.get(subject,{})
                    for q,steps in targets.items():
                        row=next(r for r in rows if r["subject"]==subject and r["id"]==q)
                        for mode in ("bf16_auto","bf16_math","fp32_math"):
                            pairs=core.cache_prefix_pairs(model,tok.encode(row["prompt"]).ids,
                                row["generated_token_ids"],steps,mode=mode)
                            for pair in pairs:
                                append({"kind":"PRECISION_PAIR","subject":subject,"question_id":q,"step":pair["step"],
                                    "profile":mode,"cached_id":pair["cached_id"],"uncached_id":pair["uncached_id"],
                                    "original_native_id":row["generated_token_ids"][pair["step"]-1],
                                    "argmax_match":pair["cached_id"]==pair["uncached_id"],"max_abs":pair["max_abs"],"rms":pair["rms"],
                                    "cached":core.output_metrics(pair["cached"],row["generated_token_ids"][pair["step"]-1],eos,tok.decode),
                                    "uncached":core.output_metrics(pair["uncached"],row["generated_token_ids"][pair["step"]-1],eos,tok.decode)})
                    for q in sorted({c["question_id"] for c in panel}):
                        row=next(r for r in rows if r["subject"]==subject and r["id"]==q)
                        for repeat in (1.,2.):
                            with core.recurrence(model,repeat):
                                text,gen=sample(model,cfg,tok,row["prompt"],max_new=16,temperature=0,top_k=1,
                                    device=device,logits_last_only=True,return_metadata=True)
                                schedule=model.visit_schedule()
                            actual_generations+=1
                            expected=tok.decode(tok.encode(row["prompt"]).ids+row["generated_token_ids"][:16])
                            append({"kind":"NATIVE_SAMPLE","subject":subject,"question_id":q,"prompt":row["prompt"],
                                "repeat":repeat,"actual_visits":schedule,"decoded":text,"generation":gen,
                                "R1_prefix_text_match":text==expected if repeat==1. else None,
                                "training_distribution_mismatch":repeat==2.})
        restored=[id(model.layers[i].mlp[0]) for i in group]==original_refs and cfg.infer_repeat==1.
    finally:
        info["new_generations"]=actual_generations
        manifest=writer.close(lineage=info) if writer._total_rows else None
        if manifest: verify(out,manifest)
        old.write(out/"partial.json",{"input":info,"rows_manifest":manifest,"summaries":summaries,
            "new_generations":actual_generations,"optimizer_updates":0,"checkpoint_writes":0})
    if any(noop_diffs) or not restored:
        raise ValueError("same-state no-op or in-memory configuration restoration failed")
    return {"input":info,"status":"CAUSAL_MEASUREMENT_COMPLETE","rows_manifest":manifest,
        "summaries":summaries,"same_state_noop_max_abs":max(noop_diffs),"in_memory_restored":restored,
        "new_generations":actual_generations,"whole_wall_sec":time.perf_counter()-start,
        "optimizer_updates":0,"checkpoint_writes":0,
        "causal_scope":"controlled history/last-activation interventions and local MLP swaps; not unique cause or training-level proof"},0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("contract","intervene","readback"),required=True)
    p.add_argument("--tag",default=TAG);p.add_argument("--max-wall-sec",type=int,default=600)
    p.add_argument("--execute",action="store_true");p.add_argument("--check-only",action="store_true")
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=600:p.error("bounded60..600 seconds required")
    info={"schema":"P093B_CAUSAL_PROBE_V1","mode":args.mode,"tag":args.tag,
        "code_sha256":{n:old.digest(ROOT/n) for n in dict.fromkeys(CODE)},
        "live_source_sha256":LIVE_SHA,"model_loading":"NOT_RUN","new_generations":0,
        "optimizer_updates":0,"checkpoint_writes":0,"max_wall_sec":args.max_wall_sec,
        "planned_scope":"4 existing cases/3 unique questions x3MLP variants; history1/3/8 x3controls; last-layer patch16 x2donors; R1/R2 inference; 6cache prefixes x3precision"}
    if args.check_only or not args.execute:
        print("[PREFLIGHT] "+json.dumps(info));return 0
    out=directory(args.tag,args.mode)
    if out.exists(): print("[HOLD] old evidence preserved");return 8
    out.mkdir(parents=True)
    try:
        if args.mode=="contract":
            test=subprocess.run([sys.executable,"-B","-X","utf8","-m","unittest","scripts.test_p093b_causal_probe","-v"],cwd=ROOT,timeout=args.max_wall_sec)
            if test.returncode: raise ValueError("CPU causal contracts failed")
            result={"input":info,"status":"CPU_CONTRACT_PASS","new_generations":0};rc=0
        elif args.mode=="readback":
            path=directory(args.tag,"intervene")
            result=json.loads((path/"report.json").read_text())
            if result.get("status")!="CAUSAL_MEASUREMENT_COMPLETE" or result["input"]["code_sha256"]!=info["code_sha256"]:
                raise FileNotFoundError("complete same-code intervention required")
            from scripts.p106b_shards import verify
            verify(path,result["rows_manifest"])
            result={"input":info,"status":"CAUSAL_READBACK_COMPLETE","source_sha256":old.digest(path/"report.json"),
                "rows":result["rows_manifest"]["rows"],"new_generations":0};rc=0
        else:
            contract=json.loads((directory(args.tag,"contract")/"report.json").read_text())
            if contract.get("status")!="CPU_CONTRACT_PASS" or contract["input"]["code_sha256"]!=info["code_sha256"]:
                raise FileNotFoundError("fresh same-code CPU contract required")
            with budget(args.max_wall_sec): result,rc=execute(info,out,args)
    except BaseException as exc:
        rc=130 if isinstance(exc,KeyboardInterrupt) else 8 if isinstance(exc,(TimeoutError,FileNotFoundError,FileExistsError)) else 9
        result={"input":info,"status":"PARTIAL_OR_HOLD" if rc in (8,130) else "TOOL_FAILURE",
            "error_type":type(exc).__name__,"reason":str(exc),"new_generations":info["new_generations"]}
    old.write(out/"report.json",result)
    print("[EXPERIMENT_FINAL] "+json.dumps({"mode":args.mode,"status":result["status"],"exit_code":rc,
        "new_generations":result.get("new_generations",0),"optimizer_updates":0,"checkpoint_writes":0}))
    return rc


if __name__=="__main__":
    raise SystemExit(main())
