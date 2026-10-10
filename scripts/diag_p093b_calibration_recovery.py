"""User-run P093B dev/precision recovery. No private/model IO in check-only."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p093b_native_repair as old
PARENT_SHA="A402BF1DC982134C762D116AC312B4338ECA2BAFD9545EE8CB16DBF4C67A4749"
TAG="p093b_recovery_v2_s1337"
MODES=("contract","tune_a","capacity_b","readback","precision")
CODE=("scripts/diag_p093b_calibration_recovery.py","scripts/p093b_calibration_recovery.py",
      "scripts/test_p093b_calibration_recovery.py","scripts/diag_p093b_native_repair.py",
      "scripts/p093b_native_repair.py","tinylm/model/modules.py","tinylm/model/ternary.py","tinylm/infer/generate.py")
PROBES=(
("ko_context","정보: 가=빨강, 나=파랑입니다.\n질문: 나의 색은 무엇입니까?\n답:"),
("en_context","Facts: A=red, B=blue.\nQuestion: What is the color of B?\nAnswer:"),
("ko_math","질문: 2 더하기 3은 얼마입니까?\n답:"),
("en_math","Question: What is 2 plus 3?\nAnswer:"),
("ko_literal","질문: 숫자 1만 출력하세요.\n답:"),
("en_literal","Question: Output only the number 1.\nAnswer:"),
("ko_reason","문장: 비가 오면 길이 젖습니다.\n질문: 길이 젖을 수 있는 이유를 간단히 설명하세요.\n답:"),
("en_reason","Sentence: Roads get wet when it rains.\nQuestion: Briefly explain why a road might be wet.\nAnswer:"))


def info(args):
    if args.seed!=1337 or not 1<=args.max_wall_sec<=3600: raise ValueError("preregistered seed/wall required")
    return {"schema":"P093B_RECOVERY_V2","mode":args.mode,"tag":args.tag,
        "parent":str(old.PARENT.relative_to(ROOT)),"parent_expected_sha256":PARENT_SHA,
        "source":str(old.POOL.relative_to(ROOT)),"seed":1337,"code_sha256":{p:old.digest(ROOT/p) for p in CODE},
        "model_loading":"NOT_RUN","full_training":"NOT_RUN","model_quality":"NOT_ESTABLISHED",
        "max_wall_sec":args.max_wall_sec,"lr_grid":[1e-3,1e-4],"checkpoints":[0,20,50,100,250],
        "selection":"DEV_ONLY per rank/LR; independent final test/CE/actual answers",
        "activation_positions_per_layer":{"train":2048,"dev":512,"test":512},"prompt_schema":"legacy plaintext QA; not ChatML"}


def directory(tag,mode): return old.directory(tag,"recovery_"+mode)


def require_contract(args,metadata):
    report=json.loads((directory(args.tag,"contract")/"report.json").read_text())
    if report.get("status")!="CPU_CONTRACT_PASS" or report["input"]["code_sha256"]!=metadata["code_sha256"]:
        raise ValueError("fresh exact recovery CPU contract required")


def actual_answers(model,cfg,tok,output,label,deadline=None):
    import torch
    from tinylm.infer.generate import sample
    from scripts.p106b_shards import ShardWriter,verify
    writer=ShardWriter(output,"actual_answers_"+label)
    with torch.no_grad():
        for i,(ident,prompt) in enumerate(PROBES):
            if deadline is not None and time.monotonic()>=deadline: raise TimeoutError("generation recovery wall budget")
            torch.manual_seed(2026101030+i)
            decoded,meta=sample(model,cfg,tok,prompt,max_new=96,temperature=0,top_k=1,
                device="cuda",logits_last_only=True,return_metadata=True)
            prefix=tok.decode(tok.encode(prompt).ids)
            if not decoded.startswith(prefix): raise ValueError("prompt extraction failed")
            record={"condition":label,"id":ident,"prompt":prompt,"decoded":decoded,"answer":decoded[len(prefix):],
                "generation":meta,"semantic_quality":"PENDING_GPT_REVIEW","scope":"8 diagnostics, not broad benchmark"}
            writer.append(record); print("[ACTUAL_ANSWER] "+json.dumps(record,ensure_ascii=False),flush=True)
    manifest=writer.close(lineage={"first_answer_only":True,"questions":8,"quality":"PENDING_GPT_REVIEW"});verify(output,manifest)
    return manifest


def load_observation(args,metadata):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.p106b_education_followup import ARMS
    from scripts.p106b_gate_runtime import idle_before_gpu
    spec=ARMS["a"]; token_path=ROOT/spec["tokenizer"]
    if not old.regular(old.PARENT) or not old.regular(old.POOL) or not old.regular(token_path):
        raise FileNotFoundError("pinned parent/source/tokenizer absent or linked")
    if old.digest(old.PARENT)!=PARENT_SHA or old.digest(token_path)!=spec["tok_sha"]:
        raise ValueError("pinned parent/tokenizer SHA differs")
    idle_before_gpu(); torch.manual_seed(args.seed)
    with torch.no_grad(): model,cfg,device=load_model("dense",str(old.PARENT),"cuda")
    metadata.update(model_loading="MEASURED",parent_sha256=PARENT_SHA,tokenizer_sha256=spec["tok_sha"])
    if cfg.n_layers!=16 or cfg.tie_mlp or cfg.cla_group!=2 or cfg.n_modes!=1:
        raise ValueError("native pinned geometry differs")
    ids=list(range(cfg.n_prelude,cfg.n_prelude+4))
    if any(getattr(model.layers[i],k,False) for i in ids for k in ("has_lora","has_film","has_lrm")):
        raise ValueError("additional adapters outside native restoration scope")
    windows,quality,source=old.input_windows(old.POOL,cfg.vocab_size,args.seed)
    groups={}
    for name,selection,count in (("train",windows[:16],2048),("dev",windows[16:20],512),("test",windows[20:24],512)):
        x,y=old.capture(model,ids,selection,count,device);groups[name]=(x,y)
        metadata[name+"_x_sha256"]=old.tensor_sha(x)
    metadata.update(source,group_layers=ids)
    originals=[model.layers[i].mlp[0] for i in ids]
    return torch,model,cfg,ids,originals,groups,quality,Tokenizer.from_file(str(token_path))


def execute(args,metadata,output):
    import torch
    from scripts import p093b_native_repair as native
    from scripts import p093b_calibration_recovery as recovery
    previous=None; eligible=None
    deadline=time.monotonic()+args.max_wall_sec
    if args.mode=="precision":
        previous=directory(args.tag,"capacity_b")
        prior=json.loads((previous/"report.json").read_text())
        if prior.get("status")!="RECOVERY_CALIBRATION_COMPLETE" or prior["input"]["code_sha256"]!=metadata["code_sha256"]:
            raise FileNotFoundError("current capacity-B report absent/incomplete/stale")
        eligible=[r for r in prior["ranks"] if r["local_viable"]]
        if not eligible: return {"input":metadata,"status":"PREREQUISITE_HOLD","reason":"no_viable_unquantized_capacity_rank","model_loading":"NOT_RUN"},8
    torch,model,cfg,ids,originals,groups,quality,tok=load_observation(args,metadata)
    shared=native.shared_native(originals,cfg); train_x,train_y=groups["train"];dev_x,dev_y=groups["dev"];test_x,test_y=groups["test"]
    baseline=native.measure(shared,test_x,test_y)
    parent_ce=old.ce_probe(model,quality,"cuda")
    parent_answers=actual_answers(model,cfg,tok,output,"parent",deadline)
    with native.patched_group(model,ids,shared):
        shared_ce=old.ce_probe(model,quality,"cuda")
        shared_answers=actual_answers(model,cfg,tok,output,"shared",deadline)
    torch.cuda.reset_peak_memory_stats()
    if args.mode=="precision":
        for key in ("parent_sha256","source_selected_sha256","train_x_sha256","dev_x_sha256","test_x_sha256"):
            if prior["input"].get(key)!=metadata.get(key): raise ValueError("capacity fingerprint differs: "+key)
        rows=[]
        for chosen in eligible:
            adapters=old.load_adapters(previous,chosen["artifact_stem"],shared,cfg,metadata)
            rounded=recovery.half_storage_roundtrip(adapters)
            quantized=[[native.GSQAdapter(a).eval().native_export() for a in row] for row in adapters]
            for name,payload in (("fp32_reference",adapters),("fp16_storage_roundtrip",rounded),("native_ternary_factors",quantized)):
                score=native.measure(shared,test_x,test_y,payload)
                with native.patched_group(model,ids,shared,payload):
                    ce=old.ce_probe(model,quality,"cuda");answers=actual_answers(model,cfg,tok,output,"r"+str(chosen["rank"])+"_"+name,deadline)
                rows.append({"rank":chosen["rank"],"name":name,"test":score,"ce":ce,"actual_answers":answers,
                    "local_viable":old.viable(score["nrms"],baseline["nrms"]),
                    "account":recovery.byte_account(payload),"resident_dtype":"FP32 even for FP16 storage round-trip"})
        return {"input":metadata,"status":"PRECISION_GATE_COMPLETE","variants":rows,
            "rank_selection":"all eligible capacity ranks; no lowest-test-score cherry-pick",
            "quality":"PENDING_GPT_REVIEW","packed_kernel_speed":"NOT_RUN","runtime_memory_saving":"NOT_ESTABLISHED"},0
    ranks=(8,16) if args.mode=="tune_a" else (32,64); records=[]
    for rank in ranks:
        torch.manual_seed(args.seed+rank)
        initial=native.residual_adapters(originals,shared,train_x,rank,cfg)
        trials=[];states=[]
        for lr in (1e-3,1e-4):
            adapters=copy.deepcopy(initial)
            trial,state=recovery.dev_fit(shared,adapters,train_x,train_y,dev_x,dev_y,lr=lr,deadline=deadline)
            trials.append(trial);states.append(state)
        best=recovery.select_trial(trials);adapters=copy.deepcopy(initial);recovery.restore(adapters,states[best])
        test=native.measure(shared,test_x,test_y,adapters)
        with native.patched_group(model,ids,shared,adapters):
            ce=old.ce_probe(model,quality,"cuda");answers=actual_answers(model,cfg,tok,output,"rank"+str(rank),deadline)
        stem="rank"+str(rank);artifact=old.save_candidate(output,stem,shared,adapters,metadata)
        record={"rank":rank,"lr_trials":trials,"selected_trial":best,"selected_lr":trials[best]["lr"],
            "selected_step":trials[best]["selected_step"],"selected_dev_nrms":trials[best]["selected_dev_nrms"],
            "test":test,"ce":ce,"actual_answers":answers,"local_viable":old.viable(test["nrms"],baseline["nrms"]),
            "artifact_stem":stem,"artifact":artifact,"factor_bytes":recovery.byte_account(adapters)}
        records.append(record);print("[ACTUAL_RECOVERY] "+json.dumps({k:v for k,v in record.items() if k not in ("artifact","lr_trials")},ensure_ascii=False),flush=True)
    return {"input":metadata,"status":"RECOVERY_CALIBRATION_COMPLETE","ranks":records,"shared_test":baseline,
        "parent_ce":parent_ce,"shared_ce":shared_ce,"parent_answers":parent_answers,"shared_answers":shared_answers,
        "local_peak_reserved_bytes":torch.cuda.max_memory_reserved(),"quality":"PENDING_GPT_REVIEW",
        "memory_scope":"parent reference retained; not deployed RSS"},0 if any(r["local_viable"] for r in records) else 8


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--mode",choices=MODES,required=True)
    p.add_argument("--tag",default=TAG);p.add_argument("--seed",type=int,default=1337)
    p.add_argument("--max-wall-sec",type=int,default=3600)
    p.add_argument("--execute",action="store_true");p.add_argument("--check-only",action="store_true");a=p.parse_args()
    metadata=info(a);output=directory(a.tag,a.mode)
    if a.check_only or not a.execute:
        print("[PREFLIGHT] "+json.dumps(metadata,ensure_ascii=False));print("[NOT_RUN] no parent/tokenizer/cache/model/GPU");return 0
    if output.exists():print("[PREREQUISITE_HOLD] preserve old evidence; use new namespace");return 8
    output.mkdir(parents=True)
    try:
        if a.mode=="contract":
            r=subprocess.run([sys.executable,"-B","-X","utf8","-m","unittest",
                "scripts.test_p093b_native_repair","scripts.test_p093b_calibration_recovery","-v"],cwd=ROOT,timeout=600)
            if r.returncode:raise ValueError("CPU operator recovery regression failed")
            report={"input":metadata,"status":"CPU_CONTRACT_PASS","model_loading":"NOT_RUN"};rc=0
        else:
            require_contract(a,metadata)
            if a.mode=="readback":
                rows=[json.loads((directory(a.tag,m)/"report.json").read_text()) for m in ("tune_a","capacity_b")]
                for key in ("parent_sha256","source_selected_sha256","train_x_sha256","dev_x_sha256","test_x_sha256","code_sha256"):
                    if rows[0]["input"].get(key)!=rows[1]["input"].get(key):raise ValueError("A/capacity fingerprint differs: "+key)
                if any(r.get("status")!="RECOVERY_CALIBRATION_COMPLETE" for r in rows):raise FileNotFoundError("two recovery arms not complete")
                report={"input":metadata,"status":"RECOVERY_PAIR_READBACK_COMPLETE","arms":rows,"real_answers":"PENDING_GPT_REVIEW"};rc=0
            else:report,rc=execute(a,metadata,output)
    except (FileNotFoundError,FileExistsError) as e:
        started=metadata.get("model_loading")=="MEASURED";rc=9 if started else 8
        report={"input":metadata,"status":"TOOL_FAILURE" if started else "PREREQUISITE_HOLD","reason":str(e)}
    except KeyboardInterrupt:report={"input":metadata,"status":"INTERRUPTED"};rc=130
    except Exception as e:report={"input":metadata,"status":"TOOL_FAILURE","error_type":type(e).__name__,"reason":str(e)};rc=9
    old.write(output/"report.json",report)
    print("[EXPERIMENT_FINAL] "+json.dumps({"mode":a.mode,"status":report["status"],"exit_code":rc,
        "evidence":str(output.relative_to(ROOT)),"actual_answer_review":"PENDING_GPT_REVIEW"},ensure_ascii=False));return rc

if __name__=="__main__":raise SystemExit(main())
