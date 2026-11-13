"""Real completed93M CE/ACTD gradient and resource mechanics, zero updates."""
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
from scripts import diag_p106b_actd_topk as d
from scripts import p106b_actd_cache as cache
from scripts import p106b_actd_consumer as consumer


def read_cache():
    p,rows=d.verify();out=d.BASE/'teacher';report=json.loads((out/'report.json').read_text())
    witness=json.loads((d.BASE/'ROOT_TEACHER_EXIT_v1.json').read_text())
    if (report.get('status')!='ACTD_NATIVE_TOP128_COMPLETE' or report.get('returncode')!=0
            or report.get('rows_completed')!=128 or not report.get('sources_and_inputs_unchanged')
            or report.get('final_cuda_cleanup',{}).get('allocated_bytes')!=0
            or report.get('final_cuda_cleanup',{}).get('reserved_bytes')!=0
            or report.get('owned_model_alive_after_release')is not False
            or witness.get('actual_process_exit_code')!=0 or witness.get('report_sha256')!=d.inventory.digest(out/'report.json')
            or report.get('profile_sha256')!=d.inventory.digest(d.BASE/'profile.json')):
        raise ValueError('complete same-profile teacher cache plus actual root exit0 required')
    from scripts.p106b_shards import verify
    verify(out,report['cache_manifest']);cached={}
    for shard in report['cache_manifest']['shards']:
        for line in (out/shard['path']).read_text().splitlines():
            r=json.loads(line)
            if r['row_id']in cached:raise ValueError('duplicate teacher cache row')
            cached[r['row_id']]=r
    if set(cached)!={r['row_id'] for r in rows}:raise ValueError('exact full TRAIN128 row coverage required')
    anchors=json.loads((d.BASE/'anchor_lookup.json').read_text());accepted={};holds={}
    for row in rows:
        r=cached[row['row_id']]
        if r['schema']!='P106B_ACTD_NATIVE_TOP128_ROW_V1' or r['prepared_row_sha256']!=d.encoder.object_sha(row):
            raise ValueError('top128 row is not from this exact prepared source/record/position')
        distributions={int(i):v for i,v in r['distributions'].items()}
        good,held=cache.accepted_positions(row,distributions,policy=p['primary_policy'],k=128,anchor_lookup=anchors,student_vocab=32768)
        if r['acceptance'][p['primary_policy']]!={'accepted':len(good),'held':len(held)}:raise ValueError('teacher acceptance differs from independently read raw')
        accepted[row['row_id']]=good;holds[row['row_id']]=held
    count=sum(map(len,accepted.values()))
    if count!=report['accepted_positions'][p['primary_policy']]:raise ValueError('full-cache denominator differs')
    return p,rows,accepted,holds,count,report


def compare_gradients(torch,reference,observed):
    if set(reference)!=set(observed):raise ValueError('repeat gradient parameter set differs')
    maximum=outside=0;norm=delta=0.
    for name,a in reference.items():
        b=observed[name]
        if a.shape!=b.shape or not bool(torch.isfinite(b).all()):raise ValueError('nonfinite/mismatched repeat gradient')
        maximum=max(maximum,float((a-b).abs().max()));outside+=int((~torch.isclose(a,b,atol=1e-5,rtol=1e-4)).sum())
        norm+=float(a.double().square().sum());delta+=float((a.double()-b.double()).square().sum())
    return dict(maximum_absolute_difference=maximum,outside_tolerance=outside,
        relative_l2=(delta/max(norm,1e-300))**.5,atol=1e-5,rtol=1e-4,quality_claim=False)


