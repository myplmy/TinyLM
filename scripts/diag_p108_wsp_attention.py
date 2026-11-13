#!/usr/bin/env python3
"""User111/112: forward-only p10/p25-inspired intervention on completed float.

Fresh versioned data/profile, dev selection then frozen test. No gradients,
training, checkpoint writing, old test selection or original source changes.
"""
import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import random
import time
import traceback

from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as repair
from scripts import p108_wsp_attention as wsp
from scripts import diag_p108_weight_space as old
from scripts.p108_balanced_practice import StrictWriter
from scripts.p106b_shards import ShardWriter, verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT = Path(__file__).resolve().parents[1]
TAG = 'p108_wsp_attn_v1_20261105'
MODEL = 'new595-broad-f'
BASE = ROOT / 'test_result/evidence' / TAG
DEADLINE = datetime(2026, 11, 5, 7, 40, tzinfo=timezone.utc)
SOURCES = ('scripts/p108_wsp_attention.py', 'scripts/diag_p108_wsp_attention.py',
           'scripts/test_p108_wsp_attention.py', 'scripts/p108_weight_space.py',
           'scripts/diag_p108_weight_space.py', 'scripts/p108_balanced_practice.py',
           'scripts/p106b_shards.py', 'scripts/diag_p107_hybrid_mntp.py')
PLAN = 'test_plan/P108_직접가중치-방향수리와-학습개입.md'


