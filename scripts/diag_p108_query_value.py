#!/usr/bin/env python3
"""Same sealed value optimizer at the final prompt token, then actual writes.

Previously exposed wording is diagnostic material, never independent test data.
Original weights, source modules and globals remain unchanged.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend
from scripts import interactive_research_infer as manual
from scripts import p108_value_edit as value
from scripts import diag_p108_value_edit as prior
from scripts import p108_query_value as core
from scripts import p108_nullspace_write as solver
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import diag_p108_weight_space as common
from scripts.p106b_shards import ShardWriter, verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT = Path(__file__).resolve().parents[1]
TAG = 'p108_query_value_v1_20261113'
BASE = ROOT/'test_result/evidence'/TAG
SOURCE = ROOT/'test_result/evidence/p108_value_relative_v1_20261113'
DEADLINE = datetime(2026, 11, 13, 8, tzinfo=timezone.utc)
SOURCES = ('scripts/p108_query_value.py', 'scripts/diag_p108_query_value.py',
           'scripts/test_p108_query_value.py', 'scripts/test_p108_query_driver.py',
           'scripts/p108_nullspace_write.py', 'scripts/p108_value_edit.py',
           'scripts/diag_p108_value_edit.py', 'scripts/p108_wsp_attention.py',
           'scripts/p108_weight_space.py', 'scripts/diag_p108_weight_space.py',
           'scripts/p106b_shards.py', 'scripts/diag_p107_hybrid_mntp.py')


class Budget:
    def __init__(self): self.start = time.monotonic()
    def check(self):
        if time.monotonic()-self.start > 5400 or (DEADLINE-datetime.now(timezone.utc)).total_seconds() < 900:
            raise TimeoutError('query-value authority or cleanup reserve')


def pack(active, row):
    item = prior.pack(active, row)
    return dict(item, position=core.prompt_end(item))


@contextmanager
def oracle(active, module, row, delta):
    item = pack(active, dict(row, expected=row.get('expected') or 'x'))
    with value.inject(module, item['position'], delta): yield


def cap_status(relative):
    if not 0 < relative <= .20: return 'CAP20_REJECTED'
    return 'PRIMARY_CAP5' if relative <= .05 else 'LARGE_EDIT_DIAGNOSTIC_ONLY'


def pick(candidates):
    chosen = min(candidates, key=lambda c:(-c['oracle_fit']['exact'],
        c['optimization']['trace'][-1]['nll'], c['optimization']['actual_value_norm']))
    return chosen if chosen['oracle_fit']['exact'] else None


def prepare():
    if BASE.exists(): raise FileExistsError('fresh query-value namespace required')
    if datetime.now(timezone.utc) >= DEADLINE: raise TimeoutError('authority expired')
    old = common.read_json(SOURCE/'profile.json'); report = common.read_json(SOURCE/'actual/report.json')
    if report['status'] != 'TECHNICAL_COMPLETE_QUALITY_SEPARATE' or not report['registered_core_unchanged']:
        raise ValueError('closed same-subject optimizer study required')
    manifest = common.read_json(SOURCE/'actual/answers_shards_manifest.json'); verify_shards(SOURCE/'actual', manifest)
    references = {str(path.relative_to(ROOT)):manual.file_sha(path) for path in
        [SOURCE/'data.json', SOURCE/'profile.json', SOURCE/'actual/report.json', SOURCE/'actual/answers_shards_manifest.json']}
    for s in manifest['shards']:
        path = SOURCE/'actual'/s['path']; references[str(path.relative_to(ROOT))] = manual.file_sha(path)
    sources = dict(manual.required_source_pins()); sources.update({n:manual.file_sha(ROOT/n) for n in SOURCES})
    common.write_json(BASE/'data.json', common.read_json(SOURCE/'data.json'))
    (BASE/'initial_plan.txt').write_bytes((ROOT/prior.PLAN).read_bytes())
    copied = {k:old[k] for k in ['layers','value_steps','value_lr','value_parameterization','kl_weight',
        'value_regularization','value_norm_cap','max_new','model']}
    common.write_json(BASE/'profile.json', dict(copied, schema='P108_QUERY_VALUE_V1', tag=TAG,
        authority_directive=115, deadline=DEADLINE.isoformat(), sources=sources, references=references,
        source_origin=report['origin'], data_sha256=manual.file_sha(BASE/'data.json'),
        plan_sha256=manual.file_sha(BASE/'initial_plan.txt'), manifest_sha256=manual.canonical_sha(manual.verify_manifest()),
        position='LAST_PROMPT_TOKEN_NOT_LAST_TEACHER_FORCED_TOKEN', selection='FIT_ORACLE_THEN_FIT_NLL_THEN_VALUE_NORM',
        primary_cap=.05, diagnostic_cap=.20, rank_rtol=1e-8, random_seeds=[9011,9029,9041],
        old_subject_candidates=report['candidates'], reused_test_not_independent=True,
        base_optimizer_updates=0, checkpoint_writes=0, max_phase_seconds=5400))
    print('[PREPARED] '+TAG, flush=True)


def verify():
    p = common.read_json(BASE/'profile.json')
    if p['authority_directive'] != 115 or p['deadline'] != DEADLINE.isoformat(): raise ValueError('frozen authority mismatch')
    for name, sha in dict(p['sources'], **p['references']).items():
        if manual.file_sha(ROOT/name) != sha: raise ValueError('source/reference changed: '+name)
    for name, key in [('data.json','data_sha256'), ('initial_plan.txt','plan_sha256')]:
        if manual.file_sha(BASE/name) != p[key]: raise ValueError('frozen data/plan changed')
    if manual.canonical_sha(manual.verify_manifest()) != p['manifest_sha256']: raise ValueError('original model changed')
    return p


def capture(active, module, row):
    item = pack(active, row); saved = {}
    def hook(_module, args, output):
        if saved: raise RuntimeError('one capture per forward required')
        saved['keys'] = args[0][0].detach().cpu().clone()
    handle = module.register_forward_hook(hook)
    try:
        with torch.no_grad(): prior.target_nll(active, item)
    finally: handle.remove()
    k = saved['keys']; pos = item['position']
    return k[pos], torch.cat([k[:pos], k[pos+1:]])


def run():
    p = verify(); budget = Budget(); budget.check(); out = BASE/'actual'
    if out.exists(): raise FileExistsError('query-value actual already attempted')
    writer = ShardWriter(out, 'answers', limit=3_000_000)
    report = dict(schema=p['schema'], tag=TAG, status='RUNNING', candidates=[], facts=[],
        reused_test_not_independent=True, base_optimizer_updates=0, checkpoint_writes=0)
    active = modules = module = delta = candidates = candidate = selected = generic = None
    original_globals = {k:prior.optimize_value.__globals__[k] for k in ['pack','oracle']}
    optimize = core.adapt_optimizer(prior.optimize_value, pack, oracle)
    failure = None
    try:
        manual.require_idle_gpu()
        reply = subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=10, check=True)
        if not reply.stdout.strip().isdigit() or int(reply.stdout.strip()) < 4096:
            raise MemoryError('point query requires4096MiB free; not continuous OOM assurance')
        report['free_mib_at_entry'] = int(reply.stdout.strip())
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            torch.set_num_threads(4); torch.cuda.reset_peak_memory_stats()
            report['origin'] = {k:active[k] for k in ['name','checkpoint_sha256','core_sha256','tokenizer_sha256']}
            if report['origin'] != p['source_origin']: raise ValueError('source model identity changed')
            data = common.read_json(BASE/'data.json'); rows = data['rows']; modules = wsp.outputs(active['model'])
            sm = common.read_json(SOURCE/'actual/answers_shards_manifest.json'); baseline = {}
            for s in sm['shards']:
                for line in (SOURCE/'actual'/s['path']).read_text().splitlines():
                    r = json.loads(line)
                    if r['variant'] == 'original':
                        if r['id'] in baseline: raise ValueError('duplicate original row')
                        baseline[r['id']] = r
            if set(baseline) != {r['id'] for r in rows}: raise ValueError('complete source baseline required')
            for row in rows:
                if any(baseline[row['id']][k] != row[k] for k in row): raise ValueError('source input changed')
                writer.append(dict(baseline[row['id']], reused_source=str(SOURCE.relative_to(ROOT))))
            probe = rows[0]; _, live = manual.emit(active, probe['question'], max_new=64)
            if live['generated_ids'] != baseline[probe['id']]['generation']['generated_ids']:
                raise RuntimeError('initial live baseline parity failed')
            generic = {layer:[] for layer in p['layers']}; handles = []
            for layer in p['layers']:
                def hook(_module,args,_output,layer=layer): generic[layer].append(args[0][0,-8:].detach().cpu())
                handles.append(modules[f'mlp:{layer}'].register_forward_hook(hook))
            try:
                with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
                    for question in data['calibration_questions']:
                        budget.check(); ids = common.prompt_ids(active, question)
                        active['model'](torch.tensor([ids], device='cuda'), logits_last_only=True)
            finally:
                for handle in handles: handle.remove()
            generic = {k:torch.cat(v) for k,v in generic.items()}
            with value.freeze_parameters(active['model']):
                for fact in dict.fromkeys(r['fact'] for r in rows if r['fact']):
                    fits = [r for r in rows if r['fact'] == fact and r['split'] == 'fit']; sub = fits[0]['subject']
                    texts = ([f'{sub}에 관해 간단히 소개하세요.', f'{sub}에 관한 정보를 알려주세요.']
                        if fits[0]['language'] == 'ko' else [f'Give a short introduction to {sub}.', f'Tell me something about {sub}.'])
                    anchors = [dict(fits[0], id=f'{fact}:anchor:{i}', question=q, expected=None) for i,q in enumerate(texts)]
                    candidates = []
                    for layer in p['layers']:
                        budget.check(); module = modules[f'mlp:{layer}']; value.refresh_autograd_views(active['model'], active['route'])
                        _, v, stats = optimize(active, module, fits, anchors, p, budget)
                        generated = []
                        for row in fits:
                            with oracle(active, module, row, v.to(module.weight)):
                                generated.append(prior.generated(active,row,writer,f'{fact}:layer{layer}:last_oracle_fit'))
                        old = next(c for c in p['old_subject_candidates'] if c['fact'] == fact and c['layer'] == layer)
                        candidate = dict(fact=fact,layer=layer,optimization=stats,oracle_fit=metrics.summarize(generated),
                            old_subject_oracle_fit=old['oracle_fit'],value_delta=v.tolist())
                        candidates.append(candidate); report['candidates'].append(candidate)
                        common.write_json(out/f'{fact}_layer{layer}_fit.json', candidate)
                        print('[QUERY_VALUE] '+json.dumps(dict(fact=fact,layer=layer,last_fit=candidate['oracle_fit']['exact'],
                            subject_fit=old['oracle_fit']['exact'])),flush=True)
                    selected = pick(candidates)
                    if selected is None:
                        report['facts'].append(dict(fact=fact,status='ORACLE_GATE_NEGATIVE_NOT_RUN')); continue
                    layer = selected['layer']; module = modules[f'mlp:{layer}']; v = torch.tensor(selected['value_delta'])
                    captures = [capture(active,module,r) for r in fits]; keys = torch.stack([c[0] for c in captures])
                    protected = torch.cat([*(c[1] for c in captures),generic[layer]])
                    fact_report = dict(fact=fact,selected=selected,arms=[])
                    try:
                        factors,stats = solver.constrained_factors(keys,v[None,:].repeat(len(keys),1),protected,rank_rtol=p['rank_rtol'])
                    except ValueError as exc:
                        if 'infeasible' not in str(exc): raise
                        fact_report.update(status='PROTECTED_TARGET_INFEASIBLE',reason=str(exc)); report['facts'].append(fact_report); continue
                    cpu_delta = solver.dense_delta(factors); relative = float(cpu_delta.norm())/float(module.weight.detach().norm())
                    fact_report.update(status=cap_status(relative),relative_weight_norm=relative,constraint=stats)
                    common.write_json(out/f'{fact}_write_packet.json',dict(left=factors['left'].tolist(),right=factors['right'].tolist(),
                        base_weight_sha256=metrics.tensor_sha(module.weight),delta_sha256=metrics.tensor_sha(cpu_delta),stats=fact_report))
                    if fact_report['status'] == 'CAP20_REJECTED': report['facts'].append(fact_report); continue
                    singular = torch.linalg.svdvals(factors['left'])
                    rank = max(1,int((singular>singular.max()*1e-8).sum()))
                    arms = [('last_value_write',cpu_delta)]
                    for seed in p['random_seeds']:
                        rng = torch.Generator().manual_seed(seed)
                        random = torch.randn(cpu_delta.shape[0],rank,generator=rng)@torch.randn(rank,cpu_delta.shape[1],generator=rng)
                        random *= cpu_delta.norm()/random.norm(); arms.append((f'random{seed}',random))
                    confirm = [r for r in rows if r['fact'] == fact or r['split'] == 'protect' or (r['split'] == 'dev' and r['fact'] != fact)]
                    for name, matrix in arms:
                        budget.check(); delta = matrix.to(module.weight)
                        with wsp.edit(active['model'],active['route'],[(f'mlp:{layer}',delta)]) as receipt:
                            answers = [prior.generated(active,r,writer,f'{fact}:{name}') for r in confirm]
                        fact_report['arms'].append(dict(name=name,receipt=receipt,relative_weight_norm=relative,
                            fit=metrics.summarize([r for r in answers if r['fact']==fact and r['split']=='fit']),
                            dev=metrics.summarize([r for r in answers if r['fact']==fact and r['split']=='dev']),
                            reused_wording=metrics.summarize([r for r in answers if r['fact']==fact and r['split']=='test']),
                            protect=metrics.summarize([r for r in answers if r['split']=='protect']),all=metrics.summarize(answers)))
                    report['facts'].append(fact_report); common.write_json(out/f'{fact}_report.json',fact_report)
                    module = delta = cpu_delta = matrix = random = arms = factors = captures = keys = protected = answers = None
            _, live = manual.emit(active,probe['question'],max_new=64)
            if live['generated_ids'] != baseline[probe['id']]['generation']['generated_ids']: raise RuntimeError('final live rollback failed')
            report.update(registered_core_unchanged=True,final_rollback_token_parity=True,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
            modules = module = delta = None
        active = None; report['status'] = 'TECHNICAL_COMPLETE_QUALITY_SEPARATE'
    except BaseException as exc:
        traceback.print_exc(); report.update(status='ERROR',error=repr(exc)); failure=RuntimeError('Query-value: '+repr(exc))
    finally:
        active = modules = module = delta = cpu_delta = matrix = random = arms = factors = captures = keys = protected = answers = None
        gc.collect()
        try: close_owned_cuda(torch,report)
        except BaseException as exc:
            report.update(status='ERROR',cleanup_error=repr(exc))
            if failure is None: failure=RuntimeError('Query-value cleanup: '+repr(exc))
        report['source_optimizer_globals_unchanged'] = all(prior.optimize_value.__globals__[k] is obj for k,obj in original_globals.items())
        if not report['source_optimizer_globals_unchanged']:
            report['status']='ERROR'; failure=RuntimeError('source optimizer globals changed')
        try: verify(); report['sources_assets_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',source_error=repr(exc))
            if failure is None: failure=RuntimeError('Query-value source: '+repr(exc))
        manifest = writer.close(lineage=dict(profile_sha256=manual.file_sha(BASE/'profile.json'))); verify_shards(out,manifest)
        report.update(seconds=time.monotonic()-budget.start,answer_rows=manifest['rows'],
            value_optimizer_updates=sum(c['optimization']['value_optimizer_updates'] for c in report['candidates']),
            supervised_target_token_exposures=sum(c['optimization']['supervised_target_token_exposures'] for c in report['candidates']))
        common.write_json(out/'report.json',report)
    if failure is not None: raise failure
    print('[COMPLETE] '+json.dumps(dict(status=report['status'],seconds=report['seconds'],rows=report['answer_rows'])),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);a=p.parse_args()
    (prepare if a.phase=='prepare' else run)()


if __name__=='__main__': main()
