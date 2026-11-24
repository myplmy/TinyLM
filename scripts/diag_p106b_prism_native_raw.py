"""User161 existing Prism raw-logit canary; prepare/check never load a model."""
from __future__ import annotations
import argparse,hashlib,json,math,os,signal,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import p106b_prism_native as native
TAG='p106b_prism_native_raw_v1_20261117'
OUT=ROOT/'test_result/evidence'/TAG;PROFILE=OUT/'profile.json'
AUDIT=ROOT/'handoff/audit/research_20261118_01a1e647'
ASSETS=ROOT/'test_result/evidence/p106b_bonsai2b_prism_assets_v1_20261117/report.json'
OLD=ROOT/'test_result/evidence/p106b_bonsai2b_prism_canary_v1_20261117/actual'
CUTOFF=datetime.fromisoformat('2026-11-18T16:30:00+09:00').timestamp()
HARD=1200
SOURCES=('scripts/p106b_prism_native.py','scripts/p106b_prism_abi_layout.c',
    'scripts/test_p106b_prism_native.py','scripts/diag_p106b_prism_native_raw.py',
    'run_P106B_Stage8pr2Wc_native_raw.sh','scripts/interactive_research_infer.py')

class Hold(ValueError):pass

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest().upper()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path,value):
    raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True)+'\n').encode()
    if len(raw)>=20_000_000:raise ValueError('metadata 20MB cap')
    with Path(path).open('xb')as f:f.write(raw)

def identity():return {name:digest(ROOT/name)for name in SOURCES}

def verify():
    profile=read(PROFILE)
    if identity()!=profile['sources']:raise ValueError('frozen native source changed')
    for name,sha in profile['pins'].items():
        path=Path(name)if Path(name).is_absolute()else ROOT/name
        if digest(path)!=sha:raise ValueError('frozen native input changed: '+name)
    for name,target in profile['runtime_symlinks'].items():
        if not Path(name).is_symlink()or os.readlink(name)!=target:raise ValueError('runtime alias changed')
    return profile

def stored_http(profile):
    values=np.full(profile['vocab'],np.nan,dtype=np.float64);ordered=[]
    manifest=read(OLD/'full_distribution_shards_manifest.json')
    for shard in manifest['shards']:
        for line in (OLD/shard['path']).open(encoding='utf-8'):
            row=json.loads(line);index=row['id']
            if type(index)is not int or not 0<=index<len(values)or not math.isnan(float(values[index])):
                raise ValueError('complete unique old HTTP native IDs required')
            values[index]=float(row['logprob']);ordered.append(index)
    if len(ordered)!=len(values)or not np.isfinite(values).all():raise ValueError('old HTTP coverage differs')
    return values,ordered

