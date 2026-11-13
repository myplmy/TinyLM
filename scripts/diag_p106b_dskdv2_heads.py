"""CPU native TinyLM head/VJP and real overlap projector initialization only."""
from datetime import datetime,timezone
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import resource
import time
import traceback
from scripts import p106b_dskdv2_contract as contract
from scripts import p106b_dskdv2_heads as heads
from scripts import diag_p106b_gsq_objective as loader
from scripts import diag_p106b_qwen35_text_core6 as q
from scripts import interactive_research_infer as manual

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'test_result/evidence/p106b_dskdv2_heads_v1_20261113'
DATA=ROOT/'test_result/evidence/p106b_dskdv2_contract_v1_20261113'
MAP=ROOT/'test_result/evidence/p106b_actd_anchor_v1_20261113'
QUALIFIED=ROOT/'test_result/evidence/p106b_qwen35_fixedshape_v1_20261113'
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SOURCES=('scripts/p106b_dskdv2_heads.py','scripts/test_p106b_dskdv2_heads.py',
    'scripts/diag_p106b_dskdv2_heads.py','scripts/p106b_dskdv2_contract.py',
    'scripts/diag_p106b_gsq_objective.py','scripts/interactive_research_infer.py',
    'scripts/diag_p106b_qwen35_text_core6.py','tinylm/model/transformer.py')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
read=lambda p:json.loads(p.read_text())


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8')as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+chr(10))


