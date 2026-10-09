"""User-only matched-view SFT and Gemma2QA gates; no model in check-only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
MODES=("contract","prepare","fixed","views","readback","teacher")
CODE=("scripts/diag_p106d_views.py","scripts/p106d_views.py","scripts/p106d_teacher_views.py",
      "scripts/p106b_rule_views.py","scripts/train_sft_p090.py","scripts/p106b_education_followup.py",
      "scripts/test_p106d_views.py","scripts/test_p106d_teacher_views.py","scripts/test_p106d_driver.py")
SCHEMA="P106D_VIEW_GATE_V1"


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest().upper()


def paths(tag,mode):
    if not re.fullmatch(r"[a-z0-9_]+",tag): raise ValueError("safe new tag required")
    corpus=ROOT/"HF/sft_ready"/tag/"corpus"
    evidence=ROOT/"test_result/evidence"/tag/mode
    for path in (corpus,evidence):
        if any(p.is_symlink() for p in (path,*path.parents)): raise ValueError("linked output ancestor")
    return corpus,evidence


def write(path,value):
    body=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    if len(body.encode())>20_000_000: raise ValueError("report exceeds20MB")
    with path.open("x",encoding="utf-8") as f: f.write(body)


def info(args):
    if args.seed!=1337 or not 1<=args.max_wall_sec<=3600: raise ValueError("preregistered seed/wall budget required")
    return {"schema":SCHEMA,"mode":args.mode,"tag":args.tag,"seed":args.seed,
        "code_sha256":{p:digest(ROOT/p) for p in CODE},"max_wall_sec":args.max_wall_sec,
        "parent_spec":"scripts.p106b_education_followup.ARMS[b]","micro_bs":8,"accum":16,
        "grad_checkpoint":True,"compile":"default","lr":1e-4,"muon_lr":4e-4,
        "epochs":4,"optimizer_updates":8,"actual_data_tokens":"MEASURE_IN_MANIFEST",
        "max_padded_slots":8*8*16*1024,"model_loading":"NOT_RUN","student_intelligence":"NOT_ESTABLISHED"}


def read_report(path):
    if not path.is_file() or path.is_symlink(): raise FileNotFoundError("required current report absent")
    return json.loads(path.read_text(encoding="utf-8"))


def require_contract(args,metadata):
    report=read_report(paths(args.tag,"contract")[1]/"report.json")
    if report.get("status")!="CPU_CONTRACT_PASS" or report["input"]["code_sha256"]!=metadata["code_sha256"]:
        raise ValueError("CPU contract absent/stale")


def tokenizer():
    from tokenizers import Tokenizer
    from scripts.p106b_education_followup import ARMS
    spec=ARMS["b"]; path=ROOT/spec["tokenizer"]
    if not path.is_file() or path.is_symlink() or digest(path)!=spec["tok_sha"]: raise FileNotFoundError("pinned chat32 tokenizer absent/stale")
    return Tokenizer.from_file(str(path)),spec


def put_rows(directory,stem,rows,lineage):
    from scripts.p106b_shards import ShardWriter,verify
    writer=ShardWriter(directory,stem)
    for row in rows: writer.append(row)
    manifest=writer.close(lineage=lineage); verify(directory,manifest)
    return manifest


def get_rows(directory,stem):
    from scripts.p106b_shards import verify
    manifest=read_report(directory/(stem+"_shards_manifest.json")); verify(directory,manifest)
    rows=[]
    for part in manifest["shards"]:
        rows.extend(json.loads(line) for line in (directory/part["path"]).read_text(encoding="utf-8").splitlines())
    return rows,manifest


def prepare(args,metadata,corpus):
    from scripts.p106d_views import build,real_signature
    tok,spec=tokenizer()
    if corpus.exists(): raise FileExistsError("preserve old corpus namespace")
    corpus.mkdir(parents=True)
    started=time.perf_counter(); data=build(lambda row:real_signature(row,tok),seed=args.seed)
    report=data["report"]; lineage={"source":"code-owned procedural fixtures","root_definition_sha256":report["source_definition_sha256"],"tokenizer_sha256":spec["tok_sha"]}
    shards={"fixed_train":put_rows(corpus,"fixed_train",data["fixed"],lineage) if data["fixed"] else None}
    for epoch,rows in enumerate(data["epochs"],1):
        shards[f"view_train_{epoch:02d}"]=put_rows(corpus,f"view_train_{epoch:02d}",rows,lineage) if rows else None
    shards["val_probes"]=put_rows(corpus,"val_probes",data["probes"],lineage) if data["probes"] else None
    report.update(input=metadata,tokenizer_sha256=spec["tok_sha"],shards=shards,
        status="CORPUS_READY" if report["ready"] else "CORPUS_INCOMPLETE",wall_sec=time.perf_counter()-started)
    write(corpus/"report.json",report)
    return report,0 if report["ready"] else 8


def classify(answer,gold):
    # Only closed code-owned tasks. Not a list of allegedly wrong natural words.
    body=answer.strip()
    if gold.startswith("{"):
        try: return json.loads(body)==json.loads(gold)
        except (ValueError,TypeError): return False
    if gold.casefold() in ("true","false"): return body.casefold()==gold.casefold()
    if re.fullmatch(r"-?\d+",gold):
        return bool(re.fullmatch(r"[+-]?\d+",body)) and int(body)==int(gold)
    return body==gold


def probe_answers(base,cfg,tok,rows,directory,label):
    import torch
    from tinylm.infer.generate import sample
    from tinylm.chat.serialize import serialize
    from scripts.p106d_views import text_at
    from scripts.p106b_shards import ShardWriter,verify
    writer=ShardWriter(directory,"answers_"+label); passed=0
    base.eval()
    with torch.no_grad(): base.freeze_quant()
    stop=[tok.encode("<|im_end|>").ids]
    for i,row in enumerate(rows):
        prompt=serialize({"messages":row["messages"][:-1]},"chatml",add_generation_prompt=True)
        torch.manual_seed(2026100900+i)
        decoded,meta=sample(base,cfg,tok,prompt,max_new=64,temperature=0,top_k=1,device="cuda",
            logits_last_only=True,return_metadata=True,stop_token_sequences=stop)
        prefix=tok.decode(tok.encode(prompt).ids)
        if not decoded.startswith(prefix): raise ValueError("generation prompt extraction failed")
        answer=decoded[len(prefix):].split("<|im_end|>",1)[0]; gold=text_at(row,-1)
        ok=classify(answer,gold); passed+=int(ok)
        record={"label":label,"root":row["meta"]["root_concept_id"],"language":row["meta"]["language"],
            "prompt":prompt,"raw_decoded":decoded,"answer":answer,"gold":gold,"generation":meta,
            "closed_code_contract_pass":ok,"rubric":"closed procedural input only; not free QA correctness"}
        writer.append(record)
        print("[ACTUAL_ANSWER] "+json.dumps({"label":label,"question":text_at(row,-2),"answer":answer,"gold":gold,"pass":ok},ensure_ascii=False),flush=True)
    manifest=writer.close(lineage={"label":label,"questions":len(rows),"first_answer_only":True}); verify(directory,manifest)
    base.clear_quant()
    return {"questions":len(rows),"first_answer_pass":passed,"shards":manifest,"scope":"closed task subset, no intelligence claim"}


def native_probe_ce(base,cfg,spec,device):
    import numpy as np
    import torch
    import torch.nn.functional as F
    path=ROOT/spec["cache"]/"val.bin"
    if not path.is_file() or path.is_symlink(): raise FileNotFoundError("native comparison cache absent/linked")
    pool=np.memmap(path,dtype="<u2",mode="r")
    if len(pool)<1024: raise ValueError("native probe cache too short")
    windows=[np.array(pool[i*128:(i+1)*128],dtype=np.int64) for i in range(8)]
    base.eval()
    with torch.no_grad(): base.freeze_quant()
    values=[]
    with torch.no_grad():
        for window in windows:
            t=torch.tensor(window[None],dtype=torch.long,device=device); logits=base(t[:,:-1])
            values.append(float(F.cross_entropy(logits.float().reshape(-1,cfg.vocab_size),t[:,1:].reshape(-1))))
    base.clear_quant()
    return {"ce":sum(values)/len(values),"window_ce":values,"prediction_tokens":8*127,
        "source_scope":"first8 shared native-val windows; past leakage/knowledge generalization not resolved"}


def train(args,metadata,corpus,evidence):
    import dataclasses
    import torch
    from scripts.p106b_education_followup import load_student,arm_inputs
    from scripts.train_sft_p090 import encode_records,micro_groups,loss_sum
    from scripts.p106b_gate_runtime import idle_before_gpu
    report=read_report(corpus/"report.json")
    if (not report.get("ready") or report.get("train_rows")!=256 or report["input"]["code_sha256"]!=metadata["code_sha256"]):
        raise FileNotFoundError("matched256 corpus absent/incomplete/stale; no student loaded")
    tok,spec=tokenizer(); fixed,_=get_rows(corpus,"fixed_train"); probes,_=get_rows(corpus,"val_probes")
    if report.get("tokenizer_sha256")!=spec["tok_sha"]:
        raise ValueError("corpus tokenizer identity differs from parent")
    views=[get_rows(corpus,f"view_train_{epoch:02d}")[0] for epoch in range(1,5)]
    fixed_encoded=encode_records(fixed,tok,1024,32768); encoded_views=[encode_records(rows,tok,1024,32768) for rows in views]
    sig=[(len(x),count) for x,y,count in fixed_encoded]
    if any([(len(x),count) for x,y,count in rows]!=sig for rows in encoded_views): raise ValueError("live tokenizer slot x/target mismatch")
    stem="m100s10_ko-en_300M_dense_chat32_"+args.tag+"_"+args.mode
    checkpoint=ROOT/"runs/ckpt"/(stem+".pt")
    if checkpoint.exists() or checkpoint.is_symlink(): raise FileExistsError("fresh student output collision")
    verified=arm_inputs("b")
    idle_before_gpu(); deadline=time.monotonic()+args.max_wall_sec
    torch,model,base,cfg,tok,adam,muon=load_student("b",training=True)
    metadata.update(model_loading="MEASURED",parent_sha256=verified["sha"],tokenizer_sha256=verified["tok_sha"])
    parent_answers=probe_answers(base,cfg,tok,probes,evidence,"parent")
    parent_native=native_probe_ce(base,cfg,spec,"cuda")
    pad=tok.token_to_id("<|pad|>") or 0; updates=processed=targets=0; history=[]
    grad_max=0.0; torch.cuda.reset_peak_memory_stats()
    for epoch in range(4):
        rows=fixed_encoded if args.mode=="fixed" else encoded_views[epoch]
        order=list(range(256)); random.Random(args.seed+epoch).shuffle(order)
        begin=time.perf_counter(); epoch_x=epoch_targets=0; base.train(); model.train()
        for groups in micro_groups(rows,order,8,16):
            if time.monotonic()>=deadline: raise TimeoutError("student gate wall budget")
            mass=sum(r[2] for micro in groups for r in micro)
            adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
            for micro in groups:
                (loss_sum(model,micro,pad,"cuda",cfg.vocab_size,2048)/mass).backward()
                epoch_x+=sum(len(r[0]) for r in micro); epoch_targets+=sum(r[2] for r in micro)
            grads=[p.grad for p in base.parameters() if p.grad is not None]
            if not grads or not all(torch.isfinite(g).all() for g in grads): raise ValueError("empty/nonfinite student gradients")
            grad_max=max(grad_max,max(float(g.abs().max()) for g in grads))
            torch.nn.utils.clip_grad_norm_(base.parameters(),1.0); adam.step(); muon.step(); updates+=1
        if epoch_x!=report["epoch_x_tokens"] or epoch_targets!=report["epoch_assistant_targets"]: raise ValueError("actual epoch exposure mismatch")
        processed+=epoch_x; targets+=epoch_targets
        history.append({"epoch":epoch+1,"updates":updates,"processed_tokens":epoch_x,"assistant_targets":epoch_targets,"wall_sec":time.perf_counter()-begin})
    if updates!=8: raise ValueError("optimizer count differs from preregistered8")
    child_answers=probe_answers(base,cfg,tok,probes,evidence,"child")
    child_native=native_probe_ce(base,cfg,spec,"cuda")
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    with checkpoint.open("xb") as f: torch.save({"cfg":dataclasses.asdict(cfg),"model":base.state_dict(),"step":updates,
        "epoch":4,"processed_tokens":processed,"tokenizer_sha256":spec["tok_sha"],"tokenizer_lineage":"chat32",
        "source_parent_sha256":spec["sha"],"data_report_sha256":digest(corpus/"report.json")},f)
    return {"schema":SCHEMA,"input":metadata,"status":"STUDENT_GATE_COMPLETE","arm":args.mode,
        "updates":updates,"processed_tokens":processed,"assistant_targets":targets,"grad_max":grad_max,"history":history,
        "parent_answers":parent_answers,"child_answers":child_answers,"parent_native":parent_native,"child_native":child_native,
        "checkpoint":str(checkpoint.relative_to(ROOT)),"checkpoint_sha256":digest(checkpoint),
        "local_peak_reserved_bytes":torch.cuda.max_memory_reserved(),"actual_quality":"REQUIRES_RESULT_ANALYSIS",
        "data_report_sha256":digest(corpus/"report.json")},0


def request_with_evidence(session,payload,append,generation_id,*,timeout):
    from urllib.error import HTTPError
    started=time.perf_counter()
    try:
        return session.request("/v1/chat/completions",payload,timeout=timeout)
    except HTTPError as error:
        raw=error.read(2_000_001); clipped=len(raw)>2_000_000
        body=raw[:2_000_000].decode("utf-8",errors="replace")
        body=body.replace(session.key,"[REDACTED]")
        append({"generation_id":generation_id,"request":payload,"http_status":error.code,
            "error_type":"HTTPError","error_body":body,"body_truncated":clipped,
            "request_wall_sec":time.perf_counter()-started,
            "captured_body_sha256":hashlib.sha256(raw).hexdigest().upper()})
        raise
    except Exception as error:
        append({"generation_id":generation_id,"request":payload,"error_type":type(error).__name__,
                "request_wall_sec":time.perf_counter()-started,"reason":str(error).replace(session.key,"[REDACTED]")})
        raise


def teacher_rates(rows):
    grouped={}
    for row in rows: grouped.setdefault((row["case"],row["condition"]),[]).append(row)
    complete={condition:{case for (case,c),items in grouped.items() if c==condition
        and len(items)==(2 if condition=="single" else 1)
        and all(r["status"]=="QA_VIEWS_WIRE_COMPLETE" for r in items)} for condition in ("single","paired")}
    common=complete["single"]&complete["paired"]
    output={"common_complete_sources":sorted(common),"scope":"all retry costs included; completion tokens are not student data"}
    for condition in ("single","paired"):
        selected=[r for r in rows if r["condition"]==condition]
        common_rows=[r for r in selected if r["case"] in common]
        def stats(items):
            seconds=sum(r["request_sum_sec_including_retries"] for r in items)
            x=sum(r["candidate_x_tokens"] for r in items)
            return {"request_sum_sec":seconds,"candidate_x_tokens":x,
                "candidate_assistant_targets":sum(r["candidate_targets"] for r in items),
                "completion_tokens":sum(r["completion_tokens_including_retries"] for r in items),
                "candidate_x_per_sec":x/seconds if seconds else None,"requests_with_retries":sum(r["attempts"] for r in items)}
        output[condition]={"all_sources":stats(selected),"same_completed_sources":stats(common_rows),
                           "complete_sources":len(complete[condition])}
    return output


def teacher(args,metadata,evidence):
    from scripts import p106d_teacher_views as wire
    from scripts import p106b_gemma_teacher as gemma
    from scripts.p106b_shards import ShardWriter,verify
    from scripts.p106d_views import real_signature
    from scripts.p106b_mtp_teacher import response_metrics
    from scripts.diag_p106_vram_sample import read_memory
    from scripts.diag_p106b_gemma_telemetry_resume import telemetry_scope
    from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
    from scripts.p106b_gate_runtime import idle_before_gpu
    tok,_=tokenizer(); assets=gemma.assets(True); idle_before_gpu()
    reader=RetryingMemoryReader(read_memory,emit=lambda line:print(line,flush=True))
    raw=ShardWriter(evidence,"teacher_raw"); saved=ShardWriter(evidence,"teacher_canonical")
    rows=[]; deadline=time.monotonic()+args.max_wall_sec
    counts={"raw":0,"candidate":0}
    raw_manifest=candidate_manifest=None
    def append_raw(record):
        raw.append(record); counts["raw"]+=1
    try:
        with telemetry_scope(reader),gemma.GemmaSession(mtp=False) as session:
            for i,case in enumerate(wire.cases()):
                conditions=("single","paired") if i%2==0 else ("paired","single")
                for condition in conditions:
                    for view_number in ((1,2) if condition=="single" else (1,)):
                        count=1 if condition=="single" else 2; result=None
                        generation=f"{case['id']}_{condition}_{view_number}"
                        total_request_sec=0.0; total_completion_tokens=0
                        for attempt in range(3):
                            if time.monotonic()>=deadline: raise TimeoutError("teacher QA-view wall budget")
                            request=wire.payload(case,count,args.seed+i*100+view_number+attempt,view_number=view_number)
                            if attempt:
                                request["messages"][0]["content"]+=" STRUCTURE RETRY: exact ordered start labels and copied QUESTION_1 literal required. Preserve source."
                            started=time.perf_counter(); reply=request_with_evidence(session,request,append_raw,generation,timeout=min(300,max(1,int(deadline-time.monotonic()))))
                            session.check(); elapsed=time.perf_counter()-started
                            result=wire.parse(reply,count,case,view_number=view_number); metrics=response_metrics(reply,elapsed)
                            total_request_sec+=elapsed; total_completion_tokens+=int(metrics.get("completion_tokens") or 0)
                            record={"generation_id":generation,"attempt":attempt+1,"condition":condition,"case":case,
                                "request":request,"reply":reply,"parsed":result,"metrics":metrics}
                            append_raw(record)
                            print("[TEACHER_VIEW] "+json.dumps({"id":generation,"attempt":attempt+1,"status":result["status"],
                                "pairs":result["pairs"],"wall_sec":elapsed,"semantic_truth":"NOT_REVIEWED"},ensure_ascii=False),flush=True)
                            if result["status"]=="QA_VIEWS_WIRE_COMPLETE": break
                        useful_x=useful_targets=0
                        if result["status"]=="QA_VIEWS_WIRE_COMPLETE":
                            pending=[]
                            for j,pair in enumerate(result["pairs"]):
                                row=wire.wrap(case,pair,group_id=case["id"],view_id=generation+f"_v{j+1}",teacher_sha=assets["model_sha256"])
                                try: x,t=real_signature(row,tok)
                                except ValueError:
                                    result["status"]="STUDENT_WIRE_INVALID"; pending=[]; break
                                useful_x+=x; useful_targets+=t; pending.append(row)
                            if pending:
                                for row in pending: saved.append(row); counts["candidate"]+=1
                            else: useful_x=useful_targets=0
                        rows.append({"case":case["id"],"condition":condition,"attempts":attempt+1,"status":result["status"],
                            "final_request_sec":elapsed,"completion_tokens":metrics.get("completion_tokens"),
                            "request_sum_sec_including_retries":total_request_sec,"completion_tokens_including_retries":total_completion_tokens,
                            "candidate_x_tokens":useful_x,"candidate_targets":useful_targets,"semantic_truth":"NOT_REVIEWED"})
    finally:
        if counts["raw"]:
            raw_manifest=raw.close(lineage={"schema":wire.VERSION,"assets":assets,"completion_scope":"may be partial"})
            verify(evidence,raw_manifest)
        if counts["candidate"]:
            candidate_manifest=saved.close(lineage={"schema":wire.VERSION,"semantic_truth":"NOT_REVIEWED"})
            verify(evidence,candidate_manifest)
        write(evidence/"teacher_partial.json",{"schema":SCHEMA,"input":metadata,
            "status":"PRESERVED_PARTIAL_JOURNAL","rows_completed":rows,
            "raw_manifest":raw_manifest,"candidate_manifest":candidate_manifest,
            "telemetry":reader.snapshot(),"quality":"NOT_REVIEWED"})
    accepted=sum(r["status"]=="QA_VIEWS_WIRE_COMPLETE" for r in rows)
    return {"schema":SCHEMA,"input":metadata,"status":"TEACHER_VIEWS_COMPLETE" if accepted==24 else "TEACHER_VIEWS_INCOMPLETE",
        "requests":rows,"rates":teacher_rates(rows),"raw_manifest":raw_manifest,"candidate_manifest":candidate_manifest,"telemetry":reader.snapshot(),
        "candidate_truth":"NOT_REVIEWED","speed_adoption":"NOT_ESTABLISHED"},0 if accepted==24 else 8


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--mode",choices=MODES,required=True)
    p.add_argument("--execute",action="store_true"); p.add_argument("--check-only",action="store_true")
    p.add_argument("--tag",default="p106d_ruleviews_v1_s1337"); p.add_argument("--seed",type=int,default=1337)
    p.add_argument("--max-wall-sec",type=int,default=None); a=p.parse_args()
    a.max_wall_sec=a.max_wall_sec or (1800 if a.mode in ("fixed","views") else 3600)
    if a.mode in ("fixed","views") and a.max_wall_sec>1800:
        raise ValueError("student diagnostic cap is1800 seconds")
    metadata=info(a); corpus,evidence=paths(a.tag,a.mode)
    if a.check_only or not a.execute:
        print("[PREFLIGHT] "+json.dumps(metadata,ensure_ascii=False)); print("[NOT_RUN] no source/tokenizer/model/GPU loaded; explicit execute required"); return 0
    if evidence.exists(): print("[PREREQUISITE_HOLD] preserve prior evidence, use new stage/tag"); return 8
    evidence.mkdir(parents=True)
    print("[PHASE] regression/preconditions then "+a.mode+"; readiness is separate from student intelligence",flush=True)
    try:
        if a.mode=="contract":
            modules=["scripts.test_p106b_rule_views","scripts.test_p106d_views","scripts.test_p106d_teacher_views","scripts.test_p106d_driver"]
            r=subprocess.run([sys.executable,"-B","-X","utf8","-m","unittest",*modules,"-v"],cwd=ROOT,timeout=600)
            if r.returncode: raise ValueError("CPU rule/view transport regression failed")
            report={"schema":SCHEMA,"input":metadata,"status":"CPU_CONTRACT_PASS","model_loading":"NOT_RUN"}; rc=0
        else:
            require_contract(a,metadata)
            if a.mode=="prepare": report,rc=prepare(a,metadata,corpus)
            elif a.mode in ("fixed","views"): report,rc=train(a,metadata,corpus,evidence)
            elif a.mode=="teacher": report,rc=teacher(a,metadata,evidence)
            else:
                rows=[read_report(paths(a.tag,m)[1]/"report.json") for m in ("fixed","views")]
                if any(r.get("status")!="STUDENT_GATE_COMPLETE" for r in rows): raise FileNotFoundError("two student arms not complete")
                for key in ("data_report_sha256","updates","processed_tokens","assistant_targets"):
                    if rows[0].get(key)!=rows[1].get(key): raise ValueError("matched student exposure differs: "+key)
                report={"schema":SCHEMA,"input":metadata,"status":"PAIR_READBACK_COMPLETE","arms":rows,"intelligence":"NOT_ESTABLISHED"}; rc=0
    except (FileNotFoundError,FileExistsError) as e:
        started=metadata.get("model_loading")=="MEASURED"
        report={"schema":SCHEMA,"input":metadata,"status":"TOOL_FAILURE" if started else "PREREQUISITE_HOLD",
                "reason":str(e),"model_loading":metadata.get("model_loading","NOT_RUN")}; rc=9 if started else 8
    except KeyboardInterrupt: report={"schema":SCHEMA,"input":metadata,"status":"INTERRUPTED"}; rc=130
    except Exception as e:
        report={"schema":SCHEMA,"input":metadata,"status":"TOOL_FAILURE","error_type":type(e).__name__,"reason":str(e)}; rc=9
    write(evidence/"report.json",report)
    print("[EXPERIMENT_FINAL] "+json.dumps({"mode":a.mode,"status":report["status"],"exit_code":rc,
        "evidence":str(evidence.relative_to(ROOT)),"student_intelligence":"NOT_ESTABLISHED"},ensure_ascii=False))
    return rc


if __name__=="__main__": raise SystemExit(main())
