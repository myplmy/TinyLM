#!/usr/bin/env python3
"""완주한 새 CP의 고정12질문을 plain/ChatML로 각각 생성하는 별도 접점.

원 sample·prompt 계약과 strict_runtime를 재사용한다. 원답24개를 보존하며
종료·128도달은 정답 판정이 아니다. 실제 실행과 원답 판독은 총괄 소유다.
"""
from __future__ import annotations
import time
STARTED=time.monotonic()
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_native_format_official as official
from scripts import interactive_research_infer as interactive
from scripts.p106b_shards import ShardWriter,verify

training=official.training
supervisor=training.supervisor
Hold=training.Hold
SCHEMA="P106B_NATIVE_FORMAT_DIALOGUE_V1"
PROFILE="P106B_NATIVE_FORMAT_DIALOGUE_PROFILE_V1"
PREFIX="p106b_native_format_dialogue_v1_20261026_"
END=datetime(2026,10,26,8,tzinfo=timezone.utc)
TRAINING_SHA="9EA74842B672407044FB52B668B56EC8AD2C4390229409C7E12EE5F9B002F90C"
OFFICIAL_SHA="6E08116657927517C1A8FE6C616902DA2794996D3E6934AD21125E4F317BAA22"
CASES_REF=dict(path="handoff/audit/oct26_research/native_dialogue_cases_v1.json",
    sha256="EA3AE329D8774A54CF4E0D4BA37D692E135A3B2AA336F00548CDBEF97A23E321")
MODES=("plain","chatml")
CONTRACT=dict(master="FP32",compute="FP32",attention="SDPA_MATH",tf32=False,
    anneal=1.,freeze_quant=True,mtp=False,mtp_tokens=1,temperature=0.,top_k=1,
    max_new=128,use_cache=True,logits_last_only=True,stop_at_eos=True,eos_id=2,
    chatml_stop_ids=[4],plain_stop_ids=[],history=False,seed=1337,
    cases=12,requests=24,request_order="CASE_ORDER_THEN_PLAIN_CHATML",
    quantization_scope="TLINEAR_WEIGHTS_ONLY")
CODE=tuple(sorted(set((*official.CODE,*interactive.REQUIRED_SOURCES,
    "scripts/interactive_infer.py","tinylm/infer/dialogue.py",
    "scripts/diag_p106b_native_format_dialogue.py","scripts/test_p106b_native_format_dialogue.py"))))
require=training.require
canonical=training.canonical
sha=training.sha
safe=training.path


def source_identity(budget=None):
    files={name:official.digest(safe(name),budget) for name in CODE}
    return dict(files=files,sha256=sha(files))


def read_ref(ref,budget):
    safe(ref["path"])
    return official.read_ref(ref,budget)


def closed_train(profile,state,budget):
    spec=profile.get("closed_train")
    if not isinstance(spec,dict) or type(spec.get("actual_supervisor_exit")) is not int or spec["actual_supervisor_exit"] != 0:
        raise Hold("총괄이 회수한 실제 학습 부모 종료0이 아직 없다")
    parent=read_ref(spec,budget)
    child=parent.get("worker") or {}
    if (type(parent.get("returncode")) is not int or parent["returncode"] != 0
            or not training.supervision_ok(parent.get("supervision",{}))
            or child.get("status") != "TRAIN2289_COMPLETE" or type(child.get("updates")) is not int
            or child["updates"] != 2289 or child.get("totals") != dict(targets=300023808,x_tokens=300023808)):
        raise Hold("실제 전체2289·300023808과 자연 종결0이 없는 CP는 열지 않는다")
    report=training.read_closed(spec,state,profile["arm"],"train")
    child=report["worker"]
    require(child.get("synthetic") is False and child.get("scratch_core_sha256") == training.CORE
        and child.get("original_weights_copied") is False and isinstance(child.get("cfg"),dict)
        and child.get("quantization_route") == official.ROUTE
        and re.fullmatch("[0-9A-F]{64}",str(child.get("final_core_sha256",""))),
        "실제 새 CP의 fresh core·cfg·삼진 계보가 다르다")
    require(Path(child["checkpoint"]).parts[:2] == ("runs","ckpt")
        and len(Path(child["checkpoint"]).parts) == 3,"완주한 새 로컬 CP만 연다")
    return child


