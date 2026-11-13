"""Only a new teacher-to-student projector is optimized; frozen model bodies never run."""
import argparse
import gc
import hashlib
import json
import os
import time
import traceback
import numpy as np
from scripts import diag_p106b_dskdv2_bridge as native
from scripts.p106b_projector_split import split_by_root

ROOT=native.ROOT;BASE=ROOT/'test_result/evidence/p106b_dskdv2_projector_warmup_v1_20261113'
SOURCES=('scripts/p106b_projector_split.py','scripts/test_p106b_projector_split.py','scripts/diag_p106b_dskdv2_projector_warmup.py')


def prepare():
    native.verify();native.require_closed('student');_a,_p,rows,cached,_f,_ac,_m=native.inputs();native.data.guard()
    if BASE.exists():raise FileExistsError('fresh projector namespace required')
    split=split_by_root(rows);count={k:sum(sum(p['accepted']for p in cached[r['row_id']]['positions'])for r in rows if r['row_id']in ids)for k,ids in split.items()}
    if sum(count.values())!=538 or min(count.values())<1:raise ValueError('same native538 split required')
    sources=[ROOT/x for x in SOURCES]+[native.BASE/'profile.json',native.BASE/'student/report.json',native.BASE/'ROOT_STUDENT_EXIT_v1.json',
        ROOT/'test_result/evidence/p106b_dskdv2_geometry_v1_20261113/report.json',ROOT/'test_result/evidence/p106b_dskdv2_geometry_v1_20261113/ROOT_ACTUAL_EXIT_v1.json']
    native.exact.write(BASE/'profile.json',dict(tag=BASE.name,authority_directive=115,deadline=native.data.DEADLINE.isoformat(),
        sources={str(x.relative_to(ROOT)):native.exact.digest(x)for x in sources},split=split,positions=count,
        updates=100,lr=.001,betas=[.9,.999],eps=1e-8,weight_decay=0.,clip_norm=1.,seed=1337,
        measurements=[0,25,50,75,100],early_stopping=False,student_updates=0,checkpoint_writes=0,
        root_split_is_not_global_document_leakage_certificate=True,quality_claim=False))
    print('[PROJECTOR_PREPARED] '+json.dumps(dict(positions=count,rows={k:len(v)for k,v in split.items()},model_loads=0,gpu_calls=0)),flush=True)