def run():
    start=time.perf_counter()
    if (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:raise TimeoutError('authority reserve')
    if BASE.exists():raise FileExistsError('fresh CPU head namespace required')
    p=read(DATA/'profile.json');receipt=read(DATA/'ROOT_CPU_EXIT_v1.json')
    if receipt.get('actual_process_exit_code')!=0 or receipt.get('profile_sha256')!=sha(DATA/'profile.json'):
        raise ValueError('closed exact byte CPU contract required')
    qualified=read(QUALIFIED/'profile.json');qr=read(QUALIFIED/'ROOT_CANARY_EXIT_v1.json')
    if qr.get('actual_process_exit_code')!=0 or qr.get('report_sha256')!=sha(QUALIFIED/'canary/report.json'):
        raise ValueError('original teacher runtime canary proof required')
    q.verify_pins(qualified['sources']);assets=q.asset_identity()
    if assets!=qualified['assets']:raise ValueError('same exact teacher assets required')
    old=read(MAP/'report.json');old_profile=read(MAP/'profile.json')
    if old.get('sources_unchanged')is not True or old.get('profile_sha256')!=sha(MAP/'profile.json'):
        raise ValueError('original exact byte mapping provenance required')
    for artifact in old['artifacts']:
        if sha(MAP/artifact['path'])!=artifact['sha256']:raise ValueError('original mapping artifact changed')
    anchors=read(MAP/'teacher_to_student_anchors.json');modes=read(MAP/'teacher_mapping_modes.json')
    tids=[i for i,mode in enumerate(modes) if mode==1];sids=[anchors[i] for i in tids]
    if len(tids)!=23302 or len(anchors)!=248320 or any(type(i)is not int or not 0<=i<32768 for i in sids):
        raise ValueError('all and only exact ordinary shared-byte columns required')
    teacher_metadata=read(Path(assets['files']['config.json']['resolved_path']))
    if teacher_metadata.get('tie_word_embeddings')is not True:raise ValueError('qualified tied teacher head required')
    keys=[k for k,v in assets['inventory']['language'].items() if k.endswith('embed_tokens.weight') and v['shape']==[248320,1024]]
    if len(keys)!=1:raise ValueError('one exact native tied teacher head key required')
    references={str(x.relative_to(ROOT)):sha(x) for x in
        [DATA/'profile.json',DATA/'ROOT_CPU_EXIT_v1.json',MAP/'profile.json',MAP/'report.json',
         MAP/'teacher_to_student_anchors.json',MAP/'teacher_mapping_modes.json',QUALIFIED/'profile.json',
         QUALIFIED/'canary/report.json',QUALIFIED/'ROOT_CANARY_EXIT_v1.json']}
    profile=dict(schema='P106B_DSKDV2_NATIVE_HEAD_CPU_V1',tag=BASE.name,authority_directive=115,deadline=DEADLINE.isoformat(),
        sources={name:sha(ROOT/name) for name in SOURCES},references=references,teacher_assets=assets,
        overlap_columns=len(tids),ordinary_exact_only=True,teacher_key=keys[0],student_checkpoint=p['original_student_checkpoint'],
        teacher_model_loading=False,student_model_loading='GUARDED_CPU_HEAD_ONLY',body_forwards=0,
        feature_seed=61113,feature_shape=[4,768],precision='CPU_FP32_NATIVE_HEAD_CPU_FP64_INITIALIZER',
        cpu_threads=4,gpu=False,optimizer_updates=0,checkpoint_writes=0,
        runtime_versions={n:importlib.metadata.version(n) for n in ('torch','safetensors')},quality_claim=False)
    write(BASE/'profile.json',profile)
    model=up=emb=teacher_rows=s=t=init=h=a=b=ga=gb=None;failure=None
    report=dict(schema=profile['schema'],tag=BASE.name,status='RUNNING',profile_sha256=sha(BASE/'profile.json'),body_forwards=0,
        teacher_models=0,gpu_calls=0,optimizer_updates=0,checkpoint_writes=0,quality_claim=False)
    try:
        torch,model,manifest,entry,spec=loader.load_cpu();torch.set_num_threads(4);model.eval()
        report['student_models_loaded_cpu']=1
        if str(spec.checkpoint)!=p['original_student_checkpoint']:raise ValueError('same completed93M native checkpoint required')
        if model.embedding_quantized()is not None or model.emb_up is None:
            raise ValueError('this diagnostic requires the inspected native unexported factored head')
        up=model._emb_up_w();emb=model._emb_w()
        if up.shape!=(768,256) or emb.shape!=(32768,256):raise ValueError('actual native head shape changed')
        generator=torch.Generator(device='cpu').manual_seed(61113)
        h=torch.randn(4,768,generator=generator,dtype=torch.float32,requires_grad=True)
        cotangent=torch.randn(4,32768,generator=generator,dtype=torch.float32)/32768
        from torch.nn import functional as F
        a=model._head_logits(h);b=F.linear(F.linear(h,up.detach().T),emb.detach())
        ga=torch.autograd.grad((a*cotangent).sum(),h)[0]
        gb=torch.autograd.grad((b*cotangent).sum(),h)[0]
        report['head_primal_exact']=torch.equal(a,b);report['hidden_vjp_exact']=torch.equal(ga,gb)
        report['head_primal_max_abs']=float((a.detach()-b.detach()).abs().max());report['hidden_vjp_max_abs']=float((ga-gb).abs().max())
        if not report['head_primal_exact'] or not report['hidden_vjp_exact']:raise ValueError('native CPU FP32 head operator/VJP changed')
        if any(param.grad is not None for param in model.parameters()):raise ValueError('head-only VJP accumulated master gradients')
        report['student_core_unchanged']=manual.state_fingerprint(model)==entry['core_sha256']
        if not report['student_core_unchanged']:raise ValueError('actual native student core changed')
        t0=time.perf_counter()
        s=up.detach().double()@emb.detach().index_select(0,torch.tensor(sids)).double().T
        from safetensors import safe_open
        with safe_open(assets['files'][q.WEIGHT]['resolved_path'],framework='pt',device='cpu')as source:
            teacher_rows=heads.gather_rows(source.get_slice(keys[0]),tids,rows=248320,width=1024)
        t=teacher_rows.T.double();report['head_extraction_seconds']=time.perf_counter()-t0
        t0=time.perf_counter();init=contract.initialize_projectors(s,t,rtol=1e-8)
        report['initialization_seconds']=time.perf_counter()-t0;report['initialization']=init['stats']
        report['student_overlap_shape']=list(s.shape);report['teacher_overlap_shape']=list(t.shape)
        report['student_overlap_duplicate_ids']=len(sids)-len(set(sids))
        write(BASE/'overlap_ids.json',dict(teacher_ids=tids,student_ids=sids,mapping_mode=1))
        if time.perf_counter()-start>900:raise TimeoutError('CPU head phase budget')
        for name,digest in dict(profile['sources'],**references).items():
            if sha(ROOT/name)!=digest:raise ValueError('pinned source/metadata changed: '+name)
        if q.asset_identity()!=assets:raise ValueError('original teacher files changed')
        if sha(ROOT/spec.checkpoint)!=entry['checkpoint']['sha256']:raise ValueError('original student file changed')
        if torch.cuda.is_initialized():raise RuntimeError('CPU diagnostic initialized CUDA')
        report.update(status='CPU_NATIVE_HEAD_VJP_AND_INITIALIZATION_COMPLETE',original_files_unchanged=True,
            cuda_initialized=False,actual_teacher_hidden_collected=False,gpu_bf16_native_vjp_verified=False,
            full_dskdv2_training_ready=False)
    except BaseException as exc:
        traceback.print_exc();failure=exc;report.update(status='ERROR',error=repr(exc))
    finally:
        model=up=emb=teacher_rows=s=t=init=h=a=b=ga=gb=None;gc.collect()
        report.update(seconds=time.perf_counter()-start,peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        write(BASE/'report.json',report)
    if failure is not None:raise failure
    print('[DSKDV2_HEAD_CPU_FINAL] '+json.dumps({k:report[k] for k in
        ('status','seconds','head_primal_exact','hidden_vjp_exact','initialization')}),flush=True)


if __name__=='__main__':run()
