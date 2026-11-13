"""Two-layer conditional residual allocation versus the same-budget final-layer edit."""
import argparse
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
import torch
from torch.nn import functional as F
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import diag_p108_joint_write as old
from scripts import p108_distributed_residual as distributed
from scripts import p108_joint_write as joint
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import diag_p108_weight_space as common
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import ShardWriter,verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT=old.ROOT;TAG='p108_distributed_residual_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
PRECISION=ROOT/'test_result/evidence/p108_joint_precision_v1_20261113'
SOURCES=('scripts/p108_distributed_residual.py','scripts/test_p108_distributed_residual.py','scripts/diag_p108_distributed_residual.py')
LAYERS=(8,11)


def prepare():
    old.Budget().check();p=old.verify()
    if BASE.exists():raise FileExistsError('fresh distributed residual namespace required')
    closure=common.read_json(PRECISION/'ROOT_ACTUAL_EXIT_v1.json')
    if closure['actual_tool_exit']!=0 or closure['report_sha256']!=manual.file_sha(PRECISION/'actual/report.json'):
        raise ValueError('actual native single-layer closure required')
    data=common.read_json(old.BASE/'data.json');original,oracle=old.raw_sources(data['rows'],11)
    if len(original)!=68 or len(oracle)!=24 or sum(bool(r['exact'])for r in oracle.values())!=18:
        raise ValueError('unchanged original68 and fit-only layer11 oracle18/24 required')
    values={};refs=dict(p['references'])
    for fact in sorted({r['fact']for r in data['rows']if r['split']=='fit'}):
        path=old.SOURCE/'actual'/f'{fact}_layer11_fit.json';record=common.read_json(path)
        if record['fact']!=fact or record['layer']!=11 or len(record['value_delta'])!=768:raise ValueError('frozen original layer11 value required')
        values[fact]=record['value_delta'];refs[str(path.relative_to(ROOT))]=manual.file_sha(path)
    refs[str((PRECISION/'ROOT_ACTUAL_EXIT_v1.json').relative_to(ROOT))]=manual.file_sha(PRECISION/'ROOT_ACTUAL_EXIT_v1.json')
    refs[str((PRECISION/'actual/report.json').relative_to(ROOT))]=manual.file_sha(PRECISION/'actual/report.json')
    sources=dict(p['sources']);sources.update({name:manual.file_sha(ROOT/name)for name in SOURCES})
    common.write_json(BASE/'data.json',data)
    (BASE/'initial_plan.txt').write_bytes((ROOT/'test_plan/P108_직접가중치-방향수리와-학습개입.md').read_bytes())
    common.write_json(BASE/'profile.json',dict(tag=TAG,authority_directive=115,deadline=old.DEADLINE.isoformat(),
        model=p['model'],origin=p['source_origin'],sources=sources,references=refs,layers=list(LAYERS),final_layer=11,
        values11=values,data_sha256=manual.file_sha(BASE/'data.json'),plan_sha256=manual.file_sha(BASE/'initial_plan.txt'),
        relative_cap=.05,budget_reference='MINIMUM_ORIGINAL_WEIGHT_NORM; SAME_ABSOLUTE_CAP_FOR_BOTH_ARMS',
        moment_ridge_ratio=.01,random_seeds=[10007,10009,10037],random_layer_seed_rule='BASE_SEED_PLUS_LAYER_INDEX',
        original_rows=68,reused_fit_oracle_rows=24,new_global_arms=5,new_raw_answers=340,
        base_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,reused_public_not_independent=True))
    print('[DISTRIBUTED_PREPARED] '+json.dumps(dict(tag=TAG,layers=list(LAYERS),oracle11_fit=18,model_load=False,gpu=False)),flush=True)