def metadata(args,budget):
    own=source_identity(budget)
    require(args.source_sha256 == own["sha256"],"현재 대화 source pin이 다르다")
    require(training.source_identity()["sha256"] == TRAINING_SHA
        and official.source_identity(budget)["sha256"] == OFFICIAL_SHA,"기존47/58 동결 source가 달라졌다")
    ref=dict(path=args.profile,sha256=args.profile_sha256)
    profile=read_ref(ref,budget)
    require(profile.get("schema") == PROFILE and profile.get("root_approved") is True
        and profile.get("source_sha256") == own["sha256"]
        and profile.get("training_source_sha256") == TRAINING_SHA
        and profile.get("official_source_sha256") == OFFICIAL_SHA
        and profile.get("cases") == CASES_REF and profile.get("generation_contract") == CONTRACT
        and profile.get("deadline") == END.isoformat()
        and type(profile.get("cleanup_reserve_sec")) is int and profile["cleanup_reserve_sec"] >= 120
        and type(profile.get("entry_free_mib")) is int and profile["entry_free_mib"] > 0,
        "동결12질문·고정128·현재 총괄 profile·17시 마감이 필요하다")
    cases=read_ref(CASES_REF,budget)
    require(isinstance(cases,list) and len(cases) == 12
        and len({case["id"] for case in cases}) == 12
        and all(set(case) == {"id","language","group","question"}
            and isinstance(case["id"],str) and re.fullmatch("[A-Za-z0-9_]+",case["id"])
            and case["language"] in ("ko","en")
            and case["group"] in ("USER_REPORTED_FAILURE","FIXED_GENERAL")
            and isinstance(case["question"],str) and case["question"].strip() for case in cases)
        and sum(case["group"] == "USER_REPORTED_FAILURE" for case in cases) == 6,
        "원형 사용자6문항과 일반6문항의 실제 순서·질문이 필요하다")
    train_args=SimpleNamespace(mode="train",profile=profile["training_profile"]["path"],
        profile_sha256=profile["training_profile"]["sha256"],f4=profile["training_f4"]["path"],
        f4_sha256=profile["training_f4"]["sha256"])
    train_state=training.metadata(train_args)
    require(train_state["source_identity"]["sha256"] == TRAINING_SHA,"완주 학습 source가 다르다")
    child=closed_train(profile,train_state,budget)
    budget.check("대화 원형·완주 CP 입장 후")
    return dict(profile=profile,profile_ref=ref,profile_sha256=args.profile_sha256,source_identity=own,
        cases=cases,training_args=train_args,training_state=train_state,train=child,train_spec=profile["closed_train"])


def immutable(state,budget):
    require(source_identity(budget) == state["source_identity"],"생성 중 source가 달라졌다")
    require(read_ref(state["profile_ref"],budget) == state["profile"]
        and read_ref(CASES_REF,budget) == state["cases"],"생성 중 profile 또는 질문이 달라졌다")
    current=training.metadata(state["training_args"])
    require(current == state["training_state"]
        and closed_train(state["profile"],current,budget) == state["train"],"생성 중 완주 원형이 달라졌다")
    budget.check("대화 원형 불변 검산 후")


def generation_tools():
    sample,capture,forward=interactive.generation_tools(ROOT)
    from tinylm.infer import dialogue
    return dialogue,sample,capture,forward


