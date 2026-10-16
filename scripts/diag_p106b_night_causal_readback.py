#!/usr/bin/env python3
"""CPU-only future-answer perturbation check; no learning or checkpoint writes."""
from pathlib import Path
import copy
import gc
import hashlib
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_night_question_scores as prior
qa=prior.qa
TAG='p106b_night_causal_readback_v1_s1337'
OUT=ROOT/'test_result/evidence'/TAG/'report.json'
CODE=(*prior.CODE,'scripts/diag_p106b_night_causal_readback.py',
      'scripts/test_p106b_night_causal_readback.py')


def prefixes(bundle,tok):
    from tinylm.chat.serialize import serialize
    values=[]
    for qi in range(2):
        cells=sorted((c for c in bundle['cells'] if c['question_index']==qi),key=lambda c:c['candidate_index'])
        if [c['candidate_index'] for c in cells]!=[0,1]:raise ValueError('exact two candidate cells required')
        for cell in cells:prior.method._cell(cell)
        candidates=[c['x'][:c['content_positions'][0]+1] for c in cells]
        prompt=copy.deepcopy(cells[0]['row']);prompt['messages']=prompt['messages'][:1]
        actual=list(tok.encode(serialize(prompt,'chatml',add_generation_prompt=True)).ids)
        if candidates[0]!=candidates[1] or candidates[0]!=actual:
            raise ValueError('shifted predictor prefix differs from actual answer-free generation prompt')
        values.append(dict(question_index=qi,prefix=actual,cells=cells))
    if values[0]['prefix']==values[1]['prefix']:raise ValueError('two distinct actual question prefixes required')
    return values


def tensor_sha(value):
    return hashlib.sha256(value.detach().cpu().contiguous().view(-1).view(__import__('torch').uint8).numpy().tobytes()).hexdigest().upper()


def delta(left,right):
    import torch
    if (left.shape!=right.shape or not left.numel() or not torch.isfinite(left).all()
            or not torch.isfinite(right).all()):raise ValueError('finite equal nonempty tensor shape required')
    return dict(shape=list(left.shape),max_abs=float((left-right).abs().max()),
        exact_equal=bool(torch.equal(left,right)),left_sha256=tensor_sha(left),right_sha256=tensor_sha(right))


def selected(wire,ids):
    if len(ids)!=4 or len(set(ids))!=4:raise ValueError('four previously source-fixed review bundle IDs required')
    result=[b for b in wire if b['source_bundle_id'] in ids]
    if sorted(b['source_bundle_id'] for b in result)!=sorted(ids):raise ValueError('missing source review bundle')
    if {l:sum(b['bundle']['language']==l for b in result) for l in ('ko','en')}!={'ko':2,'en':2}:
        raise ValueError('same original two Korean/two English review bundles required')
    return result


