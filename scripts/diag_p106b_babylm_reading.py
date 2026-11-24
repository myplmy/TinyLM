"""Current-user161 full BabyLM reading predictions; official OLS stays NOT_RUN."""
from __future__ import annotations
import argparse,gc,json,math,os,signal,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import p106b_babylm_reading as core
from scripts import diag_p106b_babylm_semantics as base
prior,runtime=base.prior,base.runtime
TAG='p106b_babylm_reading_v1_20261117_s1337'
OUT=ROOT/'test_result/evidence'/TAG;PROFILE=OUT/'profile.json'
CUTOFF=datetime.fromisoformat('2026-11-18T16:30:00+09:00').timestamp()
HARD=1800;MAX_EVENTS=64_000_000
EXTRA=('scripts/p106b_babylm_reading.py','scripts/test_p106b_babylm_reading.py',
    'scripts/diag_p106b_babylm_reading.py','run_P106B_Stage8read1Wc_predictions.sh')
Hold=core.ReadingHold

def identity():
    files=dict(base.signature()['files'])
    for name in EXTRA:files[name]=prior.digest(ROOT/name)
    return dict(files=files,sha256=prior.object_sha(files))

def pairs_and_rows():
    rows=core.rows();pairs=[];seen={}
    for row in rows:
        for pair in ((row['context'],row['word']),row['previous']):
            if pair is not None and pair not in seen:seen[pair]=len(pairs);pairs.append(list(pair))
    return rows,pairs

class UniformTrace:
    def __init__(self,torch,vocab):self.value=torch.zeros((1,1,vocab),dtype=torch.float32);self.calls=0
    def __call__(self,**inputs):self.calls+=1;return(self.value,)

