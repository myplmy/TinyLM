"""Existing BabyLM COMPS/entity full-file evaluation; current user158 window.

No acquisition or training. Only explicit actual loads one existing model.
Old expired execute/controller functions are never called or rebound.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc,hashlib,json,math,os,signal,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_babylm_causal as prior
from scripts import diag_p106b_official_core6 as runtime
from scripts import p106b_babylm_semantics as core

TAG='p106b_babylm_semantics_v1_20261117_s1337'
OUT=ROOT/'test_result/evidence'/TAG
AUDIT=ROOT/'handoff/audit/research_20261117_01a1e647'
INTAKE=AUDIT/'BABYLM_CURRENT_LOCAL_INTAKE_v1.json'
PROFILE=OUT/'profile.json'
CUTOFF=datetime.fromisoformat('2026-11-17T16:40:00+09:00').timestamp()
HARD=1800
MAX_EVENTS=512_000_000
EXTRA=('scripts/diag_p106b_babylm_semantics.py','scripts/test_diag_p106b_babylm_semantics.py',
    'scripts/p106b_babylm_semantics.py','scripts/test_p106b_babylm_semantics.py',
    'scripts/diag_p106b_resource_matrix.py','scripts/diag_p106b_external_core6.py',
    'scripts/test_p106b_official_lm_adapter.py')

class Hold(ValueError):pass

def signature():
    files=dict(prior.identity()['files'])
    for name in EXTRA:files[name]=prior.digest(ROOT/name)
    return dict(files=files,sha256=prior.object_sha(files))

def config():
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    value=configure_hf_cache()
    for key,val in runtime.OFFLINE.items():os.environ[key]=val
    os.environ['TOKENIZERS_PARALLELISM']='false'
    return value

def verify_inputs():
    intake=prior.read(INTAKE);pins={str(INTAKE.relative_to(ROOT)):prior.digest(INTAKE)}
    if intake['total_decoded_rows']!=97808 or len(intake['files'])!=7:
        raise ValueError('complete existing seven-file intake required')
    for name,expected in prior.PINNED.items():
        if prior.digest(ROOT/name)!=expected:raise ValueError('original source/data/license manifest differs')
        pins[name]=expected
    for name,(expected,_nodes) in __import__('scripts.p106b_babylm_causal',fromlist=['FILES']).FILES.items():
        path=prior.SOURCE/name
        if prior.digest(path)!=expected:raise ValueError('official original source differs')
        pins[str(path.relative_to(ROOT))]=expected
    for spec in intake['files']:
        path=ROOT/spec['path']
        if prior.digest(path)!=spec['sha256'] or path.stat().st_size!=spec['bytes']:
            raise ValueError('whole evaluation-only file identity differs')
        pins[spec['path']]=spec['sha256']
    return intake,pins

def records(spec,official):
    kept=0
    with (ROOT/spec['path']).open(encoding='utf-8') as stream:
        for line_no,line in enumerate(stream,1):
            raw=json.loads(line)
            for decoded in core.decode(official,spec['task'],raw,Path(spec['path']).name):
                # Cluster definition is input-only and sealed before model outputs.
                cluster=(['COMPS_PROPERTY',raw['property']] if spec['task']=='comps'
                    else ['ENTITY_FILE_SAMPLE_ID',Path(spec['path']).name,raw['sample_id']])
                yield dict(decoded=decoded,trace=dict(file=spec['path'],raw_line=line_no,
                    kept_index=kept,cluster=cluster,source_id=raw.get('id',raw.get('example_id'))))
                kept+=1
    if kept!=spec['decoded_rows']:raise ValueError('official decoder full count differs')

def selected_indices(count):
    if type(count)is not int or count<1:raise ValueError('positive source count required')
    return {i*(count-1)//31 for i in range(32)}

def padded_positions(chunk,items):
    return sum(len(chunk)*max(len(item[1]['sentence_'+str(j)+'_tokens'])-1 for item in items)
        for j in range(len(chunk[0]['decoded']['sentences'])))

def tokenizer_sweep(official,processor,spec):
    candidates=selected_indices(spec['decoded_rows']);first_uid=set()
    all_lengths=[];longest=(-1,-1);counts=Counter();native=0
    for record in records(spec,official):
        decoded=record['decoded'];idx=record['trace']['kept_index'];uid=decoded['UID']
        if uid not in first_uid:first_uid.add(uid);candidates.add(idx)
        item=core.processed_item(official,processor,decoded)
        lengths=[len(item[1]['sentence_'+str(j)+'_tokens'])-1 for j in range(len(decoded['sentences']))]
        native+=sum(lengths);all_lengths.append(lengths);counts[uid]+=1
        if max(lengths)>longest[0]:longest=(max(lengths),idx)
    candidates.add(longest[1]);chosen=sorted(candidates)
    def positions(indices):
        values=[all_lengths[i] for i in indices]
        return sum(len(batch)*sum(max(row[j] for row in batch) for j in range(len(batch[0])))
            for start in range(0,len(values),8) if (batch:=values[start:start+8]))
    if dict(counts)!=spec['by_UID']:raise ValueError('whole UID preflight denominator differs')
    return dict(rows=len(all_lengths),by_UID=dict(counts),max_input_length=longest[0],longest_index=longest[1],
        native_input_positions=native,padded_input_positions=positions(range(len(all_lengths))),
        cost_indices=chosen,cost_padded_input_positions=positions(chosen),
        cost_selection='32 evenly spaced plus first per UID plus first native maximum;input only',
        truncations=0,additional_exclusions=0)

def prepare():
    cache=config();import torch
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    if torch.cuda.is_initialized():raise ValueError('CPU preflight must not initialize CUDA')
    intake,pins=verify_inputs()
    if prior.digest(runtime.CANARY)!=runtime.CANARY_SHA:raise ValueError('historical receipt itself changed')
    old_canary=prior.read(runtime.CANARY)
    if old_canary.get('status')!='OFFICIAL_ADAPTER_GPU_ORACLE_COMPLETE' or old_canary.get('returncode')!=0:
        raise ValueError('historical receipt must retain its original status')
    drift={name:dict(historical=sha,current=prior.digest(ROOT/name))
        for name,sha in old_canary['source_sha256'].items() if prior.digest(ROOT/name)!=sha}
    pre=dict(historical_receipt=str(runtime.CANARY.relative_to(ROOT)),historical_sha256=runtime.CANARY_SHA,
        historical_receipt_is_not_current_admission=bool(drift),historical_source_drift=drift,
        current_admission='CURRENT_SOURCE_PINS_AND_CPU_CONTRACTS_PLUS_MANDATORY_NEW_REAL_MODEL_ORACLES_BEFORE_COST_OR_FULL')
    official,proof=core.load_official(prior.SOURCE,torch,device='cpu')
    from scripts.p106b_babylm_causal import TextProcessor
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    native_path=ROOT/'data_cache/tok-ko-en-32768-chat32.json'
    pins[str(native_path.relative_to(ROOT))]=prior.digest(native_path)
    reference=prior.read(runtime.FALCON_REFERENCE)['asset_sha256']
    for name,expected in reference.items():
        path=runtime.FALCON/name
        if prior.digest(path)!=expected:raise ValueError('existing Falcon assets differ')
        pins[str(path.relative_to(ROOT))]=expected
    tokenizers=dict(native=(Tokenizer.from_file(str(native_path)),True,32768),
        falcon=(AutoTokenizer.from_pretrained(str(runtime.FALCON),local_files_only=True,
            trust_remote_code=False),False,json.loads((runtime.FALCON/'config.json').read_text())['vocab_size']))
    sweeps={}
    for name,(tok,is_native,vocab) in tokenizers.items():
        processor=TextProcessor(tok,native=is_native,vocab=vocab);sweeps[name]={}
        for spec in intake['files']:
            result=tokenizer_sweep(official,processor,spec)
            sweeps[name][Path(spec['path']).stem]=result
            print('CPU_SWEEP',name,Path(spec['path']).name,result['rows'],result['max_input_length'],flush=True)
    if torch.cuda.is_initialized():raise ValueError('CPU prepare unexpectedly initialized CUDA')
    profile=dict(schema='P106B_BABYLM_SEMANTICS_V1',tag=TAG,UTC=datetime.now(timezone.utc).isoformat(),
        user_directive=158,models=runtime.MODELS,files=intake['files'],pins=pins,
        sources=signature(),prerequisites=pre,official_AST=proof,tokenizer_sweeps=sweeps,cache_policy=cache,
        policy=dict(all_decoded_rows=97808,original_raw_rows=100511,author_skipped_rows=2703,
            task_order=['entity_tracking','comps'],within_file_order='UNCHANGED',batch=8,seed=1337,
            precision='FP32;TF32_OFF;NO_KV;NO_AUTOCAST',official_temperatures=[1.],max_input=1024,
            metric='ORIGINAL_RAW_PHRASE_SUM;TASK_UID_MACRO_PERCENT',
            training_updates=0,checkpoint_writes=0,teacher_loads=0,download=0,installation=0,
            per_model_max_wall_seconds=HARD,forecast_multiplier=1.5,forecast_reserve=120,
            new_model_cutoff=CUTOFF,CUDA_allocated_cap_bytes=8*1024**3,
            event_bytes_cap=MAX_EVENTS,shard_limit_bytes=10_000_000,
            uncertainty='No new quality ruler. Input-only paired cluster bootstrap may be reported later;no seed CI or training gain claim.',
            cluster='COMPS:property shared across files;Entity:file+sample_id',
            baseline='Uniform expected COMPS50/Entity20. Good-first always-first is label leakage,not a baseline.'),
        CPU_contracts=dict(semantic=6,driver=2,current_adapter=21),model_loads=0,GPU_calls=0)
    OUT.mkdir(parents=True,exist_ok=False);prior.write(PROFILE,profile)
    print('PROFILE',prior.digest(PROFILE),profile['sources']['sha256'],flush=True)

def verify_profile():
    profile=prior.read(PROFILE)
    if profile['sources']!=signature():raise ValueError('frozen execution source changed')
    for name,expected in profile['pins'].items():
        if prior.digest(ROOT/name)!=expected:raise ValueError('frozen input changed: '+name)
    return profile

def forecast(costs,sweep):
    if set(costs)!=set(sweep):raise Hold('all seven measured cost files required')
    value=math.fsum(costs[name]['wall_seconds']*sweep[name]['padded_input_positions']
        /sweep[name]['cost_padded_input_positions'] for name in sweep)*1.5+120
    if not math.isfinite(value) or value<=0:raise Hold('finite measured whole-file forecast required')
    return value

def score_file(official,torch,forward,processor,pad,spec,meta,mode,directory,check,byte_counter):
    from scripts.p106b_shards import ShardWriter
    tick=time.perf_counter();rows=list(records(spec,official))
    if mode=='cost':rows=[rows[i] for i in meta['cost_indices']]
    expected=dict(Counter(record['decoded']['UID'] for record in rows))
    stem=mode+'_'+Path(spec['path']).stem
    writer=ShardWriter(directory,stem,limit=10_000_000)
    def sink(event):
        amount=len((json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode())
        if byte_counter[0]+amount>MAX_EVENTS:raise Hold('predeclared full event storage cap exceeded')
        byte_counter[0]+=amount;writer.append(event)
    args=argparse.Namespace(task=spec['task'],save_predictions=True,images_path=None)
    collate=official['get_causal_collate_fn'](pad)
    measured=[0,0]
    try:
        with core.RankAudit(official,torch,task=spec['task'],sink=sink) as audit:
            def batches():
                for chunk in core.contiguous_batches(rows):
                    check();items=[core.processed_item(official,processor,r['decoded']) for r in chunk]
                    measured[0]+=padded_positions(chunk,items);measured[1]+=len(chunk)
                    audit.set_batch(chunk,items)
                    yield collate(items)
                    if mode=='full' and measured[1]%2048==0:
                        print('PROGRESS',spec['task'],Path(spec['path']).stem,measured[1],len(rows),flush=True)
            stats,predictions=official['compute_causal_results'](args,forward,batches(),[1.])
        accuracies,average=official['process_results'](args,stats)
        summary=audit.summary(average[1.],expected_by_uid=expected)
        expected_positions=meta['cost_padded_input_positions' if mode=='cost' else 'padded_input_positions']
        if measured!=[expected_positions,len(rows)]:raise ValueError('full measured native shapes/order differ from preflight')
        manifest=writer.close(lineage=dict(model=directory.name,mode=mode,task=spec['task'],
            source_file=spec['path'],source_sha256=spec['sha256'],data_use='EVALUATION_ONLY_NOT_TRAIN'))
        result=dict(summary,manifest=manifest,official_accuracies=accuracies,
            wall_seconds=time.perf_counter()-tick,padded_positions=measured[0],
            source_file=spec['path'],source_sha256=spec['sha256'],formal_quality=(mode=='full'))
        prior.write(directory/(stem+'_summary.json'),result)
        print('FILE_CLOSED',stem,summary['rows'],summary['UID_macro_percent'],result['wall_seconds'],flush=True)
        return result
    except BaseException:
        if not writer.manifest_path.exists():
            if writer._total_rows:writer.close(lineage=dict(complete=False,mode=mode,task=spec['task']))
            else:writer._finish()
        raise

def real_phrase_oracle(official,torch,forward,processor,pad,profile,sweep):
    checks=[];collate=official['get_causal_collate_fn'](pad)
    for task in ('comps','entity_tracking'):
        spec=next(s for s in profile['files'] if s['task']==task)
        target=sweep[Path(spec['path']).stem]['longest_index']
        row=next(row for row in records(spec,official) if row['trace']['kept_index']==target)
        item=core.processed_item(official,processor,row['decoded']);values=collate([item])[1]
        for j in range(len(row['decoded']['sentences'])):
            prefix='sentence_'+str(j);targets=values[prefix+'_targets'].cuda();mask=values[prefix+'_phrase_mask'].cuda()
            logits=forward(input_ids=values[prefix+'_inputs'].cuda(),attention_mask=values[prefix+'_attn_mask'].cuda())['logits']
            labels=targets.clone();labels[mask==0]=-100
            original=(torch.nn.functional.log_softmax(logits,dim=-1).gather(-1,targets.unsqueeze(-1)).squeeze(-1)*mask).sum()
            ce=-torch.nn.functional.cross_entropy(logits.reshape(-1,forward.vocab),labels.reshape(-1),ignore_index=-100,reduction='sum')
            if not math.isclose(float(original),float(ce),abs_tol=1e-5,rel_tol=1e-4):raise ValueError('real original phrase vs full-label CE differs')
            checks.append(dict(task=task,source=row['trace'],candidate=j,phrase_sum=float(original),full_label_CE=float(ce),
                native_ids=item[1][prefix+'_tokens'].tolist(),phrase_mask=item[1][prefix+'_phrase_mask'].tolist(),passed=True))
            del logits,targets,mask,labels,original,ce
    return checks

def actual(model):
    started=time.perf_counter();profile=verify_profile();cache=config()
    if model not in profile['models']:raise ValueError('unregistered model')
    if time.time()+HARD+60>CUTOFF:raise Hold('full hard-cap new-model interval no longer fits current cutoff')
    directory=OUT/model;directory.mkdir(exist_ok=False)
    report=dict(tag=TAG,model=model,status='STARTED',returncode=1,PID=os.getpid(),
        started_at=datetime.now(timezone.utc).isoformat(),profile_sha256=prior.digest(PROFILE),
        source_sha256=profile['sources']['sha256'],cost_files={},full_files={},training_updates=0,checkpoint_writes=0,
        forecast_admitted=False,all_97808_complete=False,cache_policy=cache)
    import torch
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.manual_seed(1337)
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p106b_resource_matrix import close_cuda
    from scripts.diag_p106b_external_core6 import close_report
    from scripts.p106b_babylm_causal import TextProcessor
    forward=processor=lm=None;byte_counter=[0]
    def check():
        if (OUT/'STOP').exists():raise Hold('owned STOP requested')
        if time.perf_counter()-started>HARD or time.time()>CUTOFF-30:raise Hold('current wall/clock cap')
        if torch.cuda.memory_allocated()>8*1024**3:raise Hold('predeclared owned allocator cap')
    def interrupt(_sig,_frame):raise Hold('owned wall-clock signal')
    old=signal.signal(signal.SIGINT,interrupt)
    try:
        report['GPU_entry']=require_idle_gpu();check()
        official,proof=core.load_official(prior.SOURCE,torch,device='cuda');report['official_AST']=proof
        sweep=profile['tokenizer_sweeps']['falcon' if model=='falcon90m' else 'native']
        with runtime.model_runtime(model,torch) as (lm,model_proof):
            report['model_proof']=model_proof
            forward=prior.FullLogits(lm,torch,check)
            processor=TextProcessor(lm.tokenizer,native=hasattr(lm,'core'),vocab=forward.vocab)
            pad=lm.core.pad_id if hasattr(lm,'core') else lm.tokenizer.pad_token_id
            if type(pad)is not int or not 0<=pad<forward.vocab:raise ValueError('actual native PAD required')
            report['native_policy']=dict(vocab=forward.vocab,pad_id=pad,manual_BOS=False,chat_template=False)
            from torch.nn.attention import sdpa_kernel,SDPBackend
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                report['synthetic_oracle']=prior.numerical_canary(official,lm,forward,torch,processor,pad)
                report['real_phrase_oracle']=real_phrase_oracle(official,torch,forward,processor,pad,profile,sweep)
                for spec in profile['files']:
                    name=Path(spec['path']).stem
                    report['cost_files'][name]=score_file(official,torch,forward,processor,pad,spec,sweep[name],
                        'cost',directory,check,byte_counter)
                seconds=forecast(report['cost_files'],sweep)
                report['forecast_seconds']=seconds
                remaining=min(HARD-(time.perf_counter()-started),CUTOFF-time.time()-30)
                if seconds>remaining:raise Hold('measured whole97808 forecast exceeds remaining wall window')
                report['forecast_admitted']=True;print('FORECAST_ADMITTED',model,seconds,remaining,flush=True)
                for task in profile['policy']['task_order']:
                    torch.manual_seed(1337)
                    for spec in profile['files']:
                        if spec['task']!=task:continue
                        name=Path(spec['path']).stem
                        report['full_files'][name]=score_file(official,torch,forward,processor,pad,spec,sweep[name],
                            'full',directory,check,byte_counter)
                report['full_forward_calls']=forward.calls;report['full_forward_native_positions']=forward.input_tokens
                report['all_97808_complete']=sum(r['rows'] for r in report['full_files'].values())==97808
                if not report['all_97808_complete']:raise ValueError('whole new formal suite missing rows')
            # Drop all extra model aliases before the strict runtime closes.
            forward.lm=None;forward=processor=None
        lm=None
        report.update(status='FULL_COMPS_ENTITY_COMPLETE',returncode=0)
    except BaseException as exc:
        report.update(status='HOLD' if isinstance(exc,Hold) else 'ERROR',returncode=8 if isinstance(exc,Hold) else 1,
            error=dict(type=type(exc).__name__,message=str(exc)[:2000]))
        print('ACTUAL_ERROR',report['error'],flush=True)
    finally:
        signal.signal(signal.SIGINT,old)
        if forward is not None:forward.lm=None
        forward=processor=lm=None;gc.collect()
        try:
            if torch.cuda.is_initialized():report['CUDA_close']=close_cuda(torch)
            else:report['CUDA_close']=dict(allocated_bytes=0,reserved_bytes=0,initialized=False)
            if report['CUDA_close']['allocated_bytes'] or report['CUDA_close']['reserved_bytes']:
                raise ValueError('owned CUDA not fully released')
            report['owned_model_released']=True
        except BaseException as exc:
            report.update(status='CLOSURE_ERROR',returncode=9,cleanup_error=str(exc)[:2000])
        try:verify_profile();report['sources_and_inputs_unchanged']=True
        except BaseException as exc:
            report.update(status='SOURCE_EXIT_ERROR',returncode=9,source_exit_error=str(exc)[:2000])
        report.update(ended_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-started,
            event_bytes=byte_counter[0],model_claim='EXISTING_FROZEN_CHECKPOINT;NOT_A_NEW_TRAINING_GAIN')
        close_report(directory/'report.json',report)
    print('TERMINAL',model,report['status'],report['returncode'],report['wall_seconds'],flush=True)
    return report['returncode']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('check','prepare','actual'))
    parser.add_argument('--model',choices=runtime.MODELS);args=parser.parse_args()
    if args.action=='prepare':prepare();return 0
    if args.action=='check':print(json.dumps(signature()));return 0
    if not args.model:parser.error('--model required for actual')
    return actual(args.model)

if __name__=='__main__':raise SystemExit(main())
