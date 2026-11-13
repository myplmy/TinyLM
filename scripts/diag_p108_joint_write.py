"""One common-layer joint packet; no per-query weight selection or new fitting."""
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
from scripts import p108_joint_write as joint
from scripts import diag_p108_query_value as prior
from scripts import diag_p108_query_transport as transport
from scripts import p108_value_edit as value
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import diag_p108_weight_space as common
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter,verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT=Path(__file__).resolve().parents[1];TAG='p108_joint_write_v1_20261113'
BASE=ROOT/'test_result/evidence'/TAG;SOURCE=prior.BASE
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SOURCES=tuple(dict.fromkeys((*transport.SOURCES,'scripts/p108_joint_write.py','scripts/test_p108_joint_write.py',
 'scripts/diag_p108_joint_write.py','scripts/test_p108_joint_driver.py')))


class Budget:
    def __init__(self):self.start=time.monotonic()
    def check(self):
        if time.monotonic()-self.start>1800 or (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('joint write phase/authority cleanup reserve')


def prepare():
    Budget().check()
    if BASE.exists():raise FileExistsError('fresh joint namespace required')
    old=common.read_json(SOURCE/'profile.json');result=common.read_json(SOURCE/'actual/report.json')
    if result['status']!='TECHNICAL_COMPLETE_QUALITY_SEPARATE' or not result['registered_core_unchanged']:
        raise ValueError('closed original values and restored core required')
    data=common.read_json(SOURCE/'data.json');families=sorted({r['fact'] for r in data['rows'] if r['split']=='fit'})
    if len(families)!=12 or len(data['rows'])!=68 or len(data['calibration_questions'])!=128:
        raise ValueError('same12 families/68 questions/128 calibration prompts required')
    candidates=[];refs={}
    for fact in families:
        for layer in (2,5,8,11):
            path=SOURCE/'actual'/f'{fact}_layer{layer}_fit.json';record=common.read_json(path)
            if record['fact']!=fact or record['layer']!=layer or len(record['value_delta'])!=768:
                raise ValueError('complete frozen value record required')
            candidates.append(record);refs[str(path.relative_to(ROOT))]=manual.file_sha(path)
    layer,scores=joint.choose_common_layer(candidates,families=families)
    if layer!=8:raise ValueError('previously audited fit-only common layer changed')
    selected=[r for r in candidates if r['layer']==layer]
    manifest=common.read_json(SOURCE/'actual/answers_shards_manifest.json');verify_shards(SOURCE/'actual',manifest)
    for path in [SOURCE/'profile.json',SOURCE/'data.json',SOURCE/'actual/report.json',SOURCE/'actual/answers_shards_manifest.json',
                 *[SOURCE/'actual'/s['path'] for s in manifest['shards']]]:refs[str(path.relative_to(ROOT))]=manual.file_sha(path)
    sources=dict(manual.required_source_pins());sources.update({n:manual.file_sha(ROOT/n) for n in SOURCES})
    common.write_json(BASE/'data.json',data)
    (BASE/'initial_plan.txt').write_bytes((ROOT/'test_plan/P108_직접가중치-방향수리와-학습개입.md').read_bytes())
    profile=dict(schema='P108_JOINT_WRITE_V1',tag=TAG,authority_directive=115,deadline=DEADLINE.isoformat(),
        model=old['model'],sources=sources,references=refs,source_origin=result['origin'],layer=layer,
        common_layer_selection='LEXICOGRAPHIC_NEGATIVE_FIT_EXACT_FIT_NLL_LAYER; NO_DEV_OR_PUBLIC_SELECTION',
        fit_scores=scores,values={r['fact']:r['value_delta'] for r in selected},
        manifest_sha256=manual.canonical_sha(manual.verify_manifest()),data_sha256=manual.file_sha(BASE/'data.json'),
        plan_sha256=manual.file_sha(BASE/'initial_plan.txt'),primary_cap=.05,covariance_ridge_ratio=.01,
        random_seeds=[10007,10009,10037],single_weight_packet=True,
        base_optimizer_updates=0,value_optimizer_updates=0,new_supervised_target_exposures=0,
        checkpoint_writes=0,max_new=64,reused_public_questions_not_independent=True)
    common.write_json(BASE/'profile.json',profile)
    print('[JOINT_PREPARED] '+json.dumps(dict(tag=TAG,layer=layer,fit_scores=scores,model_load=False,gpu=False)),flush=True)


def verify():
    p=common.read_json(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=DEADLINE.isoformat() or not p['single_weight_packet']:
        raise ValueError('joint authority/single packet contract changed')
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/name)!=sha:raise ValueError('joint pinned source changed: '+name)
    for name,key in [('data.json','data_sha256'),('initial_plan.txt','plan_sha256')]:
        if manual.file_sha(BASE/name)!=p[key]:raise ValueError('joint frozen data/plan changed')
    if manual.canonical_sha(manual.verify_manifest())!=p['manifest_sha256']:raise ValueError('completed model inventory changed')
    return p


def calibration_inputs(active,module,questions,budget):
    parts=[]
    def hook(_module,args,_output):parts.append(args[0][0,-8:].detach().cpu().clone())
    handle=module.register_forward_hook(hook)
    try:
        with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            for question in questions:
                budget.check();ids=common.prompt_ids(active,question)
                active['model'](torch.tensor([ids],device='cuda'),logits_last_only=True)
    finally:handle.remove()
    if len(parts)!=128:raise ValueError('one original calibration forward per prompt required')
    return torch.cat(parts)


def raw_sources(rows,layer):
    manifest=common.read_json(SOURCE/'actual/answers_shards_manifest.json');verify_shards(SOURCE/'actual',manifest)
    original={};oracle={}
    for shard in manifest['shards']:
        for line in (SOURCE/'actual'/shard['path']).read_text().splitlines():
            r=json.loads(line)
            if r['variant']=='original':original[r['id']]=r
            elif r['split']=='fit' and r['variant']==r['fact']+f':layer{layer}:last_oracle_fit':oracle[r['id']]=r
    if set(original)!={r['id'] for r in rows} or set(oracle)!={r['id'] for r in rows if r['split']=='fit'}:
        raise ValueError('complete original68 and same-layer oracle fit24 raw required')
    for row in rows:
        if any(original[row['id']][key]!=row[key] for key in row):raise ValueError('reused source question/answer metadata changed')
    return original,oracle


def summaries(rows):
    return dict(all=metrics.summarize(rows),**{s:metrics.summarize([r for r in rows if r['split']==s]) for s in ('fit','dev','test','protect')})


def write_packet(path,packet,weight_sha,**metadata):
    common.write_json(path,dict(left=packet['left'].tolist(),right=packet['right'].tolist(),
        base_weight_sha256=weight_sha,delta_sha256=metrics.tensor_sha(packet['delta']),
        intended_factor_columns=packet['left'].shape[1],**metadata))


def run():
    p=verify();budget=Budget();budget.check();out=BASE/'actual'
    if out.exists():raise FileExistsError('joint actual already attempted')
    writer=ShardWriter(out,'answers',limit=3_000_000)
    report=dict(schema=p['schema'],tag=TAG,status='RUNNING',base_optimizer_updates=0,value_optimizer_updates=0,
        new_supervised_target_exposures=0,checkpoint_writes=0,single_weight_packet=True,
        reused_public_questions_not_independent=True,arms=[],generation_parities=0)
    active=active_model=modules=module=delta_gpu=packet=candidate=v=None;failure=None
    try:
        manual.require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        if not free.isdigit() or int(free)<4096:raise MemoryError('joint4096MiB free point required')
        report['entry_free_mib']=int(free)
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
            report['origin']={k:active[k] for k in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256')}
            if report['origin']!=p['source_origin']:raise ValueError('original completed float model changed')
            data=common.read_json(BASE/'data.json');rows=data['rows'];modules=wsp.outputs(active['model']);module=modules[f'mlp:{p["layer"]}']
            original,oracle=raw_sources(rows,p['layer'])
            for row in original.values():writer.append(dict(row,variant='original',reused_source=str(SOURCE.relative_to(ROOT))))
            for row in oracle.values():writer.append(dict(row,variant='common_layer_oracle',reused_source=str(SOURCE.relative_to(ROOT))))
            report['reused_rows']=len(original)+len(oracle);report['baseline']=summaries(list(original.values()))
            probe=next(r for r in rows if r['split']=='fit');_,live=manual.emit(active,probe['question'],max_new=64);report['generation_parities']+=1
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('joint initial original parity failed')
            prefills={}
            for row in rows:
                budget.check();prefills[row['id']]=transport.capture(active,module,dict(row,expected=row.get('expected')or'x'))
            fits=[r for r in rows if r['split']=='fit'];k=torch.stack([prefills[r['id']]['key'] for r in fits],dim=1)
            target=torch.stack([torch.tensor(p['values'][r['fact']],dtype=torch.float32) for r in fits],dim=1)
            sampled=calibration_inputs(active,module,data['calibration_questions'],budget)
            moment,report['covariance']=joint.covariance(sampled,ridge_ratio=p['covariance_ridge_ratio'])
            weight=module.weight.detach().cpu().clone();weight_sha=metrics.tensor_sha(weight)
            packet=joint.joint_packet(k,target,moment,weight,relative_cap=p['primary_cap'])
            report['joint_geometry']=packet['stats']
            realized=(weight+packet['delta'])-weight
            actual_relative=float(realized.double().norm())/float(weight.double().norm())
            if not 0<actual_relative<=p['primary_cap']:raise RuntimeError('realized joint weight change violates primary cap')
            report['realized_relative_norm']=actual_relative
            report['realized_fit_response_residuals']=((realized.double()@k.double()-target.double()).norm(dim=0)/target.double().norm(dim=0)).tolist()
            write_packet(out/'joint_packet.json',packet,weight_sha,stats=packet['stats'],realized_relative_norm=actual_relative)
            oracle_rows=list(oracle.values())
            first_fit=probe;v=torch.tensor(p['values'][first_fit['fact']],device='cuda')
            with prior.oracle(active,module,first_fit,v):_,live=manual.emit(active,first_fit['question'],max_new=64)
            report['generation_parities']+=1
            if live['generated_ids']!=oracle[first_fit['id']]['generation']['generated_ids']:raise RuntimeError('same common-layer frozen oracle parity failed')
            v=None
            for row in rows:
                if row['split']in ('fit','protect'):continue
                budget.check();v=torch.tensor(p['values'][row['fact']])
                _,result=transport.local_answer(active,module,row,v,writer,'common_layer_oracle');oracle_rows.append(result)
            report['common_layer_oracle']=summaries(oracle_rows);v=None
            local=[]
            for row in rows:
                budget.check();v=(realized.double()@prefills[row['id']]['key'].double()).float()
                _,result=transport.local_answer(active,module,row,v,writer,'joint_realized_local');local.append(result)
            report['joint_local']=summaries(local);v=None
            candidates=[dict(name='joint',**packet)]
            for seed in p['random_seeds']:
                control=joint.random_spectral_packet(packet,seed=seed)
                write_packet(out/f'random{seed}_packet.json',control,weight_sha,seed=seed,
                    intended_singular_values=control['intended_singular_values'],norm_match_error=control['relative_norm_match_error'])
                candidates.append(dict(name=f'random{seed}',**control))
            for candidate in candidates:
                budget.check();delta_gpu=candidate['delta'].to(module.weight);generated=[];after_hashes=set();maximum_response_error=0.
                expected_realized=(weight+candidate['delta'])-weight
                if float(expected_realized.double().norm())/float(weight.double().norm())>p['primary_cap']:
                    raise RuntimeError('random/current realized cap violation')
                with wsp.edit(active['model'],active['route'],[(f'mlp:{p["layer"]}',delta_gpu)]) as receipt:
                    after=metrics.tensor_sha(module.weight)
                    for row in rows:
                        budget.check();captured=transport.capture(active,module,dict(row,expected=row.get('expected')or'x'))
                        if not torch.equal(captured['key'],prefills[row['id']]['key']):raise RuntimeError('same-layer upstream prompt key changed')
                        actual=captured['output'].double()-prefills[row['id']]['output'].double()
                        predicted=expected_realized.double()@prefills[row['id']]['key'].double()
                        maximum_response_error=max(maximum_response_error,float((actual-predicted).abs().max()))
                        if not torch.allclose(actual,predicted,atol=1e-5,rtol=1e-4):raise RuntimeError('joint actual module response differs from registered linear edit')
                        result=prior.prior.generated(active,row,writer,candidate['name']+'_global')
                        transport.first_token_parity(captured['logits'],result);generated.append(result)
                        after_hashes.add(metrics.tensor_sha(module.weight))
                    if after_hashes!={after}:raise RuntimeError('weights changed across questions; not a single joint model')
                report['arms'].append(dict(name=candidate['name'],summary=summaries(generated),receipt=receipt,
                    one_after_weight_sha256=after,questions_per_unchanged_weight=len(generated),all_upstream_keys_exact=True,
                    max_linear_response_absolute_error=maximum_response_error))
                print('[JOINT_ARM] '+json.dumps(dict(name=candidate['name'],fit=report['arms'][-1]['summary']['fit']['exact'],
                    dev=report['arms'][-1]['summary']['dev']['exact'],wording=report['arms'][-1]['summary']['test']['exact'],
                    protect=report['arms'][-1]['summary']['protect']['exact'])),flush=True)
                delta_gpu=None
            _,live=manual.emit(active,probe['question'],max_new=64);report['generation_parities']+=1
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('joint final rollback token parity failed')
            report.update(final_rollback_token_parity=True,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
            active_model=active['model']
            if any(q.grad is not None for q in active_model.parameters()):raise RuntimeError('zero-optimizer experiment created master gradients')
            report['final_core_sha256']=manual.state_fingerprint(active_model)
            if report['final_core_sha256']!=p['source_origin']['core_sha256']:raise RuntimeError('joint final registered core changed')
            active_model=None;modules=module=delta_gpu=None
        active=None
        checkpoint=manual.resolve_model(p['model']).checkpoint
        report['original_checkpoint_unchanged']=manual.file_sha(ROOT/checkpoint)==p['source_origin']['checkpoint_sha256']
        if not report['original_checkpoint_unchanged']:raise RuntimeError('original joint checkpoint file changed')
        report.update(status='JOINT_TECHNICAL_COMPLETE_QUALITY_SEPARATE',registered_core_unchanged=True)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        active=active_model=modules=module=delta_gpu=candidate=packet=v=None;gc.collect()
        try:close_owned_cuda(torch,report)
        except BaseException as exc:
            report.update(status='ERROR',cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();report['sources_assets_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        manifest=writer.close(lineage=dict(tag=TAG,profile_sha256=manual.file_sha(BASE/'profile.json')));verify_shards(out,manifest)
        report.update(seconds=time.monotonic()-budget.start,answer_rows=manifest['rows'],new_raw_rows=manifest['rows']-report.get('reused_rows',0))
        common.write_json(out/'report.json',report)
    if failure is not None:raise failure
    print('[JOINT_FINAL] '+json.dumps({k:report[k] for k in ('status','seconds','answer_rows','new_raw_rows')}),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','actual']);a=p.parse_args()
    (prepare if a.phase=='prepare' else run)()


if __name__=='__main__':main()
