#!/usr/bin/env python3
"""Observe CE/greedy divergence on frozen FIT and selection DEV only."""
import argparse
import gc
import json
import time
import traceback
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p108b_evaluate as evaluation
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108_query_value as pack_owner
from scripts import p108b_replay as replay
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter

BASE=atlas.BASE
OUT=BASE/'token_bridge_v2'
PROFILE=BASE/'token_bridge_profile_v2.json'
INITIAL_PLAN=BASE/'token_bridge_initial_plan_v2.md'
CODE=('scripts/diag_p108b_token_bridge.py','scripts/test_p108b_token_bridge.py')


def token_statistics(logits,targets):
    if logits.ndim!=2 or len(logits)!=len(targets)or len(targets)<2 or int(targets[-1])!=4:
        raise ValueError('answer tokens followed by one canonical EOT4 required')
    logp=torch.log_softmax(logits.double(),dim=-1)
    nll=-logp.gather(1,targets[:,None])[:,0]
    first=logp[0];gold=int(targets[0]);chosen=int(first.argmax())
    return dict(mean_ce=float(nll.mean()),answer_ce=float(nll[:-1].mean()),eot_ce=float(nll[-1]),
        answer_token_count=len(targets)-1,first_gold_id=gold,first_top_id=chosen,
        first_gold_rank=int((first>first[gold]).sum())+1,first_gold_probability=float(first[gold].exp()),
        first_top_probability=float(first[chosen].exp()),first_gold_margin=float(first[gold]-first[chosen]),
        eot_probability_after_gold=float(logp[-1,4].exp()),gold_token_nll=nll.tolist())


def prepare():
    p=evaluation.verify()
    library.write_new(PROFILE,dict(schema='P108B_TOKEN_BRIDGE_V2',arms=p['arms'],
        evaluation_profile_sha256=manual.file_sha(BASE/'evaluation_profile_v1.json'),
        sources={n:manual.file_sha(atlas.ROOT/n)for n in CODE},max_seconds=1200,
        role='FIT24 plus48 selection DEV targets; no FINAL or new optimization',
        generated_prefix_positions=[0,1,4,8],generation_source='EXACT_SAVED_GREEDY64',
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN)))
    with INITIAL_PLAN.open('xb')as f:f.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[TOKEN_BRIDGE_PREPARED] 72cases per frozen state; no generation or learning',flush=True)


def verify():
    p=evaluation.verify();r=json.loads(PROFILE.read_text(encoding='utf-8'))
    if r['arms']!=p['arms']or manual.file_sha(BASE/'evaluation_profile_v1.json')!=r['evaluation_profile_sha256']:
        raise ValueError('frozen evaluation states changed')
    for name,sha in r['sources'].items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('token bridge source changed')
    if manual.file_sha(INITIAL_PLAN)!=r['initial_plan_sha256']:raise ValueError('initial token plan changed')
    return p,r


