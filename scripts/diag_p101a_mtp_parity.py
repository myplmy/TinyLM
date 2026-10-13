#!/usr/bin/env python3
"""User-only no-retraining parity diagnosis of saved NTP/MTP outputs.

At the first differing token, replay the same native history and separately
change multi-query verification and prefix rebuilding. This measures numerical
path differences, not semantic truth or a production-speed adoption decision.
"""
from __future__ import annotations
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p101a_sft_mtp as prior


class CaptureTokens:
    def __init__(self,tok):self.tok=tok;self.decoded_ids=None
    def __getattr__(self,name):return getattr(self.tok,name)
    def decode(self,ids):self.decoded_ids=list(ids);return self.tok.decode(ids)


class PrecisionForward:
    def __init__(self,model,precision):self.model=model;self.precision=precision
    def __getattr__(self,name):return getattr(self.model,name)
    def __call__(self,*args,**kwargs):
        import torch
        from torch.nn.attention import sdpa_kernel,SDPBackend
        with (sdpa_kernel(SDPBackend.MATH) if self.precision=='fp32_math' else nullcontext()):
            with torch.autocast('cuda',enabled=self.precision!='fp32_math',dtype=torch.bfloat16):
                return self.model(*args,**kwargs)
    def mtp_aux_logits(self,*args):
        import torch
        with torch.autocast('cuda',enabled=self.precision!='fp32_math',dtype=torch.bfloat16):
            return self.model.mtp_aux_logits(*args)


def first_difference(left,right):
    return next((i for i,(a,b) in enumerate(zip(left,right)) if a!=b),
        min(len(left),len(right)) if len(left)!=len(right) else None)


def logit_difference(left,right):
    values=left.float().flatten();other=right.float().flatten()
    scores,ids=values.topk(2)
    return dict(left_top1=int(ids[0]),left_top2=int(ids[1]),left_margin=float(scores[0]-scores[1]),
        right_top1=int(other.argmax()),max_abs=float((values-other).abs().max()),
        argmax_equal=int(ids[0])==int(other.argmax()))


def shadow(model,prompt_ids,native_generated,index,device):
    import torch
    history=prompt_ids+native_generated[:index]
    past=None
    if index:
        _,past=model(torch.tensor([prompt_ids],device=device),use_cache=True,logits_last_only=True)
        for token in native_generated[:index-1]:
            _,past=model(torch.tensor([[token]],device=device),past_kv=past,use_cache=True,logits_last_only=True)
        pending=[history[-1]]
    else:pending=history
    a,kv_a=model(torch.tensor([pending],device=device),past_kv=past,use_cache=True,logits_last_only=True)
    future=native_generated[index:index+2] or [history[-1]]
    b,_=model(torch.tensor([pending+future],device=device),past_kv=past,use_cache=True)
    c,kv_c=model(torch.tensor([history],device=device),use_cache=True,logits_last_only=True)
    differences={}
    for key in kv_a:
        differences[str(key)]=[float((v.float()-w.float()).abs().max()) for v,w in zip(kv_a[key],kv_c[key])]
    return dict(index=index,same_history_tokens=len(history),pending_query_tokens=len(pending),
        multi_query_tokens=len(pending)+len(future),
        incremental_vs_multi=logit_difference(a[:,-1],b[:,len(pending)-1]),
        incremental_vs_rebuild=logit_difference(a[:,-1],c[:,-1]),kv_max_abs_by_owner=differences,
        interpretation='same-prefix numerical counterfactual; not a training or semantic cause proof')


def check(arm):
    _,old=prior.paths('p101a_sft_mtp_v1_s1337')
    source=prior.report_path(old,arm)
    report=json.loads(source.read_text())
    if report.get('status')!='SFT_MTP_TRAINED_EVAL_PENDING' or not report.get('checkpoint_saved'):
        raise FileNotFoundError('completed exact trained MTP arm required')
    path=prior.checkpoint('p101a_sft_mtp_v1_s1337',arm)
    if not path.is_file() or path.is_symlink():raise FileNotFoundError('trained checkpoint absent or linked')
    target=ROOT/'test_result/evidence/p101a_mtp_parity_v2_s1337'/arm
    if target.exists() or target.is_symlink():raise FileExistsError('preserve prior parity evidence')
    return path,target,dict(source_report=str(source.relative_to(ROOT)),source_report_sha256=prior.data.digest(source),
        checkpoint_sha256=report['checkpoint_sha256'],tokenizer_sha256=prior.data.TOK_SHA,
        student_training='NOT_RUN',checkpoint_save=False)


