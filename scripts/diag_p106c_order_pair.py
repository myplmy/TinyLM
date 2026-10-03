#!/usr/bin/env python3
"""P106C Stage7W: identical draws, fixed versus half-reversed training order.

Closed-world diagnostic, not production SFT. Only --execute loads a model.
Fresh parent per arm; original data and Stage6 reports stay read-only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.diag_p106c_balanced_policy import (ARMS, A_PATH, A_SHA, require_a,
    frozen_role, digest, data_hash, training_history_evidence, write_json)
from scripts.diag_p106c_prompt_cache import prompt_grid
from scripts.p106c_data import canonical
from scripts.p106c_replay import Runner, snapshot, restore, cpu_tree, code_contract
from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit, disposition

SOURCE=ROOT/'HF/sft_ready/p106c_balanced_policy_v1'
SOURCE_SHA='3E6A4D6530FB445783F66C33B4E609FEC972A0FA35A4070ACF32FFCD1FBACE88'
OUTPUT=ROOT/'HF/sft_ready/p106c_order_pair_v1'
CALIBRATION_SHA='15ADCB9F8C1A8EB378993189BFA95673D9ED02A83BD51F20EA33A5B25E7C3DCB'
BOUNDARIES=(8,16,32)


def order_variant(left, right, reverse):
    """Reconstruct both facts from code gold; never swap the requested target."""
    if (left['pair_id']!=right['pair_id'] or left['language']!=right['language']
            or left['gold']==right['gold'] or left['role']!=right['role']):
        raise ValueError('invalid fact pair')
    role=left['role']
    if role not in ('train','rehearsal'):
        raise ValueError('only training roles may be transformed')
    a,b=left['pair_id']+'a',left['pair_id']+'b'
    facts={a:left['gold'],b:right['gold']}
    def question(target, rev):
        first,second=(b,a) if rev else (a,b)
        x,y=facts[first],facts[second]
        if role=='train':
            return (f'표: {first}={x}, {second}={y}. {target}의 색은? 색 이름 한 단어만 답하세요.' if left['language']=='ko' else
                    f'Table: {first}={x}, {second}={y}. What color is {target}? Answer with the color only.')
        return (f'기억할 값: {first} 색 {x}; {second} 색 {y}. {target}에 해당하는 색만 쓰세요.' if left['language']=='ko' else
                f'Remember: {first} has color {x}; {second} has color {y}. Return only {target}\'s color.')
    result=[]
    for row,target in ((left,a),(right,b)):
        if row['question']!=question(target,False):
            raise ValueError('frozen template differs; do not guess its meaning')
        result.append({**row,'question':question(target,reverse),
                       'source_id':row['id'],'training_order':'ba' if reverse else 'ab'})
    return result


def materialize(batch_plan, roles, mixed):
    output=[]
    for step,spec in enumerate(batch_plan):
        rows=[]
        for field,role in (('candidate','train'),('rehearsal','rehearsal')):
            ids=spec[field]
            if len(ids)!=16:
                raise ValueError('exactly eight pairs per role are required')
            language_slot=Counter()
            for pos in range(0,16,2):
                i,j=ids[pos:pos+2]
                if i%2 or j!=i+1:
                    raise ValueError('adjacent complete a/b question pair required')
                left,right=roles[role][i],roles[role][j]
                lang=left['language'];slot=language_slot[lang];language_slot[lang]+=1
                # Opposite edges of the frozen four-color cycle: half of each
                # language/role reversed, with every color represented in each order.
                rows.extend(order_variant(left,right,mixed and (slot+step)%2==0))
            if dict(language_slot)!={'ko':4,'en':4}:
                raise ValueError('language pair counts differ')
        output.append(rows)
    return output


def evaluation_grid():
    rows=prompt_grid(frozen_role('sealed'))
    # Each context/order has two targets, not eight answers under one pair ID.
    return [{**r,'pair_id':f"{r['pair_id']}_{r['family']}_{int(r['reversed'])}"} for r in rows]


def check():
    if OUTPUT.exists() or OUTPUT.is_symlink() or OUTPUT.parent.is_symlink():
        raise FileExistsError('preserve existing output; new stage/version required')
    if digest(SOURCE/'report.json')!=SOURCE_SHA:
        raise ValueError('Stage6 report changed')
    source=json.loads((SOURCE/'report.json').read_text(encoding='utf-8'))
    plan=json.loads((SOURCE/'batch_plan.json').read_text(encoding='utf-8'))
    if data_hash(plan)!=source['input']['plan_sha256'] or len(plan['baseline'])!=32:
        raise ValueError('Stage6 frozen draw plan differs')
    if digest(A_PATH)!=A_SHA:
        raise ValueError('A path report changed')
    require_a(json.loads(A_PATH.read_text(encoding='utf-8')))
    for key,sha in (('parent','sha'),('tokenizer','tok_sha')):
        if digest(ROOT/ARMS['b'][key])!=ARMS['b'][sha]:
            raise ValueError('parent/tokenizer changed')
    if shutil.disk_usage(ROOT).free<8*2**30:
        raise ValueError('8GiB free disk required; no cleanup')
    from tokenizers import Tokenizer
    from scripts.train_sft_p090 import encode_records
    tok=Tokenizer.from_file(str(ROOT/ARMS['b']['tokenizer']))
    roles={role:frozen_role(role) for role in ('train','rehearsal')}
    batches={a:materialize(plan['baseline'],roles,a=='mixed') for a in ('fixed','mixed')}
    encoded={a:[encode_records([canonical(r) for r in batch],tok,256,32768) for batch in arm]
             for a,arm in batches.items()}
    for left,right in zip(encoded['fixed'],encoded['mixed']):
        if [(len(x),n) for x,y,n in left]!=[(len(x),n) for x,y,n in right]:
            raise ValueError('order change alters input/target token mass')
        if [tuple(v for v in y if v!=-100) for x,y,n in left]!=[tuple(v for v in y if v!=-100) for x,y,n in right]:
            raise ValueError('answer token sequence changed')
    info={'schema':'P106C_ORDER_PAIR_PREFLIGHT_V1','source_sha256':SOURCE_SHA,
          'draw_plan_sha256':data_hash(plan),'a_sha256':A_SHA,'parent_sha256':ARMS['b']['sha'],
          'tokenizer_sha256':ARMS['b']['tok_sha'],'batches_sha256':data_hash(batches),
          'updates_per_arm':32,'micro':8,'accum':4,'context':256,'checkpoint_on':True,
          'actual_x_per_arm':sum(len(x) for batch in encoded['fixed'] for x,y,n in batch),
          'targets_per_arm':sum(n for batch in encoded['fixed'] for x,y,n in batch),
          'teacher_requests':0,'selector_used':False,'max_wall_sec':1800,
          'code':code_contract(),'driver_sha256':digest(Path(__file__)),
          'trace_helper_sha256':digest(ROOT/'scripts/diag_p106c_balanced_policy.py'),
          'claim':'POSTHOC training-order intervention; no fresh sealed or general-intelligence claim'}
    return batches,encoded,info


def execute(batches,encoded,info):
    idle_before_gpu()
    OUTPUT.mkdir(parents=True,exist_ok=False)
    write_json(OUTPUT/'batches.json',batches)
    report={'schema':'P106C_ORDER_PAIR_V1','status':'RUNNING','input':info,'boundaries':[],
            'checkpoint_writes':0,'teacher_requests':0}
    began=time.perf_counter();runner=None
    try:
        with wall_limit(1800):
            path=ROOT/'HF/sft_ready/p106c_replay_v1/calibrate/report.json'
            if digest(path)!=CALIBRATION_SHA:
                raise ValueError('calibration changed')
            calibration=json.loads(path.read_text(encoding='utf-8'))
            runner=Runner()
            if runner.s0_sha256!=calibration['s0_sha256']:
                raise ValueError('fresh parent/optimizer/RNG differs')
            parent_ce=calibration['native_parent']['ce']
            states={a:runner.s0 for a in encoded};histories={a:[] for a in encoded}
            counts={a:Counter() for a in encoded}
            grid=evaluation_grid();sealed=frozen_role('sealed');controls=frozen_role('controls')
            first=0
            for end in BOUNDARIES:
                boundary={'updates_per_arm':end,'arms':[]}
                for arm in ('fixed','mixed'):
                    restore(runner.base,runner.optimizers,states[arm])
                    for step in range(first,end):
                        rows=encoded[arm][step]
                        histories[arm].append({'update':step+1,**runner.step(rows,[1]*32,12000+step)})
                        counts[arm]['x_tokens']+=sum(len(x) for x,y,n in rows)
                        counts[arm]['targets']+=sum(n for x,y,n in rows)
                    states[arm]=snapshot(runner.base,runner.optimizers)
                    row={'arm':arm,'updates':end,**dict(counts[arm]),**training_history_evidence(histories[arm])}
                    row['grid']={}
                    for family in ('table','box'):
                        for reverse in (False,True):
                            key=f'{family}_{"ba" if reverse else "ab"}'
                            subset=[r for r in grid if r['family']==family and r['reversed']==reverse]
                            row['grid'][key]=runner.answers(subset,OUTPUT,f'{arm}_{end:03d}_{key}')
                    row['transfer_probe']=runner.answers(sealed,OUTPUT,f'{arm}_{end:03d}_transfer')
                    row['controls']=runner.answers(controls,OUTPUT,f'{arm}_{end:03d}_controls')
                    row['native']=runner.native()
                    row['parent_native_delta']=row['native']['ce']-parent_ce
                    row['dev']=runner.scores('dev')
                    boundary['arms'].append(row)
                    if end==32:
                        with (OUTPUT/f'{arm}_student.pt').open('xb') as f:
                            runner.torch.save({'model':cpu_tree(runner.base.state_dict()),'cfg':runner.cfg.__dict__,
                                'sft':{'arm':arm,'updates':end,'input':info,'claim':'MODEL_ONLY_POSTHOC_ENDPOINT'}},f)
                        report['checkpoint_writes']+=1
                if [(r['x_tokens'],r['targets']) for r in boundary['arms']][0]!=[(r['x_tokens'],r['targets']) for r in boundary['arms']][1]:
                    raise ValueError('boundary token masses differ')
                report['boundaries'].append(boundary)
                write_json(OUTPUT/f'boundary_{end:03d}.json',boundary)
                print('[ORDER_BOUNDARY] '+json.dumps(boundary,ensure_ascii=False),flush=True)
                first=end
            report.update(status='ORDER_PAIR_COMPARISON_COMPLETE',exit_code=0,parent_native_ce=parent_ce,
                          completed_updates_per_arm=first,adoption='NOT_DECIDED')
    except (Exception,KeyboardInterrupt) as exc:
        status,rc=disposition(exc);report.update(status=status,exit_code=rc,reason=f'{type(exc).__name__}: {exc}')
    finally:
        report['training_updates']=runner.updates if runner is not None else 0
        report['peak_reserved_mib']=runner.torch.cuda.max_memory_reserved()/2**20 if runner is not None else None
        report['whole_wall_sec']=time.perf_counter()-began
        write_json(OUTPUT/'report.json',report)
        print('[P106C_ORDER_SUMMARY] '+json.dumps({k:v for k,v in report.items() if k!='boundaries'},ensure_ascii=False),flush=True)
    return report['exit_code']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only',action='store_true');group.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    try:
        batches,encoded,info=check()
        if args.check_only:
            print(json.dumps(info,ensure_ascii=False));return 0
        return execute(batches,encoded,info)
    except Exception as exc:
        print(f'[HOLD] {type(exc).__name__}: {exc}',file=sys.stderr);return 8


if __name__=='__main__':
    raise SystemExit(main())