def prepare():
    if PROFILE.exists():raise FileExistsError('new native profile already exists')
    assets=read(ASSETS);old_profile=read(OLD.parent/'profile.json')
    if digest(ASSETS)!=old_profile['assets_receipt_sha256']:raise ValueError('closed asset receipt changed')
    bundle=Path(assets['bundle']);pins={str(ASSETS.relative_to(ROOT)):digest(ASSETS),
        str((OLD.parent/'profile.json').relative_to(ROOT)):digest(OLD.parent/'profile.json'),
        assets['model']:assets['model_sha256']}
    if digest(ROOT/assets['model'])!=assets['model_sha256']:raise ValueError('exact existing model differs')
    for name,item in assets['runtime_files'].items():
        path=bundle/name
        if path.stat().st_size!=item['bytes']or digest(path)!=item['sha256']:raise ValueError('existing runtime differs')
        pins[str(path)]=item['sha256']
    aliases={}
    for path in sorted(bundle.iterdir()):
        if path.is_symlink():
            if path.resolve().parent!=bundle:raise ValueError('runtime alias leaves exact bundle')
            aliases[str(path)]=os.readlink(path)
        elif path.is_file()and path.name.startswith('libggml')and '.so' in path.name:
            pins[str(path)]=digest(path)
    manifest=read(OLD/'full_distribution_shards_manifest.json')
    for name in ('full_distribution_shards_manifest.json','tokenization_A.json','tokenization_B.json'):
        pins[str((OLD/name).relative_to(ROOT))]=digest(OLD/name)
    for shard in manifest['shards']:
        path=OLD/shard['path']
        if digest(path)!=shard['sha256']:raise ValueError('original full probability shard differs')
        pins[str(path.relative_to(ROOT))]=shard['sha256']
    probe=OUT/'abi/probe'
    result=subprocess.run([str(probe)],capture_output=True,text=True,check=True,timeout=5)
    observed={}
    for line in result.stdout.splitlines():
        cells=line.split()
        if cells[0]=='STRUCT':observed[cells[1]]=dict(size=int(cells[2]),alignment=int(cells[3]),fields={})
        elif cells[0]=='FIELD':observed[cells[1]]['fields'][cells[2]]=int(cells[3])
        else:raise ValueError('unknown layout output')
    if observed!=native.layout():raise ValueError('primary C/ctypes ABI layout differs')
    pins[str(probe.relative_to(ROOT))]=digest(probe)
    test=ROOT/'test_result/101_log_20261117_P106B_Stage8pr2Wb1_native_cpu_contracts.txt'
    text=test.read_text()
    if 'Ran 8 tests'not in text or '\nOK\n'not in text or '[runlog] 종료코드 0'not in text:
        raise ValueError('exact current CPU8 receipt required')
    pins[str(test.relative_to(ROOT))]=digest(test)
    profile=dict(schema='P106B_PRISM_NATIVE_RAW_V1',user_directive=161,UTC=datetime.now(timezone.utc).isoformat(),
        cutoff=CUTOFF,hard_seconds=HARD,bundle=str(bundle),model=assets['model'],vocab=248320,
        sources=identity(),pins=pins,runtime_symlinks=aliases,ABI=observed,CPU_tests=8,
        primary_commit=native.COMMIT,primary_header_blob=native.HEADER_BLOB,
        acquisition='READ_PRIMARY_DECLARATIONS_ONLY;NO_NEW_HEADER_PACKAGE_LIBRARY_OR_ENVIRONMENT',
        prompts=dict(A=read(OLD/'tokenization_A.json'),B=read(OLD/'tokenization_B.json')),
        policy=dict(raw_FP32_vectors=['A0','B','A1'],context=1024,n_batch=512,n_ubatch=512,threads=4,
            flash_attention=0,offload='ALL',memory_clear_data=True,template=False,manual_BOS=False,
            native_special_policy='EXACT_OLD_PLAIN_AND_NATIVE_IDS',max_output_bytes=64_000_000,
            minimum_free_bytes=8*1024**3,logprob_atol=1e-5,logprob_rtol=1e-4,
            HTTP_original_mass_atol=.0005,HTTP_invalid_scores_used_for_benchmark=False,
            old_HTTP_comparison='DIAGNOSTIC_ONLY;NORMAL_FLOAT32_PROBABILITY_MASK;ALL_OTHERS_COUNTED',
            partial_or_missing_raw_logits='HOLD',formal_benchmark=False,training_steps=0,checkpoint_writes=0))
    write(PROFILE,profile)
    print('NATIVE_PROFILE',digest(PROFILE),'pins',len(pins),'sources',len(profile['sources']),flush=True)

def guard(start=None):
    if time.time()>=CUTOFF-30 or (OUT/'STOP').exists():raise Hold('native current cutoff or owned STOP')
    if start is not None and time.monotonic()-start>HARD-90:raise Hold('native compute budget')

