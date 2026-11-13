#!/usr/bin/env python3
"""Frozen final-prompt values written with soft covariance or plain rank one."""
import argparse
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import interactive_research_infer as manual
from scripts import diag_p108_query_value as prior
from scripts import p108_value_edit as value
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import diag_p108_weight_space as common
from scripts.diag_p108_nullspace_write import target_logits
from scripts.p106b_shards import ShardWriter,verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT=Path(__file__).resolve().parents[1]
TAG='p108_query_covariance_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
SOURCE=prior.BASE;DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SOURCES=tuple(dict.fromkeys((*prior.SOURCES,'scripts/diag_p108_query_covariance.py',
    'scripts/test_p108_query_covariance.py','scripts/diag_p108_nullspace_write.py')))


class Budget:
    def __init__(self):self.start=time.monotonic()
    def check(self):
        if time.monotonic()-self.start>3600 or (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('query covariance phase/authority reserve')


def frozen_selected(report):
    selected=[f['selected'] for f in report['facts']]
    if (len(selected)!=12 or len({s['fact'] for s in selected})!=12 or
        any(s['layer'] not in (8,11) or s['oracle_fit']['exact']<1 or len(s['value_delta'])!=768 for s in selected)):
        raise ValueError('same12 frozen values/layers required; no reselection')
    return selected


def choose_reference(candidates):
    return next((c for name in ('covariance','plain') for c in candidates if c['name']==name),None)


def prepare():
    if BASE.exists():raise FileExistsError('fresh covariance namespace required')
    if datetime.now(timezone.utc)>=DEADLINE:raise TimeoutError('authority expired')
    report=common.read_json(SOURCE/'actual/report.json')
    if report['status']!='TECHNICAL_COMPLETE_QUALITY_SEPARATE' or not report['registered_core_unchanged']:
        raise ValueError('completed query value study required')
    selected=frozen_selected(report);manifest=common.read_json(SOURCE/'actual/answers_shards_manifest.json')
    verify_shards(SOURCE/'actual',manifest)
    paths=[SOURCE/'profile.json',SOURCE/'data.json',SOURCE/'actual/report.json',SOURCE/'actual/answers_shards_manifest.json']
    paths += [SOURCE/'actual'/s['path'] for s in manifest['shards']]
    paths += [SOURCE/'actual'/(s['fact']+'_write_packet.json') for s in selected]
    refs={str(p.relative_to(ROOT)):manual.file_sha(p) for p in paths}
    sources=dict(manual.required_source_pins());sources.update({n:manual.file_sha(ROOT/n) for n in SOURCES})
    common.write_json(BASE/'data.json',common.read_json(SOURCE/'data.json'))
    (BASE/'initial_plan.txt').write_bytes((ROOT/prior.prior.PLAN).read_bytes())
    common.write_json(BASE/'profile.json',dict(schema='P108_QUERY_COVARIANCE_V1',tag=TAG,
        authority_directive=115,deadline=DEADLINE.isoformat(),model=prior.prior.MODEL,sources=sources,references=refs,
        selected=selected,source_origin=report['origin'],data_sha256=manual.file_sha(BASE/'data.json'),
        plan_sha256=manual.file_sha(BASE/'initial_plan.txt'),manifest_sha256=manual.canonical_sha(manual.verify_manifest()),
        covariance_ridge_ratio=.01,primary_cap=.05,diagnostic_cap=.20,random_seeds=[10007,10009,10037],
        base_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,reused_test_not_independent=True,
        max_new=64,max_phase_seconds=3600))
    print('[PREPARED] '+TAG,flush=True)


def verify():
    p=common.read_json(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat():raise ValueError('frozen authority mismatch')
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/name)!=sha:raise ValueError('pinned source/reference changed: '+name)
    for name,key in [('data.json','data_sha256'),('initial_plan.txt','plan_sha256')]:
        if manual.file_sha(BASE/name)!=p[key]:raise ValueError('frozen data/plan changed')
    if manual.canonical_sha(manual.verify_manifest())!=p['manifest_sha256']:raise ValueError('original model changed')
    return p


def run():
    p=verify();budget=Budget();budget.check();out=BASE/'actual'
    if out.exists():raise FileExistsError('covariance actual already attempted')
    writer=ShardWriter(out,'answers',limit=3_000_000)
    report=dict(schema=p['schema'],tag=TAG,status='RUNNING',facts=[],reused_test_not_independent=True,
        base_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0)
    active=modules=module=delta=reference=generated=oracle_logits=items=item=None;failure=None
    try:
        manual.require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
            capture_output=True,text=True,timeout=10,check=True).stdout.strip()
        if not free.isdigit() or int(free)<4096:raise MemoryError('4096MiB point free required')
        report['free_mib_at_entry']=int(free)
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
            report['origin']={k:active[k] for k in ['name','checkpoint_sha256','core_sha256','tokenizer_sha256']}
            if report['origin']!=p['source_origin']:raise ValueError('completed source model changed')
            rows=common.read_json(BASE/'data.json')['rows'];modules=wsp.outputs(active['model'])
            manifest=common.read_json(SOURCE/'actual/answers_shards_manifest.json');original={};hard={}
            for s in manifest['shards']:
                for line in (SOURCE/'actual'/s['path']).read_text().splitlines():
                    r=json.loads(line)
                    if r['variant']=='original':original[r['id']]=r
                    elif r['variant'].endswith(':last_value_write'):hard[r['variant'],r['id']]=r
            if set(original)!={r['id'] for r in rows}:raise ValueError('complete original baseline required')
            for row in rows:
                if any(original[row['id']][k]!=row[k] for k in row):raise ValueError('original input changed')
                writer.append(dict(original[row['id']],reused_source=str(SOURCE.relative_to(ROOT))))
            for row in hard.values():writer.append(dict(row,reused_source=str(SOURCE.relative_to(ROOT))))
            probe=rows[0];_,live=manual.emit(active,probe['question'],max_new=64)
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('initial original token parity failed')
            keys={layer:[] for layer in {s['layer'] for s in p['selected']}};handles=[]
            for layer in keys:
                def hook(_module,args,_output,layer=layer):keys[layer].append(args[0][0,-8:].detach().cpu())
                handles.append(modules[f'mlp:{layer}'].register_forward_hook(hook))
            try:
                with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                    for question in common.read_json(BASE/'data.json')['calibration_questions']:
                        budget.check();ids=common.prompt_ids(active,question)
                        active['model'](torch.tensor([ids],device='cuda'),logits_last_only=True)
            finally:
                for handle in handles:handle.remove()
            inverses={};report['covariance']={}
            for layer,parts in keys.items():
                inverse,stats=value.inverse_second_moment(torch.cat(parts),p['covariance_ridge_ratio'])
                inverses[layer]=inverse;report['covariance'][str(layer)]=stats
            keys=handles=None
            for index,selected in enumerate(p['selected']):
                budget.check();fact=selected['fact'];layer=selected['layer'];module=modules[f'mlp:{layer}']
                fits=[r for r in rows if r['fact']==fact and r['split']=='fit'];items=[prior.pack(active,r) for r in fits]
                fit_keys=torch.stack([prior.capture(active,module,r)[0] for r in fits]);key=fit_keys.mean(0)
                v=torch.tensor(selected['value_delta']);oracle_logits=[]
                for item in items:
                    with value.inject(module,item['position'],v.to(module.weight)):oracle_logits.append(target_logits(active,item))
                if index==0:
                    packet=common.read_json(SOURCE/'actual'/(fact+'_write_packet.json'))
                    if metrics.tensor_sha(module.weight)!=packet['base_weight_sha256']:raise ValueError('source matrix changed')
                    matrix=(torch.tensor(packet['left'],dtype=torch.float64)@torch.tensor(packet['right'],dtype=torch.float64)).float()
                    if metrics.tensor_sha(matrix)!=packet['delta_sha256']:raise ValueError('hard packet changed')
                    with wsp.edit(active['model'],active['route'],[(f'mlp:{layer}',matrix.to(module.weight))]):
                        _,live=manual.emit(active,fits[0]['question'],max_new=64)
                    if live['generated_ids']!=hard[fact+':last_value_write',fits[0]['id']]['generation']['generated_ids']:
                        raise RuntimeError('source hard-write live parity failed')
                    report['source_hard_live_parity']=True
                candidates=[];fact_report=dict(fact=fact,layer=layer,attempts=[],arms=[])
                for name,inv in [('covariance',inverses[layer]),('plain',torch.eye(key.numel(),dtype=torch.float64))]:
                    matrix,stats=value.rank_one(key,v,inv);relative=float(matrix.norm())/float(module.weight.detach().norm())
                    status=prior.cap_status(relative)
                    residual=(matrix.double()@fit_keys.double().T-v.double()[:,None]).norm(dim=0)/v.double().norm()
                    attempt=dict(name=name,cap_status=status,relative_weight_norm=relative,fit_key_relative_residuals=residual.tolist(),write=stats)
                    fact_report['attempts'].append(attempt)
                    direction=inv@key.double();direction/=key.double()@direction
                    common.write_json(out/f'{fact}_{name}_packet.json',dict(left=v.tolist(),right=direction.tolist(),
                        base_weight_sha256=metrics.tensor_sha(module.weight),delta_sha256=metrics.tensor_sha(matrix),stats=attempt))
                    if status!='CAP20_REJECTED':candidates.append(dict(name=name,delta=matrix,relative=relative))
                reference=choose_reference(candidates)
                if reference is None:
                    report['facts'].append(fact_report);items=module=oracle_logits=None;continue
                for seed in p['random_seeds']:
                    rng=torch.Generator().manual_seed(seed)
                    matrix=torch.randn(module.weight.shape[0],1,generator=rng)@torch.randn(1,module.weight.shape[1],generator=rng)
                    matrix*=reference['delta'].norm()/matrix.norm()
                    candidates.append(dict(name=f'random{seed}',delta=matrix,relative=reference['relative'],matched_to=reference['name']))
                confirm=[r for r in rows if r['fact']==fact or r['split']=='protect' or (r['split']=='dev' and r['fact']!=fact)]
                for candidate in candidates:
                    budget.check();delta=candidate['delta'].to(module.weight)
                    with wsp.edit(active['model'],active['route'],[(f'mlp:{layer}',delta)]) as receipt:
                        actual=[target_logits(active,item) for item in items]
                        comparisons=[dict(max_abs=float((a-b).abs().max()),argmax_equal=bool(torch.equal(a.argmax(-1),b.argmax(-1)))) for a,b in zip(actual,oracle_logits)]
                        generated=[]
                        for row in confirm:
                            budget.check();generated.append(prior.prior.generated(active,row,writer,fact+':'+candidate['name']))
                    fact_report['arms'].append(dict(name=candidate['name'],relative_weight_norm=candidate['relative'],
                        cap_status=prior.cap_status(candidate['relative']),matched_to=candidate.get('matched_to'),receipt=receipt,
                        oracle_logit_comparison=comparisons,all=metrics.summarize(generated),
                        **{split:metrics.summarize([r for r in generated if r['fact']==fact and r['split']==split]) for split in ['fit','dev','test']},
                        protect=metrics.summarize([r for r in generated if r['split']=='protect'])))
                report['facts'].append(fact_report);common.write_json(out/f'{fact}_report.json',fact_report)
                print('[QUERY_COVARIANCE] '+json.dumps(dict(fact=fact,arms=[dict(name=a['name'],fit=a['fit']['exact'],dev=a['dev']['exact'],
                    wording=a['test']['exact'],relative=a['relative_weight_norm']) for a in fact_report['arms']])),flush=True)
                module=delta=reference=generated=oracle_logits=items=item=candidates=candidate=actual=matrix=None
            _,live=manual.emit(active,probe['question'],max_new=64)
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('final original rollback parity failed')
            report.update(registered_core_unchanged=True,final_rollback_token_parity=True,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
            modules=module=delta=items=item=None
        active=None;report['status']='TECHNICAL_COMPLETE_QUALITY_SEPARATE'
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError('Query covariance: '+repr(exc))
    finally:
        active=modules=module=delta=reference=generated=oracle_logits=items=item=candidates=candidate=actual=matrix=None
        gc.collect()
        try:close_owned_cuda(torch,report)
        except BaseException as exc:
            report.update(status='ERROR',cleanup_error=repr(exc))
            if failure is None:failure=RuntimeError('Query covariance cleanup: '+repr(exc))
        try:verify();report['sources_assets_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',source_error=repr(exc))
            if failure is None:failure=RuntimeError('Query covariance source: '+repr(exc))
        manifest=writer.close(lineage=dict(profile_sha256=manual.file_sha(BASE/'profile.json')));verify_shards(out,manifest)
        report.update(seconds=time.monotonic()-budget.start,answer_rows=manifest['rows']);common.write_json(out/'report.json',report)
    if failure is not None:raise failure
    print('[COMPLETE] '+json.dumps(dict(status=report['status'],seconds=report['seconds'],rows=report['answer_rows'])),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);a=p.parse_args()
    (prepare if a.phase=='prepare' else run)()


if __name__=='__main__':main()