def emit(active,case,mode,budget,*,tools=None):
    dialogue,sample,capture_type,forward_type=generation_tools() if tools is None else tools
    torch,model,cfg,tok=active["torch"],active["model"],active["cfg"],active["tokenizer"]
    budget.check("요청 전")
    chosen,stops=dialogue.resolve_mode(tok,dict(vocab_size=cfg.vocab_size),mode)
    require(chosen == mode and stops == ([4] if mode == "chatml" else [])
        and tok.token_to_id("<eos>") == 2,"기존 plain/ChatML·EOS/EOT 계약이 다르다")
    prompt=dialogue.make_prompt(case["question"],mode)
    prefix=tok.encode(prompt).ids
    dialogue.validate_input_ids(prefix,cfg.vocab_size)
    require(len(prefix)+128 <= cfg.max_seq_len,"질문과128 생성이 문맥을 넘어서며 자동 절단하지 않는다")
    active["route"].assert_active()
    captured=capture_type(tok)
    torch.cuda.synchronize(); began=time.monotonic()
    with torch.no_grad():
        _,trace=sample(forward_type(model,"fp32_math"),cfg,captured,prompt,max_new=128,
            temperature=0.,top_k=1,device="cuda",use_cache=True,stop_at_eos=True,eos_id=2,
            logits_last_only=True,return_metadata=True,mtp_tokens=1,
            stop_token_sequences=[stops] if stops else None)
    torch.cuda.synchronize(); seconds=time.monotonic()-began
    budget.check("요청 생성 후")
    active["route"].assert_active()
    all_ids=captured.decoded_ids
    display=dialogue.answer_from_ids(tok,prefix,all_ids,trace.get("generated_tokens"))
    generated=all_ids[len(prefix):]
    raw=tok.decode(generated,skip_special_tokens=False)
    row=dict(case_id=case["id"],language=case["language"],group=case["group"],
        question=case["question"],mode=mode,prompt=prompt,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest().upper(),
        prompt_ids=prefix,prompt_ids_sha256=sha(prefix),all_ids=all_ids,generated_ids=generated,
        generated_ids_sha256=sha(generated),answer=raw,answer_sha256=hashlib.sha256(raw.encode()).hexdigest().upper(),
        display_answer=display,display_removes_all_special_tokens=True,trace=trace,
        max_new_reached=len(generated) == 128,stopped_at_length_cap=trace.get("finish_reason") == "MAX_NEW",
        generation_wall_sec=seconds,quality_claim=False,
        prompt_helper="tinylm.infer.dialogue.make_prompt",sampler="tinylm.infer.generate.sample",
        allocator=dict(allocated_mib=torch.cuda.memory_allocated()/2**20,
            reserved_mib=torch.cuda.memory_reserved()/2**20,
            peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))
    validate_record(row,case,mode)
    return row


def validate_record(row,case,mode):
    prefix,generated=row["prompt_ids"],row["generated_ids"]
    trace=row["trace"]; count=trace.get("generated_tokens"); reason=trace.get("finish_reason")
    require(row["case_id"] == case["id"] and row["language"] == case["language"] and row["group"] == case["group"]
        and row["question"] == case["question"] and row["mode"] == mode
        and row["prompt_helper"] == "tinylm.infer.dialogue.make_prompt"
        and row["sampler"] == "tinylm.infer.generate.sample" and row["quality_claim"] is False
        and row["display_removes_all_special_tokens"] is True,"실제 원질문·모드·원답 계보가 다르다")
    require(isinstance(row["prompt"],str) and row["prompt"] and (mode != "plain" or row["prompt"] == case["question"])
        and row["prompt_sha256"] == hashlib.sha256(row["prompt"].encode()).hexdigest().upper()
        and isinstance(prefix,list) and prefix and isinstance(generated,list)
        and all(type(v) is int and 0 <= v < 32768 for v in prefix+generated)
        and len(prefix)+128 <= 1024 and type(count) is int and 1 <= count <= 128 and len(generated) == count
        and row["all_ids"] == prefix+generated and row["prompt_ids_sha256"] == sha(prefix)
        and row["generated_ids_sha256"] == sha(generated)
        and isinstance(row["answer"],str) and isinstance(row["display_answer"],str)
        and row["answer_sha256"] == hashlib.sha256(row["answer"].encode()).hexdigest().upper(),
        "실제 prompt·생성 ID·원답 SHA와 문맥·길이가 다르다")
    require(trace.get("max_new") == 128 and trace.get("eos_token_available") is True
        and trace.get("stop_at_eos_requested") is True and trace.get("stop_at_eos_effective") is True
        and row["max_new_reached"] is (count == 128)
        and row["stopped_at_length_cap"] is (reason == "MAX_NEW")
        and training.finite_number(row["generation_wall_sec"],positive=True),"고정128·종료·실제 시간 기록이 다르다")
    stops=[[4]] if mode == "chatml" else None
    require(trace.get("stop_token_sequences") == stops,"모드별 기존 EOT 종료 설정이 다르다")
    if reason == "EOS":
        require(generated[-1] == 2 and trace.get("matched_stop_sequence") is None,"실제 EOS 종료 ID가 다르다")
    elif reason == "STOP_SEQUENCE":
        require(mode == "chatml" and generated[-1] == 4 and trace.get("matched_stop_sequence") == [4],
                "실제 ChatML EOT 종료 ID가 다르다")
    else:
        require(reason == "MAX_NEW" and count == 128 and trace.get("matched_stop_sequence") is None,
                "정의한 EOS/EOT/128 종료가 아니다")
    body=generated[:-1] if reason in ("EOS","STOP_SEQUENCE") else generated
    require(2 not in body and (mode != "chatml" or 4 not in body),"기존 sampler가 먼저 종료해야 할 ID가 본문에 있다")
    require(all(training.finite_number(v) for v in row["allocator"].values()),"allocator 수치가 비유한 값이다")