def run():
    p,rows,accepted,holds,count,teacher=read_cache();start=time.perf_counter();d.guard(start,1800)
    out=d.BASE/'student'
    if out.exists():raise FileExistsError('student mechanics already attempted')
    out.mkdir();report=dict(tag=d.TAG,status='RUNNING',returncode=9,training=False,optimizer_updates=0,
        checkpoint_writes=0,quality_claim=False,profile_sha256=d.inventory.digest(d.BASE/'profile.json'),
        teacher_report_sha256=d.inventory.digest(d.BASE/'teacher/report.json'),ce_denominator=772,
        actd_denominator=count,accepted_by_language={language:sum(len(accepted[r['row_id']]) for r in rows if r['language']==language) for language in ('ko','en')},
        held_positions=sum(map(len,holds.values())),original_ce_unchanged=True,
        started_at=datetime.now(timezone.utc).isoformat(),blocks=[])
    if not count:
        report.update(status='VALID_SIGNAL_NEGATIVE_ZERO_ACCEPTED_POSITIONS',returncode=0,seconds=time.perf_counter()-start)
        d.write_new(out/'report.json',report);print('[ACTD_STUDENT_SIGNAL_NEGATIVE] '+json.dumps(report),flush=True);return
    torch=model=manifest=entry=spec=None;failure=None;references={}
    try:
        from scripts import interactive_research_infer as manual
        from scripts import diag_p106b_gsq_objective as old
        report['entry_gpu_point']=manual.require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        if not free.isdigit() or int(free)<8192:raise MemoryError('ACTD mechanics requires8192MiB free point')
        torch,model,manifest,entry,spec=old.load_cpu()
        if entry!=p['student_model'] or old.object_sha(manifest)!=p['manual_manifest_sha256']:
            raise ValueError('same strict completed93M checkpoint/manifest required')
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        model.cfg.grad_checkpoint=True;model.train();model.cuda();initial=manual.state_fingerprint(model)
        report.update(initial_core_sha256=initial,model='new595-broad-q',native_weight_route='EXISTING_CHECKPOINT_NATIVE_TLINEAR_STE',
            precision='BF16_EAGER_TF32_OFF_HEAD_REDUCTIONS_FP32',checkpoint=True,compile=False,mtp=False,
            micro=8,accum=16,width=1024,actual_x_per_block=32216,padded_slots_per_block=131072,
            additional_alm_or_gsq=False,original_parent_checkpoint=str(spec.checkpoint))
        from tinylm.train.mtp_sft import Record,pad_records
        records=[Record(r['packed']['student']['ids'][:-1],r['packed']['student']['labels'][1:],r['packed']['student']['turn_ids'][1:]) for r in rows]
        for index,enable in enumerate([False,True,True,False]):
            d.guard(start,1680);model.zero_grad(set_to_none=True);torch.manual_seed(1337)
            gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();tick=time.perf_counter()
            block=dict(index=index,arm='CE_PLUS_ACTD' if enable else 'CE_ONLY',microbatches=0,ce_targets=0,actd_positions=0,loss=0.,ce_sum=0.,anchor_sum=0.,residual_sum=0.)
            for micro in range(16):
                d.guard(start,1680);begin=micro*8;subset=rows[begin:begin+8]
                x,y,segments=pad_records(records[begin:begin+8],p['student_pad_id'],'cuda',fixed_width=1024,batch_size=8)
                positions=[dict(pos,batch_row=i) for i,row in enumerate(subset) for pos in accepted[row['row_id']]]
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=model(x,return_hidden=True)
                    terms=consumer.components(model,hidden,y,segments,positions,ce_denominator=772,actd_denominator=count,
                        enable_actd=enable,residual_weight=1.,chunk=64,checkpoint_heads=True)
                terms['loss'].backward()
                for key in ['loss','ce_sum','anchor_sum','residual_sum']:block[key]+=float(terms[key].detach())
                block['ce_targets']+=terms['ce_targets'];block['actd_positions']+=terms['actd_positions'];block['microbatches']+=1
                del x,y,segments,positions,hidden,terms
            torch.cuda.synchronize();block['forward_backward_seconds']=time.perf_counter()-tick
            block['peak_allocated_bytes']=torch.cuda.max_memory_allocated();block['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            gradients={n:q.grad.detach().cpu().clone() for n,q in model.named_parameters() if q.grad is not None}
            if not gradients or any(not bool(torch.isfinite(g).all()) for g in gradients.values()):raise ValueError('finite actual student gradients required')
            block['gradient_tensors']=len(gradients);block['gradient_norm']=sum(float(g.double().square().sum()) for g in gradients.values())**.5
            if block['gradient_norm']<=0:raise ValueError('student gradients must be nonzero')
            if block['arm']in references:block['repeat_gradient_comparison']=compare_gradients(torch,references[block['arm']],gradients)
            else:references[block['arm']]=gradients
            if block['ce_targets']!=772 or block['actd_positions']!=(count if enable else 0):raise ValueError('original CE/global ACTD target accounting differs')
            block['core_unchanged']=manual.state_fingerprint(model)==initial
            if not block['core_unchanged']:raise ValueError('zero-optimizer mechanics changed model core')
            report['blocks'].append(block);d.write_new(out/f'block_{index}.json',block)
            print('[ACTD_STUDENT_BLOCK] '+json.dumps(block),flush=True)
        report['ce_vs_actd_gradient_difference']=compare_gradients(torch,references['CE_ONLY'],references['CE_PLUS_ACTD'])
        report.update(status='ACTD_ACTUAL_HEAD_GRADIENT_COST_COMPLETE',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',returncode=9,error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        model=manifest=entry=spec=None;references={};gc.collect()
        if torch is not None and torch.cuda.is_initialized():
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:
                report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:
            d.verify();read_cache();report['sources_inputs_and_cache_unchanged']=True
            report['original_checkpoint_unchanged']=d.inventory.digest(d.ROOT/p['student_checkpoint'])==p['student_model']['checkpoint']['sha256']
            if not report['original_checkpoint_unchanged']:raise ValueError('original checkpoint changed')
        except BaseException as exc:
            report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report.update(seconds=time.perf_counter()-start,finished_at=datetime.now(timezone.utc).isoformat())
        d.write_new(out/'report.json',report)
    if failure is not None:raise failure
    print('[ACTD_STUDENT_FINAL] '+json.dumps({k:report[k] for k in ['status','returncode','seconds','ce_denominator','actd_denominator']}),flush=True)


if __name__=='__main__':run()
