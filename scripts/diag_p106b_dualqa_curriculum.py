#!/usr/bin/env python3
"""Same-parent, exposure-matched four-epoch repeat/contrast SFT; fresh outputs."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
import copy
import json
import math
import os
import tempfile
import time
from scripts import p106b_dualqa_course as data
from scripts import diag_p106b_dualqa_production as producer
from scripts import diag_p106b_binding_auxiliary as old_code
from scripts import diag_p101a_sft_mtp as training
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_native_windows import NATIVE_TRAIN,reader as native_reader
TAG='p106b_dualqa_curriculum_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
NATIVE=producer.legacy.source.NATIVE
CODE=(*training.CODE,*producer.CODE,*old_code.CODE,'scripts/diag_p106b_dualqa_curriculum.py','scripts/test_p106b_dualqa_curriculum.py',
      'scripts/p106b_dualqa_course.py','scripts/test_p106b_dualqa_course.py','scripts/p106b_binding_auxiliary.py',
      'scripts/p106b_native_windows.py','scripts/p106b_padding_probe.py','scripts/p106b_shards.py')


def info():
    return dict(schema=data.VERSION,tag=TAG,code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        parent=str(producer.PARENT.relative_to(ROOT)),parent_sha256=producer.PARENT_SHA,
        tokenizer_sha256=training.data.TOK_SHA,seed=1337,micro_bs=8,accum=16,seq=1024,
        epochs=4,expected_updates=176,grad_checkpoint=True,compile='default',lr=5e-5,muon_lr=2e-4,
        matrix_weight_decay=0,native_weight=1.,native_rows_per_update=8,gradient_clip=1.,
        arms=list(data.ARMS),epoch_pairing=dict(repeat=['Q1Q1','Q2Q2','Q1Q1','Q2Q2'],contrast=['Q1Q2','Q2Q1','Q1Q2','Q2Q1']),
        common_code_auxiliary=1.,code_head_parameters=1538,code_head_scope='verified code binding causal suffix only',
        source_qa_semantic_labels_inferred=False,head_used_in_inference=False,source_span_head_used=False,
        student_mtp=False,teacher_data_parser='OPTIONAL_NOTE_V2',
        padding='SFT right align128 max1024; native1024',formal_train_ready=False,
        deadline_utc=producer.legacy.source.DEADLINE.isoformat(),scope='matched curriculum study, not75M/300M or world intelligence')


def checkpoint(arm,epoch=None):
    return ROOT/'runs/ckpt'/f"m100s10_ko-en_dualqa_dense_chat32_{TAG}_{arm}{'_epoch'+str(epoch) if epoch else ''}.pt"


def write_rows(directory,name,rows,lineage):
    w=ShardWriter(directory,name)
    for row in rows:w.append(row)
    m=w.close(lineage=lineage);verify(directory,m);return m


def freeze():
    from tokenizers import Tokenizer
    from tinylm.train.mtp_sft import encode_record
    import numpy as np
    producer.legacy.source.deadline()
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old course namespace preserved')
    source,jobs,processed,counts,batch_refs=producer.state()
    if not producer.quotas_met(counts):raise GateNegative('complete six source quotas required before student')
    if training.data.digest(producer.PARENT)!=producer.PARENT_SHA or training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:
        raise ValueError('selected parent/tokenizer changed')
    tok=Tokenizer.from_file(str(training.data.TOKENIZER));students={s:[] for s in ('train','dev','test')}
    accepted_roots=set();references=[]
    for ref in batch_refs:
        rp=ROOT/ref['path'];b=json.loads(rp.read_text());directory=rp.parent
        good={x['root'] for x in b['results'] if x['accepted']}
        if not b['candidate_manifest']:
            if good:raise ValueError('accepted roots without sealed candidates')
            continue
        for candidate in training.data.stream_rows(directory,b['candidate_manifest']):
            if candidate['root'] not in good:continue
            row=candidate['student'];root=row['meta']['semantic_root_id']
            if root in accepted_roots:raise ValueError('same source accepted twice')
            accepted_roots.add(root);students[row['meta']['source_split']].append(row)
        references.append(ref)
    for split,n in producer.data.TARGETS.items():
        students[split].sort(key=lambda r:(r['meta']['language'],r['meta']['semantic_root_id']))
        if Counter(r['meta']['language'] for r in students[split])!=dict(ko=n,en=n):raise ValueError('exact source quotas and unique contexts required')
    old,old_rows=old_code.read_course();code=data.code_rows(old_rows,TAG)
    contract=data.known_contract(code,tok,data.binding.approved_questions())
    if len(contract)!=3072:raise ValueError('only verified3072 code binding rows get labels')
    train_views,proof=data.marginal_proof(students['train'],tok);rows={};counts_by_view={}
    for arm in data.ARMS:
        for parity in (0,1):
            key=arm+str(parity);rows[key]=train_views[arm,parity]+copy.deepcopy(code)
            counts_by_view[key]=data.totals(rows[key],tok)[0]
            if counts_by_view[key]['rows']!=5632:raise ValueError('source1536 +code4096 rows required')
    code_dev=[copy.deepcopy(r) for r in old_rows['dev'] if r['meta']['kind']!='public_qa']
    if len(code_dev)!=640:raise ValueError('known code dev640 required')
    rows['dev']=[data.view(r,'contrast',p,tok) for p in (0,1) for r in students['dev']]+code_dev
    rows['test_source']=students['test'];rows['code_retention_dev']=copy.deepcopy(old_rows['test'])
    jobmap={j['root']:j for j in jobs};bridges=[]
    for r in students['test']:
        j=jobmap[r['meta']['semantic_root_id']]
        from tinylm.chat.canonical import normalize,validate
        prefix=producer.legacy.method.POLICY[j['language']]
        q=prefix+j['reference']+('\n질문:\n' if j['language']=='ko' else '\nQuestion:\n')+j['bridge_question']
        row=validate(normalize(dict(messages=[dict(role='user',content=q),dict(role='assistant',content=j['bridge_gold'])],
            meta=dict(r['meta'],kind='public_qa',rubric='UNSCORED_PUBLIC_QA',bridge='ORIGINAL_PUBLIC_FIRST_QA_UNVERIFIED'))))
        encode_record(row,tok);bridges.append(row)
    rows['test_bridge']=bridges
    for split in ('dev','test_source','code_retention_dev','test_bridge'):counts_by_view[split]=data.totals(rows[split],tok)[0]
    teacher4=proof['summary']['repeat'];code_counts=data.totals(code,tok)[0]
    expected=dict(sft_x_tokens=teacher4['x_tokens']+4*code_counts['x_tokens'],
        assistant_targets=teacher4['assistant_targets']+4*code_counts['assistant_targets'],native_x_tokens=176*8192,
        code_auxiliary_rows=4*len(contract),code_auxiliary_position_events=4*sum(len(x['positions']) for x in contract.values()))
    native=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r')
    previous=producer.legacy.source.required(producer.legacy.source.CORPUS/'report.json')
    exclude=set(previous['native_train_offsets'])
    old_native=producer.legacy.source.required(ROOT/'HF/sft_ready/p106b_context_replay_v2_s1337/corpus/report.json')
    exclude.update(old_native['native_train_offsets'])
    offsets=[i for i in data.binding.prior.source.native_offsets(len(native),176*8+len(exclude)+1024) if i not in exclude][:176*8]
    if len(offsets)!=1408 or len(set(offsets))!=1408:raise ValueError('disjoint native train windows required')
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={k:write_rows(CORPUS,k,values,info()) for k,values in rows.items()}
    labels_manifest=write_rows(CORPUS,'code_labels',[dict(signature=k,**v) for k,v in sorted(contract.items())],dict(schema=data.VERSION))
    result=dict(info(),status='DUALQA_MATCHED_COURSE_FROZEN',producer_inputs_sha256=training.data.digest(producer.OUTPUT/'inputs.json'),
        producer_batch_refs=references,producer_code_sha256=source['code_sha256'],counts=counts_by_view,manifests=manifests,
        labels_manifest=labels_manifest,source_contexts={s:len(v) for s,v in students.items()},
        marginal_exposure_proof=proof,expected_exposures=expected,source_qa_truth='TEACHER_PSEUDO_UNVERIFIED',
        code_truth='PRODUCER_EXACT_CONTRACT',native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,
        native_train_offsets=offsets,native_train_sha256=training.data.digest(ROOT/NATIVE_TRAIN),
        native_val_sha256=training.data.digest(NATIVE/'val.bin'),save_epoch_checkpoints=True,
        independent_world_truth=False,cross_language_semantic_overlap='NOT_AUDITED',
        old_source_test_reused_only_for_parent_development=True,new_final_source_from_reserve_not_old_test=True)
    training.write(CORPUS/'report.json',result);training.write(EVIDENCE/'corpus_report.json',result)
    print('[DUALQA_MATCHED_COURSE] '+json.dumps(dict(counts=counts_by_view,expected_exposures=expected,marginals_match=True)),flush=True)
    return 0


def read_course():
    r=producer.legacy.source.required(CORPUS/'report.json')
    if r['status']!='DUALQA_MATCHED_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:raise ValueError('same frozen student code required')
    if training.data.digest(producer.PARENT)!=producer.PARENT_SHA or training.data.digest(ROOT/r['native_train_file'])!=r['native_train_sha256'] or training.data.digest(NATIVE/'val.bin')!=r['native_val_sha256']:
        raise ValueError('immutable parent/cache changed')
    rows={s:list(training.data.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}
    labels={x['signature']:{k:v for k,v in x.items() if k!='signature'} for x in training.data.stream_rows(CORPUS,r['labels_manifest'])}
    return r,rows,labels


def load_parent():
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    if training.data.digest(producer.PARENT)!=producer.PARENT_SHA or training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('parent/tokenizer identity differs')
    state=torch.load(producer.PARENT,map_location='cpu',weights_only=True)
    if state['tokenizer_sha256']!=training.data.TOK_SHA or not isinstance(state['cfg'],dict):raise ValueError('exact saved chat32 lineage required')
    cfg=TMTConfig(**state['cfg']);cfg.grad_checkpoint=True
    if (cfg.n_layers,cfg.dim,cfg.ffn_dim,cfg.vocab_size,cfg.max_seq_len)!=(14,768,2048,32768,1024) or cfg.tie_mlp or cfg.mtp_aux:raise ValueError('dense14/R1/noMTP geometry required')
    torch.manual_seed(1337);model=TiedMLPTransformer(cfg);model.load_state_dict(_strip(state['model']),strict=True);del state
    model.set_anneal(1.);model.eval()
    if list(model.visit_schedule())!=list(range(14)):raise ValueError('R1 visits required')
    model.train();return torch,model,cfg,Tokenizer.from_file(str(training.data.TOKENIZER)),training.state_fingerprint(model)


def padded(records,pad,device='cuda'):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_padding_probe import width
    return core.pad_records(records,pad,device,fixed_width=width([len(r.x) for r in records],True),batch_size=8)


def sft_objective(word_sum,word_denom,auxiliary_sum,auxiliary_denom):
    if word_denom<=0 or auxiliary_denom<0:raise ValueError('whole update denominators required')
    return word_sum/word_denom+(auxiliary_sum/auxiliary_denom if auxiliary_denom else auxiliary_sum*0)


def loss_eval(model,head,tok,rows,labels,pad):
    import torch
    from tinylm.train import mtp_sft as core
    totals=Counter();model.eval()
    with torch.no_grad():
        for i in range(0,len(rows),8):
            chosen=rows[i:i+8];records=[core.encode_record(r,tok) for r in chosen];x,y,seg=padded(records,pad)
            known=[labels.get(data.binding.prior.source.sha(r['messages'])) for r in chosen]+[None]*(8-len(chosen))
            bits=[v['bit'] if v else None for v in known];windows=[v['positions'] if v else None for v in known]
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hidden=model(x,return_hidden=True)
                for is_source,name in ((True,'source'),(False,'code')):
                    mask=torch.tensor([r['meta']['kind']=='public_qa' for r in chosen]+[False]*(8-len(chosen)),device='cuda')
                    if not is_source:mask=~mask
                    target=y.masked_fill(~mask[:,None],-100)
                    sums,valid=core.components(model,hidden,target,seg,horizons=(),checkpoint_heads=False)
                    totals[name+'_sum']+=float(sums[1]);totals[name+'_targets']+=valid[1]
                extra,n,c,events=data.binding.suffix_auxiliary_sum(head,hidden,y,bits,windows,dense=True)
            totals.update(auxiliary_sum=float(extra),auxiliary_rows=n,auxiliary_correct=c)
    model.train();return dict(totals,source_ce=totals['source_sum']/totals['source_targets'],code_ce=totals['code_sum']/totals['code_targets'],
        scope='same DEV teacher-forced source/code and known query bit; not free or semantic answers')


def budget(r):
    costs={}
    for arm in data.ARMS:
        p=EVIDENCE/('cost_'+arm)/'report.json';c=producer.legacy.source.required(p)
        if c['code_sha256']!=info()['code_sha256'] or c['updates']!=8:raise ValueError('same-code actual costs8 required')
        steady=c['step_seconds'][1:]
        if len(steady)!=7 or any(not math.isfinite(x) or x<=0 for x in steady):raise ValueError('seven finite steady costs required')
        costs[arm]=max(steady)*176+900
    completed=[a for a in data.ARMS if (EVIDENCE/a/'report.json').is_file()]
    needed=sum(v for k,v in costs.items() if k not in completed)+2400+2700
    remaining=(producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    return dict(estimates_sec=costs,completed=completed,needed_sec=needed,remaining_sec=remaining,fits=needed<remaining,
        scope='forecast; includes2400 evaluation and2700 closure, not guaranteed upper bound')


def train(args,cost=False):
    from tinylm.train import mtp_sft as core
    r,rows,labels=read_course();arm=args.arm;target=EVIDENCE/(('cost_' if cost else '')+arm)
    if target.exists() or (not cost and any(checkpoint(arm,e).exists() for e in (None,1,2,3))):raise GateNegative('old arm outputs preserved')
    if not cost:
        b=budget(r);print('[DUALQA_STUDENT_BUDGET] '+json.dumps(b),flush=True)
        if not b['fits']:raise GateNegative('both courses/evaluation/closure must fit before17')
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        torch,model,cfg,tok,initial=load_parent();model=model.cuda();model.train()
        cpu_rng=torch.random.get_rng_state().clone();cuda_rng=torch.cuda.get_rng_state().clone()
        head=data.binding.new_head(cfg.dim,'cuda')
        if not torch.equal(cpu_rng,torch.random.get_rng_state()) or not torch.equal(cuda_rng,torch.cuda.get_rng_state()):raise ValueError('head RNG changed')
        if training.state_fingerprint(model)!=initial:raise ValueError('head changed body initialization')
        encoded={p:[core.encode_record(row,tok) for row in rows[arm+str(p)]] for p in (0,1)}
        labels_by_id={};windows_by_id={}
        for parity,records in encoded.items():
            for row,record in zip(rows[arm+str(parity)],records):
                known=labels.get(data.binding.prior.source.sha(row['messages']))
                labels_by_id[id(record)]=known['bit'] if known else None;windows_by_id[id(record)]=known['positions'] if known else None
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('pad absent')
        native=native_reader(ROOT,r);torch.cuda.reset_peak_memory_stats();before=None if cost else training.native_ce(model,NATIVE)
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_dualqa_curriculum_')
        compiled=torch.compile(model,mode='default');adam,muon=training.optimizers(model)
        for opt in (adam,muon):
            for g in opt.param_groups:g['lr']*=.5
        head_opt=torch.optim.AdamW(head.parameters(),lr=.001,weight_decay=0)
        steps=sft_x=assistant=native_x=aux_rows=aux_positions=padded_x=0;history=[];seconds=[];grad_max=0.;clip_events=0
        dev_approved=data.binding.approved_questions('dev');dev_labels=data.known_contract([x for x in rows['dev'] if x['meta']['kind']!='public_qa'],tok,dev_approved)
        all_labels={**labels,**dev_labels}
        for epoch in range(4):
            for group in training.batches(encoded[epoch%2],epoch):
                producer.legacy.source.deadline();tick=time.perf_counter();denom=sum(rec.targets for micro in group for rec in micro)
                aux_denom=sum(labels_by_id[id(rec)] is not None for micro in group for rec in micro)
                for opt in (adam,muon,head_opt):opt.zero_grad(set_to_none=True)
                for micro in group:
                    x,y,seg=padded(micro,pad);bits=[labels_by_id[id(rec)] for rec in micro]+[None]*(8-len(micro));windows=[windows_by_id[id(rec)] for rec in micro]+[None]*(8-len(micro))
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=compiled(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=())
                        extra,n,c,events=data.binding.suffix_auxiliary_sum(head,hidden,y,bits,windows,dense=True)
                        loss=sft_objective(sums[1],denom,extra,aux_denom)
                    if not torch.isfinite(loss):raise ValueError('nonfinite word/query loss')
                    loss.backward();sft_x+=sum(rec.x_tokens for rec in micro);assistant+=sum(rec.targets for rec in micro)
                    aux_rows+=n;aux_positions+=events;padded_x+=x.numel()
                nr=[core.Record(a[:-1].astype('int64').tolist(),a[1:].astype('int64').tolist(),[1]*1024) for a in native[steps*8:(steps+1)*8]]
                if len(nr)!=8:raise ValueError('native train schedule exhausted')
                x,y,seg=core.pad_records(nr,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=compiled(x,return_hidden=True);sums,valid=core.components(model,hidden,y,seg,horizons=());loss=sums[1]/8192
                loss.backward();native_x+=8192
                grad=torch.nn.utils.clip_grad_norm_([*model.parameters(),*head.parameters()],1.)
                if not torch.isfinite(grad):raise ValueError('nonfinite gradient')
                grad_max=max(grad_max,float(grad));clip_events+=int(grad>1.)
                adam.step();muon.step()
                if aux_denom:head_opt.step()
                steps+=1;torch.cuda.synchronize();seconds.append(time.perf_counter()-tick)
                if steps==1 or steps%16==0:print('[DUALQA_STUDENT_UPDATE] '+json.dumps(dict(arm=arm,epoch=epoch+1,updates=steps,sft_x=sft_x,assistant=assistant,native_x=native_x,auxiliary_rows=aux_rows,last_sec=seconds[-1])),flush=True)
                if cost and steps==8:break
            if cost:break
            dev=loss_eval(model,head,tok,rows['dev'],all_labels,pad);native_eval=training.native_ce(model,NATIVE)
            cp=checkpoint(arm,None if epoch==3 else epoch+1)
            with cp.open('xb') as stream:torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=steps,
                tokenizer_sha256=training.data.TOK_SHA,tokenizer_lineage='chat32',training_only_auxiliary=head.state_dict(),
                curriculum=dict(tag=TAG,arm=arm,epoch=epoch+1),optimizer_saved=False),stream)
            history.append(dict(epoch=epoch+1,updates=steps,dev=dev,native=native_eval,checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=training.data.digest(cp)))
            print('[DUALQA_STUDENT_EPOCH] '+json.dumps(dict(arm=arm,**history[-1])),flush=True)
        expected=r['expected_exposures']
        if not cost and (steps!=176 or sft_x!=expected['sft_x_tokens'] or assistant!=expected['assistant_targets'] or native_x!=expected['native_x_tokens'] or aux_rows!=expected['code_auxiliary_rows'] or aux_positions!=expected['code_auxiliary_position_events']):raise ValueError('planned marginal exposure mismatch')
        norm=float(sum(p.detach().square().sum() for p in head.parameters()).sqrt())
        if norm==0:raise ValueError('known-code head never updated')
        result=dict(info(),status='COST_MEASURED' if cost else 'TRAINED_NEW_SOURCE_TEST_PENDING',arm=arm,updates=steps,
            corpus_sha256=training.data.digest(CORPUS/'report.json'),initial_core_sha256=initial,
            sft_x_tokens=sft_x,assistant_targets=assistant,native_x_tokens=native_x,padded_sft_tokens=padded_x,
            auxiliary_rows=aux_rows,auxiliary_position_events=aux_positions,auxiliary_parameter_l2=norm,
            head_not_in_normal_model_state=True,head_in_free_generation=False,native_before=before,history=history,
            step_seconds=seconds,grad_max=grad_max,clip_events=clip_events,gradient_clip=1.,
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,whole_sec=time.perf_counter()-began,
            optimizer_saved=False,actual_model_history_dialogues='NOT_RUN')
        if not cost:
            result.update(checkpoint=str(checkpoint(arm).relative_to(ROOT)),checkpoint_sha256=training.data.digest(checkpoint(arm)),
                dev_best_epoch_by_source_ce=min(history,key=lambda x:x['dev']['source_ce'])['epoch'],
                dev_best_scope='secondary candidate only; primary paired test uses final4epoch')
        training.write(target/'report.json',result)
    print('[DUALQA_STUDENT_FINAL] '+json.dumps(dict(arm=arm,status=result['status'],updates=steps,whole_sec=result['whole_sec'])),flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','cost','train'),required=True)
    p.add_argument('--arm',choices=data.ARMS,default='repeat');p.add_argument('--max-wall-sec',type=int,default=7200)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=14400:p.error('bounded60..14400')
    if a.mode=='freeze' and a.arm!='repeat':p.error('--arm applies only to cost/train; cannot ignore a nondefault arm')
    if a.check_only:print('[DUALQA_STUDENT_CHECK_ONLY] '+json.dumps(info()));return 0
    if not a.execute:p.error('explicit execution required')
    try:
        producer.legacy.source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closing margin required')
        if a.mode=='freeze':return freeze()
        return train(a,cost=a.mode=='cost')
    except GateNegative as exc:print('[DUALQA_STUDENT_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[DUALQA_STUDENT_INTERRUPTED] preserve partial evidence and epoch checkpoints');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_STUDENT_ERROR] '+type(exc).__name__+': '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