def run():
    import torch
    from tokenizers import Tokenizer
    from torch.nn.attention import sdpa_kernel,SDPBackend
    from tinylm.infer.generate import load_model
    from scripts.p106b_gate_runtime import wall_limit
    for path in (OUT,*OUT.parents):
        if path.is_symlink():raise ValueError('linked CPU output refused')
        if path==ROOT:break
    if OUT.exists():raise FileExistsError('old CPU causal readback preserved')
    if torch.cuda.is_initialized():raise ValueError('CPU check requires CUDA never initialized')
    began=time.perf_counter();torch.set_num_threads(4)
    with wall_limit(600):
        frozen,wire=prior.read_inputs()
        previous=qa.required(prior.source.FROZEN/'report.json')
        wire=selected(wire,previous['review_bundle_ids'])
        tok=Tokenizer.from_file(str(qa.data.TOKENIZER))
        fixed=[(b,prefixes(b['bundle'],tok)) for b in wire]
        reports={}
        for endpoint in prior.ENDPOINTS:
            checkpoint,identity,expected,report_hash,_=prior.free_answers(endpoint,wire)
            prior.endpoint_report(endpoint,'full',frozen,prior.read_inputs()[1])
            model,cfg,device=load_model(arch='dense',ckpt_path=str(checkpoint),device='cpu')
            initial=prior.probe.panel.foundation.runtime.state_fingerprint(model)
            if initial!=expected or next(model.parameters()).dtype!=torch.float32 or device!='cpu':
                raise ValueError('actual same FP32 checkpoint body required on CPU')
            events=[];question_changes=[]
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                for bundle,questions in fixed:
                    q_logits=[]
                    for question in questions:
                        x=torch.tensor([question['prefix']],dtype=torch.long,device='cpu')
                        prefix_h=model(x,return_hidden=True)[0]
                        logits=model._head_logits(prefix_h[-1:].unsqueeze(0))[0,0]
                        q_logits.append(logits)
                        for cell in question['cells']:
                            full_h=model(torch.tensor([cell['x']],dtype=torch.long,device='cpu'),return_hidden=True)[0]
                            position=cell['content_positions'][0]
                            full_logits=model._head_logits(full_h[position:position+1].unsqueeze(0))[0,0]
                            event=dict(source_bundle_id=bundle['source_bundle_id'],cell_id=cell['cell_id'],
                                question_index=question['question_index'],candidate_index=cell['candidate_index'],
                                prefix_tokens=len(question['prefix']),full_tokens=len(cell['x']),
                                hidden=delta(prefix_h,full_h[:position+1]),logits=delta(logits,full_logits),
                                same_argmax=int(logits.argmax())==int(full_logits.argmax()))
                            events.append(event)
                    question_changes.append(dict(source_bundle_id=bundle['source_bundle_id'],
                        question_only_logits=delta(q_logits[0],q_logits[1])))
            final=prior.probe.panel.foundation.runtime.state_fingerprint(model)
            if initial!=final or qa.data.digest(checkpoint)!=identity or torch.cuda.is_initialized():
                raise ValueError('CPU read-only body/file/device proof failed')
            reports[endpoint]=dict(checkpoint=str(checkpoint.relative_to(ROOT)),checkpoint_sha256=identity,
                initial_core_sha256=initial,final_core_sha256=final,primary_report_sha256=report_hash,
                events=events,question_changes=question_changes,
                max_hidden_delta=max(e['hidden']['max_abs'] for e in events),
                max_logit_delta=max(e['logits']['max_abs'] for e in events),
                exact_equal_logits=sum(e['logits']['exact_equal'] for e in events),cells=len(events))
            print('[CPU_CAUSAL_MODEL] '+json.dumps(dict(endpoint=endpoint,
                cells=len(events),max_logit_delta=reports[endpoint]['max_logit_delta'],
                exact_equal_logits=reports[endpoint]['exact_equal_logits'])),flush=True)
            del model;gc.collect()
        result=dict(schema='P106B_NIGHT_CAUSAL_CPU_V1',tag=TAG,status='CPU_CAUSAL_READBACK_COMPLETE',
            code_sha256={p:qa.data.digest(ROOT/p) for p in sorted(set(CODE))},
            source_score_cpu_sha256=qa.data.digest(prior.FROZEN/'report.json'),
            source_bundle_cpu_sha256=qa.data.digest(prior.source.FROZEN/'report.json'),
            selected_source_bundle_ids=previous['review_bundle_ids'],selection_from_model_answers=False,
            reports=reports,cuda_initialized=torch.cuda.is_initialized(),device='cpu',precision='FP32_MATH',
            threads=4,whole_seconds=time.perf_counter()-began,updates=0,checkpoints_written=0,
            quality_pass_declared=False,numerical_tolerance_chosen=False,
            interpretation='finite sampled causal-prefix comparison, not semantic correctness or universal causal proof')
        qa.write(OUT,result)
        if qa.required(OUT)!=result:raise ValueError('CPU output roundtrip failed')
        print('[CPU_CAUSAL_COMPLETE] '+json.dumps(dict(seconds=result['whole_seconds'],cuda=False)),flush=True)
    return 0


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not args.execute:parser.error('explicit bounded CPU model read required')
    try:raise SystemExit(run())
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[CPU_CAUSAL_ERROR] '+str(exc));raise SystemExit(9)
