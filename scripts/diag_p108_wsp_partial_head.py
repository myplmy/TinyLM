#!/usr/bin/env python3
"""Partial O-head attenuation after an observed loop/echo tradeoff.

Reuse closed baseline/full-head dev answers; a strict dev gate controls new
test execution. No training, new heads, gradients or checkpoint writes.
"""
import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import random
import time
import traceback
import torch
from scripts import diag_p108_wsp_attention as prior
from scripts import diag_p108_wsp_headscan as scan
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as repair
from scripts import diag_p108_weight_space as common
from scripts import interactive_research_infer as manual
from scripts.p108_balanced_practice import StrictWriter
from scripts.p106b_shards import ShardWriter,verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT=Path(__file__).resolve().parents[1]
TAG='p108_wsp_partial_v1_20261105'
BASE=ROOT/'test_result/evidence'/TAG
SOURCES=('scripts/diag_p108_wsp_partial_head.py','scripts/test_p108_wsp_partial_head.py',
         'scripts/diag_p108_wsp_headscan.py','scripts/diag_p108_wsp_attention.py',
         'scripts/p108_wsp_attention.py','scripts/p108_weight_space.py',
         'scripts/diag_p108_weight_space.py','scripts/p108_balanced_practice.py',
         'scripts/p106b_shards.py','scripts/diag_p107_hybrid_mntp.py')


def eligible(candidate,baseline):
    return (candidate['exact']>baseline['exact'] and candidate['protected_exact']>=baseline['protected_exact']
            and all(candidate[k]<=baseline[k] for k in ('loop_indicators','question_echoes','empty')))


