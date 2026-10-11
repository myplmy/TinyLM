#!/usr/bin/env python3
"""User-only parent/shared/r64 prompt x decoder attribution; no weight updates."""
from __future__ import annotations
from contextlib import nullcontext
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p093b_native_repair as old
from scripts import diag_p093b_calibration_recovery as recovery
from scripts import p093b_generation_probe as probe
from scripts.p106b_shards import ShardWriter,verify

BASE=ROOT/"test_result/evidence/p093b_recovery_v2_s1337/recovery_capacity_b"
REPORT_SHA="4C8D5952F3803E98106A830CF0F446682AADC0F556CE1394C8D03033DC1C937F"
CODE=("scripts/diag_p093b_generation_attribution.py","scripts/p093b_generation_probe.py",
      "scripts/test_p093b_generation_probe.py","scripts/diag_p093b_native_repair.py",
      "scripts/p093b_native_repair.py","tinylm/infer/generate.py","tinylm/model/modules.py",
      "tinylm/model/ternary.py","tinylm/model/transformer.py","tinylm/config.py")

def output(tag,mode):return old.directory(tag,"generation_"+mode)

def metadata(a):
    return {"schema":probe.VERSION,"mode":a.mode,"tag":a.tag,
        "code_sha256":{n:old.digest(ROOT/n) for n in CODE},"source_recovery_report_sha256":REPORT_SHA,
        "max_new":96,"new_generations":0 if a.mode=="representation" else 192,"reused_plain_greedy_answers":24,
        "subjects":["parent","shared","rank64"],"prompt_types":["plain","fewshot"],
        "decoder_types":["greedy","nucleus_p095_t1"],"nucleus_seeds":[17,29,43],
        "model_loading":"NOT_RUN","optimizer_updates":0,"checkpoint_writes":0,"quality":"PENDING_GPT_REVIEW"}

def original_answers(role):
    p=BASE/("actual_answers_"+role+"_shards_manifest.json")
    m=json.loads(p.read_text());verify(BASE,m)
    rows=[json.loads(line) for part in m["shards"] for line in (BASE/part["path"]).read_text().splitlines()]
    if len(rows)!=8 or [r["id"] for r in rows]!=[i for i,p in recovery.PROBES]:
        raise ValueError("exact prior8 questions required")
    return rows,old.digest(p)

def source():
    if not old.regular(BASE/"report.json") or old.digest(BASE/"report.json")!=REPORT_SHA:
        raise FileNotFoundError("exact saved capacity report absent/stale")
    report=json.loads((BASE/"report.json").read_text())
    if report.get("status")!="RECOVERY_CALIBRATION_COMPLETE":
        raise FileNotFoundError("capacity run incomplete")
    for name,sha in report["input"]["code_sha256"].items():
        if old.digest(ROOT/name)!=sha:raise ValueError("original recovery source changed: "+name)
    if not any(r["rank"]==64 for r in report["ranks"]):raise ValueError("saved rank64 absent")
    return report

def representation(a,info,directory):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts import p093b_native_repair as native
    from scripts.p106b_education_followup import ARMS
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    report=source();spec=ARMS["a"];tok_path=ROOT/spec["tokenizer"]
    if old.digest(old.PARENT)!=recovery.PARENT_SHA or old.digest(tok_path)!=spec["tok_sha"]:
        raise ValueError("parent/tokenizer identity differs")
    idle_before_gpu();start=time.perf_counter()
    model,cfg,device=load_model("dense",str(old.PARENT),"cuda")
    if cfg.n_layers!=16 or cfg.tie_mlp or cfg.n_modes!=1:raise ValueError("original geometry differs")
    info.update(model_loading="MEASURED",new_generations=0,parent_sha256=recovery.PARENT_SHA,
        tokenizer_sha256=spec["tok_sha"],return_hidden_scope="final RMS normalized hidden; head logits not computed")
    ids=report["input"]["group_layers"];originals=[model.layers[i].mlp[0] for i in ids]
    shared=native.shared_native(originals,cfg);adapters=old.load_adapters(BASE,"rank64",shared,cfg,report["input"])
    tok=Tokenizer.from_file(str(tok_path));rows=[]
    try:
        with torch.no_grad():
            for role in ("parent","shared","rank64"):
                saved,_=original_answers(role)
                context=nullcontext() if role=="parent" else native.patched_group(model,ids,shared,
                    adapters if role=="rank64" else None)
                with context:
                    for record in saved:
                        for kind,text in (("prompt",record["prompt"]),("prompt_with_saved_answer",record["prompt"]+record["answer"])):
                            encoded=tok.encode(text)
                            if not 2<=len(encoded.ids)<=min(256,cfg.max_seq_len):raise ValueError("bounded representation positions required; no silent crop")
                            tokens=torch.tensor([encoded.ids],device=device,dtype=torch.long)
                            with torch.autocast("cuda",dtype=torch.bfloat16):
                                hidden=model(tokens,return_hidden=True)[0]
                            row={"subject":role,"id":record["id"],"kind":kind,
                                "input_text":text,"token_ids":encoded.ids,
                                "statistics":probe.representation_stats(hidden,encoded.ids),"new_answer_generated":False}
                            rows.append(row);print("[REPRESENTATION_OBSERVATION] "+json.dumps(row),flush=True)
    finally:
        old.write(directory/"partial.json",{"input":info,"observations":rows,"optimizer_updates":0,"checkpoint_writes":0})
    return {"input":info,"status":"REPRESENTATION_OBSERVATION_COMPLETE","observations":rows,
        "whole_wall_sec":time.perf_counter()-start,"new_generations":0,"optimizer_updates":0,
        "causality":"48 saved-text forwards, not proof that anisotropy causes repetition; same-token reuse separated"},0

