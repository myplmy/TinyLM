#!/usr/bin/env python3
"""User-operated model menu; selected checkpoint owns config/tokenizer identity.

No checkpoint is opened by discovery, --list or --help. Actual model loading is
only after explicit user selection. Interactive input is forbidden without TTY.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import gc
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import tinylm  # noqa:F401
from tinylm import paths
from tinylm.infer.catalog import discover_models,filter_models,resolve_selection
from tinylm.infer import dialogue as contract


def _ordered(records,order):
    if order=="recent":return sorted(records,key=lambda r:(-r.modified_ns,r.stem))
    if order=="name":return sorted(records,key=lambda r:r.stem)
    return list(records)  # Existing catalog validation-loss order; never quality certification.


def _display(records,limit):
    shown=records if limit<=0 else records[:limit]
    print("\n모델 선택: 최신 저장시각/val은 답변 품질 순위가 아닙니다.")
    print("_best는 저장된 DEV 대표이며 최종본보다 좋은 답을 보장하지 않습니다.")
    for index,row in enumerate(shown,1):
        stamp=datetime.fromtimestamp(row.modified_ns/1e9,timezone(timedelta(hours=9))).strftime("%m-%d %H:%M")
        value="?" if row.display_val is None else f"{row.display_val:.5f}"
        print(f"{index:>4}. {row.selector}")
        print(f"      저장(KST)={stamp} data={row.data} arch={row.arch or '선택시 cfg 확인'} val={value}")
    if len(records)>len(shown):print(f"추가 {len(records)-len(shown)}개: /검색어 또는 all로 표시하세요.")
    return shown


def _choose(records,limit,preset_selection=None):
    if preset_selection:return resolve_selection(records,preset_selection)
    view=records
    while True:
        shown=_display(view,limit)
        try:raw=input("모델 번호/명칭 (/검색어, all, q): ").strip()
        except (EOFError,KeyboardInterrupt):return None
        if raw.lower() in ("q","quit",":q"):return None
        if raw.lower()=="all":view=records;limit=0;continue
        if raw.startswith("/"):
            view=filter_models(records,raw[1:])
            if not view:print("일치 모델이 없습니다.");view=records
            continue
        try:return resolve_selection(shown,raw)
        except ValueError as exc:print("[선택 오류]",exc)


def _metadata(record,runtime=None):
    print("checkpoint:",record.checkpoint)
    print("selector:",record.selector)
    print("학습 JSON:",record.log_path or "없음; 선택한 가중치 저장 cfg로 확인")
    if runtime:
        meta=runtime["metadata"];route=runtime["route"]
        print("checkpoint SHA:",runtime["checkpoint_sha256"])
        print("저장 cfg 공유표시:",{key:value for key,value in meta["cfg"].items() if key.startswith("tie_")})
        print("학습 JSON 구조표시:",record.arch or "없음","/ step:",meta["step"],"/ epoch:",meta["epoch"])
        print("tokenizer:",route.path)
        print("tokenizer SHA:",route.sha256,"/ 학습 SHA 일치:",route.verified)
        print("mode:",runtime["mode"],"/ precision:",runtime["precision"],"/ device:",runtime["device"])
        if runtime.get("vocabulary_contract"):
            print("어휘 호환 계약:",runtime["vocabulary_contract"])
        if not route.verified:print("[주의] 저장된 학습 tokenizer SHA가 없어 정체성 미인증:",route.reason)
    print("[주의] 대화 표지/종료 성공과 질문 정답성은 별개입니다. 최신 모델도 오답일 수 있습니다.")


def _load_runtime(record,args):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    before=record.checkpoint.stat()
    identity=contract.file_sha(record.checkpoint)
    # Only the chosen checkpoint is read. Release its CPU weights before GPU load.
    state=torch.load(record.checkpoint,map_location="cpu",weights_only=True)
    metadata=contract.selected_metadata(state);del state;gc.collect()
    route=contract.resolve_tokenizer(record,metadata,paths.DATA_CACHE,args.tokenizer)
    tokenizer=Tokenizer.from_file(str(route.path))
    if contract.file_sha(route.path)!=route.sha256:raise ValueError("tokenizer가 확인 도중 바뀌었습니다.")
    allow_extra_special=getattr(args,"allow_extra_special_tokens",False)
    vocabulary=contract.validate_vocabulary(tokenizer,metadata["cfg"],allow_extra_special=allow_extra_special)
    mode,stop_ids=contract.resolve_mode(tokenizer,metadata["cfg"],args.mode,allow_extra_special=allow_extra_special)
    if args.history and mode!="chatml":raise ValueError("--history는 ChatML 경계가 확인된 모드에서만 사용할 수 있습니다.")
    # CLI arch labels need not equal MLP tying (e.g. attention-only sharing).
    # With an explicit checkpoint, load_model builds the full stored cfg and
    # strict state; do not reject a valid model based on that coarse label.
    if args.precision=="fp32-math":
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    base,cfg,device=load_model(metadata["arch"],str(record.checkpoint),args.device)
    after=record.checkpoint.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError("체크포인트가 읽는 도중 바뀌었습니다.")
    if cfg.vocab_size!=metadata["cfg"]["vocab_size"]:raise ValueError("실제 로드 cfg가 달라졌습니다.")
    model=PrecisionForward(base,"fp32_math") if args.precision=="fp32-math" else base
    return dict(model=model,cfg=cfg,device=device,tokenizer=tokenizer,metadata=metadata,
        route=route,mode=mode,stop_ids=stop_ids,precision=args.precision,checkpoint_sha256=identity,
        vocabulary_contract=vocabulary)


def _emit(runtime,question,args,history=()):
    import torch
    from scripts.diag_p101a_mtp_parity import CaptureTokens
    from tinylm.infer.generate import sample
    tok=runtime["tokenizer"];prompt=contract.make_prompt(question,runtime["mode"],history)
    ids=tok.encode(prompt).ids
    contract.validate_input_ids(ids,runtime["cfg"].vocab_size)
    if len(ids)+args.max_new>runtime["cfg"].max_seq_len:
        raise ValueError(f"입력 {len(ids)} + 생성 {args.max_new} > 문맥 {runtime['cfg'].max_seq_len}; 자동 절단하지 않습니다. :reset 또는 짧은 질문을 쓰세요.")
    captured=CaptureTokens(tok)
    with torch.no_grad():
        _,metadata=sample(runtime["model"],runtime["cfg"],captured,prompt,max_new=args.max_new,
            temperature=args.temperature,top_k=args.top_k,device=runtime["device"],use_cache=True,
            logits_last_only=True,return_metadata=True,
            stop_token_sequences=[runtime["stop_ids"]] if runtime["stop_ids"] else None)
    answer=contract.answer_from_ids(tok,ids,captured.decoded_ids,metadata["generated_tokens"])
    return answer,dict(metadata,prompt_tokens=len(ids))


def _print_answer(answer,metadata):
    print("답변:",answer)
    print("종료:",metadata["finish_reason"],"/ 생성 토큰:",metadata["generated_tokens"],
          "/ 입력 토큰:",metadata.get("prompt_tokens","?"))
    print("[종료 표시는 정답 판정이 아닙니다.]")


def _validation_probe(record,runtime,args):
    # The existing validation continuation tool is not an SFT answer validator.
    if not runtime["route"].verified or runtime["mode"]=="chatml" or runtime["route"].path.name.endswith("-chat32.json"):
        print("[val] chat32 또는 학습 정체성 미인증의 raw cache를 자동 추정하지 않습니다.")
        return
    print("[val] 실제 cache의 원문 이어쓰기이며 SFT 정답/벤치 평가가 아닙니다.")
    from tinylm.infer.text_probe import select_cache,span_offsets
    import numpy as np
    import json
    cache=select_cache(paths.DATA_CACHE,record.data,pool_tokens=str(record.pool_tokens) if record.pool_tokens else None)
    meta=json.loads((cache/"meta.json").read_text(encoding="utf-8"))
    if str(meta.get("tokenizer_sha256","")).upper()!=runtime["route"].sha256:
        print("[val] cache의 tokenizer SHA가 없거나 선택 모델과 다릅니다. 원문 token ID를 읽지 않습니다.")
        return
    values=np.memmap(cache/"val.bin",dtype=np.dtype(meta.get("token_dtype","uint16")),mode="r")
    offset=span_offsets(len(values),96,48,1,seed=99)[0];tok=runtime["tokenizer"]
    context=tok.decode(list(map(int,values[offset:offset+96])))
    print("CONTEXT:",context);print("GOLD:",tok.decode(list(map(int,values[offset+96:offset+144]))))
    answer,generation=_emit(runtime,context,args);_print_answer(answer,generation)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",help="표시 번호, 정확한 tag/stem/파일명 또는 고유 부분문자열")
    parser.add_argument("--filter",default="")
    parser.add_argument("--limit",type=int,default=30)
    parser.add_argument("--sort",choices=("recent","name","val"),default="recent")
    parser.add_argument("--device",choices=("cpu","cuda"),default=None)
    parser.add_argument("--max-new",type=int,default=128)
    parser.add_argument("--temperature",type=float,default=0.)
    parser.add_argument("--top-k",type=int,default=1)
    parser.add_argument("--mode",choices=("auto","plain","chatml"),default="auto")
    parser.add_argument("--tokenizer",type=Path,help="정확한 로컬 JSON; 저장 SHA가 있으면 일치해야 함")
    parser.add_argument("--allow-extra-special-tokens",action="store_true",
        help="기본 어휘와 ID가 동일한 추가 특수 토큰만 명시 허용; 범위 밖 특수 토큰 입력은 거부")
    parser.add_argument("--precision",choices=("fp32-math","native"),default="fp32-math")
    parser.add_argument("--history",action="store_true",help="chatml에서 실제 이전 질문/답을 유지; 기본은 독립 질문")
    parser.add_argument("--prompt",help="한 번만 생성하고 종료")
    parser.add_argument("--list",action="store_true",help="모델 가중치 없이 목록만")
    args=parser.parse_args(argv)
    if args.max_new<1 or args.top_k<1 or not math.isfinite(args.temperature) or args.temperature<0:parser.error("생성 토큰/top-k는 양수,온도는0이상이어야 합니다.")
    records=_ordered(filter_models(discover_models(paths.RUNS/"ckpt",paths.RUNS/"logs"),args.filter),args.sort)
    if not records:print("[STOP] 선택 가능한 checkpoint가 없습니다.",file=sys.stderr);return 2
    if args.list:_display(records,args.limit);return 0
    if not sys.stdin.isatty() and not (args.model and args.prompt is not None):
        parser.error("대화형 선택/입력에는 터미널이 필요합니다. run_queue에 넣지 마세요. 자동 호출은 --list 또는 --model NAME --prompt TEXT를 쓰세요.")
    selection=args.model
    while True:
        try:record=_choose(records,args.limit,selection)
        except ValueError as exc:print("[STOP]",exc,file=sys.stderr);return 2
        selection=None
        if record is None:return 0
        print("[선택 후 검증/로드]",record.checkpoint.name)
        try:runtime=_load_runtime(record,args)
        except (ValueError,OSError) as exc:
            print("[로드 중단]",exc,file=sys.stderr)
            if args.model or args.prompt is not None:return 2
            continue
        _metadata(record,runtime)
        print("생성 설정: temperature=",args.temperature,"top_k=",args.top_k,
              "max_new=",args.max_new,"history=",args.history,"/ MTP 추론 OFF")
        if args.prompt is not None:
            try:answer,meta=_emit(runtime,args.prompt,args);_print_answer(answer,meta);return 0
            except ValueError as exc:print("[STOP]",exc,file=sys.stderr);return 2
        history=[];history_on=args.history
        print("명령: :model 모델변경 / :meta / :reset / :history on|off / :quit")
        print("기본 질문은 독립이며, ChatML 표지만으로 대화 능력이 보장되지는 않습니다.")
        try:
            while True:
                try:question=input("\n질문> ")
                except (EOFError,KeyboardInterrupt):return 0
                command=question.strip().lower()
                if command in (":q",":quit","quit"):return 0
                if command==":model":break
                if command==":meta":_metadata(record,runtime);continue
                if command==":reset":history=[];print("이력을 지웠습니다.");continue
                if command in (":history on",":history off"):
                    if command.endswith(" on") and runtime["mode"]!="chatml":
                        print("plain 이어쓰기에서는 대화 이력을 켜지 않습니다.");continue
                    history_on=command.endswith(" on");history=[];print("이력:",history_on);continue
                if command==":val":
                    try:_validation_probe(record,runtime,args)
                    except (ValueError,OSError) as exc:print("[val 중단]",exc)
                    continue
                if not question.strip():continue
                try:answer,meta=_emit(runtime,question,args,history if history_on else ())
                except ValueError as exc:print("[입력 중단]",exc);continue
                _print_answer(answer,meta)
                if history_on and answer:history=contract.add_turn(history,question,answer)
        finally:
            device=runtime["device"];runtime.clear();gc.collect()
            if str(device).startswith("cuda"):
                import torch
                torch.cuda.empty_cache()


if __name__=="__main__":raise SystemExit(main())
