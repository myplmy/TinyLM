"""Owned DWA native TRAIN128 zero-update CE/DWA ABBA engineering diagnostic.

Reuse the closed original teacher feature cache, not its expired runtime.
No teacher body, optimizer step, new checkpoint or quality evaluation is run.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager,redirect_stdout
from datetime import datetime,timezone
import gc,hashlib,io,json,os,signal,sys,time,traceback,unittest,weakref
from pathlib import Path
import tinylm
from scripts import diag_p106b_dvlm_pts as original
from scripts import p106b_dwa_cma as cma
from scripts import p106b_dwa_native as boundary

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'test_result/evidence/p106b_dwa_native_v1_20261117_s1337'
PROFILE=BASE/'profile.json'
CONTRACTS=ROOT/'handoff/audit/research_20261117_01a1e647/CPU_NEW_METHOD_CONTRACTS_v1.json'
RECOVERED=ROOT/'test_result/evidence/p106b_dskdv2_hidden_recovery_v2_20261113'
HEADS=ROOT/'test_result/evidence/p106b_dskdv2_heads_v1_20261113'
HEAD_GATE=ROOT/'test_result/evidence/p106b_dskdv2_bridge_v1_20261113/head/report.json'
PLAN=ROOT/'test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md'
CUTOFF=datetime(2026,11,17,7,40,tzinfo=timezone.utc)
TAG='p106b_dwa_native_v1_20261117_s1337'
OWN_SOURCES=('scripts/diag_p106b_dwa_native.py','scripts/p106b_dwa_native.py',
    'scripts/test_p106b_dwa_native.py','scripts/p106b_dwa_cma.py','scripts/test_p106b_dwa_cma.py',
    'scripts/p106b_softdtw_triton_v2.py','scripts/p106b_dwa_reference.py',
    'scripts/p106b_dskdv2_bridge.py','scripts/interactive_research_infer.py',
    'scripts/diag_p106b_resource_matrix.py','scripts/diag_p014e_packed_deploy.py')

digest=original.digest
read=original.read
def write(path,value):
    data=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(data)>=20_000_000:raise ValueError('owned DWA metadata must remain below20MB')
    with Path(path).open('xb') as stream:stream.write(data)

def guard(start=None):
    if datetime.now(timezone.utc)>=CUTOFF or (BASE/'STOP').exists():raise TimeoutError('user158 DWA cutoff/owned STOP')
    if start is not None and time.monotonic()-start>=1800:raise TimeoutError('DWA compute cap1800s')

def inputs():
    parent,rows=original.parent_rows()
    closure=read(RECOVERED/'actual/report.json');witness=read(RECOVERED/'ROOT_ACTUAL_EXIT_v1.json')
    if (closure['returncode']!=0 or witness['actual_tool_exit']!=0
            or witness['report_sha256']!=digest(RECOVERED/'actual/report.json')
            or not closure['sources_features_and_assets_unchanged'] or not witness['all_four_cached_hidden_exact']):
        raise ValueError('closed exact native128 feature cache required')
    feature_manifest=read(RECOVERED/'features_manifest.json')
    features={entry['row_id']:entry for entry in feature_manifest['features']}
    if set(features)!={row['row_id'] for row in rows}:raise ValueError('original feature128 row identity differs')
    student_count=teacher_count=0
    for row in rows:
        feature=features[row['row_id']];path=ROOT/feature['path']
        if (not str(path.relative_to(ROOT)).startswith('data_cache/p106b_dskdv2_hidden_v1_20261113/')
                or path.is_symlink() or not path.is_file() or digest(path)!=feature['sha256']
                or feature['shape']!=[len(row['teacher']['ids'])-1,1024] or path.stat().st_size!=feature['bytes']):
            raise ValueError('exact existing teacher predictor feature changed')
        for view in (row['packed']['student'],row['teacher']):
            if (len(view['ids'])!=len(view['supervised']) or any(type(v)is not bool for v in view['supervised'])
                    or not sum(view['supervised'][1:])):raise ValueError('full native boolean nonempty target mask required')
        student_count+=sum(row['packed']['student']['supervised'][1:]);teacher_count+=sum(row['teacher']['supervised'][1:])
        student=row['packed']['student']
        if any((label!=-100)!=mask or mask and label!=token for label,mask,token in
                zip(student['labels'],student['supervised'],student['ids'])):
            raise ValueError('original student labels/next-target mask changed')
    if student_count!=772 or teacher_count!=811:raise ValueError('complete native772/811 target inventory required')
    heads=read(HEADS/'profile.json');assets=heads['teacher_assets']['files']
    if heads['teacher_key']!='model.language_model.embed_tokens.weight':raise ValueError('exact tied teacher key differs')
    config=read(Path(assets['config.json']['resolved_path']))
    if config.get('tie_word_embeddings') is not True:raise ValueError('source native teacher input/output tying required')
    for item in assets.values():
        path=Path(item['resolved_path'])
        if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
            raise ValueError('exact existing teacher assets changed')
    if read(HEAD_GATE)['selected_head_policy']!='CHUNK':raise ValueError('closed original native head chunk gate required')
    from scripts import interactive_research_infer as manual
    manifest=manual.verify_manifest();entry=manifest['entries']['new595-broad-q']
    if (manual.canonical_sha(manifest)!=parent['manual_manifest_sha256']
            or entry!=parent['student_model'] or entry['checkpoint']['path']!=parent['student_checkpoint']):
        raise ValueError('original exact completed student/manifest identity differs')
    if digest(ROOT/parent['student_checkpoint'])!=parent['student_model']['checkpoint']['sha256']:
        raise ValueError('original student checkpoint SHA differs')
    references=[RECOVERED/'actual/report.json',RECOVERED/'ROOT_ACTUAL_EXIT_v1.json',RECOVERED/'features_manifest.json',
        HEADS/'profile.json',HEAD_GATE,original.PARENT/'profile.json',ROOT/manual.MANIFEST,CONTRACTS]
    references.extend(original.PARENT/part['path'] for part in parent['prepared_manifest']['shards'])
    return dict(parent=parent,rows=rows,features=features,teacher_assets=assets,teacher_key=heads['teacher_key'],
        student_entry=entry,references={str(path.relative_to(ROOT)):digest(path) for path in references})

def source_names():
    from scripts import diag_p106b_gsq_objective as loader
    return tuple(dict.fromkeys((*OWN_SOURCES,'scripts/diag_p106b_gsq_objective.py',*loader.SOURCES,*original.SOURCES)))

def prepare():
    guard()
    if BASE.exists():raise FileExistsError('preserve DWA namespace')
    closed=read(CONTRACTS)
    if not closed['successful'] or closed['contracts_by_module']['DWA_CMA']!=12:raise ValueError('existing completed CMA12 required')
    for name in ('scripts/p106b_dwa_cma.py','scripts/test_p106b_dwa_cma.py'):
        if digest(ROOT/name)!=closed['source_SHA256'][name]:raise ValueError('CMA12 source changed')
    suite=unittest.defaultTestLoader.loadTestsFromName('scripts.test_p106b_dwa_native')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun!=5:raise RuntimeError('all5 native boundary contracts required')
    import torch
    if torch.cuda.is_initialized():raise RuntimeError('CPU contracts unexpectedly initialized CUDA')
    evidence=inputs()
    from scripts import check_run_registry as registry
    output=io.StringIO()
    with redirect_stdout(output):
        logs=registry.load();code=registry.cmd_tag(logs,TAG)
    if code!=0:raise ValueError('DWA tag collision')
    BASE.mkdir()
    with (BASE/'initial_plan.md').open('xb') as stream:stream.write(PLAN.read_bytes())
    policy=dict(order=['CE_ONLY','DWA','DWA','CE_ONLY'],rows=128,student_targets=772,teacher_targets=811,
        microbatch=1,accum_rows=128,width=1024,student_body='BF16_AUTOCAST_NATIVE_STE',
        dual_space='FP32_TF32_OFF',DTW='EXISTING_GPU_FP64_V2;DIFFERENTIABLE_FP32_TO_FP64_CAST',
        teacher_body_loads=0,student_models=1,optimizer_updates=0,checkpoint_writes=0,
        temperature=1.,ce_rate=1.,kd_rate=1.,dtw_rate=1.,confidence_gate_scale=1.,
        projector_initialization='SEEDED1337_CPU_LINEAR_BIAS_FALSE_KAIMING_UNIFORM_DEFAULT;NO_TRAINED_WARMUP',
        band=dict(alpha=.7,base=5.,entropy_scale=2.,penalty=1.),gamma=.1,
        complete_update_denominator=772,original_alignment538_filter='NOT_USED;ALL_NATIVE772_AND811_TARGETS',
        max_compute_seconds=1800,max_phase_seconds=1920,max_output_bytes=180_000_000,
        first_complete_block_forecast='MAX_OBSERVED_BLOCK_X_REMAINING_X1.5_PLUS60;UNSEEN_ARM_NOT_GUARANTEED;NO_SUITE_SHRINK',
        minimum_free_vram_bytes=8*1024**3,allocator_peak_cap_bytes=8*1024**3,
        repeat_gradient_gate='EXACT_SHA256_ALL_NATIVE_AND_PROJECTOR_GRADIENTS;STOP_ON_NEGATIVE',
        quality_claim=False,corpus_admitted=False)
    profile=dict(schema='P106B_DWA_NATIVE_ZERO_UPDATE_ABBA_V1',tag=TAG,authority_directive=158,
        cutoff=CUTOFF.isoformat(),sources={name:digest(ROOT/name) for name in source_names()},
        references=evidence['references'],initial_plan_sha256=digest(BASE/'initial_plan.md'),policy=policy,
        row_ids=[row['row_id'] for row in evidence['rows']],features=evidence['features'],
        teacher_assets=evidence['teacher_assets'],teacher_key=evidence['teacher_key'],
        student_checkpoint=evidence['parent']['student_checkpoint'],
        student_checkpoint_sha256=evidence['parent']['student_model']['checkpoint']['sha256'],
        inherited_CMA_CPU_contracts=12,new_boundary_CPU_contracts=5,
        runtime=dict(torch=str(torch.__version__),CUDA=torch.version.cuda,python=sys.version),
        registry_preflight=dict(tag=TAG,exit=code,stdout=output.getvalue()),model_loads=0,CUDA_initializations=0)
    write(PROFILE,profile);print('[DWA_NATIVE_PREPARED]CPU12+5;original128/772student/811teacher;teacher-body0;GPU NOT_RUN',flush=True)

def verify():
    guard();p=read(PROFILE)
    if (p['authority_directive']!=158 or p['cutoff']!=CUTOFF.isoformat()
            or p['sources']!={name:digest(ROOT/name) for name in p['sources']}
            or p['references']!={name:digest(ROOT/name) for name in p['references']}
            or p['initial_plan_sha256']!=digest(BASE/'initial_plan.md')):
        raise ValueError('frozen native DWA source/profile/reference mismatch')
    evidence=inputs()
    if [row['row_id'] for row in evidence['rows']]!=p['row_ids'] or evidence['features']!=p['features']:
        raise ValueError('complete native DWA input identity differs')
    return p,evidence

@contextmanager
def phase_alarm(seconds):
    prior=signal.getsignal(signal.SIGALRM)
    def expired(*_):raise TimeoutError('owned DWA phase wall cap')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior)

def gradients(torch,model,projectors,enabled):
    result={};total=0.
    tensors=list(model.named_parameters())+list(projectors.named_parameters(prefix='dwa_projectors'))
    for name,param in tensors:
        if param.grad is None:continue
        value=param.grad.detach().cpu().contiguous()
        if not bool(torch.isfinite(value).all()):raise ValueError('nonfinite native gradient: '+name)
        result[name]=hashlib.sha256(value.view(torch.uint8).numpy().tobytes()).hexdigest().upper()
        total+=float(value.double().square().sum())
    if not any(name.startswith('dwa_projectors') for name in result)==enabled:
        raise ValueError('projector gradient scope differs from declared arm')
    return result,total**.5

def run_block(torch,model,teacher_head,projectors,p,rows,features,enabled,index,start):
    import numpy as np
    from scripts.p106b_softdtw_triton_v2 import soft_dtw
    from scripts.p106b_dskdv2_bridge import teacher_logits
    from torch.nn import functional as F
    policy=p['policy'];model.zero_grad(set_to_none=True);projectors.zero_grad(set_to_none=True)
    torch.manual_seed(1337);gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
    model.zero_grad(set_to_none=True);projectors.zero_grad(set_to_none=True)
    torch.manual_seed(1337);gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize();tick=time.monotonic()
    block=dict(index=index,arm='DWA' if enabled else 'CE_ONLY',rows=[],raw_sums={},student_targets=0,teacher_targets=0)
    student_head=(model._emb_w().detach()@model._emb_up_w().detach().T) if enabled else None
    def student_embedding(ids):return F.linear(F.embedding(ids,model._emb_w()),model._emb_up_w())
    for row in rows:
        guard(start);native=row['packed']['student'];teacher=row['teacher'];ids=native['ids']
        x=torch.full((1,1024),0,dtype=torch.long,device='cuda')
        x[0,:len(ids)-1]=torch.tensor(ids[:-1],dtype=torch.long,device='cuda')
        with torch.autocast('cuda',dtype=torch.bfloat16):h=model(x,return_hidden=True)[0,:len(ids)-1]
        with torch.autocast('cuda',enabled=False):
            sv=boundary.predictor_view(torch,ids,native['supervised'],h.float(),student_embedding)
            sl=model._head_logits(sv.hidden)
            if enabled:
                th=torch.from_numpy(np.load(ROOT/features[row['row_id']]['path'],allow_pickle=False).copy()).to('cuda')
                tv=boundary.predictor_view(torch,teacher['ids'],teacher['supervised'],th,
                    lambda selected:F.embedding(selected,teacher_head))
                with torch.no_grad():tl=teacher_logits(tv.hidden,teacher_head)
                packet=cma.loss_components(torch,sv,tv,sl,tl,query=projectors['query'],t2s=projectors['t2s'],
                    s2t=projectors['s2t'],embedding_t2s=projectors['embedding_t2s'],
                    student_head=student_head,teacher_head=teacher_head,kd_gate_scale=policy['confidence_gate_scale'],
                    dtw=lambda cost:soft_dtw(cost.double().contiguous(),gamma=policy['gamma']),band=policy['band'])
                loss=boundary.streaming_share(packet,global_student_targets=772)
                raw={key:float(value.detach()) for key,value in packet['raw'].items()}
                teacher_count=tv.count
            else:
                ce=F.cross_entropy(sl,sv.targets,reduction='sum');loss=ce/772
                raw={'student_ce':float(ce.detach())};teacher_count=sum(teacher['supervised'][1:])
            if not bool(torch.isfinite(loss)):raise ValueError('nonfinite native row loss')
        loss.backward()
        block['rows'].append(dict(row_id=row['row_id'],student_count=sv.count,teacher_count=teacher_count,raw=raw))
        block['student_targets']+=sv.count;block['teacher_targets']+=teacher_count
        for key,value in raw.items():block['raw_sums'][key]=block['raw_sums'].get(key,0.)+value
        if teacher_head.grad is not None:raise ValueError('frozen original teacher head received gradient')
        del x,h,sv,sl,loss
        if enabled:del th,tv,tl,packet
    accounting=boundary.close_accounting(block['rows'],expected_ids=p['row_ids'],student_targets=772,teacher_targets=811)
    torch.cuda.synchronize();block['forward_backward_seconds']=time.monotonic()-tick
    block.update(accounting,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
    if max(block['peak_allocated_bytes'],block['peak_reserved_bytes'])>policy['allocator_peak_cap_bytes']:
        raise cma.AdmissionHold('native DWA allocator8GiB cap exceeded')
    block['gradient_SHA256'],block['gradient_norm']=gradients(torch,model,projectors,enabled)
    block['gradient_tensors']=len(block['gradient_SHA256'])
    return block

def actual():
    guard();start=time.monotonic();out=BASE/'actual';out.mkdir()
    model=teacher_head=projectors=torch=None;model_ref=None;p=None
    report=dict(schema='P106B_DWA_NATIVE_ZERO_UPDATE_ABBA_V1',authority_directive=158,status='INCOMPLETE',returncode=1,
        blocks=[],teacher_body_loads=0,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,
        corpus_admitted=False,closure_errors=[],model_load_attempted=False)
    try:
        with phase_alarm(1800):
            p,evidence=verify()
            if datetime.now(timezone.utc).timestamp()+1920>=CUTOFF.timestamp():raise TimeoutError('whole DWA phase no longer fits cutoff')
            from scripts.interactive_research_infer import require_idle_gpu,state_fingerprint
            report['GPU_idle_point']=require_idle_gpu()
            if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise ValueError('deterministic cuBLAS workspace must precede Torch')
            import torch
            torch.set_num_interop_threads(1);torch.set_num_threads(4)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.use_deterministic_algorithms(True);torch.set_float32_matmul_precision('highest')
            free,total=torch.cuda.mem_get_info();report['free_vram_point_bytes']=free
            if free<p['policy']['minimum_free_vram_bytes']:raise cma.AdmissionHold('native DWA needs free8GiB at admission')
            from scripts import diag_p106b_gsq_objective as loader
            report['model_load_attempted']=True
            torch,model,_manifest,entry,_spec=loader.load_cpu();torch.set_num_threads(4)
            model_ref=weakref.ref(model);before=state_fingerprint(model)
            if before!=entry['core_sha256']:raise ValueError('original native student state differs')
            model.cfg.grad_checkpoint=True;model.train();model.cuda()
            weight=next(item for name,item in p['teacher_assets'].items() if name.endswith('.safetensors'))
            from safetensors import safe_open
            with safe_open(weight['resolved_path'],framework='pt',device='cpu') as source:
                teacher_head=source.get_tensor(p['teacher_key']).float().to('cuda')
            if teacher_head.shape!=(248320,1024) or teacher_head.requires_grad:raise ValueError('full tied frozen teacher head required')
            with torch.random.fork_rng(devices=[]):
                torch.random.default_generator.manual_seed(1337)
                projectors=torch.nn.ModuleDict({name:torch.nn.Linear(a,b,bias=False) for name,a,b in (
                    ('query',1536,2048),('t2s',1024,768),('s2t',768,1024),('embedding_t2s',1024,768))})
            projector_before=state_fingerprint(projectors);projectors.cuda()
            report.update(student_initial_core_sha256=before,projector_initial_state_sha256=projector_before,
                teacher_head_bytes=teacher_head.numel()*teacher_head.element_size(),
                projector_parameters=sum(v.numel() for v in projectors.parameters()),
                startup_peak_allocated_bytes=torch.cuda.max_memory_allocated(),startup_peak_reserved_bytes=torch.cuda.max_memory_reserved())
            references={}
            for index,arm in enumerate(p['policy']['order']):
                block=run_block(torch,model,teacher_head,projectors,p,evidence['rows'],evidence['features'],arm=='DWA',index,start)
                block['student_core_unchanged']=state_fingerprint(model)==before
                block['projectors_unchanged']=state_fingerprint(projectors)==projector_before
                if arm in references:
                    old=references[arm]
                    different=[name for name,value in block['gradient_SHA256'].items() if old.get(name)!=value]
                    block['repeat_gradient_exact']=set(old)==set(block['gradient_SHA256']) and not different
                    block['repeat_different_gradient_tensors']=different
                else:references[arm]=block['gradient_SHA256'];block['repeat_gradient_exact']=None
                report['blocks'].append(block);write(out/('block_'+str(index)+'.json'),block)
                print('[DWA_NATIVE_BLOCK]'+json.dumps({key:block[key] for key in ('index','arm','forward_backward_seconds','student_targets','teacher_targets','gradient_tensors','gradient_norm','repeat_gradient_exact')},ensure_ascii=False),flush=True)
                if not block['student_core_unchanged'] or not block['projectors_unchanged']:
                    raise ValueError('zero-update original model/projector state changed')
                if block['repeat_gradient_exact'] is False:raise ValueError('same-arm native gradient repeat is not exact')
                if index<3:
                    forecast=max(item['forward_backward_seconds'] for item in report['blocks'])*(3-index)*1.5+60
                    report.setdefault('remaining_forecasts',[]).append(dict(after_block=index,seconds=forecast))
                    if time.monotonic()-start+forecast>=1800:raise cma.AdmissionHold('first full block forecasts beyond full ABBA budget')
            report.update(status='NATIVE_DWA_FULL128_ZERO_UPDATE_ABBA_COMPLETE',returncode=0,
                student_final_core_sha256=state_fingerprint(model),projector_final_state_sha256=state_fingerprint(projectors))
    except BaseException as error:
        report.update(status='NATIVE_DWA_HOLD' if isinstance(error,cma.AdmissionHold) else 'NATIVE_DWA_ERROR',
            returncode=8 if isinstance(error,cma.AdmissionHold) else 1,
            error=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        model=teacher_head=projectors=None;gc.collect()
        report['model_released']=model_ref is None or model_ref() is None
        if not report['model_released']:report['closure_errors'].append('owned student model retained')
        if torch is not None and torch.cuda.is_initialized():
            try:
                from scripts.diag_p106b_resource_matrix import close_cuda
                proof={};close_cuda(torch,proof=proof);report['final_cuda_cleanup']=proof
                if proof['allocated_bytes'] or proof['reserved_bytes']:raise RuntimeError('owned CUDA memory remains')
            except BaseException as error:report['closure_errors'].append(str(error))
        if p is not None:
            try:verify();report['sources_assets_inputs_unchanged']=True
            except BaseException as error:report['closure_errors'].append(str(error))
        if report['closure_errors']:report.update(status='NATIVE_DWA_CLOSURE_ERROR',returncode=9)
        report['remaining_blocks_NOT_RUN']=4-len(report['blocks']);report['wall_seconds']=time.monotonic()-start
        write(out/'report.json',report)
        print('[DWA_NATIVE_FINAL]'+json.dumps({key:report[key] for key in ('status','returncode','wall_seconds','remaining_blocks_NOT_RUN','model_released','closure_errors')},ensure_ascii=False),flush=True)
    return report['returncode']

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','check','actual'))
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='check':verify();print('[DWA_NATIVE_CHECK]frozen sources/closed cache/complete inputs matched;no model load')
    else:raise SystemExit(actual())

if __name__=='__main__':main()
