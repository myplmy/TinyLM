#!/usr/bin/env python3
"""New Oct16 bounded QA/grounding study; immutable inputs, fresh outputs only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
from datetime import datetime,timezone
import copy
import gc
import json
import math
import os
import random
import tempfile
import time
from scripts import p106b_grounded_span as method
from scripts import diag_p101a_sft_mtp as training
from scripts import p101a_sft_mtp_data as public
from scripts import p106b_retention_course as rules
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_native_windows import reader as native_reader,NATIVE_TRAIN
TAG='p106b_grounded_span_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
CORPUS=OUTPUT/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
NATIVE=ROOT/'data_cache/ko-en_601000000_chat32'
DEADLINE=datetime(2026,10,16,8,0,tzinfo=timezone.utc)
CODE=(*training.CODE,'scripts/p106b_grounded_span.py','scripts/diag_p106b_grounded_span.py',
      'scripts/test_p106b_grounded_span.py','scripts/p106b_padding_probe.py','scripts/p106b_retention_course.py',
      'scripts/p106b_native_windows.py','scripts/p106b_shards.py')


def deadline():
    if datetime.now(timezone.utc)>=DEADLINE:raise TimeoutError('Oct16 17:00 KST execution authority expired')


def info():
    return dict(schema=method.VERSION,tag=TAG,code_sha256={p:public.digest(ROOT/p) for p in sorted(set(CODE))},
        parent=str(training.PARENT.relative_to(ROOT)),parent_sha256=training.PARENT_SHA,tokenizer_sha256=public.TOK_SHA,
        seed=1337,micro_bs=8,accum=16,seq=1024,checkpoint_on=True,compile='default',epochs=4,
        lr=5e-5,muon_lr=2e-4,matrix_weight_decay=0,native_weight=1.,gradient_clip=1.,
        arms=method.ARMS,auxiliary_rank=64,auxiliary_in_free_generation=False,student_mtp=False,
        execution_padding='RIGHT_ALIGN128_MAX1024; native fixed1024',deadline_utc=DEADLINE.isoformat(),
        teacher_calls=0,formal_train_ready=False,semantic_truth='PUBLIC_SOURCE_UNVERIFIED',
        scope='natural source QA learning study, not75M/300M or general intelligence')


def checkpoint(arm):return ROOT/'runs/ckpt'/f'm100s10_ko-en_grounded_span_dense_chat32_{TAG}_{arm}.pt'


def required(path):
    if not path.is_file() or path.is_symlink():raise GateNegative('missing regular prerequisite: '+str(path.relative_to(ROOT)))
    return json.loads(path.read_text())


def old_source_exclusions():
    roots=set();keys=set();identities=[]
    for tag in ('p106b_source_course_v1_s1337','p106b_source_expand_v2_s1337'):
        directory=ROOT/'HF/sft_ready'/tag;r=required(directory/'sources_report.json')
        identities.append(dict(report=str((directory/'sources_report.json').relative_to(ROOT)),sha256=public.digest(directory/'sources_report.json')))
        for item in public.stream_rows(directory,r['manifest']):
            roots.add(item['root'])
            for message in item['source']['messages'][:2]:keys.update(method.passage_keys(method.text(message)))
    return roots,keys,identities


def freeze():
    deadline()
    if OUTPUT.exists() or EVIDENCE.exists():raise GateNegative('previous namespace preserved; use a new stage')
    from tokenizers import Tokenizer
    from tinylm.train import mtp_sft as core
    import numpy as np
    if public.digest(public.PUBLIC/'report.json')!=public.PUBLIC_SHA or public.digest(public.TOKENIZER)!=public.TOK_SHA:
        raise ValueError('pinned original public/tokenizer differs')
    tok=Tokenizer.from_file(str(public.TOKENIZER));old_roots,old_keys,old_identity=old_source_exclusions()
    candidates=[];seen=set();rejected=Counter();source_manifests={}
    for original_split in ('train','val'):
        manifest=required(public.PUBLIC/(original_split+'_shards_manifest.json'));source_manifests[original_split]=manifest
        for row in public.stream_rows(public.PUBLIC,manifest):
            m=row['meta']
            if m.get('selection_family')!='Flan-Coqa':continue
            language=m.get('language');root=m['parent_concept_id']
            if language not in ('ko','en'):raise ValueError('undeclared source language')
            if root in old_roots:rejected['previous_source_root']+=1;continue
            try:
                pair=method.first_pair(row)
                if len(tok.encode(pair['answer']).ids)>24:raise ValueError('target longer than24 student tokens')
                item=method.wrap(row,pair,'UNASSIGNED');rec=core.encode_record(item,tok)
                locations=method.locations(item,tok,rec)
            except ValueError as exc:rejected[str(exc)]+=1;continue
            identity=method.sha([language,pair['reference']])
            if identity in seen:rejected['duplicate_reference']+=1;continue
            seen.add(identity);keys=method.passage_keys(pair['reference'])
            if keys&old_keys:rejected['exact24word_previous_source']+=1;continue
            candidates.append(dict(row=item,root=identity,keys=keys,record=rec,locations=locations))
    # Greedy hash ordering is independent of input shard order. One source per
    # exact24-word overlap component is retained; no question/answer semantics.
    pools=defaultdict(list);taken_keys=set()
    for item in sorted(candidates,key=lambda x:method.sha([TAG,x['root']])):
        if item['keys']&taken_keys:rejected['exact24word_candidate_overlap']+=1;continue
        taken_keys.update(item['keys']);pools[item['row']['meta']['language']].append(item)
    supply={l:len(v) for l,v in pools.items()};rows={s:[] for s in ('train','dev','test')}
    for lang in ('ko','en'):
        values=pools[lang]
        if len(values)<1280:raise GateNegative('natural QA unique source supply short: '+json.dumps(supply))
        for split,a,b in (('test',0,128),('dev',128,256),('train',256,1280)):
            for item in values[a:b]:
                row=item['row'];row['meta'].update(source_split=split,actual_x_tokens=item['record'].x_tokens,
                    assistant_targets=item['record'].targets,exact_passage_group_id=item['root'])
                rows[split].append(row)
    code=rules.code_rows()['train']
    bindings=[r for r in code if r['meta']['kind'].startswith('binding_')]
    others=[r for r in code if not r['meta']['kind'].startswith('binding_')]
    # Whole four-view roots, not random individual views.
    selected_roots=[]
    for language in ('ko','en'):
        selected_roots+=sorted({r['meta']['semantic_root_id'] for r in bindings if r['meta']['language']==language},key=lambda x:method.sha([TAG,x]))[:64]
    code=[copy.deepcopy(r) for r in bindings if r['meta']['semantic_root_id'] in selected_roots]
    for language in ('ko','en'):
        code+=copy.deepcopy(sorted([r for r in others if r['meta']['language']==language],key=lambda r:method.sha(r['messages']))[:256])
    if len(code)!=1024:raise ValueError('fixed1024 code replay rows required')
    for r in code:r['meta']['grounded_span_course']=TAG
    rows['train']+=code
    counts={};labels={}
    for split,values in rows.items():
        totals=Counter();languages=Counter();kinds=Counter()
        for row in values:
            rec=core.encode_record(row,tok)
            if rec.x_tokens>1024:raise ValueError('no truncation')
            loc=method.locations(row,tok,rec)
            if loc is not None:labels[method.sha(row['messages'])]=loc
            totals.update(rows=1,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            languages[row['meta']['language']]+=1;kinds[row['meta']['kind']]+=1
        counts[split]=dict(totals,languages=dict(languages),kinds=dict(kinds))
    n=4*len(rows['train'])//128
    native=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r');old=required(ROOT/'HF/sft_ready/p106b_context_replay_v2_s1337/corpus/report.json')
    exclude=set(old['native_train_offsets']);offsets=[p for p in rules.native_offsets(len(native),n*8+len(exclude)+1024) if p not in exclude][:n*8]
    if len(offsets)!=n*8:raise ValueError('native windows unavailable')
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={}
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split)
        for row in values:writer.append(row)
        manifests[split]=writer.close(lineage=info());verify(CORPUS,manifests[split])
    writer=ShardWriter(CORPUS,'span_labels')
    for signature,loc in sorted(labels.items()):writer.append(dict(signature=signature,location=loc))
    lm=writer.close(lineage=dict(schema=method.VERSION,scope='source-only char/token spans'))
    report=dict(info(),status='GROUNDED_SPAN_COURSE_FROZEN',counts=counts,manifests=manifests,labels_manifest=lm,
        source_manifests=source_manifests,public_source_report_sha256=public.PUBLIC_SHA,old_source_exclusions=old_identity,
        candidate_supply=supply,rejections=dict(rejected),expected_updates=n,natural_train_rows=2048,
        code_train_rows=1024,auxiliary_train_rows=2048,native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,
        native_train_offsets=offsets,native_train_sha256=public.digest(ROOT/NATIVE_TRAIN),
        native_val_sha256=public.digest(NATIVE/'val.bin'),exact24word_cross_split_overlap=0,
        cross_language_semantic_overlap='NOT_AUDITED; same translated fact may survive',
        private_source_files='IGNORED_HF; no source text in staged metrics',automatic_75M_admission=False)
    training.write(CORPUS/'report.json',report);training.write(EVIDENCE/'corpus_report.json',report)
    print('[GROUNDED_SPAN_CORPUS] '+json.dumps(dict(counts=counts,supply=supply,updates=n)),flush=True)
    return 0


def read_course():
    r=required(CORPUS/'report.json')
    if r['status']!='GROUNDED_SPAN_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:
        raise ValueError('frozen code changed; preserve old namespace')
    if public.digest(ROOT/r['native_train_file'])!=r['native_train_sha256'] or public.digest(NATIVE/'val.bin')!=r['native_val_sha256']:
        raise ValueError('native source changed')
    rows={s:list(public.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}
    labels={x['signature']:x['location'] for x in public.stream_rows(CORPUS,r['labels_manifest'])}
    return r,rows,labels


def padded(records,pad,device='cuda'):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_padding_probe import width
    return core.pad_records(records,pad,device,fixed_width=width([len(x.x) for x in records],True),batch_size=8)


def loss_eval(model,head,rows,labels,tok,pad):
    import torch
    from tinylm.train import mtp_sft as core
    totals=Counter();model.eval()
    with torch.no_grad():
        for i in range(0,len(rows),8):
            selected=rows[i:i+8];records=[core.encode_record(r,tok) for r in selected]
            ll=[labels.get(method.sha(r['messages'])) for r in selected]+[None]*(8-len(selected))
            x,y,seg=padded(records,pad)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hidden=model(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=(),checkpoint_heads=False)
                loss,n,c,both=method.auxiliary_sum(head,hidden,ll)
            totals.update(sft_sum=float(sums[1]),sft_targets=valid[1],span_sum=float(loss),span_rows=n,span_boundaries_correct=c,span_both_correct=both)
    model.train()
    return dict(totals,sft_ce=totals['sft_sum']/totals['sft_targets'],span_ce=totals['span_sum']/totals['span_rows'],
        scope='teacher-forced DEV loss and source location, not free answer correctness')


def forecast(r,remaining):
    costs={}
    for arm in method.ARMS:
        report=required(EVIDENCE/('cost_'+arm)/'report.json')
        if report['code_sha256']!=info()['code_sha256'] or report['updates']!=8:raise ValueError('same-code cost8 required')
        steady=report['step_seconds'][1:]
        if len(steady)!=7 or any(not math.isfinite(x) or x<=0 for x in steady):raise ValueError('seven actual steady costs required')
        costs[arm]=dict(p95=max(steady),estimate_sec=max(steady)*r['expected_updates']+600)
    completed=[a for a in method.ARMS if (EVIDENCE/a/'report.json').is_file()]
    need=sum(v['estimate_sec'] for a,v in costs.items() if a not in completed)+1200+2700
    return dict(costs=costs,completed=completed,remaining_sec=remaining,needed_sec=need,fits=need<remaining,
        scope='forecast not guarantee;1200evaluation/2700closure margin')


def train(args,cost=False):
    from tinylm.train import mtp_sft as core
    r,rows,labels=read_course();arm=args.arm;weight=method.ARMS[arm]
    target=EVIDENCE/(('cost_' if cost else '')+arm);out=checkpoint(arm)
    if target.exists() or (not cost and out.exists()):raise GateNegative('previous arm preserved')
    if not cost:
        budget=forecast(r,(DEADLINE-datetime.now(timezone.utc)).total_seconds())
        print('[GROUNDED_SPAN_BUDGET] '+json.dumps(budget),flush=True)
        if not budget['fits']:raise GateNegative('both arms/evaluation/closing margin must fit')
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        torch,model,cfg,tok,initial=training.load_runtime('parent_ntp');model=model.cuda();model.train()
        head=method.new_head(cfg.dim,'cuda');head_before={k:v.detach().cpu().clone() for k,v in head.state_dict().items()}
        if training.state_fingerprint(model)!=initial:raise ValueError('head initialization changed body')
        records=[core.encode_record(x,tok) for x in rows['train']]
        lookup={id(rec):labels.get(method.sha(row['messages'])) for rec,row in zip(records,rows['train'])}
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('pad missing')
        native=native_reader(ROOT,r);os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_grounded_span_')
        torch.cuda.reset_peak_memory_stats();before=None if cost else training.native_ce(model,NATIVE)
        compiled=torch.compile(model,mode='default');adam,muon=training.optimizers(model)
        for opt in (adam,muon):
            for g in opt.param_groups:g['lr']*=.5
        head_opt=torch.optim.AdamW(head.parameters(),lr=.001,weight_decay=0)
        steps=sft_x=assistant=native_x=span_rows=0;history=[];seconds=[];grad_max=0.;clip_events=0;span_sum=0.
        for epoch in range(4):
            for group in training.batches(records,epoch):
                deadline();tick=time.perf_counter();denom=sum(rec.targets for micro in group for rec in micro)
                adenom=sum(lookup[id(rec)] is not None for micro in group for rec in micro)
                if adenom<=0:raise ValueError('natural QA per update required')
                for opt in (adam,muon,head_opt):opt.zero_grad(set_to_none=True)
                for micro in group:
                    ll=[lookup[id(rec)] for rec in micro]+[None]*(8-len(micro));x,y,seg=padded(micro,pad)
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=compiled(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=())
                        extra,n,correct,both=method.auxiliary_sum(head,hidden,ll);loss=sums[1]/denom+weight*extra/adenom
                    if not torch.isfinite(loss):raise ValueError('nonfinite training loss')
                    loss.backward();sft_x+=sum(rec.x_tokens for rec in micro);assistant+=sum(rec.targets for rec in micro)
                    span_rows+=n;span_sum+=float(extra.detach())
                selected=native[steps*8:(steps+1)*8]
                nr=[core.Record(a[:-1].astype('int64').tolist(),a[1:].astype('int64').tolist(),[1]*1024) for a in selected]
                x,y,seg=core.pad_records(nr,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    h=compiled(x,return_hidden=True);sums,valid=core.components(model,h,y,seg,horizons=());loss=sums[1]/8192
                loss.backward();native_x+=8192
                grad=torch.nn.utils.clip_grad_norm_([*model.parameters(),*head.parameters()],1.)
                if not torch.isfinite(grad):raise ValueError('nonfinite gradient')
                grad_max=max(grad_max,float(grad));clip_events+=int(grad>1.)
                for opt in (adam,muon,head_opt):opt.step()
                steps+=1;torch.cuda.synchronize();seconds.append(time.perf_counter()-tick)
                if steps==1 or steps%8==0:print('[GROUNDED_SPAN_UPDATE] '+json.dumps(dict(arm=arm,updates=steps,
                    sft_x_tokens=sft_x,assistant_targets=assistant,native_x_tokens=native_x,span_rows=span_rows,last_sec=seconds[-1])),flush=True)
                if cost and steps==8:break
            if cost:break
            history.append(dict(epoch=epoch+1,updates=steps,dev=loss_eval(model,head,rows['dev'],labels,tok,pad),native=training.native_ce(model,NATIVE)))
            print('[GROUNDED_SPAN_EPOCH] '+json.dumps(dict(arm=arm,**history[-1])),flush=True)
        if not cost and (steps!=r['expected_updates'] or sft_x!=4*r['counts']['train']['actual_x_tokens'] or assistant!=4*r['counts']['train']['assistant_targets']
                or span_rows!=4*r['auxiliary_train_rows'] or native_x!=8192*steps):raise ValueError('actual planned exposure mismatch')
        change=float(sum((v.detach().cpu()-head_before[k]).square().sum() for k,v in head.state_dict().items()).sqrt())
        if (not weight and change!=0) or (weight and change==0):raise ValueError('zero/active auxiliary update postcondition')
        result=dict(info(),status='COST_MEASURED' if cost else 'TRAINED_TEST_PENDING',arm=arm,weight=weight,updates=steps,
            corpus_sha256=public.digest(CORPUS/'report.json'),initial_core_sha256=initial,sft_x_tokens=sft_x,
            assistant_targets=assistant,native_x_tokens=native_x,span_rows_computed=span_rows,span_rows_active=span_rows if weight else 0,
            span_cumulative_ce=span_sum/span_rows,auxiliary_parameter_delta_l2=change,auxiliary_parameters=sum(p.numel() for p in head.parameters()),
            head_in_normal_model_state=False,head_in_free_generation=False,step_seconds=seconds,history=history,
            native_before=before,grad_max=grad_max,gradient_clip=1.,clip_events=clip_events,
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,whole_sec=time.perf_counter()-began,
            actual_quality='NOT_EVALUATED',optimizer_saved=False)
        if not cost:
            with out.open('xb') as stream:torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=steps,
                tokenizer_sha256=public.TOK_SHA,tokenizer_lineage='chat32',training_only_auxiliary=head.state_dict(),
                auxiliary_method=dict(tag=TAG,arm=arm)),stream)
            result.update(checkpoint=str(out.relative_to(ROOT)),checkpoint_sha256=public.digest(out))
        training.write(target/'report.json',result)
    print('[GROUNDED_SPAN_FINAL] '+json.dumps(dict(arm=arm,status=result['status'],updates=steps,whole_sec=result['whole_sec'])),flush=True)
    return 0


def generate(model,cfg,tok,rows,directory,label,max_new=64):
    import torch
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    writer=ShardWriter(directory,'answers_'+label);counts=defaultdict(Counter)
    model.eval();model.freeze_quant();wrapped=PrecisionForward(model,'fp32_math')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    try:
        with torch.no_grad():
            for row in rows:
                deadline();m=row['meta'];prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
                cap=min(max_new,cfg.max_seq_len-len(tok.encode(prompt).ids))
                if cap<1:raise ValueError('no generation room')
                output,meta=sample(wrapped,cfg,tok,prompt,max_new=cap,temperature=0.,top_k=1,device='cuda',logits_last_only=True,
                    return_metadata=True,stop_token_sequences=[tok.encode('<|im_end|>').ids])
                prefix=tok.decode(tok.encode(prompt).ids)
                if not output.startswith(prefix):raise ValueError('exact decoded prefix missing')
                answer=output[len(prefix):];gold=method.text(row['messages'][-1]);same=answer.strip()==gold.strip()
                judged=rules.exact(answer,gold,m['rubric']) if m['rubric'] in ('EXACT_SCALAR','EXACT_BOOLEAN','EXACT_INTEGER','EXACT_JSON_OBJECT') else None
                lane=m['language']+':'+m['kind'];counts[lane].update(cases=1,literal=int(same),code_exact=int(judged is True),code_scored=int(judged is not None),
                    token_f1=method.token_f1(answer,gold),empty=int(not answer.strip()),max_new=int(meta['finish_reason'].startswith('MAX_NEW')))
                writer.append(dict(messages=row['messages'][:-1],answer=answer,gold=gold,meta=m,generation=meta,
                    literal=same,exact_code_contract=judged,semantic_truth='SOURCE_UNVERIFIED; literal equality is not world truth',auxiliary_used=False))
    finally:model.clear_quant();model.train()
    manifest=writer.close(lineage=dict(precision='FP32_MATH',temperature=0,top_k=1,max_new=max_new,auxiliary_used=False,student_mtp=False))
    verify(directory,manifest)
    return dict(counts={k:dict(v) for k,v in counts.items()},manifest=manifest,directory=str(directory.relative_to(ROOT)),scope='literal source target + lexical F1, not a semantic judge')


def evaluate(args):
    import torch
    from tinylm.infer.generate import _strip
    r,rows,labels=read_course();target=EVIDENCE/'evaluate'
    if target.exists():raise GateNegative('previous evaluation preserved')
    reports={a:required(EVIDENCE/a/'report.json') for a in method.ARMS}
    for a,report in reports.items():
        if report['status']!='TRAINED_TEST_PENDING' or report['code_sha256']!=info()['code_sha256'] or public.digest(ROOT/report['checkpoint'])!=report['checkpoint_sha256']:
            raise ValueError('same-code completed two arms required')
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter();arms={}
    selected=[]
    for lang in ('ko','en'):selected.extend([x for x in rows['train'] if x['meta']['kind']=='natural_first_qa' and x['meta']['language']==lang][:16])
    with wall_limit(args.max_wall_sec):
        for arm in ('parent',*method.ARMS):
            torch,model,cfg,tok,initial=training.load_runtime('parent_ntp')
            if arm!='parent':
                saved=torch.load(ROOT/reports[arm]['checkpoint'],map_location='cpu',weights_only=True)
                model.load_state_dict(_strip(saved['model']),strict=True);del saved
            model=model.cuda();directory=LOCAL/'evaluate'/arm
            value=dict(test=generate(model,cfg,tok,rows['test'],directory,'test'),train_diagnostic=generate(model,cfg,tok,selected,directory,'train32'),native=training.native_ce(model,NATIVE))
            old=required(ROOT/'HF/sft_ready/p106b_binding_aux_v1_s1337/corpus/report.json')
            panel=list(public.stream_rows(ROOT/'HF/sft_ready/p106b_binding_aux_v1_s1337/corpus',old['manifests']['public_eval']))
            # Existing helper has an expired historical deadline: do not patch it.
            value['public_dev16']=generate(model,cfg,tok,panel,directory,'old_public_dev16',max_new=256)
            code_test=list(public.stream_rows(ROOT/'HF/sft_ready/p106b_binding_aux_v1_s1337/corpus',old['manifests']['test']))
            value['old_code640']=generate(model,cfg,tok,code_test,directory,'old_code640')
            from scripts.p106b_education_followup import answers
            from scripts.diag_p101a_mtp_parity import PrecisionForward
            value['legacy8']=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8')
            arms[arm]=value
            training.write(target/(arm+'_report.json'),dict(info(),arm=arm,metrics=value))
            print('[GROUNDED_SPAN_EVAL] '+json.dumps(dict(arm=arm,test=value['test']['counts'],train32=value['train_diagnostic']['counts'],native=value['native'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    result=dict(info(),status='GROUNDED_SPAN_EVALUATED',arms=arms,cases_per_arm=len(rows['test']),
        whole_sec=time.perf_counter()-began,evaluation_uses_auxiliary=False,world_truth='NOT_RUN',
        interpretation='source document holdout; cross-language semantic and pretraining overlap not excluded')
    training.write(target/'report.json',result);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','cost','train','evaluate'),required=True)
    p.add_argument('--arm',choices=tuple(method.ARMS),default='span0');p.add_argument('--max-wall-sec',type=int,default=7200)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=21600:p.error('wall range60..21600')
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        deadline();margin=2700 if a.mode=='train' else 600
        a.max_wall_sec=min(a.max_wall_sec,int((DEADLINE-datetime.now(timezone.utc)).total_seconds())-margin)
        if a.max_wall_sec<60:raise GateNegative('closing margin before authorized deadline')
        if a.mode=='freeze':return freeze()
        if a.mode=='evaluate':return evaluate(a)
        return train(a,cost=a.mode=='cost')
    except GateNegative as exc:print('[GROUNDED_SPAN_HOLD] '+str(exc),flush=True);return 8
    except KeyboardInterrupt:print('[GROUNDED_SPAN_INTERRUPTED] partial new output preserved',flush=True);return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[GROUNDED_SPAN_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return 9


if __name__=='__main__':raise SystemExit(main())