def fresh_test():
    rows=[]
    for family in ('arithmetic','lookup','role','boolean','update','copy','repeat','json'):
        for i in range(8):
            ko=i%2==0; target=(i//2)%2;a,b=3+i,13-i
            names=('민수','영희') if ko else ('Alice','Bob')
            words=('책','모자') if i<4 else ('컵','의자')
            if not ko:words=('book','hat') if i<4 else ('cup','chair')
            if family=='arithmetic':
                q=f'숫자 {a}와 {b+target}를 더하세요. 계산한 수만 적으세요.' if ko else f'Find the sum of {a} and {b+target}. Return only the number.'
                answer=str(a+b+target)
            elif family=='lookup':
                facts=[f'{names[0]}는 {words[0]}을 가집니다',f'{names[1]}는 {words[1]}을 가집니다'] if ko else [f'{names[0]} owns the {words[0]}',f'{names[1]} owns the {words[1]}']
                if i>=4:facts.reverse()
                q='. '.join(facts)+(f'. {names[target]}가 가진 물건의 이름만 답하세요.' if ko else f'. Name only the object owned by {names[target]}.')
                answer=words[target]
            elif family=='role':
                first,second=(names if i<4 else tuple(reversed(names)))
                q=(f'{first}는 요리합니다. {second}는 운전합니다. '+('요리' if target==0 else '운전')+'하는 사람 이름만 답하세요.' if ko else f'{first} cooks. {second} drives. Give only the name of the '+('cook' if target==0 else 'driver')+'.')
                answer=(first,second)[target]
            elif family=='boolean':
                left,right=bool((i//2)%2),bool((i//4)%2)
                show=lambda v:('참' if v else '거짓') if ko else ('true' if v else 'false')
                op='AND' if i<4 else 'OR'
                q=f'X{a}={show(left)}, Y{a}={show(right)}. '+(f'X{a} {op} Y{a} 값만 쓰세요.' if ko else f'Write only X{a} {op} Y{a}.')
                answer=show(left and right if op=='AND' else left or right)
            elif family=='update':
                q=(f'A의 수는 {a}, B의 수는 {b}입니다. A의 수만 {a+2}로 바꿉니다. '+('A' if target==0 else 'B')+'의 최종 수만 답하세요.' if ko else f'A has number {a} and B has number {b}. Change only A to {a+2}. Give only the final number for '+('A' if target==0 else 'B')+'.')
                answer=str(a+2 if target==0 else b)
            elif family=='copy':
                answer=('물병','연필','책상','모자')[i//2] if ko else ('bottle','pencil','desk','hat')[i//2]
                q=f'다음 단어 한 개만 복사하세요: {answer}' if ko else f'Copy this single word and nothing else: {answer}'
            elif family=='repeat':
                word=('파랑','노랑','빨강','초록')[i//2] if ko else ('blue','yellow','red','green')[i//2]
                times=2+target;answer=' '.join([word]*times)
                q=f'{word} 단어를 공백으로 나눠 정확히 {times}번 출력하세요.' if ko else f'Output the word {word} exactly {times} times, separated by spaces.'
            else:
                word=('책','모자','컵','의자')[i//2] if ko else ('book','hat','cup','chair')[i//2]
                answer=json.dumps({'answer':word},ensure_ascii=False,separators=(',',':'))
                q=f'문자열 {word}를 answer 값으로 넣은 JSON 한 개만 답하세요.' if ko else f'Return only one JSON object with answer equal to the string {word}.'
            rows.append(dict(id=f'partial_test:{family}:{i}',split='test',family=family,language='ko' if ko else 'en',
                             question=q,expected=answer,protected=family in ('copy','repeat','json')))
    if len({r['question'] for r in rows})!=len(rows):raise ValueError('duplicate fresh partial question')
    return rows


def read_closed(base):
    out=base/'actual';m=common.read_json(out/'answers_shards_manifest.json');verify_shards(out,m)
    rows=[]
    for s in m['shards']:rows.extend(json.loads(line) for line in (out/s['path']).read_text().splitlines())
    return rows,common.read_json(out/'report.json')


def prepare():
    if BASE.exists():raise FileExistsError('fresh partial profile required')
    parent=scan.verify();sources=dict(manual.required_source_pins())
    sources.update({name:manual.file_sha(ROOT/name) for name in SOURCES})
    dev=[r for r in common.read_json(prior.BASE/'data.json')['rows'] if r['split']=='dev']
    fresh=fresh_test();old_questions={r['question'] for r in common.read_json(prior.BASE/'data.json')['rows']}
    if old_questions & {r['question'] for r in fresh}:raise ValueError('partial test reuses old exact question')
    opens=[r for r in common.read_json(prior.BASE/'data.json')['rows'] if r['split']=='open']
    references={}
    for base in (prior.BASE,scan.BASE):
        for path in sorted((base/'actual').iterdir()):
            if path.suffix in ('.json','.jsonl'):references[str(path.relative_to(ROOT))]=manual.file_sha(path)
    common.write_json(BASE/'data.json',dict(rows=dev+fresh+opens,provenance='CODE_RULES_NEW_PROMPTS_NOT_GLOBAL_NOVELTY_PROOF'))
    (BASE/'initial_plan.md').write_bytes((ROOT/prior.PLAN).read_bytes())
    profile=dict(schema='P108_WSP_PARTIAL_V1',authority=[111,112],tag=TAG,model=prior.MODEL,
        deadline=prior.DEADLINE.isoformat(),max_phase_seconds=900,max_new=64,sources=sources,references=references,
        data_sha256=manual.file_sha(BASE/'data.json'),plan_sha256=manual.file_sha(BASE/'initial_plan.md'),
        manifest_sha256=parent['manifest_sha256'],heads=[['attention:12',10],['attention:5',8]],
        alphas=[.25,.5,.75],random_seeds=[23117,23129,23143],selection_split='DEV_ONLY',test_gate='STRICT_DEV_PARETO',
        gradient_calls=0,training_tokens=0,checkpoint_writes=0)
    common.write_json(BASE/'profile.json',profile);print('[PREPARED] '+TAG,flush=True)


def verify():
    p=common.read_json(BASE/'profile.json')
    if p['schema']!='P108_WSP_PARTIAL_V1' or p['authority']!=[111,112] or p['deadline']!=prior.DEADLINE.isoformat():
        raise ValueError('partial authority/schema mismatch')
    for key,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/key)!=sha:raise ValueError('partial pinned source changed: '+key)
    if manual.file_sha(BASE/'data.json')!=p['data_sha256'] or manual.file_sha(BASE/'initial_plan.md')!=p['plan_sha256']:
        raise ValueError('partial frozen inputs changed')
    if manual.canonical_sha(manual.verify_manifest())!=p['manifest_sha256']:raise ValueError('original model changed')
    return p


def run():
    p=verify();budget=prior.Budget(p);budget.check();out=BASE/'actual'
    if out.exists():raise FileExistsError('partial output already exists')
    raw=ShardWriter(out,'answers',limit=3_000_000);writer=StrictWriter(raw)
    data=common.read_json(BASE/'data.json')['rows'];source,source_report=read_closed(prior.BASE)
    original=[r for r in source if r['variant']=='original_dev'];baseline=repair.summarize(original)
    report=dict(schema=p['schema'],status='RUNNING',variants=[],gradient_calls=0,training_tokens=0,checkpoint_writes=0,
                baseline_dev=baseline,reused_baseline_rows=len(original),test_reselection=False)
    failure=None;modules=module=delta=None
    def evaluate(active,split,name):
        items=[r for r in data if r['split']==split or (split=='confirm' and r['split'] in ('test','open'))]
        rows,summary=common.evaluate(active,items,writer,name,budget,p['max_new'])
        report['variants'].append(dict(name=name,**summary));common.write_json(out/(name+'_summary.json'),summary)
        return rows,summary
    try:
        with manual.selected_runtime(manual.resolve_model(prior.MODEL)) as active:
            torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
            report['origin']={k:active[k] for k in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256')}
            if report['origin']!=source_report['origin']:raise ValueError('partial reused core differs')
            for row in original:writer.append(dict(row,variant='original_dev',reused_source=str(prior.BASE.relative_to(ROOT))))
            probe=original[0];_,parity=manual.emit(active,probe['question'],max_new=64)
            if parity['generated_ids']!=probe['generation']['generated_ids']:raise RuntimeError('baseline live parity failed')
            report['live_reuse_token_parity']=True;modules=wsp.outputs(active['model']);candidates=[]
            for key,head in p['heads']:
                for alpha in p['alphas']:
                    name=f'partial_{key.replace(":","_")}_head{head}_a{alpha}'
                    delta=alpha*wsp.head_delta(modules[key],active['cfg'].n_q_heads,head)
                    with wsp.edit(active['model'],active['route'],[(key,delta)]) as receipt:
                        _,summary=evaluate(active,'dev',name+'_dev')
                    candidate=dict(name=name,key=key,head=head,alpha=alpha,summary=summary,receipt=receipt)
                    candidate['eligible']=eligible(summary,baseline);candidates.append(candidate)
            report['candidates']=candidates;good=[r for r in candidates if r['eligible']]
            if not good:
                report['status']='DEV_GATE_NEGATIVE_TEST_NOT_RUN';report['test_execution']='NOT_RUN_PREDECLARED_DEV_GATE'
                common.write_json(out/'frozen_selection.json',dict(eligible=0,test_not_run=True,candidates=candidates))
            else:
                chosen=max(good,key=lambda r:(r['summary']['exact'],r['summary']['protected_exact'],-r['summary']['loop_indicators'],-r['alpha']))
                common.write_json(out/'frozen_selection.json',dict(chosen=chosen,selection_split='DEV_ONLY',test_reselection=False))
                report['selected']=chosen;evaluate(active,'confirm','original_confirm')
                key,head,alpha=chosen['key'],chosen['head'],chosen['alpha']
                delta=alpha*wsp.head_delta(modules[key],active['cfg'].n_q_heads,head)
                with wsp.edit(active['model'],active['route'],[(key,delta)]):evaluate(active,'confirm','selected_confirm')
                options=[(key,h) for key in modules if key.startswith('attention:') for h in range(active['cfg'].n_q_heads)
                         if (key,h)!=(chosen['key'],chosen['head'])];used=set()
                for seed in p['random_seeds']:
                    key,head=random.Random(seed).choice([item for item in options if item not in used]);used.add((key,head))
                    delta=alpha*wsp.head_delta(modules[key],active['cfg'].n_q_heads,head)
                    with wsp.edit(active['model'],active['route'],[(key,delta)]):evaluate(active,'confirm',f'random{seed}_confirm')
                report['status']='TECHNICAL_COMPLETE_QUALITY_SEPARATE'
            _,after=manual.emit(active,probe['question'],max_new=64)
            if after['generated_ids']!=probe['generation']['generated_ids']:raise RuntimeError('partial rollback token parity failed')
            report['final_rollback_token_parity']=True
        report['registered_core_unchanged']=True
    except BaseException as exc:
        failure=exc;report['status']='ERROR';report['error']=repr(exc);traceback.print_exc()
    finally:
        manifest=raw.close(lineage=dict(profile_sha256=manual.file_sha(BASE/'profile.json')));verify_shards(out,manifest)
        modules=module=delta=None;gc.collect();close_owned_cuda(torch,report);verify()
        report['wall_seconds']=time.monotonic()-budget.start;common.write_json(out/'report.json',report)
    print('[FINAL] '+json.dumps(dict(status=report['status'],wall_seconds=report['wall_seconds'])),flush=True)
    if failure is not None:raise failure


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run'))
    args=parser.parse_args();prepare() if args.phase=='prepare' else run()


if __name__=='__main__':main()