def validate_worker(child,state,directory,budget):
    require(child.get("schema") == SCHEMA and child.get("status") == "DIALOGUE24_COMPLETE"
        and child.get("source_sha256") == state["source_identity"]["sha256"]
        and child.get("profile_sha256") == state["profile_sha256"] and child.get("arm") == state["profile"]["arm"]
        and child.get("training_report_sha256") == state["train_spec"]["sha256"]
        and child.get("checkpoint_sha256") == state["train"]["checkpoint_sha256"]
        and child.get("contract") == CONTRACT and child.get("cases_ref") == CASES_REF
        and child.get("synthetic") is False and type(child.get("models_loaded")) is int and child["models_loaded"] == 1
        and type(child.get("optimizer_updates")) is int and child["optimizer_updates"] == 0
        and type(child.get("checkpoint_writes")) is int and child["checkpoint_writes"] == 0
        and type(child.get("requests")) is int and child["requests"] == 24 and child.get("quality_claim") is False,
        "24요청의 실제 무학습 생성 원형이 다르다")
    proof=child["model_proof"]
    require(proof["cpu_and_gpu_core_sha256"] == proof["final_core_sha256"] == state["train"]["final_core_sha256"]
        and proof["checkpoint_sha256"] == child["checkpoint_sha256"]
        and proof["cfg"] == state["train"]["cfg"] and proof["contract"] == official.CONTRACT
        and proof["scratch_core_sha256"] == training.CORE
        and proof["cpu_key_shape_dtype_layout_alias_verified"] is True
        and proof["all_checkpoint_floats_finite"] is True and proof["updates"] == 2289 and proof["targets"] == 300023808,
        "strict CP load와 생성 전후 본체 불변 증거가 다르다")
    official.validate_route_receipt(proof["route"]); official.validate_route_receipt(proof["final_route"])
    actual=list(official.manifests_rows(directory/"answers",child["answers_manifest"],budget))
    expected=[(case,mode) for case in state["cases"] for mode in MODES]
    require(len(actual) == len(expected) == 24,"실제24답의 순서 또는 분모가 다르다")
    for row,(case,mode) in zip(actual,expected): validate_record(row,case,mode)
    require(child["memory"]["samples"] > 0 and child["memory"]["continuous_peak_verified"] is False,
            "실제 표본 메모리와 누락 명세가 필요하다")
    return child