def data():
    rows = []
    # Distinct numeric facts, entities and literal strings across dev/test.
    for split, n, offset in (('dev', 8, 41), ('test', 16, 81)):
        for family in ('arithmetic', 'lookup', 'role', 'boolean', 'update', 'copy', 'repeat', 'json'):
            for i in range(n):
                ko = i % 2 == 0
                lang = 'ko' if ko else 'en'
                a, b = offset + i, 2 + i * 3
                name1, name2 = (f'가람{offset+i}', f'누리{offset+i}') if ko else (f'Aster{offset+i}', f'Birch{offset+i}')
                v1, v2 = ('연필', '우산') if ko else ('pencil', 'umbrella')
                target = (i // 2) % 2
                if family == 'arithmetic':
                    q = f'{a} 더하기 {b}의 답을 숫자로만 적으세요.' if ko else f'Add {a} and {b}. Output only the number.'
                    expected = str(a + b)
                elif family == 'lookup':
                    clauses = [f'{name1}의 물건은 {v1}입니다', f'{name2}의 물건은 {v2}입니다'] if ko else [f'{name1} has a {v1}', f'{name2} has an {v2}']
                    if (i // 4) % 2: clauses.reverse()
                    name = (name1, name2)[target]
                    q = '. '.join(clauses) + (f'. {name}의 물건 이름만 적으세요.' if ko else f'. Give only the object owned by {name}.')
                    expected = (v1, v2)[target]
                elif family == 'role':
                    clauses = [f'{name1}는 요리하고 {name2}는 달립니다.'] if ko else [f'{name1} cooks and {name2} runs.']
                    q = clauses[0] + ((' 달리는 사람의 이름만 적으세요.' if target else ' 요리하는 사람의 이름만 적으세요.') if ko else (' Give only the runner name.' if target else ' Give only the cook name.'))
                    expected = (name1, name2)[target]
                elif family == 'boolean':
                    x, y = bool((i // 2) % 2), bool((i // 4) % 2)
                    render = lambda z: ('참' if z else '거짓') if ko else ('true' if z else 'false')
                    op = 'AND' if (i // 2) % 2 else 'OR'
                    q = f'P{a}={render(x)}, Q{a}={render(y)}. ' + (f'P{a} {op} Q{a}의 값만 적으세요.' if ko else f'Give only the value of P{a} {op} Q{a}.')
                    expected = render(x and y if op == 'AND' else x or y)
                elif family == 'update':
                    q = (f'A는 {a}, B는 {b}입니다. B를 {b+2}로 바꿉니다. '+ ('A' if target == 0 else 'B')+'의 현재 수만 적으세요.' if ko else f'A is {a} and B is {b}. Change B to {b+2}. Give only the current number for '+('A' if target == 0 else 'B')+'.')
                    expected = str(a if target == 0 else b+2)
                elif family == 'copy':
                    expected = f'elm-{a}-{b}'
                    q = f'문자열 {expected}만 그대로 적으세요.' if ko else f'Copy exactly this string and nothing else: {expected}'
                elif family == 'repeat':
                    expected = ' '.join([str(a)] * (2 + target))
                    q = f'{a}를 공백으로 나누어 {2+target}번만 적으세요.' if ko else f'Write {a} exactly {2+target} times separated by one space.'
                else:
                    expected = json.dumps({'answer': str(a)}, ensure_ascii=False, separators=(',', ':'))
                    q = f'값 {a}를 문자열로 담는 answer 한 항목의 JSON 객체만 출력하세요.' if ko else f'Output only a JSON object with one key answer and string value {a}.'
                rows.append(dict(id=f'{split}:{family}:{i}', question=q, expected=expected, split=split,
                    family=family, language=lang, protected=family in ('copy', 'repeat', 'json')))
    calib = ['1+1은?', '2+2는?', 'A는 사과고 B는 당근이다. B는?', '사과에 대해 알려줘',
             '농구란?', '서울은 어떤 도시인가요?', '비가 오면 왜 우산을 쓰나요?', '물과 얼음은 어떻게 다른가요?',
             'What is one plus one?', 'What is basketball?', 'Tell me about apples.', 'Why do people need water?',
             'Say hello in one sentence.', 'What is the difference between ice and water?',
             '민수는 사과 3개, 영희는 사과 5개를 가집니다. 영희는 몇 개입니까?',
             'A has a pencil and B has an umbrella. What does B have?']
    for i, q in enumerate(calib):
        rows.append(dict(id=f'calib:{i}', question=q, expected=None, family='natural_loop_calibration',
            split='calib', language='ko' if i < 8 or i == 14 else 'en', protected=False))
    # Open regression answers are never scored/used to choose an edit.
    for i, q in enumerate(old.OPEN):
        rows.append(dict(id=f'open:{i}', question=q, expected=None, family='open_regression', split='open',
            language='ko' if i < 8 else 'en', protected=False))
    scored = [r['question'] for r in rows if r['expected'] is not None]
    if len(scored) != len(set(scored)):
        raise ValueError('duplicate fresh scored prompt')
    return rows


def prepare():
    if BASE.exists(): raise FileExistsError('new WSP profile namespace already exists')
    manifest = manual.verify_manifest()
    rows = data()
    sources = dict(manual.required_source_pins())
    sources.update({p: manual.file_sha(ROOT / p) for p in SOURCES})
    old.write_json(BASE/'data.json', dict(rows=rows, provenance='FRESH_CODE_RULES_NOT_OFFICIAL_BENCHMARK'))
    (BASE/'initial_plan.md').write_bytes((ROOT/PLAN).read_bytes())
    profile = dict(schema='P108_WSP_ATTENTION_V1', tag=TAG, model=MODEL, authority=[111,112],
        deadline=DEADLINE.isoformat(), max_phase_seconds=2400, max_new=64, sources=sources,
        data_sha256=manual.file_sha(BASE/'data.json'), plan_sha256=manual.file_sha(BASE/'initial_plan.md'),
        manifest_sha256=manual.canonical_sha(manifest), gradient_calls=0, updates=0, training_tokens=0,
        head_candidates=3, multi_sites=[4,8], multi_gain=1.5, random_seeds=[23117],
        calibration_only_for_sites=True, dev_only_for_selection=True, test_reselection=False,
        precision='FP32_MATH', cache=True, tf32=False, mtp=False, recurrence='R1',
        checkpoint_writes=0, official_benchmark_selection=False)
    old.write_json(BASE/'profile.json', profile)
    print('[PREPARED] '+str(BASE.relative_to(ROOT)), flush=True)


def verify():
    p = old.read_json(BASE/'profile.json')
    if p['schema'] != 'P108_WSP_ATTENTION_V1' or p['authority'] != [111,112] or p['deadline'] != DEADLINE.isoformat():
        raise ValueError('WSP frozen authority/schema differs')
    for name, sha in p['sources'].items():
        if manual.file_sha(ROOT/name) != sha: raise ValueError('source drift: '+name)
    for name, key in (('data.json','data_sha256'),('initial_plan.md','plan_sha256')):
        if manual.file_sha(BASE/name) != p[key]: raise ValueError('frozen input drift: '+name)
    if manual.canonical_sha(manual.verify_manifest()) != p['manifest_sha256']:
        raise ValueError('original independent model manifest changed')
    return p


class Budget:
    def __init__(self, profile): self.start=time.monotonic(); self.maximum=profile['max_phase_seconds']
    def check(self):
        if datetime.now(timezone.utc) >= DEADLINE or time.monotonic()-self.start > self.maximum:
            raise TimeoutError('WSP authority/phase budget reserve reached')


def collect(active, rows, budget):
    torch, model = active['torch'], active['model']
    natural = [r for r in rows if r['diagnostics']['loop_indicator']]
    if len(natural) < 4: raise ValueError('HOLD: fewer than four natural calibration loops')
    aggregate = {}
    observations = []
    for i,row in enumerate(natural[:16]):
        budget.check()
        prefix = old.prompt_ids(active,row['question'])
        body = [t for t in row['generation']['generated_ids'][-48:] if t not in (2,4)]
        interior = body[:-8]
        random.Random(23117+i).shuffle(interior)
        control = interior+body[-8:]
        if control == body:
            observations.append(dict(id=row['id'], identifiable=False)); continue
        values=[]
        for suffix in (body,control):
            ids=torch.tensor([prefix+suffix],device='cuda',dtype=torch.long)
            from torch.nn.attention import sdpa_kernel, SDPBackend
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH),wsp.capture(model) as captured:
                active['route'].assert_active(); model(ids,logits_last_only=True)
            values.append(captured)
        for key in values[0]:
            diff = (values[0][key]-values[1][key] if key=='residual' else
                    values[0][key]['output']-values[1][key]['output'])
            entry=aggregate.setdefault(key,dict(output=torch.zeros_like(diff)))
            entry['output']+=diff
            if key!='residual':
                entry.setdefault('input',torch.zeros_like(values[0][key]['input']))
                entry['input']+=values[0][key]['input']-values[1][key]['input']
        observations.append(dict(id=row['id'],identifiable=True,length=len(body)))
    count=sum(r['identifiable'] for r in observations)
    if count < 4: raise ValueError('HOLD: fewer than four identifiable loop order controls')
    u=repair.unit_direction(aggregate['residual']['output']/count).to('cuda')
    modules=wsp.outputs(model)
    heads=[];sites=[]
    for key,module in modules.items():
        entry=aggregate[key]
        sites.append(dict(key=key,score=abs(float(u.cpu() @ (entry['output']/count)))))
        if key.startswith('attention:'):
            contribution=(u @ module.weight.detach()) * (entry['input']/count).to('cuda')
            for head in range(active['cfg'].n_q_heads):
                cols=wsp.head_columns(module,active['cfg'].n_q_heads,head)
                heads.append(dict(key=key,head=head,score=abs(float(contribution[cols].sum())),width=len(cols)))
    heads.sort(key=lambda r:(-r['score'],r['key'],r['head']))
    sites.sort(key=lambda r:(-r['score'],r['key']))
    return u,dict(natural_loops=len(natural),identifiable_pairs=count,observations=observations,
        head_ranking=heads,site_ranking=sites,direction=u.cpu().tolist(),protocol='NATURAL_LOOP_ORDER_CONTROL_FINAL_RESIDUAL')


def candidates(active,u,calib,profile):
    modules=wsp.outputs(active['model']); result=[]
    for i,entry in enumerate(calib['head_ranking'][:profile['head_candidates']]):
        result.append(dict(name=f'head_top{i+1}',kind='head',spec=entry,
            edits=[(entry['key'],wsp.head_delta(modules[entry['key']],active['cfg'].n_q_heads,entry['head']))]))
    for n in profile['multi_sites']:
        # Both branches must actually be edited; unrestricted top-k can be all MLP.
        keys=[r['key'] for kind in ('attention:','mlp:')
              for r in [v for v in calib['site_ranking'] if v['key'].startswith(kind)][:n//2]]
        if len(keys)!=n: raise ValueError('not enough distinct sites in both output branches')
        edits=[(key,repair.projection_delta(modules[key].weight.detach(),u,list(range(modules[key].weight.shape[1])),profile['multi_gain'])) for key in keys]
        result.append(dict(name=f'multi_top{n}',kind='multi',spec=dict(keys=keys,gain=profile['multi_gain']),edits=edits))
    return result


def random_control(active,proposal,seed):
    torch=active['torch'];modules=wsp.outputs(active['model'])
    if proposal['kind']=='head':
        options=[(key,head) for key in modules if key.startswith('attention:') for head in range(active['cfg'].n_q_heads)
                 if (key,head)!=(proposal['spec']['key'],proposal['spec']['head'])]
        key,head=random.Random(seed).choice(options)
        return [(key,wsp.head_delta(modules[key],active['cfg'].n_q_heads,head))],dict(key=key,head=head,match='HEAD_COUNT_AND_WIDTH_ONLY_NOT_NORM')
    gen=torch.Generator(device='cpu').manual_seed(seed)
    u=repair.unit_direction(torch.randn(active['cfg'].dim,generator=gen)).to('cuda')
    result=[]
    for key,delta in proposal['edits']:
        m=modules[key];d=repair.projection_delta(m.weight.detach(),u,list(range(m.weight.shape[1])),1.)
        if not float(d.norm()): raise ValueError('zero random projection')
        result.append((key,d*(delta.norm()/d.norm())))
    return result,dict(seed=seed,match='SAME_SITES_PER_MATRIX_DELTA_NORM')


def run():
    p=verify(); budget=Budget(p); budget.check()
    out=BASE/'actual'
    if out.exists(): raise FileExistsError('actual output already exists')
    raw=ShardWriter(out,'answers',limit=3_000_000); writer=StrictWriter(raw)
    report=dict(schema=p['schema'],status='RUNNING',variants=[],training_tokens=0,optimizer_updates=0,
                gradient_calls=0,checkpoint_writes=0,official_benchmark='NOT_RUN')
    failure=None
    rows=old.read_json(BASE/'data.json')['rows']
    def evaluate(active,split,name):
        chosen=[r for r in rows if r['split']==split or (split=='confirm' and r['split'] in ('test','open'))]
        result,summary=old.evaluate(active,chosen,writer,name,budget,p['max_new'])
        report['variants'].append(dict(name=name,**summary))
        old.write_json(out/f'{name}_summary.json',summary)
        return result,summary
    try:
        with manual.selected_runtime(manual.resolve_model(MODEL)) as active:
            torch=active['torch'];torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
            report['origin']={k:active[k] for k in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256')}
            calib_rows,_=evaluate(active,'calib','original_calib')
            u,calib=collect(active,calib_rows,budget);old.write_json(out/'calibration.json',calib)
            proposals=candidates(active,u,calib,p)
            dev,original_dev=evaluate(active,'dev','original_dev')
            probe=dev[0]
            first_key=next(iter(wsp.outputs(active['model'])))
            with wsp.edit(active['model'],active['route'],[(first_key,torch.zeros_like(wsp.outputs(active['model'])[first_key].weight))]):
                _,meta=manual.emit(active,probe['question'],max_new=p['max_new'])
            if meta['generated_ids']!=probe['generation']['generated_ids']: raise RuntimeError('no-op token parity failed')
            report['noop_token_parity']=True
            for proposal in proposals:
                budget.check()
                with wsp.edit(active['model'],active['route'],proposal['edits']) as receipt:
                    _,summary=evaluate(active,'dev',proposal['name']+'_dev')
                proposal['summary']=summary
                old.write_json(out/(proposal['name']+'_edit.json'),dict(spec=proposal['spec'],receipts=receipt))
            key=lambda c:(c['summary']['exact'],c['summary']['protected_exact'],-c['summary']['empty'],
                          -c['summary']['question_echoes'],-c['summary']['loop_indicators'],
                          -sum(float(d.norm()) for _,d in c['edits']))
            winners=[max((c for c in proposals if c['kind']==kind),key=key) for kind in ('head','multi')]
            selected=dict(selection_split='DEV_ONLY',test_reselection=False,original_dev=original_dev,
                winners=[dict(name=c['name'],kind=c['kind'],spec=c['spec'],dev=c['summary']) for c in winners])
            old.write_json(out/'frozen_selection.json',selected)
            report['selection_sha256']=manual.file_sha(out/'frozen_selection.json')
            report['selected']=selected
            baseline,base_summary=evaluate(active,'confirm','original_confirm')
            for proposal in winners:
                with wsp.edit(active['model'],active['route'],proposal['edits']) as receipt:
                    _,summary=evaluate(active,'confirm',proposal['name']+'_confirm')
                for seed in p['random_seeds']:
                    edits,match=random_control(active,proposal,seed)
                    with wsp.edit(active['model'],active['route'],edits) as control_receipt:
                        evaluate(active,'confirm',proposal['name']+f'_random{seed}_confirm')
                    old.write_json(out/(proposal['name']+f'_random{seed}_edit.json'),dict(match=match,receipts=control_receipt))
            _,after=manual.emit(active,probe['question'],max_new=p['max_new'])
            if after['generated_ids']!=probe['generation']['generated_ids']: raise RuntimeError('final rollback token parity failed')
            report['final_rollback_token_parity']=True
        report['registered_core_unchanged']=True
        report['status']='TECHNICAL_COMPLETE_QUALITY_SEPARATE'
    except BaseException as exc:
        failure=exc;report['status']='HOLD' if str(exc).startswith('HOLD:') or isinstance(exc,TimeoutError) else 'ERROR'
        report['error']=repr(exc);traceback.print_exc()
    finally:
        manifest=raw.close(lineage=dict(profile_sha256=manual.file_sha(BASE/'profile.json')))
        verify_shards(out,manifest)
        # Delta tensors outlive the strict loader unless explicitly released.
        proposals=winners=proposal=edits=u=None
        gc.collect()
        import torch as cleanup_torch
        close_owned_cuda(cleanup_torch,report)
        verify()
        report['wall_seconds']=time.monotonic()-budget.start
        old.write_json(out/'report.json',report)
    print('[FINAL] '+json.dumps(dict(status=report['status'],wall_seconds=report['wall_seconds'],variants=len(report['variants']))),flush=True)
    if failure is not None: raise failure


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('prepare','run'))
    a=p.parse_args()
    prepare() if a.phase=='prepare' else run()


if __name__=='__main__': main()
