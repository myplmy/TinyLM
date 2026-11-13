"""Native full-vocabulary DSKDv2 wiring and zero-update engineering measurements."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import json
import os
import resource
import subprocess
import time
import traceback
import numpy as np
from scripts import diag_p106b_dskdv2_hidden_recovery as recovered
from scripts import p106b_dskdv2_bridge as bridge

first=recovered.first;data=first.data;exact=first.exact;heads=first.heads;ROOT=first.ROOT
TAG='p106b_dskdv2_bridge_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
SOURCES=('scripts/p106b_dskdv2_bridge.py','scripts/test_p106b_dskdv2_bridge.py','scripts/diag_p106b_dskdv2_bridge.py')


def inputs():
    recovered.verify();p=recovered.first.exact.read(recovered.BASE/'actual/report.json')
    witness=exact.read(recovered.BASE/'ROOT_ACTUAL_EXIT_v1.json')
    if p.get('returncode')!=0 or witness.get('actual_tool_exit')!=0 and witness.get('actual_process_exit_code')!=0:
        raise ValueError('actual recovered native feature proof required')
    if not p.get('sources_features_and_assets_unchanged'):raise ValueError('unchanged recovered native128 required')
    return recovered.closed_cache()


def selected(rows,cached):
    result=[]
    for row in rows:
        positions=[p for p in cached[row['row_id']]['positions']if p['accepted']]
        if positions:
            h=np.load(first.FEATURES/(row['row_id']+'.npy'),allow_pickle=False)
            result.append((row,positions,h))
    if sum(len(p)for _,p,_ in result)!=538:raise ValueError('original native accepted538 required')
    return result


def full_head(torch):
    p=exact.read(heads.BASE/'profile.json');from safetensors import safe_open
    path=p['teacher_assets']['files'][data.qualified.q.WEIGHT]['resolved_path']
    with safe_open(path,framework='pt',device='cpu')as f:w=f.get_tensor(p['teacher_key']).float()
    if w.shape!=(248320,1024)or not bool(torch.isfinite(w).all()):raise ValueError('original native full teacher head required')
    return w


def bank(torch,model,w):
    ids=exact.read(heads.BASE/'overlap_ids.json');tick=time.perf_counter()
    out=bridge.initialize_native_bank(model,w,ids['student_ids'],ids['teacher_ids'])
    out['seconds']=time.perf_counter()-tick
    old=exact.read(heads.BASE/'report.json')['initialization']
    for k in ['t2s_relative_logit_error','s2t_relative_logit_error']:
        if abs(old[k]-out['stats'][k])>1e-10:raise ValueError('same original native bank initialization changed')
    return out


def verify():
    data.guard();p=exact.read(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=data.DEADLINE.isoformat():raise ValueError('native bridge authority changed')
    for name,sha in p['sources'].items():
        if exact.digest(ROOT/name)!=sha:raise ValueError('sealed bridge source changed: '+name)
    return p


def cpu_native():
    data.guard();start=time.perf_counter()
    if BASE.exists():raise FileExistsError('fresh native bridge namespace required')
    _old,p,rows,cached,_features,_accepted,_modes=inputs()
    paths=[ROOT/s for s in SOURCES]+[recovered.BASE/'profile.json',recovered.BASE/'actual/report.json',
        recovered.BASE/'ROOT_ACTUAL_EXIT_v1.json',heads.BASE/'profile.json',heads.BASE/'report.json',heads.BASE/'overlap_ids.json']
    exact.write(BASE/'profile.json',dict(tag=TAG,authority_directive=115,deadline=data.DEADLINE.isoformat(),
        sources={str(x.relative_to(ROOT)):exact.digest(x)for x in paths},rows=128,ce_targets=772,kd_positions=538,
        micro=8,accum=16,width=1024,student_vocab=32768,teacher_vocab=248320,teacher_models=0,
        cpu_tests=6,temperature=1.,coefficient=1.,optimizer_updates=0,checkpoint_writes=0,quality_claim=False))
    from scripts import diag_p106b_gsq_objective as loader
    from scripts import interactive_research_infer as manual
    import torch
    torch.set_num_threads(4);model=w=init=up=emb=None;report=dict(tag=TAG,status='RUNNING',returncode=9,
        profile_sha256=exact.digest(BASE/'profile.json'),teacher_models=0,student_body_forwards=0,gpu_calls=0,quality_claim=False)
    failure=None
    try:
        torch,model,_manifest,entry,_spec=loader.load_cpu();model.eval();w=full_head(torch);init=bank(torch,model,w)
        report['initialization']=init['stats'];report['initialization_seconds']=init['seconds'];report['teacher_head_bytes']=w.numel()*w.element_size()
        up=model._emb_up_w().detach();emb=model._emb_w().detach();counts=Counter();agreements=Counter();primal=vjp=True
        with torch.no_grad():
            for row,positions,h in selected(rows,cached):
                data.guard(start,900);indices=[q['teacher_predictor_raw_index']for q in positions]
                projected=torch.from_numpy(h[indices].copy())@init['t2s']
                a=bridge.factored_logits(projected,up,emb);b=model._head_logits(projected)
                primal=primal and torch.equal(a,b);pred=a.argmax(-1).tolist()
                for pos,value in zip(positions,pred):
                    key=row['language']+'_mode'+str(pos['mapping_mode']);counts[key]+=1;agreements[key]+=value==pos['mapped_student_argmax']
        row,positions,h=selected(rows,cached)[0];probe=torch.from_numpy(h[[positions[0]['teacher_predictor_raw_index']]].copy())@init['t2s'];probe.requires_grad_(True)
        a=bridge.factored_logits(probe,up,emb);b=model._head_logits(probe)
        cotangent=torch.linspace(-1,1,32768).unsqueeze(0)/32768
        ga=torch.autograd.grad((a*cotangent).sum(),probe)[0];gb=torch.autograd.grad((b*cotangent).sum(),probe)[0]
        vjp=torch.equal(ga,gb)
        if not primal or not vjp:raise ValueError('actual projected-feature native head/VJP differs')
        report.update(projection_counts=dict(counts),projection_agreement=dict(agreements),native_primal_exact=primal,native_hidden_vjp_exact=vjp,
            initial_projection_is_quality_metric=False,student_core_unchanged=manual.state_fingerprint(model)==entry['core_sha256'])
        if not report['student_core_unchanged']or torch.cuda.is_initialized():raise ValueError('CPU bridge changed model or initialized CUDA')
        report.update(status='NATIVE_PROJECTED_TEACHER_SIGNAL_CPU_COMPLETE',returncode=0,cuda_initialized=False)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        model=w=init=up=emb=None;gc.collect();verify()
        report.update(seconds=time.perf_counter()-start,peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        exact.write(BASE/'cpu/report.json',report)
    if failure:raise failure
    print('[DSKDV2_NATIVE_CPU] '+json.dumps({k:report[k]for k in ['status','seconds','projection_counts','projection_agreement']}),flush=True)


def require_closed(phase):
    r=exact.read(BASE/phase/'report.json');w=exact.read(BASE/('ROOT_'+phase.upper()+'_EXIT_v1.json'))
    if r.get('returncode')!=0 or w.get('actual_tool_exit')!=0 or w.get('report_sha256')!=exact.digest(BASE/phase/'report.json'):
        raise ValueError('closed actual native '+phase+' proof required')
    return r


def head_gate(torch,rows,cached,report,start):
    from scripts import p106b_qwen35_fixedshape as fixed
    from torch.nn import functional as F
    w=full_head(torch).cuda();checks=[];chunk_good=fixed_good=True
    canaries=exact.read(first.BASE/'profile.json')['canaries']
    with torch.no_grad():
        for row in rows:
            if row['row_id']not in canaries:continue
            data.guard(start,1680);h=torch.from_numpy(np.load(first.FEATURES/(row['row_id']+'.npy'),allow_pickle=False)).cuda()
            positions=cached[row['row_id']]['positions'];indices=torch.tensor([p['teacher_predictor_raw_index']for p in positions],device='cuda')
            frame=torch.zeros((1,1024,1024),device='cuda');frame[0,:len(h)]=h
            ref=F.linear(frame,w)[0].index_select(0,indices)
            for pos,logits in zip(positions,ref):
                if int(logits.argmax())!=pos['teacher_native_argmax']or abs(float(logits.logsumexp(-1))-pos['teacher_native_logsumexp'])>1e-5+1e-4*abs(pos['teacher_native_logsumexp']):
                    raise ValueError('native full head does not reconstruct original full-vocabulary top1/LSE')
            hs=h.index_select(0,indices)
            a=bridge.teacher_logits(hs,w,indices=indices,width=1024);b=bridge.teacher_logits(hs,w)
            qa=fixed.compare_prefix(ref.unsqueeze(0),a.unsqueeze(0),atol=1e-5,rtol=1e-4)
            qb=fixed.compare_prefix(ref.unsqueeze(0),b.unsqueeze(0),atol=1e-5,rtol=1e-4)
            fixed_good=fixed_good and qa['close']and qa['argmax_equal'];chunk_good=chunk_good and qb['close']and qb['argmax_equal']
            checks.append(dict(row_id=row['row_id'],positions=len(positions),fixed=qa,chunk=qb));del h,frame,ref,hs,a,b,logits
    if len(checks)!=4 or not fixed_good:raise ValueError('all four original-frame native head gates required')
    report.update(checks=checks,selected_head_policy='CHUNK'if chunk_good else'ORIGINAL_POSITION_FIXED1024',
        original_frame_pass=fixed_good,chunk_pass=chunk_good,teacher_body_loads=0,student_models=0)


def student_cost(torch,rows,cached,p,report,start):
    gate=require_closed('head');from scripts import diag_p106b_gsq_objective as loader
    from scripts import interactive_research_infer as manual
    from scripts import p106b_actd_consumer as ce
    from scripts.diag_p106b_actd_consumer import compare_gradients
    from tinylm.train.mtp_sft import Record,pad_records
    from torch.utils.checkpoint import checkpoint
    torch,model,_manifest,entry,_spec=loader.load_cpu();w=full_head(torch);init=bank(torch,model,w)
    report['initialization_seconds']=init['seconds'];report['initialization']=init['stats']
    model.cfg.grad_checkpoint=True;model.train();model.cuda();w=w.cuda();pt=torch.nn.Parameter(init['t2s'].cuda());ps=init['s2t'].cuda()
    core=manual.state_fingerprint(model);refs={};report['blocks']=[]
    report.update(native_weight_route='EXISTING_CHECKPOINT_NATIVE_TLINEAR_STE',precision='BF16_BODY_FP32_DUALSPACE_TF32_OFF',
        deterministic_algorithms=True,checkpoint=True,compile=False,mtp=False,micro=8,accum=16,width=1024,
        actual_x_per_block=32216,ce_denominator=772,kd_denominator=538,selected_head_policy=gate['selected_head_policy'],
        teacher_body_loads=0,teacher_head_bytes=w.numel()*w.element_size(),trainable_projector_parameters=pt.numel(),original_ce_unchanged=True)
    features={r['row_id']:np.load(first.FEATURES/(r['row_id']+'.npy'),allow_pickle=False)for r in rows}
    records=[Record(r['packed']['student']['ids'][:-1],r['packed']['student']['labels'][1:],r['packed']['student']['turn_ids'][1:])for r in rows]
    for index,enable in enumerate([False,True,True,False]):
        data.guard(start,1680);model.zero_grad(set_to_none=True);pt.grad=None;torch.manual_seed(1337)
        gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();tick=time.perf_counter()
        block=dict(index=index,arm='CE_PLUS_DSKDV2'if enable else'CE_ONLY',ce_targets=0,kd_positions=0,loss=0.,ce_sum=0.,student_kd_sum=0.,teacher_kd_sum=0.,projector_ce_sum=0.)
        for micro in range(16):
            data.guard(start,1680);begin=micro*8;subset=rows[begin:begin+8]
            x,y,owners=pad_records(records[begin:begin+8],p['student_pad_id'],'cuda',fixed_width=1024,batch_size=8)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hidden=model(x,return_hidden=True);parts=ce.components(model,hidden,y,owners,[],ce_denominator=772,actd_denominator=538,enable_actd=False,chunk=64,checkpoint_heads=True)
            loss=parts['loss'];block['ce_targets']+=parts['ce_targets'];block['ce_sum']+=float(parts['ce_sum'].detach())
            if enable:
                for bi,row in enumerate(subset):
                    positions=[q for q in cached[row['row_id']]['positions']if q['accepted']]
                    for a in range(0,len(positions),8):
                        sub=positions[a:a+8];sj=torch.tensor([q['student_predictor_raw_index']for q in sub],device='cuda');tj=torch.tensor([q['teacher_predictor_raw_index']for q in sub],device='cuda')
                        for q in sub:
                            if int(y[bi,q['student_predictor_raw_index']])!=q['student_target_id']or int(owners[bi,q['student_predictor_raw_index']])!=q['owner']:raise ValueError('native original CE position/owner changed')
                        ht=torch.from_numpy(features[row['row_id']][[q['teacher_predictor_raw_index']for q in sub]].copy()).cuda()
                        labels=torch.tensor([q['mapped_student_argmax']for q in sub],device='cuda')
                        def objective(hs,ht,u,e,w,pt,ps,labels,tj):
                            with torch.autocast('cuda',enabled=False):
                                terms=bridge.native_sums(hs,ht,u,e,w,pt,ps,labels,teacher_indices=tj if gate['selected_head_policy']!='CHUNK'else None,teacher_width=1024 if gate['selected_head_policy']!='CHUNK'else None)
                                return terms['student_kd_sum'],terms['teacher_kd_sum'],terms['projector_ce_sum']
                        terms=checkpoint(objective,hidden[bi].index_select(0,sj).float(),ht,model._emb_up_w(),model._emb_w(),w,pt,ps,labels,tj,use_reentrant=False,preserve_rng_state=False)
                        loss=loss+sum(terms)/538
                        for k,t in zip(['student_kd_sum','teacher_kd_sum','projector_ce_sum'],terms):block[k]+=float(t.detach())
                        block['kd_positions']+=len(sub)
                        del terms,ht,labels,sj,tj,sub
            loss.backward();block['loss']+=float(loss.detach());del x,y,owners,hidden,parts,loss
        torch.cuda.synchronize();block['forward_backward_seconds']=time.perf_counter()-tick
        block['peak_allocated_bytes']=torch.cuda.max_memory_allocated();block['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
        gradients={name:q.grad.detach().cpu().clone()for name,q in model.named_parameters()if q.grad is not None}
        if enable:
            if pt.grad is None or not bool(torch.isfinite(pt.grad).all())or float(pt.grad.norm())<=0:raise ValueError('actual projector CE gradient missing')
            gradients['__teacher_to_student_projector']=pt.grad.detach().cpu().clone()
        elif pt.grad is not None:raise ValueError('CE-only modified extra projector')
        if w.grad is not None or ps.grad is not None:raise ValueError('frozen teacher/reverse projector got gradients')
        if len(gradients)!=(158 if enable else 157)or any(not bool(torch.isfinite(g).all())for g in gradients.values()):raise ValueError('complete finite native gradients required')
        block['gradient_tensors']=len(gradients);block['gradient_norm']=sum(float(g.double().square().sum())for g in gradients.values())**.5
        if block['arm']in refs:
            match=compare_gradients(torch,refs[block['arm']],gradients);match['all_exact']=all(torch.equal(refs[block['arm']][n],g)for n,g in gradients.items());block['repeat_gradient_comparison']=match
        else:refs[block['arm']]=gradients
        if block['ce_targets']!=772 or block['kd_positions']!=(538 if enable else 0):raise ValueError('original global CE/KD accounting changed')
        if manual.state_fingerprint(model)!=core:raise ValueError('zero-update bridge modified native core')
        report['blocks'].append(block);exact.write(BASE/'student'/f'block_{index}.json',block)
        print('[DSKDV2_NATIVE_BLOCK] '+json.dumps(block),flush=True)
    report['student_core_unchanged']=manual.state_fingerprint(model)==entry['core_sha256'];report['original_checkpoint_unchanged']=exact.digest(ROOT/p['student_checkpoint'])==p['student_model']['checkpoint']['sha256']
    if not report['student_core_unchanged']or not report['original_checkpoint_unchanged']:raise ValueError('original native student changed')


def gpu(phase):
    verify();require_closed('cpu');_a,p,rows,cached,_f,_accepted,_m=inputs();start=time.perf_counter();out=BASE/phase
    if out.exists():raise FileExistsError('native GPU phase already attempted')
    out.mkdir();report=dict(tag=TAG,status='RUNNING',returncode=9,training=False,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,
        profile_sha256=exact.digest(BASE/'profile.json'));failure=None
    import torch
    try:
        from scripts.interactive_research_infer import require_idle_gpu
        report['entry_gpu_point']=require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        if not free.isdigit()or int(free)<12288:raise MemoryError('native bridge requires12288MiB free point')
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise ValueError('strict child cuBLAS determinism required')
        torch.set_num_threads(4);torch.manual_seed(1337);torch.use_deterministic_algorithms(True,warn_only=False)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
        torch.cuda.reset_peak_memory_stats()
        if phase=='head':head_gate(torch,rows,cached,report,start)
        else:student_cost(torch,rows,cached,p,report,start)
        report.update(status='NATIVE_HEAD_POLICY_VERIFIED'if phase=='head'else'NATIVE_DUALSPACE_GRADIENT_COST_MEASURED',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        gc.collect()
        if torch.cuda.is_initialized():
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();inputs();report['sources_features_and_assets_unchanged']=True
        except BaseException as exc:report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report.update(seconds=time.perf_counter()-start,full_dskdv2_training_ready=False)
        exact.write(out/'report.json',report)
    if failure:raise failure
    print('[DSKDV2_NATIVE_FINAL] '+json.dumps({k:report[k]for k in ['status','seconds','returncode']}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['cpu-native','head','student']);a=parser.parse_args()
    if a.phase=='cpu-native':cpu_native()
    else:gpu(a.phase)


if __name__=='__main__':main()