def execute_worker(args,state,budget):
    immutable(state,budget)
    writer=ShardWriter(args.output/"answers","answers",limit=19_999_999)
    primary=None
    child=dict(schema=SCHEMA,source_sha256=state["source_identity"]["sha256"],
        profile_sha256=state["profile_sha256"],arm=state["profile"]["arm"],
        training_report_sha256=state["train_spec"]["sha256"],checkpoint_sha256=state["train"]["checkpoint_sha256"],
        contract=CONTRACT,cases_ref=CASES_REF,synthetic=False,models_loaded=1,
        optimizer_updates=0,checkpoint_writes=0,quality_claim=False,requests=0,
        raw_answer_preserves_all_special_tokens=True,core_check_scope="BEFORE_AND_AFTER_ALL24")
    try:
        with training.MemorySamples() as memory:
            with official.strict_runtime(state,budget) as (active,proof):
                child["model_proof"]=proof
                active["torch"].manual_seed(1337)
                tools=generation_tools()
                active["torch"].cuda.reset_peak_memory_stats()
                for case in state["cases"]:
                    for mode in MODES:
                        budget.check("고정 요청 시작 전")
                        row=emit(active,case,mode,budget,tools=tools)
                        writer.append(row); child["requests"]+=1
                        print(json.dumps(dict(event="DIALOGUE_REQUEST",case_id=case["id"],mode=mode,
                            finish_reason=row["trace"]["finish_reason"],generated_tokens=len(row["generated_ids"])),
                            ensure_ascii=False),flush=True)
                        budget.check("요청 raw 저장·작은 출력 뒤")
        child["memory"]=memory.summary()
        child["answers_manifest"]=writer.close(lineage=dict(schema=SCHEMA,
            checkpoint_sha256=child["checkpoint_sha256"],cases_sha256=CASES_REF["sha256"]))
        verify(args.output/"answers",child["answers_manifest"])
        child.update(status="DIALOGUE24_COMPLETE",whole_worker_seconds=time.monotonic()-budget.started)
        validate_worker(child,state,args.output,budget)
        immutable(state,budget)
        return child
    except BaseException as error:
        primary=error
        raise
    finally:
        training.close_preserving(primary,[("대화 부분 raw shard 닫기",writer._finish)])


def parser():
    value=argparse.ArgumentParser(description=__doc__)
    value.add_argument("--profile"); value.add_argument("--profile-sha256")
    value.add_argument("--source-sha256"); value.add_argument("--output")
    value.add_argument("--max-wall-sec",type=int,default=900)
    value.add_argument("--deadline",default=END.isoformat())
    value.add_argument("--parent-started",type=float,help=argparse.SUPPRESS)
    value.add_argument("--work-end",type=float,help=argparse.SUPPRESS)
    group=value.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-only",action="store_true")
    group.add_argument("--check-only",action="store_true")
    group.add_argument("--execute",action="store_true")
    group.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    return value