def verify():
    old.verify();p=common.read_json(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=old.DEADLINE.isoformat():raise ValueError('distributed authority changed')
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(ROOT/name)!=sha:raise ValueError('sealed distributed source/reference changed: '+name)
    for name,key in [('data.json','data_sha256'),('initial_plan.txt','plan_sha256')]:
        if manual.file_sha(BASE/name)!=p[key]:raise ValueError('distributed frozen input changed')
    return p


def capture(active,modules,row,*,verify_native=True):
    saved={'keys':{},'native_replays':0};handles=[]
    def projection_hook(index):
        def hook(module,args,output):
            if index in saved['keys']or output.ndim!=3 or output.shape[0]!=1:raise RuntimeError('one native projection visit required')
            if verify_native:
                if args[0].dtype!=torch.float32 or output.dtype!=torch.float32 or getattr(module,'bias',None)is not None:
                    raise ValueError('bias-free original FP32 projection required')
                with torch.no_grad(),torch.autocast('cuda',enabled=False):replay=F.linear(args[0],module.weight)
                if not torch.equal(replay,output):raise RuntimeError('actual registered native projection differs from same-shape FP32 replay')
                saved['native_replays']+=1
            saved['keys'][index]=args[0][0,-1].detach().cpu().clone()
        return hook
    def final_hook(_module,_args,output):
        if 'z'in saved or not isinstance(output,torch.Tensor)or output.ndim!=3 or output.shape[0]!=1:
            raise RuntimeError('one whole final residual block output required')
        saved['z']=output[0,-1].detach().cpu().clone()
    try:
        for index in LAYERS:handles.append(modules[index].register_forward_hook(projection_hook(index)))
        handles.append(active['model'].layers[11].register_forward_hook(final_hook))
        result=old.transport.capture(active,modules[11],dict(row,expected=row.get('expected')or'x'))
        if set(saved['keys'])!=set(LAYERS)or 'z'not in saved or not torch.equal(saved['keys'][11],result['key']):
            raise RuntimeError('actual final prompt position or layer coverage changed')
        return dict(saved,logits=result['logits'])
    finally:
        for handle in reversed(handles):handle.remove()


def moments(active,modules,questions,budget):
    parts={i:[]for i in LAYERS};handles=[]
    def hook(index):
        def retain(_module,args,_output):parts[index].append(args[0][0,-8:].detach().cpu().clone())
        return retain
    try:
        for index in LAYERS:handles.append(modules[index].register_forward_hook(hook(index)))
        with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            for question in questions:
                budget.check();ids=common.prompt_ids(active,question)
                active['model'](torch.tensor([ids],device='cuda'),logits_last_only=True)
    finally:
        for handle in reversed(handles):handle.remove()
    if any(len(v)!=128 for v in parts.values()):raise ValueError('same128 original calibration prompts required')
    result={};stats={}
    for index in LAYERS:result[index],stats[str(index)]=joint.covariance(torch.cat(parts[index]),ridge_ratio=.01)
    return result,stats


def run():
    p=verify();budget=old.Budget();budget.check();out=BASE/'actual'
    if out.exists():raise FileExistsError('distributed actual already attempted')
    writer=ShardWriter(out,'answers',limit=3_000_000)
    report=dict(tag=TAG,status='RUNNING',arms=[],base_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,
        reused_public_not_independent=True,generation_parities=0,native_projection_replays=0)
    active=modules=edits=delta_gpu=v=None;failure=None
    try:
        manual.require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        if not free.isdigit()or int(free)<4096:raise MemoryError('distributed4096MiB free point required')
        report['entry_free_mib']=int(free)
        with manual.selected_runtime(manual.resolve_model(p['model']))as active:
            torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
            origin={k:active[k]for k in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256')}
            if origin!=p['origin']:raise ValueError('original completed float model changed')
            report['origin']=origin;all_modules=wsp.outputs(active['model']);modules={i:all_modules[f'mlp:{i}']for i in LAYERS};all_modules=None
            for i in LAYERS:
                layer=active['model'].layers[i]
                if layer.has_lora or layer.has_film or layer.has_lrm or getattr(modules[i],'use_mode',False):raise ValueError('original plain gated MLP path required')
            layer=None;gates={i:float(active['model'].layers[i].gates[1].detach())for i in LAYERS}
            weights={i:modules[i].weight.detach().cpu().clone()for i in LAYERS};cap=distributed.shared_budget([weights[i]for i in LAYERS]);report.update(gates={str(k):v for k,v in gates.items()},budget=cap)
            data=common.read_json(BASE/'data.json');rows=data['rows'];fits=[r for r in rows if r['split']=='fit'];original,oracle=old.raw_sources(rows,11)
            for row in original.values():writer.append(dict(row,variant='original',reused_source=str(old.SOURCE.relative_to(ROOT))))
            for row in oracle.values():writer.append(dict(row,variant='oracle11_fit',reused_source=str(old.SOURCE.relative_to(ROOT))))
            report.update(reused_rows=92,baseline=old.summaries(list(original.values())),oracle11_fit_exact=sum(bool(r['exact'])for r in oracle.values()))
            probe=fits[0];_,live=manual.emit(active,probe['question'],max_new=64);report['generation_parities']+=1
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('original token parity failed')
            before={};targets=[]
            for row in rows:
                budget.check();before[row['id']]=capture(active,modules,row);report['native_projection_replays']+=before[row['id']]['native_replays']
            for row in fits:
                budget.check();v=torch.tensor(p['values11'][row['fact']],device='cuda')
                with old.prior.oracle(active,modules[11],row,v):targets.append(capture(active,modules,row,verify_native=False)['z'])
            v=None;target=torch.stack(targets,dim=1);current=torch.stack([before[r['id']]['z']for r in fits],dim=1)
            v=torch.tensor(p['values11'][probe['fact']],device='cuda')
            with old.prior.oracle(active,modules[11],probe,v):_,live=manual.emit(active,probe['question'],max_new=64)
            report['generation_parities']+=1;v=None
            if live['generated_ids']!=oracle[probe['id']]['generation']['generated_ids']:raise RuntimeError('frozen layer11 oracle token parity failed')
            covariance,report['covariance']=moments(active,modules,data['calibration_questions'],budget)
            keys=lambda observed,index:torch.stack([observed[r['id']]['keys'][index]for r in fits],dim=1)
            single=distributed.packet(keys(before,11),target,current,covariance[11],weights[11],remaining=1,gate=gates[11],absolute_cap=cap['single_layer_cap'])
            first=distributed.packet(keys(before,8),target,current,covariance[8],weights[8],remaining=2,gate=gates[8],absolute_cap=cap['distributed_each_cap'])
            delta_gpu=first['delta'].to(modules[8].weight)
            with wsp.edit(active['model'],active['route'],[('mlp:8',delta_gpu)]):
                conditioned={}
                for row in fits:
                    budget.check();conditioned[row['id']]=capture(active,modules,row);report['native_projection_replays']+=conditioned[row['id']]['native_replays']
                middle=torch.stack([conditioned[r['id']]['z']for r in fits],dim=1)
                second=distributed.packet(keys(conditioned,11),target,middle,covariance[11],weights[11],remaining=1,gate=gates[11],absolute_cap=cap['distributed_each_cap'])
                report['after_first_layer_final_block_residual']=float((target.double()-middle.double()).norm())
            delta_gpu=None
            candidates=[('single11',{11:single}),('distributed8_11',{8:first,11:second})]
            for seed in p['random_seeds']:candidates.append((f'random{seed}',{i:joint.random_spectral_packet(packet,seed=seed+i)for i,packet in [(8,first),(11,second)]}))
            packet_files=[]
            for name,packets in candidates:
                indices=sorted(packets);norm=distributed.realized_total([weights[i]for i in indices],[packets[i]['delta']for i in indices],absolute_cap=cap['absolute_total_cap'])
                for index in indices:
                    path=out/f'{name}_layer{index}_packet.json';packet=packets[index]
                    old.write_packet(path,packet,metrics.tensor_sha(weights[index]),layer=index,norm_budget=norm,
                        signed_gate=gates[index],stats=packet.get('stats'),absolute_cap=cap['absolute_total_cap'])
                    packet_files.append(dict(path=path.name,sha256=manual.file_sha(path)))
            common.write_json(out/'packet_manifest.json',dict(packets=packet_files,frozen_before_dev_public_protect_generations=True,
                target_sha256=metrics.tensor_sha(target),fit_ids=[r['id']for r in fits],target_source='OBSERVED_WHOLE_BLOCK11_UNDER_FROZEN_ORACLE11'))
            for name,packets in candidates:
                budget.check();indices=sorted(packets);edits=[(f'mlp:{i}',packets[i]['delta'].to(modules[i].weight))for i in indices]
                generated=[];after_hashes=set();final_outputs=[]
                with wsp.edit(active['model'],active['route'],edits)as receipt:
                    expected={i:metrics.tensor_sha(weights[i]+packets[i]['delta'])for i in indices}
                    if any(metrics.tensor_sha(modules[i].weight)!=expected[i]for i in indices):raise RuntimeError('actual registered FP32 packet realization differs')
                    for row in rows:
                        budget.check();observed=capture(active,modules,row);report['native_projection_replays']+=observed['native_replays']
                        answer=old.prior.prior.generated(active,row,writer,name);old.transport.first_token_parity(observed['logits'],answer);generated.append(answer)
                        if row['split']=='fit':final_outputs.append(observed['z'])
                        after_hashes.add(tuple(metrics.tensor_sha(modules[i].weight)for i in indices))
                    if after_hashes!={tuple(expected[i]for i in indices)}:raise RuntimeError('weights changed between questions')
                norm=distributed.realized_total([weights[i]for i in indices],[packets[i]['delta']for i in indices],absolute_cap=cap['absolute_total_cap'])
                report['arms'].append(dict(name=name,summary=old.summaries(generated),receipt=receipt,norm_budget=norm,
                    after_weight_sha256={str(i):expected[i]for i in indices},questions_per_unchanged_weight=68,
                    fit_final_block_residual=float((target.double()-torch.stack(final_outputs,dim=1).double()).norm())))
                print('[DISTRIBUTED_ARM] '+json.dumps(dict(name=name,summary=report['arms'][-1]['summary'])),flush=True);edits=None
            _,live=manual.emit(active,probe['question'],max_new=64);report['generation_parities']+=1
            if live['generated_ids']!=original[probe['id']]['generation']['generated_ids']:raise RuntimeError('final rollback token parity failed')
            report.update(final_rollback_token_parity=True,final_core_sha256=manual.state_fingerprint(active['model']),
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
            if report['final_core_sha256']!=p['origin']['core_sha256']:raise RuntimeError('original registered core changed')
            if any(param.grad is not None for param in active['model'].parameters()):raise RuntimeError('unexpected master gradient')
            modules=edits=None
        active=None
        report['original_checkpoint_unchanged']=manual.file_sha(ROOT/manual.resolve_model(p['model']).checkpoint)==p['origin']['checkpoint_sha256']
        if not report['original_checkpoint_unchanged']:raise RuntimeError('original checkpoint file changed')
        base=report['baseline'];candidate=report['arms'][1]['summary'];random_max=max(sum(a['summary'][s]['exact']for s in ('fit','dev','test'))for a in report['arms'][2:])
        report['pilot_next_stage_gate']=all(candidate[s]['exact']>base[s]['exact']for s in ('fit','dev','test'))and candidate['protect']['exact']>=base['protect']['exact']and candidate['all']['loop_indicators']<=base['all']['loop_indicators']and candidate['all']['question_echoes']<=base['all']['question_echoes']and sum(candidate[s]['exact']for s in ('fit','dev','test'))>random_max
        report.update(status='DISTRIBUTED_TECHNICAL_COMPLETE_QUALITY_SEPARATE',registered_core_unchanged=True)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        active=modules=edits=delta_gpu=v=None;gc.collect()
        try:close_owned_cuda(torch,report)
        except BaseException as exc:report.update(status='ERROR',cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();report['sources_assets_unchanged']=True
        except BaseException as exc:report.update(status='ERROR',source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:
            manifest=writer.close(lineage=dict(tag=TAG,profile_sha256=manual.file_sha(BASE/'profile.json')));verify_shards(out,manifest)
            report.update(answer_rows=manifest['rows'],new_raw_rows=manifest['rows']-report.get('reused_rows',0))
        except BaseException as exc:report.update(status='ERROR',finalizer_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report['seconds']=time.monotonic()-budget.start;common.write_json(out/'report.json',report)
    if failure is not None:raise failure
    print('[DISTRIBUTED_FINAL] '+json.dumps({k:report[k]for k in ('status','seconds','answer_rows','new_raw_rows','pilot_next_stage_gate')}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);args=parser.parse_args()
    (prepare if args.phase=='prepare'else run)()


if __name__=='__main__':main()
