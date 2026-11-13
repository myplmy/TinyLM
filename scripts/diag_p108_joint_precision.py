"""Replay frozen joint packets in native FP32; retain the old mixed gate."""
import argparse
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
import torch
from scripts import diag_p108_joint_write as old
from scripts import p108_joint_precision as precision
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import diag_p108_weight_space as common
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter, verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT=old.ROOT;SOURCE=old.BASE;TAG='p108_joint_precision_v1_20261113'
BASE=ROOT/'test_result/evidence'/TAG
SOURCES=('scripts/p108_joint_precision.py','scripts/test_p108_joint_precision.py',
         'scripts/diag_p108_joint_precision.py')


def load_reuse():
    result=common.read_json(SOURCE/'actual/report.json')
    if result['status']!='ERROR' or result.get('answer_rows')!=189 or result.get('arms')!=[]:
        raise ValueError('preserved original technical failure189, not a completed arm, required')
    manifest=common.read_json(SOURCE/'actual/answers_shards_manifest.json')
    verify_shards(SOURCE/'actual',manifest)
    rows=[];partial=[]
    for shard in manifest['shards']:
        for line in (SOURCE/'actual'/shard['path']).read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            (partial if row['variant']=='joint_global' else rows).append(row)
    counts={name:sum(r['variant']==name for r in rows) for name in ('original','common_layer_oracle','joint_realized_local')}
    if counts!={'original':68,'common_layer_oracle':52,'joint_realized_local':68} or len(partial)!=1 or len(rows)!=188:
        raise ValueError('only complete188 reused; original partial global retained separately')
    return result,manifest,rows,partial[0]


def prepare():
    old.Budget().check();p=old.verify()
    if BASE.exists():raise FileExistsError('fresh precision namespace required')
    result,manifest,reused,partial=load_reuse()
    cleanup=result['final_cuda_cleanup']
    if cleanup['allocated_bytes'] or cleanup['reserved_bytes'] or not result['sources_assets_unchanged']:
        raise ValueError('closed original failure cleanup required')
    witness=common.read_json(SOURCE/'ROOT_FAILED_EXIT_v1.json')
    if witness['actual_tool_exit']!=1 or witness['report_sha256']!=manual.file_sha(SOURCE/'actual/report.json'):
        raise ValueError('actual original error exit witness required')
    paths=[SOURCE/'profile.json',SOURCE/'data.json',SOURCE/'actual/report.json',SOURCE/'ROOT_FAILED_EXIT_v1.json',
           SOURCE/'actual/answers_shards_manifest.json']
    paths.extend(SOURCE/'actual'/s['path'] for s in manifest['shards'])
    paths.extend(SOURCE/'actual'/f'{name}_packet.json' for name in ('joint','random10007','random10009','random10037'))
    sources=dict(p['sources']);sources.update({s:manual.file_sha(ROOT/s) for s in SOURCES})
    common.write_json(BASE/'data.json',common.read_json(SOURCE/'data.json'))
    (BASE/'initial_plan.txt').write_bytes((ROOT/'test_plan/P108_직접가중치-방향수리와-학습개입.md').read_bytes())
    common.write_json(BASE/'profile.json',dict(schema='P108_JOINT_PRECISION_V1',tag=TAG,
        authority_directive=115,deadline=old.DEADLINE.isoformat(),model=p['model'],origin=p['source_origin'],layer=p['layer'],
        primary_cap=p['primary_cap'],packet_names=['joint','random10007','random10009','random10037'],
        reused_rows=188,partial_reference_only=partial['id'],source_report_sha256=manual.file_sha(SOURCE/'actual/report.json'),
        sources=sources,references={str(path.relative_to(ROOT)):manual.file_sha(path) for path in paths},
        data_sha256=manual.file_sha(BASE/'data.json'),plan_sha256=manual.file_sha(BASE/'initial_plan.txt'),
        base_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,
        old_difference_atol=1e-5,old_difference_rtol=1e-4,native_replay='EXACT',double_linearity_atol=1e-10,
        reused_public_questions_not_independent=True))
    print('[PRECISION_PREPARED] '+json.dumps(dict(tag=TAG,reused=len(reused),model_load=False,gpu=False)),flush=True)