def prepare():
    cache=base.config();import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    if torch.cuda.is_initialized():raise ValueError('CPU reading sweep must not initialize CUDA')
    official,proof=core.load_official(torch,device='cpu')
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    token_path=ROOT/'data_cache/tok-ko-en-32768-chat32.json'
    pins={str(token_path.relative_to(ROOT)):prior.digest(token_path),
        str(core.READING.relative_to(ROOT)):prior.digest(core.READING)}
    manifest_path=core.ARCHIVE/'manifest.json';manifest=prior.read(manifest_path)
    pins[str(manifest_path.relative_to(ROOT))]=prior.digest(manifest_path)
    for item in manifest['files']:
        path=ROOT/item['local_path']
        if prior.digest(path)!=item['sha256']:raise ValueError('pinned original reading archive changed')
        pins[item['local_path']]=item['sha256']
    reference=prior.read(runtime.FALCON_REFERENCE)['asset_sha256']
    pins[str(runtime.FALCON_REFERENCE.relative_to(ROOT))]=prior.digest(runtime.FALCON_REFERENCE)
    for name,expected in reference.items():
        path=runtime.FALCON/name
        if prior.digest(path)!=expected:raise ValueError('existing Falcon asset differs')
        pins[str(path.relative_to(ROOT))]=expected
    tokenizers=dict(native=(Tokenizer.from_file(str(token_path)),True,32768),
        falcon=(AutoTokenizer.from_pretrained(str(runtime.FALCON),local_files_only=True,trust_remote_code=False),
            False,json.loads((runtime.FALCON/'config.json').read_text())['vocab_size']))
    rows,pairs=pairs_and_rows();sweeps={}
    for name,(tokenizer,is_native,vocab)in tokenizers.items():
        bridge=core.TokenizerBridge(tokenizer,torch,native=is_native,vocab=vocab)
        forward=UniformTrace(torch,vocab);seen={};total_positions=0;previous=0
        for row in rows:
            for pair in ((row['context'],row['word']),row['previous']):
                if pair is None:continue
                if pair==row['previous']:previous+=1
                value=core.evaluate(official,forward,bridge,*pair)
                total_positions+=value['native_positions']
                if pair in seen and seen[pair]!=value:raise ValueError('whole CPU cached/uncached trace differs')
                seen[pair]=value
        ordered=[seen[tuple(pair)]for pair in pairs]
        costs={i*(len(pairs)-1)//31 for i in range(32)}
        longest=max(range(len(pairs)),key=lambda i:max(len(r['prefix_ids'])for r in ordered[i]['trace']))
        most=max(range(len(pairs)),key=lambda i:ordered[i]['native_positions'])
        multi=max(range(len(pairs)),key=lambda i:len(ordered[i]['trace']))
        costs.update((longest,most,multi));indices=sorted(costs)
        sweeps[name]=dict(rows=len(rows),previous_rows=sum(r['previous']is not None for r in rows),
            unique_pairs=len(pairs),uncached_calls=forward.calls,
            unique_calls=sum(len(r['trace'])for r in ordered),
            uncached_positions=total_positions,unique_positions=sum(r['native_positions']for r in ordered),
            max_input_length=max(len(t['prefix_ids'])for r in ordered for t in r['trace']),
            pair_positions=[r['native_positions']for r in ordered],cost_indices=indices,
            cost_positions=sum(ordered[i]['native_positions']for i in indices),
            oracle_indices=list(dict.fromkeys((0,longest,multi))),uniform_full_source_cache_equivalence=True,
            context_cropping=0,excluded_rows=0,replacement_decode=0)
        print('READING_CPU_SWEEP',name,json.dumps({k:v for k,v in sweeps[name].items()
            if k not in ('pair_positions','cost_indices')}),flush=True)
    if torch.cuda.is_initialized():raise ValueError('reading CPU sweep initialized CUDA')
    profile=dict(schema='P106B_BABYLM_READING_PREDICTIONS_V1',user_directive=161,tag=TAG,
        UTC=datetime.now(timezone.utc).isoformat(),models=runtime.MODELS,sources=identity(),pins=pins,
        original_AST=proof,tokenizer_sweeps=sweeps,pairs=pairs,cache_policy=cache,
        policy=dict(rows=1726,source_item_missing='FILL_LITERAL_None_AS_ORIGINAL',
            original_default_special_tokens=True,manual_BOS=False,chat_template=False,truncation=0,
            exact_pair_cache='PER_FROZEN_MODEL_ONLY;SCALAR_AND_NATIVE_TRACE;NO_LOGITS_TENSORS',
            cache_gate='REAL_REPEATED_PAIR_FLOAT_PROBABILITY_EXACT',cost_selection='INPUT_ONLY32_PLUS_LONGEST_AND_MAX_POSITIONS_AND_MULTI',
            forecast_multiplier=1.5,forecast_reserve_seconds=120,per_model_seconds=HARD,cutoff=CUTOFF,
            allocated_cap_bytes=8*1024**3,event_cap_bytes=MAX_EVENTS,shard_bytes=10_000_000,
            official_reading_OLS='NOT_RUN;STATSMODELS_AND_PATSY_NOT_INSTALLED',formal_R2=False,
            models_frozen=True,training_updates=0,checkpoint_writes=0,package_install=0,new_environment=0),
        CPU_contracts=8,model_loads=0,GPU_calls=0)
    OUT.mkdir(parents=True,exist_ok=False);prior.write(PROFILE,profile)
    print('READING_PROFILE',prior.digest(PROFILE),profile['sources']['sha256'],flush=True)

def verify():
    p=prior.read(PROFILE)
    if p['sources']!=identity():raise ValueError('frozen reading source changed')
    for name,sha in p['pins'].items():
        if prior.digest(ROOT/name)!=sha:raise ValueError('frozen reading input changed: '+name)
    return p

def actual(model):
    profile=verify();started=time.perf_counter();cache_policy=base.config()
    if time.time()+HARD+60>CUTOFF:raise Hold('whole reading model hard interval does not fit')
    if model not in profile['models']:raise ValueError('unregistered frozen reading model')
    directory=OUT/model;directory.mkdir(exist_ok=False)
    report=dict(schema='P106B_READING_WORD_PREDICTIONS_V1',model=model,user_directive=161,status='STARTED',
        returncode=1,PID=os.getpid(),profile_sha256=prior.digest(PROFILE),source_sha256=profile['sources']['sha256'],
        training_updates=0,checkpoint_writes=0,formal_reading_OLS='NOT_RUN',cache_policy=cache_policy)
    import torch
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.manual_seed(1337)
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p106b_resource_matrix import close_cuda
    from scripts.diag_p106b_external_core6 import close_report
    from scripts.p106b_shards import ShardWriter
    forward=base_forward=tokenizer=lm=None;writer=None
    def check():
        if (OUT/'STOP').exists():raise Hold('reading owned STOP')
        if time.perf_counter()-started>HARD or time.time()>CUTOFF-30:raise Hold('reading wall/clock budget')
        if torch.cuda.memory_allocated()>8*1024**3:raise Hold('reading allocated8GiB cap')
    previous=signal.signal(signal.SIGINT,lambda _s,_f:(_ for _ in()).throw(Hold('owned reading signal')))
    try:
        report['GPU_entry']=require_idle_gpu();official,proof=core.load_official(torch,device='cuda')
        report['original_AST']=proof;rows,pairs=pairs_and_rows()
        if pairs!=profile['pairs']:raise ValueError('original complete pair order differs')
        sweep=profile['tokenizer_sweeps']['falcon'if model=='falcon90m'else'native']
        with runtime.model_runtime(model,torch)as(lm,model_proof):
            try:
                report['model_proof']=model_proof;base_forward=prior.FullLogits(lm,torch,check)
                forward=core.ReadingForward(base_forward)
                tokenizer=core.TokenizerBridge(lm.tokenizer,torch,native=hasattr(lm,'core'),vocab=base_forward.vocab)
                identity_key=prior.object_sha(dict(model=model,profile=report['profile_sha256'],
                    provenance=model_proof));cache=core.ExactPairCache(identity_key)
                from torch.nn.attention import sdpa_kernel,SDPBackend
                with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                    oracles=[];forward.capture=True
                    for index in sweep['oracle_indices']:
                        forward.last_logits=[];value=core.evaluate(official,forward,tokenizer,*pairs[index])
                        oracle=core.CE_oracle(value,forward,torch);oracle['pair_index']=index;oracles.append(oracle)
                    if not all(r['passed']for r in oracles):raise ValueError('real original reading/full-label CE oracle negative')
                    a=core.evaluate(official,forward,tokenizer,*pairs[0]);b=core.evaluate(official,forward,tokenizer,*pairs[1])
                    a2=core.evaluate(official,forward,tokenizer,*pairs[0])
                    if a!=a2:raise Hold('frozen repeated reading pair probability/trace differs')
                    report['real_oracles']=oracles;report['cache_repeat_exact']=True
                    forward.capture=False;forward.last_logits=[]
                    before_positions=base_forward.input_tokens;cost_start=time.perf_counter()
                    for index in sweep['cost_indices']:
                        pair=pairs[index];cache.get(identity_key,*pair,
                            lambda pair=pair:core.evaluate(official,forward,tokenizer,*pair))
                    cost_seconds=time.perf_counter()-cost_start
                    forecast=cost_seconds*sweep['unique_positions']/sweep['cost_positions']*1.5+120
                    remaining=min(HARD-(time.perf_counter()-started),CUTOFF-time.time()-30)
                    report['cost']=dict(seconds=cost_seconds,forecast_seconds=forecast,
                        source_positions=sweep['cost_positions'],full_unique_positions=sweep['unique_positions'])
                    if not math.isfinite(forecast)or forecast>remaining:raise Hold('whole1726 measured reading forecast exceeds budget')
                    print('READING_FORECAST',model,forecast,remaining,flush=True)
                    writer=ShardWriter(directory,'predictions',limit=10_000_000);event_bytes=0;prev_count=0
                    for row in rows:
                        check();pair=(row['context'],row['word'])
                        current,hit=cache.get(identity_key,*pair,
                            lambda pair=pair:core.evaluate(official,forward,tokenizer,*pair))
                        previous_value=prev_hit=None
                        if row['previous']is not None:
                            prev_count+=1;pair=row['previous']
                            previous_value,prev_hit=cache.get(identity_key,*pair,
                                lambda pair=pair:core.evaluate(official,forward,tokenizer,*pair))
                        event=dict(index=row['index'],context=row['context'],word=row['word'],target=current,
                            target_cache_hit=hit,previous_context_word=row['previous'],previous=previous_value,
                            previous_cache_hit=prev_hit,formal_OLS=False,missing_previous_as_None=True)
                        raw=(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
                        event_bytes+=len(raw)
                        if event_bytes>MAX_EVENTS:raise Hold('whole reading event storage cap')
                        writer.append(event)
                        if (row['index']+1)%256==0:print('READING_PROGRESS',model,row['index']+1,len(rows),flush=True)
                    manifest=writer.close(lineage=dict(model=model,source_csv=str(core.READING.relative_to(ROOT)),
                        source_sha256=profile['pins'][str(core.READING.relative_to(ROOT))],data_use='EVAL_ONLY_NOT_TRAIN',
                        formal_OLS='NOT_RUN'))
                    if (prev_count!=sweep['previous_rows']or len(cache.values)!=sweep['unique_pairs']
                            or base_forward.input_tokens-before_positions!=sweep['unique_positions']):
                        raise ValueError('full original denominator/unique native positions differ')
                    report.update(rows=len(rows),previous_rows=prev_count,unique_pairs=len(cache.values),
                        cache_hits=cache.hits,cache_misses=cache.misses,event_bytes=event_bytes,
                        prediction_manifest=manifest,all1726_complete=True,native_positions=base_forward.input_tokens-before_positions)
            finally:
                if base_forward is not None:base_forward.lm=None
                forward=base_forward=tokenizer=lm=None
        report.update(status='FULL_READING_WORD_PREDICTIONS_COMPLETE_OLS_NOT_RUN',returncode=0)
    except BaseException as exc:
        report.update(status='HOLD'if isinstance(exc,Hold)else'ERROR',returncode=8 if isinstance(exc,Hold)else 1,
            error=dict(type=type(exc).__name__,message=str(exc)[:2000]))
        print('READING_ERROR',report['error'],flush=True)
    finally:
        signal.signal(signal.SIGINT,previous)
        if base_forward is not None:base_forward.lm=None
        forward=base_forward=tokenizer=lm=None;gc.collect()
        if writer is not None and not writer.manifest_path.exists():
            if writer._total_rows:writer.close(lineage=dict(complete=False,data_use='EVAL_ONLY_NOT_TRAIN'))
            else:writer._finish()
        try:
            report['CUDA_close']=(close_cuda(torch)if torch.cuda.is_initialized()else
                dict(allocated_bytes=0,reserved_bytes=0,initialized=False))
            if report['CUDA_close']['allocated_bytes']or report['CUDA_close']['reserved_bytes']:
                raise ValueError('reading owned CUDA not fully released')
            report['owned_model_released']=True
        except BaseException as exc:report.update(status='CLOSURE_ERROR',returncode=9,cleanup_error=str(exc))
        try:verify();report['sources_and_inputs_unchanged']=True
        except BaseException as exc:report.update(status='SOURCE_EXIT_ERROR',returncode=9,source_exit_error=str(exc))
        report['wall_seconds']=time.perf_counter()-started
        close_report(directory/'report.json',report)
    print('READING_TERMINAL',model,report['status'],report['returncode'],report['wall_seconds'],flush=True)
    return report['returncode']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','check','actual'))
    parser.add_argument('--model',choices=runtime.MODELS);args=parser.parse_args()
    if args.action=='prepare':prepare();return 0
    if args.action=='check':print(json.dumps(identity()));return 0
    if not args.model:parser.error('--model required for actual')
    return actual(args.model)
if __name__=='__main__':raise SystemExit(main())