def execute(a,info,directory):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model,sample
    from scripts import p093b_native_repair as native
    from scripts.p106b_education_followup import ARMS
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    report=source();spec=ARMS["a"];tok_path=ROOT/spec["tokenizer"]
    if old.digest(old.PARENT)!=recovery.PARENT_SHA or old.digest(tok_path)!=spec["tok_sha"]:
        raise ValueError("parent/tokenizer identity differs")
    idle_before_gpu();start=time.perf_counter()
    with torch.no_grad():model,cfg,device=load_model("dense",str(old.PARENT),"cuda")
    info.update(model_loading="MEASURED",parent_sha256=recovery.PARENT_SHA,tokenizer_sha256=spec["tok_sha"])
    if cfg.n_layers!=16 or cfg.tie_mlp or cfg.n_modes!=1:raise ValueError("original geometry differs")
    ids=report["input"]["group_layers"];originals=[model.layers[i].mlp[0] for i in ids]
    shared=native.shared_native(originals,cfg)
    adapters=old.load_adapters(BASE,"rank64",shared,cfg,report["input"])
    tok=Tokenizer.from_file(str(tok_path));writer=ShardWriter(directory,"answers");counts={"reused":0,"new":0}
    references={};parity=[];deadline=time.monotonic()+a.max_wall_sec
    try:
        with wall_limit(a.max_wall_sec),torch.no_grad():
            for role in ("parent","shared","rank64"):
                saved,sha=original_answers(role);references[role]=sha
                for row in saved:
                    writer.append(dict(row,subject=role,prompt_kind="plain",decoder="greedy",
                        evidence_origin="REUSED_IMMUTABLE_RESULT",new_model_generation=False))
                    counts["reused"]+=1
                context=nullcontext() if role=="parent" else native.patched_group(model,ids,shared,
                    adapters if role=="rank64" else None)
                with context:
                    for row in saved:
                        decoded,meta=sample(model,cfg,tok,row["prompt"],max_new=96,temperature=0,top_k=1,
                            device=device,use_cache=False,logits_last_only=True,return_metadata=True)
                        prefix=tok.decode(tok.encode(row["prompt"]).ids)
                        if not decoded.startswith(prefix):raise ValueError("cache-off prompt extraction differs")
                        answer=decoded[len(prefix):]
                        matched=(answer==row["answer"] and all(meta.get(k)==row["generation"].get(k)
                            for k in ("finish_reason","generated_tokens")))
                        parity.append({"subject":role,"id":row["id"],"text_finish_count_match":matched})
                        writer.append({"subject":role,"id":row["id"],"prompt":row["prompt"],"answer":answer,
                            "prompt_kind":"plain","decoder":"greedy","use_cache":False,"generation":meta,
                            "new_model_generation":True,"semantic_quality":"PENDING_GPT_REVIEW"})
                        counts["new"]+=1
                    for kind in ("plain","fewshot"):
                        for decoder in ("greedy","nucleus"):
                            if kind=="plain" and decoder=="greedy":continue
                            seeds=(17,) if decoder=="greedy" else (17,29,43)
                            for seed in seeds:
                                for i,(ident,original) in enumerate(recovery.PROBES):
                                    if time.monotonic()>=deadline:raise TimeoutError("generation attribution wall budget")
                                    text=probe.prompt(ident,original,kind);torch.manual_seed(2026101100+seed+i)
                                    sampler=nullcontext() if decoder=="greedy" else probe.nucleus_scope(.95)
                                    with sampler:
                                        decoded,meta=sample(model,cfg,tok,text,max_new=96,
                                            temperature=0 if decoder=="greedy" else 1.,
                                            top_k=1 if decoder=="greedy" else cfg.vocab_size,
                                            device=device,logits_last_only=True,return_metadata=True)
                                    prefix=tok.decode(tok.encode(text).ids)
                                    if not decoded.startswith(prefix):raise ValueError("token/text prefix extraction differs")
                                    row={"subject":role,"id":ident,"prompt_kind":kind,"decoder":decoder,
                                        "seed":seed,"prompt":text,"answer":decoded[len(prefix):],
                                        "generation":meta,"new_model_generation":True,"semantic_quality":"PENDING_GPT_REVIEW"}
                                    writer.append(row);counts["new"]+=1
                                    print("[ATTRIBUTION_ACTUAL_ANSWER] "+json.dumps(row,ensure_ascii=False),flush=True)
    finally:
        manifest=writer.close(lineage=info);verify(directory,manifest)
        old.write(directory/"partial.json",{"input":info,"counts":counts,"source_manifests_sha256":references,
            "answers":manifest,"cache_text_finish_count_pairs":parity,"checkpoint_writes":0})
    ready=counts=={"reused":24,"new":192}
    cache_match=len(parity)==24 and all(r["text_finish_count_match"] for r in parity)
    return {"input":info,"status":"GENERATION_ATTRIBUTION_COMPLETE" if ready else "INCOMPLETE",
        "counts":counts,"source_manifests_sha256":references,"answers":manifest,
        "cache_text_finish_count_pairs":parity,"cache_text_finish_count_match":cache_match,
        "cache_scope":"24 greedy text/finish/count pairs; not bitwise logits or all tokenizer-ID equivalence",
        "whole_wall_sec":time.perf_counter()-start,"optimizer_updates":0,"checkpoint_writes":0,
        "causality":"prompt/decoder attribution only; repetition reduction is not new learned intelligence"},0 if ready and cache_match else 8

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--mode",choices=("contract","decode","representation"),required=True)
    p.add_argument("--tag",default="p093b_generation_v1_s1337");p.add_argument("--max-wall-sec",type=int,default=1800)
    p.add_argument("--execute",action="store_true");p.add_argument("--check-only",action="store_true");a=p.parse_args()
    if not 60<=a.max_wall_sec<=1800:p.error("wall60..1800 required")
    info=metadata(a);directory=output(a.tag,a.mode)
    if a.check_only or not a.execute:print("[PREFLIGHT] "+json.dumps(info));return 0
    if directory.exists():print("[HOLD] preserve evidence");return 8
    directory.mkdir(parents=True)
    try:
        if a.mode=="contract":
            r=subprocess.run([sys.executable,"-B","-X","utf8","-m","unittest","scripts.test_p093b_generation_probe","-v"],cwd=ROOT,timeout=600)
            if r.returncode:raise ValueError("CPU generation contract failed")
            result={"input":info,"status":"CPU_CONTRACT_PASS"};rc=0
        else:
            contract=json.loads((output(a.tag,"contract")/"report.json").read_text())
            if contract.get("status")!="CPU_CONTRACT_PASS" or contract["input"]["code_sha256"]!=info["code_sha256"]:
                raise FileNotFoundError("current CPU contract required")
            if a.mode=="representation":
                from scripts.p106b_gate_runtime import wall_limit
                with wall_limit(min(600,a.max_wall_sec)):
                    result,rc=representation(a,info,directory)
            else:result,rc=execute(a,info,directory)
    except BaseException as e:
        rc=130 if isinstance(e,KeyboardInterrupt) else 8 if isinstance(e,(FileNotFoundError,FileExistsError)) else 9
        result={"input":info,"status":"INTERRUPTED" if rc==130 else "PREREQUISITE_HOLD" if rc==8 else "TOOL_FAILURE",
                "error_type":type(e).__name__,"reason":str(e),"optimizer_updates":0,"checkpoint_writes":0}
    old.write(directory/"report.json",result)
    print("[EXPERIMENT_FINAL] "+json.dumps({"mode":a.mode,"status":result["status"],"exit_code":rc,
        "new_model_generation":info["model_loading"],"optimizer_updates":0}));return rc

if __name__=="__main__":raise SystemExit(main())
