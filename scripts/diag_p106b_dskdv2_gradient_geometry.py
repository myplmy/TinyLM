"""One frozen TRAIN128 forward pass, separate CE/KL/projector gradients, zero updates."""
from datetime import datetime,timezone
import gc
import json
import os
import time
import traceback
import numpy as np
from scripts import diag_p106b_dskdv2_bridge as native
from scripts.p106b_gradient_geometry import geometry

ROOT=native.ROOT;BASE=ROOT/'test_result/evidence/p106b_dskdv2_geometry_v1_20261113'


def run():
    native.verify();native.require_closed('student');head=native.require_closed('head')
    if head['selected_head_policy']!='CHUNK':raise ValueError('this separate-gradient diagnostic requires qualified native chunk head')
    _a,p,rows,cached,_f,_ac,_m=native.inputs();native.data.guard()
    if BASE.exists():raise FileExistsError('fresh gradient geometry namespace required')
    start=time.perf_counter();paths=[ROOT/f for f in ['scripts/p106b_gradient_geometry.py','scripts/test_p106b_gradient_geometry.py','scripts/diag_p106b_dskdv2_gradient_geometry.py']]
    paths.extend(native.BASE/x for x in ['profile.json','student/report.json','ROOT_STUDENT_EXIT_v1.json'])
    native.exact.write(BASE/'profile.json',dict(authority_directive=115,deadline=native.data.DEADLINE.isoformat(),
        sources={str(x.relative_to(ROOT)):native.exact.digest(x)for x in paths},rows=128,ce_targets=772,kd_positions=538,
        new_body_passes=1,optimizer_updates=0,checkpoint_writes=0,quality_claim=False))
    profile=native.exact.read(BASE/'profile.json');report=dict(status='RUNNING',returncode=9,quality_claim=False,optimizer_updates=0,checkpoint_writes=0,
        profile_sha256=native.exact.digest(BASE/'profile.json'));failure=None
    import torch
    model=w=pt=ps=init=hs=ht=parts=losses=gradients=None;acc={}
    try:
        from scripts import diag_p106b_gsq_objective as loader
        from scripts import interactive_research_infer as manual
        from scripts import p106b_actd_consumer as ce
        from tinylm.train.mtp_sft import Record,pad_records
        report['entry_gpu_point']=manual.require_idle_gpu()
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise ValueError('strict cuBLAS child policy required')
        torch.set_num_threads(4);torch.manual_seed(1337);torch.use_deterministic_algorithms(True,warn_only=False)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.deterministic=True
        torch,model,_manifest,entry,_spec=loader.load_cpu();w=native.full_head(torch);init=native.bank(torch,model,w)
        model.cfg.grad_checkpoint=True;model.train();model.cuda();w=w.cuda();pt=torch.nn.Parameter(init['t2s'].cuda());ps=init['s2t'].cuda()
        names,parameters=zip(*[(n,q)for n,q in model.named_parameters()if q.requires_grad]);core=manual.state_fingerprint(model)
        records=[Record(r['packed']['student']['ids'][:-1],r['packed']['student']['labels'][1:],r['packed']['student']['turn_ids'][1:])for r in rows]
        acc={arm:{n:torch.zeros_like(q,device='cpu')for n,q in zip(names,parameters)}for arm in ['CE','STUDENT_KD','TEACHER_KD']}
        projector=torch.zeros_like(pt,device='cpu');sums={k:0. for k in ['CE','STUDENT_KD','TEACHER_KD','PROJECTOR_CE']};targets=positions_count=0
        torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();tick=time.perf_counter()
        for micro in range(16):
            native.data.guard(start,1680);begin=8*micro;subset=rows[begin:begin+8]
            x,y,owners=pad_records(records[begin:begin+8],p['student_pad_id'],'cuda',fixed_width=1024,batch_size=8)
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hs=model(x,return_hidden=True);terms=ce.components(model,hs,y,owners,[],ce_denominator=772,actd_denominator=538,enable_actd=False,chunk=64,checkpoint_heads=True)
            zero=hs.sum()*0.;losses=dict(CE=terms['loss'],STUDENT_KD=zero,TEACHER_KD=zero,PROJECTOR_CE=pt.sum()*0.);targets+=terms['ce_targets']
            for bi,row in enumerate(subset):
                sub=[q for q in cached[row['row_id']]['positions']if q['accepted']]
                if not sub:continue
                feature=np.load(native.first.FEATURES/(row['row_id']+'.npy'),allow_pickle=False)
                for a in range(0,len(sub),8):
                    pos=sub[a:a+8];sj=torch.tensor([q['student_predictor_raw_index']for q in pos],device='cuda');tj=[q['teacher_predictor_raw_index']for q in pos]
                    ht=torch.from_numpy(feature[tj].copy()).cuda();labels=torch.tensor([q['mapped_student_argmax']for q in pos],device='cuda')
                    with torch.autocast('cuda',enabled=False):parts=native.bridge.native_sums(hs[bi].index_select(0,sj).float(),ht,model._emb_up_w(),model._emb_w(),w,pt,ps,labels)
                    for dst,src in [('STUDENT_KD','student_kd_sum'),('TEACHER_KD','teacher_kd_sum'),('PROJECTOR_CE','projector_ce_sum')]:losses[dst]=losses[dst]+parts[src]/538
                    positions_count+=len(pos)
            for arm in ['CE','STUDENT_KD','TEACHER_KD']:
                gradients=torch.autograd.grad(losses[arm],parameters,retain_graph=True,allow_unused=True)
                for name,g in zip(names,gradients):
                    if g is not None:
                        if not bool(torch.isfinite(g).all()):raise ValueError('nonfinite branch gradient')
                        acc[arm][name].add_(g.detach().cpu())
                gradients=None
            gradients=torch.autograd.grad(losses['PROJECTOR_CE'],pt)[0];projector.add_(gradients.detach().cpu())
            for arm,value in losses.items():sums[arm]+=float(value.detach())
            gradients=hs=ht=parts=losses=terms=zero=x=y=owners=None
        torch.cuda.synchronize();report['forward_separate_backward_seconds']=time.perf_counter()-tick
        if targets!=772 or positions_count!=538:raise ValueError('same original CE/KD positions required')
        kd={n:acc['STUDENT_KD'][n]+acc['TEACHER_KD'][n]for n in names}
        body=[n for n in names if not n.startswith('emb')];shared=[n for n in names if n.startswith('emb')]
        report.update(ce_targets=targets,kd_positions=positions_count,normalized_branch_losses=sums,projector_gradient_norm=float(projector.double().norm()),
            named_parameter_tensors=len(names),shared_embedding_head_tensor_names=shared,body_tensor_count=len(body),
            ce_vs_student_kd=geometry(acc['CE'],acc['STUDENT_KD']),ce_vs_teacher_kd=geometry(acc['CE'],acc['TEACHER_KD']),
            ce_vs_combined_student_parameters=geometry(acc['CE'],kd),
            body_ce_vs_kd=geometry({n:acc['CE'][n]for n in body},{n:kd[n]for n in body}),
            shared_embedding_head_ce_vs_kd=geometry({n:acc['CE'][n]for n in shared},{n:kd[n]for n in shared}),
            student_core_unchanged=manual.state_fingerprint(model)==core,original_checkpoint_unchanged=native.exact.digest(ROOT/p['student_checkpoint'])==p['student_model']['checkpoint']['sha256'])
        if not report['student_core_unchanged']or not report['original_checkpoint_unchanged']:raise ValueError('native source changed')
        if any(q.grad is not None for q in parameters)or pt.grad is not None or w.grad is not None or ps.grad is not None:raise ValueError('autograd.grad must not accumulate optimizer gradients')
        report.update(status='SEPARATE_NATIVE_GRADIENT_GEOMETRY_MEASURED',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        model=w=pt=ps=init=hs=ht=parts=losses=gradients=parameters=g=value=sj=labels=terms=zero=x=y=owners=None;acc={};gc.collect()
        if torch.cuda.is_initialized():
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        for name,sha in profile['sources'].items():
            if native.exact.digest(ROOT/name)!=sha:report.update(status='ERROR',returncode=9);failure=failure or RuntimeError('pinned geometry source changed')
        native.verify();native.inputs();report['sources_features_and_assets_unchanged']=True
        report['seconds']=time.perf_counter()-start;native.exact.write(BASE/'report.json',report)
    if failure:raise failure
    print('[DSKDV2_GEOMETRY_FINAL] '+json.dumps({k:report[k]for k in ['status','seconds','body_ce_vs_kd','projector_gradient_norm']}),flush=True)


if __name__=='__main__':run()