def worker():
    profile=verify();directory=OUT/'actual';directory.mkdir(exist_ok=False)
    started=time.monotonic()
    report=dict(schema='P106B_PRISM_NATIVE_RAW_WORKER_V1',status='STARTED',returncode=1,user_directive=161,
        PID=os.getpid(),profile_sha256=digest(PROFILE),vectors={},model_load_attempted=False,
        training_steps=0,checkpoint_writes=0,formal_benchmark=False,raw_HTTP_gate='ORIGINAL_HOLD8_PRESERVED')
    model=None
    def interrupt(_s,_f):raise Hold('owned native signal')
    previous=signal.signal(signal.SIGINT,interrupt)
    try:
        guard(started)
        from scripts.interactive_research_infer import require_idle_gpu
        report['GPU_entry']=require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
            capture_output=True,text=True,check=True,timeout=10)
        report['free_vram_point_bytes']=int(free.stdout.strip())*1024**2
        if report['free_vram_point_bytes']<profile['policy']['minimum_free_bytes']:raise Hold('native free8GiB point gate')
        old_logp,old_order=stored_http(profile)
        fixed_targets=[old_order[i]for i in (0,7,profile['vocab']//2)]
        model=native.NativeModel(profile['bundle'],ROOT/profile['model'],check=lambda:guard(started))
        with model:
            report['model_load_attempted']=model.model_load_attempted;report['binary_default_fields']=model.defaults
            for name,tokenization in profile['prompts'].items():
                for key,special in (('plain_ids',False),('native_ids',True)):
                    ids=model.tokenize(tokenization['text'],add_special=special)
                    if ids!=tokenization[key]:raise ValueError('native old/new prompt tokenizer differs')
                pieces=b''.join(model.piece(i)for i in tokenization['plain_ids'])
                if pieces!=tokenization['text'].encode():raise ValueError('native plain UTF8 roundtrip differs')
            all_logits={};all_logp={}
            for label,key in (('A0','A'),('B','B'),('A1','A')):
                guard(started);tick=time.monotonic();ids=profile['prompts'][key]['native_ids']
                logits=model.logits(ids);logp=native.log_probabilities(logits)
                maximum=max(float(x)for x in logits)
                z=maximum+math.log(math.fsum(math.exp(float(x)-maximum)for x in logits))
                oracle=logits.astype(np.float64)-z
                error=float(np.max(np.abs(logp-oracle)))
                mass=math.fsum(math.exp(float(x))for x in logp)
                if error>1e-10 or abs(mass-1)>1e-12:raise ValueError('independent full FP64 normalizer differs')
                path=directory/(label+'_logits_fp32.npy')
                with path.open('xb')as f:np.save(f,logits,allow_pickle=False)
                all_logits[label]=logits;all_logp[label]=logp
                report['vectors'][label]=dict(path=str(path.relative_to(ROOT)),sha256=digest(path),
                    bytes=path.stat().st_size,ids=ids,rows=len(logits),dtype='float32',mass=mass,
                    max_logprob_oracle_difference=error,greedy_token=int(np.argmax(logits)),
                    fixed_targets=[dict(id=target,logit=float(logits[target]),logprob=float(logp[target]))for target in fixed_targets],
                    wall_seconds=time.monotonic()-tick)
                print('RAW_VECTOR',label,len(logits),mass,error,report['vectors'][label]['wall_seconds'],flush=True)
            same=bool(np.allclose(all_logp['A0'],all_logp['A1'],atol=1e-5,rtol=1e-4))
            report['state_isolation']=dict(A_B_A_passed=same,
                raw_bits_equal=bool(np.array_equal(all_logits['A0'].view(np.uint32),all_logits['A1'].view(np.uint32))),
                max_raw_difference=float(np.max(np.abs(all_logits['A0']-all_logits['A1']))),
                max_logprob_difference=float(np.max(np.abs(all_logp['A0']-all_logp['A1']))))
            if not same:raise Hold('native A/B/A logprob state isolation negative')
            normal=old_logp>=math.log(np.finfo(np.float32).tiny)
            differences=old_logp[normal]-all_logp['A0'][normal]
            offset=math.log(math.fsum(math.exp(float(x))for x in old_logp))
            report['HTTP_diagnostic']=dict(normal_probability_rows=int(normal.sum()),
                subnormal_or_sentinel_rows=int((~normal).sum()),expected_log_mass_offset=offset,
                difference_min=float(differences.min()),difference_max=float(differences.max()),
                difference_mean=float(differences.mean()),max_offset_residual=float(np.max(np.abs(differences-offset))),
                original_greedy=old_order[0],native_greedy=int(np.argmax(all_logits['A0'])),
                formal_scores_from_HTTP=0,source_cause='INFERENCE_FROM_SAME_VECTOR_AND_CONSTANT_OFFSET_NOT_FORMAL_BENCHMARK')
            report['native_calls']=model.calls;report['native_memory_clears']=model.clears
            report['native_processed_tokens']=model.processed_tokens
        report['native_owned_handles_closed']=not model.model and not model.context and not model.backend
        report.update(status='NATIVE_RAW_LOGITS_CANARY_COMPLETE',returncode=0)
    except BaseException as exc:
        report.update(status='NATIVE_HOLD'if isinstance(exc,Hold)else'NATIVE_ERROR',
            returncode=8 if isinstance(exc,Hold)else 1,error=dict(type=type(exc).__name__,message=str(exc)[:2000]))
        print('NATIVE_ERROR',report['error'],flush=True)
    finally:
        signal.signal(signal.SIGINT,previous)
        if model is not None:
            model.close();report['model_load_attempted']=model.model_load_attempted
            report['backend_was_initialized']=model.backend_was_initialized
        try:verify();report['frozen_files_unchanged']=True
        except BaseException as exc:report.update(returncode=9,status='SOURCE_EXIT_ERROR',source_exit_error=str(exc))
        report['wall_seconds']=time.monotonic()-started
        report['opaque_internal_weight_fingerprint']='NOT_AVAILABLE;SOURCE_FILES_AND_A_B_A_ARE_SEPARATE_EVIDENCE'
        write(directory/'report.json',report)
    return report['returncode']

def actual():
    profile=verify()
    if time.time()+HARD+120>CUTOFF:raise Hold('native whole current interval does not fit')
    from scripts.interactive_research_infer import require_idle_gpu
    before=require_idle_gpu();started=time.monotonic();child=None;closure_errors=[]
    env=dict(os.environ)
    for key in list(env):
        if key.startswith(('LLAMA_ARG_','GGML_')):env.pop(key)
    env.update(LD_LIBRARY_PATH=profile['bundle'],CUDA_CACHE_DISABLE='1')
    result=dict(schema='P106B_PRISM_NATIVE_RAW_PARENT_V1',user_directive=161,profile_sha256=digest(PROFILE),
        GPU_entry=before,formal_benchmark=False,training_steps=0)
    try:
        child=subprocess.Popen([sys.executable,'-B','-u','-m','scripts.diag_p106b_prism_native_raw','worker'],
            cwd=ROOT,env=env,start_new_session=True)
        result['owned_child_pid']=child.pid
        try:code=child.wait(timeout=HARD)
        except subprocess.TimeoutExpired:
            if child.poll()is None and os.getpgid(child.pid)==child.pid:os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if child.poll()is None and os.getpgid(child.pid)==child.pid:os.killpg(child.pid,signal.SIGKILL)
                child.wait(timeout=10)
            code=124
        result['child_returncode']=code
    finally:
        if child is not None and child.poll()is None:
            if os.getpgid(child.pid)==child.pid:os.killpg(child.pid,signal.SIGTERM)
            child.wait(timeout=30)
        try:result['GPU_exit']=require_idle_gpu()
        except BaseException as exc:closure_errors.append(str(exc))
        try:verify();result['frozen_files_unchanged']=True
        except BaseException as exc:closure_errors.append(str(exc))
        result.update(closure_errors=closure_errors,wall_seconds=time.monotonic()-started)
        result['returncode']=9 if closure_errors else result.get('child_returncode',1)
        result['owned_child_reaped']=child is not None and child.poll()is not None
        result['resource_scope']='NATIVE_HANDLES_AND_REAPED_PID_NVML_POINT;NOT_TORCH_ALLOCATOR_OR_CONTINUOUS_PEAK'
        write(OUT/'parent_report.json',result)
    print('NATIVE_PARENT',result['returncode'],result['wall_seconds'],flush=True)
    return result['returncode']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','check','actual','worker'));args=parser.parse_args()
    if args.action=='check':print(json.dumps(identity()));return 0
    if args.action=='prepare':prepare();return 0
    return actual()if args.action=='actual'else worker()

if __name__=='__main__':raise SystemExit(main())