def run():
    p,config=verify();budget=library.Budget(config['max_seconds']);torch.set_num_threads(4)
    data=json.loads((BASE/'data.json').read_text(encoding='utf-8'));fits=[r for r in data['rows']if r['split']=='fit']
    for name in config['arms']:
        directory=OUT/name
        if directory.exists():raise FileExistsError('preserve prior token observation')
        directory.mkdir(parents=True);started=time.monotonic();adapter=active=None;failure=None
        report=dict(status='STARTED',name=name,source_profile_sha256=manual.file_sha(PROFILE),
            rows=[],optimizer_updates=0,new_generation_calls=0,final_answers_consumed=False)
        try:
            report['entry_resources']=library.resources();arm=replay.read_arm(name)
            with manual.selected_runtime(manual.resolve_model(p['model']))as active:
                adapter=TinyAdapter(active,fits,data['calibration_questions'],budget=budget)
                try:
                    with replay.install(adapter,arm)as proof,torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                        report['weight_replay']=proof;report['unique_model_parameter_count']=sum(x.numel()for x in active['model'].parameters())
                        writer=ShardWriter(directory,'tokens',limit=3_000_000)
                        selected=[r for r in arm['answers']if r['split']=='fit'or(r['split']=='select_dev'and r['family']=='target')]
                        if len(selected)!=72:raise ValueError('exact24FIT+48DEV targets required')
                        for row in selected:
                            budget.check();packed=pack_owner.pack(active,row)
                            hidden=active['model'](packed['x'],return_hidden=True)
                            logits=active['model']._head_logits(hidden[:,packed['start']:])[0]
                            stats=token_statistics(logits,packed['targets']);prefixes=[]
                            content=list(row['generation']['generated_ids']);terminal=row['generation']['terminal_ids']
                            if terminal:content=content[:-len(terminal)]
                            for n in config['generated_prefix_positions']:
                                if n>len(content)or(n==len(content)and terminal):
                                    prefixes.append(dict(position=n,status='MODEL_ALREADY_TERMINATED'));continue
                                ids=packed['prompt_ids']+content[:n]
                                next_logits=active['model'](torch.tensor([ids],device='cuda'),logits_last_only=True)[0,-1].double()
                                lp=next_logits.log_softmax(-1);gold_prefix=packed['targets'][:n].tolist()
                                prefixes.append(dict(position=n,status='OBSERVED',generated_prefix=content[:n],
                                    follows_gold_prefix=content[:n]==gold_prefix,eot_probability=float(lp[4].exp()),
                                    eos_probability=float(lp[2].exp()),top_id=int(lp.argmax()),top_probability=float(lp.max().exp())))
                                if n==0 and content and int(lp.argmax())!=content[0]:
                                    raise RuntimeError('saved greedy first token differs from current native prefill')
                            detail=dict(id=row['id'],split=row['split'],language=row['language'],question=row['question'],
                                expected=row['expected'],actual_reply=row['answer'],exact=row['exact'],statistics=stats,actual_prefixes=prefixes)
                            writer.append(detail);report['rows'].append({k:detail[k]for k in('id','split','language','exact','statistics')})
                        report['answers_manifest']=writer.close(lineage=dict(role=config['role'],core_sha256=arm['core_sha256']))
                        report['counts']=dict(adapter.counts)
                        for split in('fit','select_dev'):
                            rows=[r for r in report['rows']if r['split']==split]
                            report[split]=dict(items=len(rows),mean_ce=sum(r['statistics']['mean_ce']for r in rows)/len(rows),
                                answer_ce=sum(r['statistics']['answer_ce']for r in rows)/len(rows),
                                eot_ce=sum(r['statistics']['eot_ce']for r in rows)/len(rows),
                                gold_first_top1=sum(r['statistics']['first_gold_rank']==1 for r in rows),
                                exact=sum(bool(r['exact'])for r in rows))
                        report['status']='TOKEN_BRIDGE_COMPLETE_CAUSAL_INTERPRETATION_LIMITED'
                    report['original_restored']=proof['original_core_restored']
                finally:
                    if adapter is not None:adapter.close();adapter=None
        except BaseException as error:
            failure=error;report.update(status='TOKEN_BRIDGE_ERROR',error=str(error),traceback=traceback.format_exc())
        finally:
            hidden=logits=next_logits=lp=packed=None
            active=adapter=None;gc.collect();cleanup_error=library.cleanup(report)
            if failure is None:failure=cleanup_error
            report['wall_seconds']=time.monotonic()-started;library.write_new(directory/'report.json',report)
            print('[TOKEN_BRIDGE_END] '+json.dumps({k:report.get(k)for k in('name','status','fit','select_dev','wall_seconds','error')}),flush=True)
        if failure is not None:raise RuntimeError('preserved token bridge failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[TOKEN_BRIDGE_CHECK] sealed inputs, no model/GPU')
    else:run()


if __name__=='__main__':main()