def verify():
    old.verify();p=common.read_json(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=old.DEADLINE.isoformat():raise ValueError('authority changed')
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/name)!=sha:raise ValueError('sealed precision source/reference changed: '+name)
    for name,key in [('data.json','data_sha256'),('initial_plan.txt','plan_sha256')]:
        if manual.file_sha(BASE/name)!=p[key]:raise ValueError('frozen precision input changed')
    return p


def capture_full(active,module,row):
    retained=[]
    def hook(_module,args,output):
        if len(retained) or getattr(module,'bias',None) is not None:raise RuntimeError('one bias-free native module visit required')
        if not args[0].is_contiguous():raise ValueError('native contiguous input required; no reshaping before replay')
        retained.append(dict(inputs=args[0].detach().cpu().clone(),outputs=output.detach().cpu().clone()))
    handle=module.register_forward_hook(hook)
    try:captured=old.transport.capture(active,module,dict(row,expected=row.get('expected')or'x'))
    finally:handle.remove()
    if len(retained)!=1:raise RuntimeError('full native prefill not captured')
    return dict(captured,**retained[0])


def run():
    p=verify();budget=old.Budget();budget.check();out=BASE/'actual'
    if out.exists():raise FileExistsError('precision actual already attempted')
    writer=ShardWriter(out,'answers',limit=3_000_000)
    report=dict(tag=TAG,schema=p['schema'],status='RUNNING',arms=[],operator_evidence=[],
        base_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,
        reused_public_questions_not_independent=True,generation_parities=0)
    active=modules=module=delta=before_gpu=after_gpu=inputs_gpu=outputs_gpu=before_outputs_gpu=None
    failure=None
    try:
        manual.require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
            capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        if not free.isdigit() or int(free)<4096:raise MemoryError('precision4096MiB free point required')
        report['entry_free_mib']=int(free)
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
            origin={k:active[k] for k in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256')}
            if origin!=p['origin']:raise ValueError('original completed model changed')
            report['origin']=origin
            source_result,_manifest,reused,old_partial=load_reuse();rows=common.read_json(BASE/'data.json')['rows']
            for row in reused:writer.append(dict(row,reused_source=str(SOURCE.relative_to(ROOT))))
            report.update(reused_rows=len(reused),baseline=source_result['baseline'],
                common_layer_oracle=source_result['common_layer_oracle'],joint_ideal_local=source_result['joint_local'])
            original={r['id']:r for r in reused if r['variant']=='original'};probe=rows[0]
            _,live=manual.emit(active,probe['question'],max_new=64);report['generation_parities']+=1
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('original live parity failed')
            modules=wsp.outputs(active['model']);module=modules[f'mlp:{p["layer"]}']
            weight=module.weight.detach().cpu().clone();before_gpu=module.weight.detach().clone()
            prefills={}
            for row in rows:
                budget.check();prefills[row['id']]=capture_full(active,module,row)
            joint_targets={}
            for name in p['packet_names']:
                record=common.read_json(SOURCE/'actual'/f'{name}_packet.json')
                materialized=precision.packet_from_record(record,weight);expected=weight+materialized
                realized_norm=float((expected.double()-weight.double()).norm())/float(weight.double().norm())
                if not 0<realized_norm<=p['primary_cap']:raise ValueError('registered realized5percent cap exceeded')
                delta=materialized.to(module.weight);generated=[];hashes=set()
                with wsp.edit(active['model'],active['route'],[(f'mlp:{p["layer"]}',delta)])as receipt:
                    if not torch.equal(module.weight.detach().cpu(),expected):raise RuntimeError('actual weight is not frozen FP32 packet realization')
                    after_hash=metrics.tensor_sha(module.weight);after_gpu=module.weight.detach().clone()
                    for row in rows:
                        budget.check();before=prefills[row['id']];after=capture_full(active,module,row)
                        if not torch.equal(before['inputs'],after['inputs']):raise RuntimeError('full upstream native inputs changed')
                        inputs_gpu=after['inputs'].to(module.weight);outputs_gpu=after['outputs'].to(module.weight)
                        before_outputs_gpu=before['outputs'].to(module.weight)
                        evidence=precision.operator_evidence(inputs_gpu,before_outputs_gpu,outputs_gpu,before_gpu,after_gpu)
                        report['operator_evidence'].append(dict(arm=name,id=row['id'],**evidence))
                        precision.require_operator(evidence)
                        result=old.prior.prior.generated(active,row,writer,name+'_global')
                        old.transport.first_token_parity(after['logits'],result);generated.append(result)
                        if name=='joint':
                            joint_targets[row['id']]=after['output']
                            if row['id']==old_partial['id']:
                                report['old_partial_token_parity']=result['generation']['generated_ids']==old_partial['generation']['generated_ids']
                                if not report['old_partial_token_parity']:raise RuntimeError('old partial actual token parity changed')
                        hashes.add(metrics.tensor_sha(module.weight))
                        inputs_gpu=outputs_gpu=before_outputs_gpu=None
                    if hashes!={after_hash}:raise RuntimeError('single model weight changed across questions')
                report['arms'].append(dict(name=name,summary=old.summaries(generated),receipt=receipt,
                    after_weight_sha256=after_hash,questions_per_unchanged_weight=len(generated),realized_relative_norm=realized_norm))
                print('[PRECISION_ARM] '+json.dumps(dict(name=name,summary=report['arms'][-1]['summary'])),flush=True)
                delta=after_gpu=None
            local=[]
            for row in rows:
                budget.check();target=joint_targets[row['id']]
                with precision.replace_once(module,target):observed=old.transport.capture(active,module,dict(row,expected=row.get('expected')or'x'))
                if not torch.equal(observed['output'],target):raise RuntimeError('native output replacement was not exact')
                with precision.replace_once(module,target):result=old.prior.prior.generated(active,row,writer,'joint_native_fp32_local')
                old.transport.first_token_parity(observed['logits'],result);local.append(result)
            report['joint_native_local']=old.summaries(local)
            _,live=manual.emit(active,probe['question'],max_new=64);report['generation_parities']+=1
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('final rollback token parity failed')
            report.update(final_rollback_token_parity=True,final_core_sha256=manual.state_fingerprint(active['model']),
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
            if report['final_core_sha256']!=p['origin']['core_sha256']:raise RuntimeError('original core not restored')
            if any(q.grad is not None for q in active['model'].parameters()):raise RuntimeError('unexpected master gradients')
            module=modules=before_gpu=after_gpu=delta=None
        active=None
        report['original_checkpoint_unchanged']=manual.file_sha(ROOT/manual.resolve_model(p['model']).checkpoint)==p['origin']['checkpoint_sha256']
        if not report['original_checkpoint_unchanged']:raise RuntimeError('original checkpoint changed')
        report.update(status='JOINT_NATIVE_PRECISION_COMPLETE_QUALITY_SEPARATE',registered_core_unchanged=True)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        active=modules=module=delta=before_gpu=after_gpu=inputs_gpu=outputs_gpu=before_outputs_gpu=None;gc.collect()
        try:close_owned_cuda(torch,report)
        except BaseException as exc:report.update(status='ERROR',cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();report['sources_assets_unchanged']=True
        except BaseException as exc:report.update(status='ERROR',source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        manifest=writer.close(lineage=dict(tag=TAG,profile_sha256=manual.file_sha(BASE/'profile.json')));verify_shards(out,manifest)
        report.update(seconds=time.monotonic()-budget.start,answer_rows=manifest['rows'],new_raw_rows=manifest['rows']-report.get('reused_rows',0))
        common.write_json(out/'report.json',report)
    if failure is not None:raise failure
    print('[PRECISION_FINAL] '+json.dumps({k:report[k]for k in ('status','seconds','answer_rows','new_raw_rows')}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);args=parser.parse_args()
    (prepare if args.phase=='prepare'else run)()


if __name__=='__main__':main()
