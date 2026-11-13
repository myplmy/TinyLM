#!/usr/bin/env python3
"""Fit-only oracle gate, finite-key protection, and real registered edits."""
import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import time
import traceback
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend
from scripts import interactive_research_infer as manual
from scripts import p108_value_edit as value
from scripts import diag_p108_value_edit as prior
from scripts import p108_nullspace_write as core
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import diag_p108_weight_space as common
from scripts.p106b_shards import ShardWriter, verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT=Path(__file__).resolve().parents[1]
TAG='p108_nullspace_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
SOURCE=ROOT/'test_result/evidence/p108_value_relative_v1_20261113'
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SOURCES=('scripts/diag_p108_nullspace_write.py','scripts/p108_nullspace_write.py',
         'scripts/test_p108_nullspace_write.py','scripts/test_p108_nullspace_driver.py',
         'scripts/diag_p108_value_edit.py','scripts/p108_value_edit.py','scripts/p108_wsp_attention.py',
         'scripts/p108_weight_space.py','scripts/diag_p108_weight_space.py','scripts/p106b_shards.py',
         'scripts/diag_p107_hybrid_mntp.py')


class Budget:
    def __init__(self):self.start=time.monotonic()
    def check(self):
        if time.monotonic()-self.start>3600 or (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('Nov13 nullspace authority/phase reserve')


def pick_candidates(candidates):
    selected=[];skipped=[]
    for fact in dict.fromkeys(c['fact'] for c in candidates):
        rows=[c for c in candidates if c['fact']==fact]
        chosen=min(rows,key=lambda c:(-c['oracle_fit']['exact'],c['optimization']['trace'][-1]['nll'],c['write']['delta_norm']))
        if not chosen['oracle_fit']['exact']:skipped.append(dict(fact=fact,reason='ORACLE_GATE_NEGATIVE_NOT_RUN'))
        else:selected.append(chosen)
    return selected,skipped


def cap_status(relative):
    if not 0<relative<=.20:return 'CAP20_REJECTED'
    return 'PRIMARY_CAP5' if relative<=.05 else 'LARGE_EDIT_DIAGNOSTIC_ONLY'


def prepare():
    if BASE.exists():raise FileExistsError('new nullspace namespace required')
    if datetime.now(timezone.utc)>=DEADLINE:raise TimeoutError('authority expired')
    report=common.read_json(SOURCE/'actual/report.json')
    if report['status']!='TECHNICAL_COMPLETE_QUALITY_SEPARATE' or not report['registered_core_unchanged']:
        raise ValueError('closed source oracle experiment required')
    selected,skipped=pick_candidates(report['candidates'])
    references={}
    for path in (SOURCE/'profile.json',SOURCE/'data.json',SOURCE/'actual/report.json',
                 SOURCE/'actual/answers_shards_manifest.json'):
        references[str(path.relative_to(ROOT))]=manual.file_sha(path)
    manifest=common.read_json(SOURCE/'actual/answers_shards_manifest.json');verify_shards(SOURCE/'actual',manifest)
    for shard in manifest['shards']:
        path=SOURCE/'actual'/shard['path'];references[str(path.relative_to(ROOT))]=manual.file_sha(path)
    for chosen in selected:
        if manual.file_sha(ROOT/chosen['packet'])!=chosen['packet_sha256']:raise ValueError('source packet changed')
        references[chosen['packet']]=chosen['packet_sha256']
    sources=dict(manual.required_source_pins());sources.update({name:manual.file_sha(ROOT/name) for name in SOURCES})
    common.write_json(BASE/'data.json',common.read_json(SOURCE/'data.json'))
    (BASE/'initial_plan.txt').write_bytes((ROOT/prior.PLAN).read_bytes())
    common.write_json(BASE/'profile.json',dict(schema='P108_NULLSPACE_WRITE_V1',tag=TAG,authority_directive=115,
        deadline=DEADLINE.isoformat(),model=prior.MODEL,sources=sources,references=references,
        source_origin=report['origin'],selected=selected,skipped=skipped,selection='FIT_ORACLE_ONLY',
        data_sha256=manual.file_sha(BASE/'data.json'),plan_sha256=manual.file_sha(BASE/'initial_plan.txt'),
        manifest_sha256=manual.canonical_sha(manual.verify_manifest()),max_new=64,
        rank_rtol=1e-8,primary_cap=.05,diagnostic_cap=.20,random_seeds=[8191,8209,8219],
        reused_test_not_independent=True,value_optimizer_updates=0,base_optimizer_updates=0,checkpoint_writes=0))
    print('[PREPARED] '+json.dumps(dict(tag=TAG,selected=len(selected),skipped=len(skipped))),flush=True)


def verify():
    p=common.read_json(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat():raise ValueError('frozen authority mismatch')
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/name)!=sha:raise ValueError('pinned source/reference changed: '+name)
    if manual.file_sha(BASE/'data.json')!=p['data_sha256'] or manual.file_sha(BASE/'initial_plan.txt')!=p['plan_sha256']:
        raise ValueError('frozen data/plan changed')
    if manual.canonical_sha(manual.verify_manifest())!=p['manifest_sha256']:raise ValueError('original model changed')
    return p


def capture_fit(active,module,row):
    item=prior.pack(active,row);cap={}
    def hook(_module,args,_output):cap['keys']=args[0][0].detach().cpu().clone()
    handle=module.register_forward_hook(hook)
    try:
        with torch.no_grad():prior.target_nll(active,item)
    finally:handle.remove()
    keys=cap['keys'];position=item['position']
    return keys[position],torch.cat((keys[:position],keys[position+1:])),item


def target_logits(active,item):
    with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
        hidden=active['model'](item['x'],return_hidden=True)
        return active['model']._head_logits(hidden[:,item['start']:])[0].detach().cpu()


def run():
    p=verify();budget=Budget();budget.check();out=BASE/'actual'
    if out.exists():raise FileExistsError('actual namespace exists')
    writer=ShardWriter(out,'answers',limit=3_000_000)
    report=dict(schema=p['schema'],status='RUNNING',tag=TAG,selected=p['selected'],skipped=p['skipped'],facts=[],
        reused_test_not_independent=True,base_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0)
    failure=None;active=modules=module=delta=items=item=None
    try:
        with manual.selected_runtime(manual.resolve_model(prior.MODEL)) as active:
            torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
            report['origin']={k:active[k] for k in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256')}
            if report['origin']!=p['source_origin']:raise ValueError('source completed model changed')
            rows=common.read_json(BASE/'data.json')['rows'];modules=wsp.outputs(active['model'])
            source_manifest=common.read_json(SOURCE/'actual/answers_shards_manifest.json')
            baseline={}
            for shard in source_manifest['shards']:
                for line in (SOURCE/'actual'/shard['path']).read_text().splitlines():
                    row=json.loads(line)
                    if row['variant']=='original':baseline[row['id']]=row
            if set(baseline)!={r['id'] for r in rows}:raise ValueError('complete source baseline required')
            for row in rows:
                if any(baseline[row['id']][k]!=row[k] for k in row):raise ValueError('baseline input changed')
                writer.append(dict(baseline[row['id']],reused_source=str(SOURCE.relative_to(ROOT))))
            probe=rows[0];_,parity=manual.emit(active,probe['question'],max_new=64)
            if parity['generated_ids']!=baseline[probe['id']]['generation']['generated_ids']:raise RuntimeError('live baseline mismatch')
            generic={layer:[] for layer in {c['layer'] for c in p['selected']}};handles=[]
            for layer in generic:
                def hook(_module,args,_output,layer=layer):generic[layer].append(args[0][0,-8:].detach().cpu())
                handles.append(modules[f'mlp:{layer}'].register_forward_hook(hook))
            try:
                with torch.no_grad():
                    for question in common.read_json(BASE/'data.json')['calibration_questions']:
                        budget.check();ids=common.prompt_ids(active,question)
                        with sdpa_kernel(SDPBackend.MATH):active['model'](torch.tensor([ids],device='cuda'),logits_last_only=True)
            finally:
                for handle in handles:handle.remove()
            generic={k:torch.cat(v) for k,v in generic.items()}
            for chosen in p['selected']:
                budget.check();fact=chosen['fact'];layer=chosen['layer'];module=modules[f'mlp:{layer}']
                fits=[r for r in rows if r['fact']==fact and r['split']=='fit']
                captures=[capture_fit(active,module,r) for r in fits]
                keys=torch.stack([c[0] for c in captures]);protected=torch.cat([c[1] for c in captures]);items=[c[2] for c in captures]
                packet=common.read_json(ROOT/chosen['packet']);v=torch.tensor(packet['left'],dtype=torch.float64)
                if metrics.tensor_sha(module.weight)!=packet['base_weight_sha256']:raise ValueError('source matrix changed')
                source_delta=(v[:,None]@torch.tensor(packet['right'],dtype=torch.float64)[None,:]).float()
                if metrics.tensor_sha(source_delta)!=packet['delta_sha256']:raise ValueError('source packet reconstruction changed')
                oracle=[]
                for item in items:
                    with value.inject(module,item['position'],v.to(module.weight)):
                        oracle.append(target_logits(active,item))
                candidates=[dict(name='source_covariance',delta=source_delta,factors=None,relative=float(source_delta.norm())/float(module.weight.detach().norm()))]
                fact_report=dict(fact=fact,layer=layer,source_oracle_fit=chosen['oracle_fit'],attempts=[],arms=[])
                for name,protect in (('fit_non_subject',protected),('fit_plus_generic',torch.cat((protected,generic[layer])))):
                    try:
                        factors,stats=core.constrained_factors(keys,v[None,:].repeat(len(keys),1),protect,rank_rtol=p['rank_rtol'])
                    except ValueError as exc:
                        if 'infeasible' not in str(exc):raise
                        fact_report['attempts'].append(dict(name=name,status='PROTECTED_TARGET_INFEASIBLE',reason=str(exc)));continue
                    cpu_delta=core.dense_delta(factors);relative=float(cpu_delta.norm())/float(module.weight.detach().norm())
                    status=cap_status(relative);attempt=dict(name=name,status=status,relative_weight_norm=relative,**stats)
                    fact_report['attempts'].append(attempt)
                    common.write_json(out/f'{fact}_{name}_factors.json',dict(left=factors['left'].tolist(),right=factors['right'].tolist(),
                        delta_sha256=metrics.tensor_sha(cpu_delta),base_weight_sha256=packet['base_weight_sha256'],stats=attempt))
                    if status!='CAP20_REJECTED':candidates.append(dict(name=name,delta=cpu_delta,factors=factors,relative=relative))
                reference=next((c for key in ('fit_plus_generic','fit_non_subject') for c in candidates if c['name']==key),None)
                if reference is not None:
                    singular=torch.linalg.svdvals(reference['factors']['left'])
                    rank=max(1,int((singular>singular.max()*1e-8).sum()))
                    for seed in p['random_seeds']:
                        generator=torch.Generator().manual_seed(seed)
                        left=torch.randn(source_delta.shape[0],rank,generator=generator);right=torch.randn(rank,source_delta.shape[1],generator=generator)
                        random=left@right;random*=reference['delta'].norm()/random.norm()
                        candidates.append(dict(name=f'random{seed}',delta=random,factors=None,relative=reference['relative'],matched_to=reference['name'],rank=rank))
                confirm=[r for r in rows if r['fact']==fact or r['split']=='protect' or (r['split']=='dev' and r['fact']!=fact)]
                fact_report['baseline']=metrics.summarize([baseline[r['id']] for r in confirm])
                for candidate in candidates:
                    budget.check();delta=candidate['delta'].to(module.weight)
                    with wsp.edit(active['model'],active['route'],[(f'mlp:{layer}',delta)]) as receipt:
                        actual=[target_logits(active,item) for item in items]
                        comparisons=[dict(max_abs=float((a-b).abs().max()),argmax_equal=bool(torch.equal(a.argmax(-1),b.argmax(-1)))) for a,b in zip(actual,oracle)]
                        generated=[]
                        for row in confirm:
                            budget.check();generated.append(prior.generated(active,row,writer,f'{fact}:{candidate["name"]}'))
                    arm=dict(name=candidate['name'],relative_weight_norm=candidate['relative'],cap_status=cap_status(candidate['relative']),
                        oracle_logit_comparison=comparisons,receipt=receipt,all=metrics.summarize(generated),
                        fit=metrics.summarize([r for r in generated if r['fact']==fact and r['split']=='fit']),
                        own_test=metrics.summarize([r for r in generated if r['fact']==fact and r['split']=='test']))
                    fact_report['arms'].append(arm)
                    print('[NULLSPACE] '+json.dumps(dict(fact=fact,name=arm['name'],fit=arm['fit']['exact'],test=arm['own_test']['exact'],
                        cap=arm['cap_status'],oracle_argmax_match=all(c['argmax_equal'] for c in comparisons))),flush=True)
                report['facts'].append(fact_report);common.write_json(out/(fact+'_report.json'),fact_report)
                captures=items=item=candidates=candidate=reference=delta=module=actual=oracle=generated=None
            _,parity=manual.emit(active,probe['question'],max_new=64)
            if parity['generated_ids']!=baseline[probe['id']]['generation']['generated_ids']:raise RuntimeError('rollback token parity failed')
            report['registered_core_unchanged']=True;report['final_rollback_token_parity']=True
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            modules=module=delta=items=item=None
        active=None;report['status']='TECHNICAL_COMPLETE_QUALITY_SEPARATE'
    except BaseException as exc:
        traceback.print_exc();report['status']='ERROR';report['error']=repr(exc);failure=RuntimeError('Original nullspace error: '+repr(exc))
    finally:
        active=modules=module=delta=items=item=captures=candidates=candidate=reference=actual=oracle=generated=None
        gc.collect()
        try:close_owned_cuda(torch,report)
        except BaseException as exc:
            report['cleanup_error']=repr(exc);report['status']='ERROR'
            if failure is None:failure=RuntimeError('Nullspace cleanup: '+repr(exc))
        manifest=writer.close(lineage=dict(profile_sha256=manual.file_sha(BASE/'profile.json')));verify_shards(out,manifest)
        report['seconds']=time.monotonic()-budget.start;report['answer_rows']=manifest['rows'];common.write_json(out/'report.json',report)
    if failure is not None:raise failure
    print('[COMPLETE] '+json.dumps(dict(status=report['status'],seconds=report['seconds'],facts=len(report['facts']))),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','run']);args=parser.parse_args()
    (prepare if args.phase=='prepare' else run)()


if __name__=='__main__':main()