def verify():
    native.verify();native.data.guard();p=native.exact.read(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=native.data.DEADLINE.isoformat():raise ValueError('projector authority changed')
    for name,sha in p['sources'].items():
        if native.exact.digest(ROOT/name)!=sha:raise ValueError('sealed projector source changed')
    return p


def actual_inner(torch,p,rows,cached,report,start):
    from scripts import diag_p106b_gsq_objective as loader
    from scripts import interactive_research_infer as manual
    torch,model,_manifest,entry,_spec=loader.load_cpu();model.eval();w=native.full_head(torch);init=native.bank(torch,model,w);w=None;gc.collect()
    up=model._emb_up_w().detach().cuda();emb=model._emb_w().detach().cuda();pt=torch.nn.Parameter(init['t2s'].cuda())
    features=[];labels=[];gold=[];metadata=[]
    for row,positions,h in native.selected(rows,cached):
        for q in positions:
            features.append(h[q['teacher_predictor_raw_index']]);labels.append(q['mapped_student_argmax']);gold.append(q['student_target_id'])
            metadata.append(dict(row_id=row['row_id'],language=row['language'],mapping_mode=q['mapping_mode']))
    h=torch.from_numpy(np.stack(features)).cuda();targets=torch.tensor(labels,device='cuda');original=torch.tensor(gold,device='cuda')
    masks={k:torch.tensor([m['row_id']in ids for m in metadata],device='cuda')for k,ids in p['split'].items()}
    if any(int(masks[k].sum())!=p['positions'][k]for k in masks):raise ValueError('exact row-root membership changed')
    native.exact.write(BASE/'position_metadata.json',dict(positions=metadata,root_split=p['split'],mapped_native_top1_agrees_original_gold=sum(a==b for a,b in zip(labels,gold))))
    optimizer=torch.optim.AdamW([pt],lr=p['lr'],betas=tuple(p['betas']),eps=p['eps'],weight_decay=p['weight_decay'])
    report.update(teacher_body_loads=0,student_body_forwards=0,student_gpu_loads=0,projector_parameters=pt.numel(),student_updates=0,
        original_native_initialization=init['stats'],initialization_seconds=init['seconds'],measurements=[],maximum_preclip_projector_gradient_norm=0.)
    torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();tick=time.perf_counter()
    for step in range(p['updates']+1):
        native.data.guard(start,1680)
        if step in p['measurements']:
            with torch.no_grad():
                logits=native.bridge.factored_logits(h@pt,up,emb);pred=logits.argmax(-1);measurement=dict(step=step,parts={})
                for k,mask in masks.items():
                    measurement['parts'][k]=dict(positions=int(mask.sum()),mapped_teacher_top1_matches=int((pred[mask]==targets[mask]).sum()),
                        original_gold_matches=int((pred[mask]==original[mask]).sum()),projector_ce=float(torch.nn.functional.cross_entropy(logits[mask],targets[mask])))
                for lang in ['ko','en']:
                    for mode in [1,3]:
                        mask=torch.tensor([m['language']==lang and m['mapping_mode']==mode for m in metadata],device='cuda')
                        measurement['parts'][lang+'_mode'+str(mode)]=dict(positions=int(mask.sum()),mapped_teacher_top1_matches=int((pred[mask]==targets[mask]).sum()))
                report['measurements'].append(measurement);del logits,pred
            print('[PROJECTOR_MEASURE] '+json.dumps(measurement),flush=True)
        if step==p['updates']:break
        optimizer.zero_grad(set_to_none=True);mask=masks['train']
        loss=torch.nn.functional.cross_entropy(native.bridge.factored_logits(h[mask]@pt,up,emb),targets[mask]);loss.backward()
        if pt.grad is None or not bool(torch.isfinite(pt.grad).all()):raise ValueError('finite projector-only gradient required')
        norm=float(torch.nn.utils.clip_grad_norm_([pt],p['clip_norm'],error_if_nonfinite=True));optimizer.step()
        report['maximum_preclip_projector_gradient_norm']=max(report['maximum_preclip_projector_gradient_norm'],norm)
    torch.cuda.synchronize();report['warmup_and_measurement_seconds']=time.perf_counter()-tick
    report.update(projector_optimizer_updates=p['updates'],fixed_step_not_dev_selected=True,final_projector_sha256=hashlib.sha256(pt.detach().cpu().contiguous().numpy().tobytes()).hexdigest().upper(),
        original_checkpoint_unchanged=native.exact.digest(ROOT/_spec.checkpoint)==entry['checkpoint']['sha256'],student_core_unchanged=manual.state_fingerprint(model)==entry['core_sha256'])
    if not report['student_core_unchanged']or not report['original_checkpoint_unchanged']:raise ValueError('frozen original student changed')
    if any(q.grad is not None for q in model.parameters()):raise ValueError('projector-only warmup touched frozen model gradients')


def actual():
    p=verify();_a,_p,rows,cached,_f,_ac,_m=native.inputs();start=time.perf_counter()
    if (BASE/'report.json').exists():raise FileExistsError('projector run already attempted')
    report=dict(status='RUNNING',returncode=9,profile_sha256=native.exact.digest(BASE/'profile.json'),quality_claim=False,checkpoint_writes=0,training_scope='NEW_PROJECTOR_ONLY');failure=None
    import torch
    try:
        from scripts.interactive_research_infer import require_idle_gpu
        report['entry_gpu_point']=require_idle_gpu()
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise ValueError('deterministic child required')
        torch.set_num_threads(4);torch.manual_seed(1337);torch.use_deterministic_algorithms(True,warn_only=False)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        actual_inner(torch,p,rows,cached,report,start);report.update(status='PROJECTOR_ONLY_WARMUP_MEASURED_NOT_STUDENT_QUALITY',returncode=0)
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
        verify();native.inputs();report['sources_features_and_assets_unchanged']=True;report['seconds']=time.perf_counter()-start;native.exact.write(BASE/'report.json',report)
    if failure:raise failure
    print('[PROJECTOR_FINAL] '+json.dumps({k:report[k]for k in ['status','seconds','projector_optimizer_updates']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);a=parser.parse_args();(prepare if a.phase=='prepare'else actual)()