def main(argv=None):
    args=parser().parse_args(argv)
    output,owned=None,False
    try:
        if args.source_only:
            print(json.dumps(dict(schema=SCHEMA,source_identity=source_identity(),model_loaded=False,
                gpu_calls=0,files_written=0),ensure_ascii=False),flush=True)
            return 0
        if not args.profile or not args.profile_sha256 or not args.source_sha256:
            raise Hold("새 대화 profile·완주 원형·source pin이 아직 없다")
        require(240 <= args.max_wall_sec <= 3600,"대화 전체 wall은240..3600초다")
        deadline=datetime.fromisoformat(args.deadline.replace("Z","+00:00"))
        require(deadline.tzinfo is not None and deadline <= END,"대화·종결은26일17시 안이다")
        start=args.parent_started if args.worker else STARTED
        budget=supervisor.Budget(args.max_wall_sec,deadline.timestamp(),started=start,reserve=120)
        if args.worker:
            require(type(args.work_end) is float and math.isfinite(args.work_end) and args.work_end < budget.end,
                "부모 종결 예약을 뺀 worker 마감이 필요하다")
            budget.end=min(budget.end,args.work_end); budget.reserve=0
        with supervisor.total_budget(budget),supervisor.termination_guard():
            state=metadata(args,budget)
            if not args.worker: budget.reserve=state["profile"]["cleanup_reserve_sec"]
            require(budget.remaining() > budget.reserve,"대화 종결 예약이 부족하다")
            if args.check_only:
                result=dict(schema=SCHEMA,status="CPU_METADATA_ONLY",returncode=0,model_loaded=False,
                    gpu_calls=0,files_written=0,requests=24,generation="NOT_RUN")
                code=0
            else:
                require(args.output and Path(args.output).parts[:2] == ("test_result","evidence")
                    and len(Path(args.output).parts) == 3
                    and re.fullmatch(PREFIX+"[A-Za-z0-9_]+",Path(args.output).name),"새 대화 이름공간이 필요하다")
                output=safe(args.output); args.output=output
                if args.worker:
                    invocation=supervisor.read_json(output/"invocation.json")
                    require(os.getppid() == invocation["parent_pid"]
                        and supervisor.proc.proc_stat(os.getppid())["starttime"] == invocation["parent_starttime"]
                        and invocation["source_sha256"] == state["source_identity"]["sha256"]
                        and invocation["profile_sha256"] == state["profile_sha256"]
                        and invocation["work_end"] == args.work_end
                        and re.fullmatch("[0-9a-f]{64}",os.environ.get(training.OWNER,"")),"소유 대화 worker의 부모 신원이 다르다")
                    owned=True
                    child=execute_worker(args,state,budget)
                    supervisor.write_once(output/"worker.json",child,budget)
                    code=0
                else:
                    require(not output.exists(),"이전 완결·부분 대화 결과를 보존한다")
                    output.mkdir(); owned=True
                    supervisor.write_once(output/"source.json",state["source_identity"],budget)
                    owner=supervisor.proc.proc_stat(os.getpid()); work_end=budget.end-budget.reserve
                    supervisor.write_once(output/"invocation.json",dict(parent_pid=os.getpid(),
                        parent_starttime=owner["starttime"],source_sha256=state["source_identity"]["sha256"],
                        profile_sha256=state["profile_sha256"],work_end=work_end),budget)
                    command=[official.worker_python(),"-I","-B","-X","utf8",str(Path(__file__).resolve())]
                    command += [item for item in (sys.argv[1:] if argv is None else argv) if item != "--execute"]
                    command += ["--worker","--parent-started",str(budget.started),"--work-end",str(work_end)]
                    observed=training.supervise(command,output,budget)
                    code=0 if training.supervision_ok(observed) else 9
                    child,child_sha=None,None
                    try:
                        if (output/"worker.json").is_file():
                            child_sha=official.digest(output/"worker.json",budget)
                            child=read_ref(dict(path=str((output/"worker.json").relative_to(ROOT)),sha256=child_sha),budget)
                        require(code != 0 or child is not None,"실제 대화 자식 완결 원형이 없다")
                        if code == 0: validate_worker(child,state,output,budget)
                        immutable(state,budget)
                    except BaseException as error:
                        code=9; observed.setdefault("post_errors",[]).append(supervisor.error_record(error,"대화 부모 종결 검산"))
                    report=dict(schema=SCHEMA,returncode=code,arm=state["profile"]["arm"],
                        source_sha256=state["source_identity"]["sha256"],profile_sha256=state["profile_sha256"],
                        supervision=observed,worker=child,worker_sha256=child_sha,
                        whole_parent_seconds=time.monotonic()-budget.started,deadline=deadline.isoformat(),
                        external_os_timeout_required=True,actual_supervisor_exit="ROOT_MUST_COLLECT")
                    supervisor.write_once(output/"report.json",report,budget)
                    supervisor.append_terminal(output,dict(event="OBSERVATION",returncode=code))
                result=dict(schema=SCHEMA,returncode=code,arm=state["profile"]["arm"])
            budget.check("최종 작은 출력 전")
            print(json.dumps(result,ensure_ascii=False),flush=True)
            budget.check("최종 작은 출력 뒤")
        budget.check("타이머·신호 복구 뒤")
        return code
    except BaseException as error:
        record=supervisor.error_record(error,"대화 전체 종결",os.environ.get(training.OWNER,""))
        if owned and output is not None and output.is_dir():
            try: supervisor.append_terminal(output,dict(event="TERMINAL_VETO",returncode=9,error=record))
            except BaseException: pass
        code=8 if isinstance(error,Hold) and not owned else 9
        try: print(json.dumps(dict(schema=SCHEMA,returncode=code,error=record),ensure_ascii=False),flush=True)
        except BaseException:
            code=9
            if owned and output is not None and output.is_dir():
                try: supervisor.append_terminal(output,dict(event="TERMINAL_VETO",returncode=9,stage="오류 출력"))
                except BaseException: pass
        return code


if __name__ == "__main__":
    raise SystemExit(main())