def execute(args):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model,sample
    from tinylm.chat.serialize import serialize
    from scripts.p106b_repeat4_gate import PROBES
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from scripts.p106b_shards import ShardWriter,verify
    path,target,info=check(args.arm)
    if prior.data.digest(path)!=info['checkpoint_sha256']:raise ValueError('saved model changed')
    if prior.data.digest(prior.data.TOKENIZER)!=prior.data.TOK_SHA:raise ValueError('tokenizer changed')
    tok=Tokenizer.from_file(str(prior.data.TOKENIZER));target.mkdir(parents=True,exist_ok=False)
    writer=ShardWriter(target,'answers');summary=[];began=time.perf_counter()
    rc=9;status='STARTED'
    try:
        idle_before_gpu()
        with wall_limit(args.max_wall_sec),torch.no_grad():
            base,cfg,_=load_model(ckpt_path=path,device='cuda',mtp_heads=4)
            for precision in ('bf16_auto','fp32_math'):
                model=PrecisionForward(base,precision)
                for ident,question in PROBES:
                    prompt=serialize({'messages':[{'role':'user','content':question}]},'chatml',add_generation_prompt=True)
                    prompt_ids=tok.encode(prompt).ids;captured=[]
                    for k in (1,2,4):
                        wrapped=CaptureTokens(tok);torch.cuda.synchronize();tick=time.perf_counter()
                        text,meta=sample(model,cfg,wrapped,prompt,max_new=64,temperature=0.,top_k=1,
                            device='cuda',logits_last_only=True,return_metadata=True,mtp_tokens=k,
                            stop_token_sequences=[tok.encode('<|im_end|>').ids])
                        torch.cuda.synchronize()
                        captured.append(dict(k=k,ids=wrapped.decoded_ids[len(prompt_ids):],text=text,
                            metadata=meta,seconds=time.perf_counter()-tick))
                    native=captured[0]
                    for row in captured:
                        difference=first_difference(native['ids'],row['ids'])
                        trace=None
                        if difference is not None and difference<len(native['ids']):
                            trace=shadow(model,prompt_ids,native['ids'],difference,'cuda')
                        record=dict(id=ident,question=question,precision=precision,profile=row,
                            equivalent_to_native=(difference is None and row['metadata']['finish_reason']==native['metadata']['finish_reason']),
                            first_difference=difference,shadow=trace)
                        writer.append(record)
                        summary.append({key:value for key,value in record.items() if key not in ('profile','shadow','question')})
                        print('[PARITY_CASE] '+json.dumps(summary[-1]),flush=True)
            status='PARITY_DIAGNOSTIC_COMPLETE';rc=0
    except BaseException as error:
        rc=130 if isinstance(error,KeyboardInterrupt) else 9;status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR'
        summary.append(dict(error_type=type(error).__name__,reason=str(error)[:1000]))
    finally:
        manifest=writer.close(lineage=info) if writer._total_rows else None
        if manifest:verify(target,manifest)
        prior.write(target/'report.json',dict(info,schema='P101A_MTP_NUMERIC_PARITY_DIAGNOSTIC_V1',
            status=status,returncode=rc,records=summary,raw_manifest=manifest,whole_sec=time.perf_counter()-began,
            production_mtp_adopted=False,semantic_truth='NOT_REVIEWED',
            result_scope='diagnostic completion is not output parity or speed PASS'))
    return rc


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',choices=('scratch_mtp','parent_mtp'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=900)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=1800:p.error('bounded diagnostic time required')
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(check(a.arm)[2]));return 0
    return execute(a)


if __name__=='__main__':raise SystemExit(main())
