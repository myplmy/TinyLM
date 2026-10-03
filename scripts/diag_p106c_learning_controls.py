#!/usr/bin/env python3
"""Stage8Wa/Wb/Wc: scratch32, order128, and familiar-name32 separate controls.

Bounded user-authorized research, no teacher/production training. Frozen old
outputs are read-only; each mode has a new immutable output directory.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import gc
import itertools
import json
import os
from pathlib import Path
import random
import re
import shutil
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.diag_p106c_order_pair import (SOURCE,SOURCE_SHA,CALIBRATION_SHA,ARMS,
    A_PATH,A_SHA,require_a,materialize,order_variant,evaluation_grid,write_json,
    training_history_evidence,frozen_role,digest,data_hash,canonical)
from scripts.p106c_replay import Runner,code_contract
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition

MODES=('initialization','horizon','names')


def extend_draws(prefix,roles,steps=128,cap=16):
    if len(prefix)!=32 or steps!=128:
        raise ValueError('extension must preserve exact32 prefix and end at128')
    result=copy.deepcopy(prefix);rng=random.Random(20261004)
    counts={role:Counter() for role in roles}
    for batch in prefix:
        for field,role in (('candidate','train'),('rehearsal','rehearsal')):
            counts[role].update(batch[field][::2])
    decks={}
    for role,source in roles.items():
        for language in ('ko','en'):
            colors=sorted({r['gold'] for r in source if r['language']==language})
            if len(colors)!=4:raise ValueError('four colors required')
            edges={}
            for i in range(0,len(source),2):
                if source[i]['language']==language:
                    edge=tuple(sorted((source[i]['gold'],source[i+1]['gold'])))
                    edges[edge]=edges.get(edge,0)+cap-counts[role][i]
            cycles={}
            for tail in itertools.permutations(colors[1:]):
                cycle=[colors[0],*tail]
                key=tuple(sorted(tuple(sorted((cycle[k],cycle[(k+1)%4]))) for k in range(4)))
                cycles.setdefault(key,cycle)
            choices=list(cycles.items());remaining=steps-len(prefix);feasible=[]
            for n0 in range(remaining+1):
                for n1 in range(remaining-n0+1):
                    allocations=(n0,n1,remaining-n0-n1)
                    if all(sum(allocations[j] for j,(cy,_) in enumerate(choices) if edge in cy)<=capacity
                           for edge,capacity in edges.items()):
                        feasible.append(allocations)
            if not feasible:raise ValueError('balanced extension infeasible under exact prefix/cap')
            allocation=min(feasible,key=lambda ns:(sum((3*n-remaining)**2 for n in ns),ns))
            deck=[cycle for n,(_,cycle) in zip(allocation,choices) for _ in range(n)]
            rng.shuffle(deck);decks[(role,language)]=deck
    for offset in range(steps-32):
        batch={}
        for field,role in (('candidate','train'),('rehearsal','rehearsal')):
            source=roles[role];ids=[]
            for language in ('ko','en'):
                colors=decks[(role,language)][offset]
                for k in range(4):
                    desired={colors[k],colors[(k+1)%4]}
                    choices=[i for i in range(0,len(source),2) if source[i]['language']==language
                             and {source[i]['gold'],source[i+1]['gold']}==desired and counts[role][i]<cap]
                    if not choices:raise ValueError('bounded balanced extension infeasible')
                    i=rng.choice(choices);counts[role][i]+=1;ids.extend((i,i+1))
            batch[field]=ids
        result.append(batch)
    if max(v for c in counts.values() for v in c.values())>cap:raise ValueError('exposure cap exceeded')
    return result,{r:max(c.values()) for r,c in counts.items()}


def familiar(row):
    if row['task']!='context_lookup':return dict(row)
    pair=row['pair_id'].split('_table_')[0].split('_box_')[0]
    # Sealed grid IDs retain original pair prefix; source rows are role_number.
    names=('민수','지수') if row['language']=='ko' else ('Alice','Bob')
    question=row['question']
    for suffix,name in zip(('a','b'),names):
        question,n=re.subn(re.escape(pair+suffix)+r'(?![A-Za-z0-9_])',name,question)
        if n<1:raise ValueError('entity mapping absent; refuse broad replacement')
    return {**row,'question':question,'source_question':row['question'],
            'entity_transform':'a=민수/Alice;b=지수/Bob'}


def construct_random_model(cfg):
    """No checkpoint parameter is an input to this constructor."""
    from tinylm.model import TiedMLPTransformer
    return TiedMLPTransformer(cfg)


def scratch_student(arm,training=False):
    if arm!='b' or not training:raise ValueError('scratch diagnostic is training B geometry only')
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from scripts.p106b_education_followup import validate_parent_lineage
    from tinylm.train.optimizer_audit import matrix_decay_groups
    from tinylm.train.muon import Muon,split_params
    torch.set_num_threads(1);torch.manual_seed(1337)
    state=torch.load(ROOT/ARMS['b']['parent'],map_location='cpu',weights_only=True)
    tok=Tokenizer.from_file(str(ROOT/ARMS['b']['tokenizer']))
    validate_parent_lineage(state,ARMS['b']['tok_sha'],ARMS['b']['lineage'],tok)
    cfg=TMTConfig(**state['cfg']);del state  # Config provenance only; NO load_state_dict.
    if cfg.n_layers!=14 or cfg.tie_mlp or cfg.vocab_size!=32768:raise ValueError('scratch geometry drift')
    cfg.grad_checkpoint=True
    base=construct_random_model(cfg).cuda();base.set_anneal(1.0)
    os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106c_scratch_')
    model=torch.compile(base,mode='default')
    groups,_=matrix_decay_groups(model,1e-4,0);matrices,_=split_params(model)
    ids={id(p) for p in matrices}
    others=[dict(g,params=[p for p in g['params'] if id(p) not in ids]) for g in groups]
    adam=torch.optim.AdamW([g for g in others if g['params']],betas=(.9,.95),eps=1e-8)
    muon=Muon(matrices,lr=4e-4,scale_mode='rms',weight_decay=0)
    return torch,model,base,cfg,tok,adam,muon


def check(mode):
    output=ROOT/f'HF/sft_ready/p106c_learning_{mode}_v1'
    if output.exists() or output.is_symlink() or output.parent.is_symlink():
        raise FileExistsError('existing/partial output preserved; new stage required')
    if digest(SOURCE/'report.json')!=SOURCE_SHA or digest(A_PATH)!=A_SHA:raise ValueError('source report drift')
    require_a(json.loads(A_PATH.read_text(encoding='utf-8')))
    source=json.loads((SOURCE/'report.json').read_text(encoding='utf-8'))
    plan=json.loads((SOURCE/'batch_plan.json').read_text(encoding='utf-8'))
    if data_hash(plan)!=source['input']['plan_sha256']:raise ValueError('draw plan drift')
    for key,sha in (('parent','sha'),('tokenizer','tok_sha')):
        if digest(ROOT/ARMS['b'][key])!=ARMS['b'][sha]:raise ValueError('parent/tokenizer changed')
    if shutil.disk_usage(ROOT).free<8*2**30:raise ValueError('8GiB free disk needed; no cleanup')
    from tokenizers import Tokenizer
    from scripts.train_sft_p090 import encode_records
    tok=Tokenizer.from_file(str(ROOT/ARMS['b']['tokenizer']))
    roles={r:frozen_role(r) for r in ('train','rehearsal')}
    draws=plan['baseline'];maximum=None
    if mode=='horizon':draws,maximum=extend_draws(draws,roles)
    fixed=materialize(draws,roles,False)
    second=(materialize(draws,roles,True) if mode=='horizon' else
            [[familiar(r) for r in batch] for batch in fixed] if mode=='names' else copy.deepcopy(fixed))
    labels=('parent','scratch') if mode=='initialization' else ('fixed','mixed') if mode=='horizon' else ('coded','familiar')
    batches=dict(zip(labels,(fixed,second)))
    encoded={a:[encode_records([canonical(r) for r in rows],tok,256,32768) for rows in bs] for a,bs in batches.items()}
    for left,right in zip(*encoded.values()):
        if [tuple(v for v in y if v!=-100) for x,y,n in left]!=[tuple(v for v in y if v!=-100) for x,y,n in right]:
            raise ValueError('answer token mismatch')
        if mode!='names' and [len(x) for x,y,n in left]!=[len(x) for x,y,n in right]:raise ValueError('input token mismatch')
    info={'schema':'P106C_LEARNING_CONTROLS_PREFLIGHT_V1','mode':mode,'source_sha256':SOURCE_SHA,
          'parent_sha256':ARMS['b']['sha'],'tokenizer_sha256':ARMS['b']['tok_sha'],
          'batches_sha256':data_hash(batches),'prefix32_draws_match':draws[:32]==plan['baseline'],
          'max_pair_exposures':maximum,'updates_per_arm':len(draws),'micro':8,'accum':4,'context':256,
          'checkpoint_on':True,'max_wall_sec':1800,'teacher_requests':0,'code':code_contract(),
          'driver_sha256':digest(Path(__file__)),
          'order_helper_sha256':digest(ROOT/'scripts/diag_p106c_order_pair.py'),
          'trace_helper_sha256':digest(ROOT/'scripts/diag_p106c_balanced_policy.py'),
          'arm_tokens':{a:{'x':sum(len(x) for b in bs for x,y,n in b),'targets':sum(n for b in bs for x,y,n in b)} for a,bs in encoded.items()},
          'claim':'POSTHOC closed-world; names change tokenization and identity familiarity; scratch removes all learned weights'}
    return output,batches,encoded,info


def execute(output,batches,encoded,info):
    idle_before_gpu();output.mkdir(parents=True,exist_ok=False);write_json(output/'batches.json',batches)
    began=time.perf_counter();runner=None
    report={'schema':'P106C_LEARNING_CONTROLS_V1','status':'RUNNING','input':info,'arms':[],
            'checkpoint_writes':0,'teacher_requests':0,'training_updates':0,'peak_reserved_mib':0}
    mode=info['mode'];boundaries=(32,64,128) if mode=='horizon' else (32,)
    try:
        with wall_limit(1800):
            path=ROOT/'HF/sft_ready/p106c_replay_v1/calibrate/report.json'
            if digest(path)!=CALIBRATION_SHA:raise ValueError('calibration changed')
            cal=json.loads(path.read_text(encoding='utf-8'))
            for arm,bs in encoded.items():
                runner=Runner(student_factory=scratch_student if arm=='scratch' else None)
                if arm=='scratch':
                    if runner.s0_sha256==cal['s0_sha256']:raise ValueError('scratch unexpectedly matches pretrained state')
                elif runner.s0_sha256!=cal['s0_sha256']:raise ValueError('pretrained initial state drift')
                arm_report={'arm':arm,'initial_state_sha256':runner.s0_sha256,'boundaries':[]}
                initial_native=runner.native() if arm=='scratch' else cal['native_parent']
                arm_report['initial_native_ce']=initial_native['ce'];report['arms'].append(arm_report)
                history=[];counts=Counter()
                for step,rows in enumerate(bs):
                    history.append({'update':step+1,**runner.step(rows,[1]*32,12000+step)})
                    report['training_updates']+=1
                    counts['x_tokens']+=sum(len(x) for x,y,n in rows);counts['targets']+=sum(n for x,y,n in rows)
                    if step+1 not in boundaries:continue
                    end=step+1
                    row={'updates':end,**dict(counts),**training_history_evidence(history)}
                    grid=evaluation_grid()
                    if arm=='familiar':grid=[familiar(r) for r in grid]
                    row['grid']={}
                    for family in ('table','box'):
                        for rev in (False,True):
                            key=f'{family}_{"ba" if rev else "ab"}'
                            subset=[r for r in grid if r['family']==family and r['reversed']==rev]
                            row['grid'][key]=runner.answers(subset,output,f'{arm}_{end:03d}_{key}')
                    sealed=frozen_role('sealed')
                    if arm=='familiar':sealed=[familiar(r) for r in sealed]
                    row['transfer_probe']=runner.answers(sealed,output,f'{arm}_{end:03d}_transfer')
                    row['controls']=runner.answers(frozen_role('controls'),output,f'{arm}_{end:03d}_controls')
                    row['native']=runner.native();row['initial_native_delta']=row['native']['ce']-initial_native['ce']
                    row['pretrained_native_delta']=row['native']['ce']-cal['native_parent']['ce']
                    row['dev']=runner.scores('dev')  # Always original coded dev, explicitly reported.
                    row['dev_scope']='original coded names for both arms; not same-domain loss for familiar'
                    arm_report['boundaries'].append(row)
                    write_json(output/f'{arm}_boundary_{end:03d}.json',row)
                    print('[CONTROL_BOUNDARY] '+json.dumps({'arm':arm,**row},ensure_ascii=False),flush=True)
                with (output/f'{arm}_student.pt').open('xb') as f:
                    runner.torch.save({'model':runner.base.state_dict(),'cfg':runner.cfg.__dict__,
                                      'sft':{'input':info,'arm':arm,'claim':'MODEL_ONLY_RESEARCH_ENDPOINT'}},f)
                report['checkpoint_writes']+=1
                report['peak_reserved_mib']=max(report['peak_reserved_mib'],runner.torch.cuda.max_memory_reserved()/2**20)
                del runner;runner=None;gc.collect()
                import torch
                torch.cuda.empty_cache()
            report.update(status='LEARNING_CONTROLS_COMPLETE',exit_code=0,adoption='NOT_DECIDED')
    except (Exception,KeyboardInterrupt) as exc:
        status,rc=disposition(exc);report.update(status=status,exit_code=rc,reason=f'{type(exc).__name__}: {exc}')
    finally:
        if runner is not None:report['peak_reserved_mib']=max(report['peak_reserved_mib'],runner.torch.cuda.max_memory_reserved()/2**20)
        report['whole_wall_sec']=time.perf_counter()-began;write_json(output/'report.json',report)
        print('[LEARNING_CONTROLS_SUMMARY] '+json.dumps({k:v for k,v in report.items() if k!='arms'},ensure_ascii=False),flush=True)
    return report['exit_code']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=MODES,required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--check-only',action='store_true');g.add_argument('--execute',action='store_true')
    a=p.parse_args()
    try:
        output,batches,encoded,info=check(a.mode)
        if a.check_only:print(json.dumps(info,ensure_ascii=False));return 0
        return execute(output,batches,encoded,info)
    except Exception as exc:
        print(f'[HOLD] {type(exc).__name__}: {exc}',file=sys.stderr);return 8


if __name__=='__main__':raise SystemExit(main())
