"""User161 BabyLM whole-file evaluation under the Nov18 long GPU grant.

Pure scoring/oracle helpers are reused unchanged. No expired controller is
called and no globals in an old execution module are rebound.
"""
from __future__ import annotations
import argparse,copy,gc,json,os,signal,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_babylm_semantics as base
prior,runtime,core=base.prior,base.runtime,base.core
Hold=base.Hold
TAG='p106b_babylm_semantics_long_v3_20261117_s1337'
OUT=ROOT/'test_result/evidence'/TAG
PROFILE=OUT/'profile.json'
AUDIT=ROOT/'handoff/audit/research_20261118_01a1e647'
AUTHORITY=AUDIT/'CURRENT_AUTHORITY_AND_SCOPE_v1.json'
INHERITED=base.PROFILE
INHERITED_SHA='C12BE432665A32BDE03BD855271508DFEB88AE393DFFBE15DFB80188E6A0DCC0'
HARD=14400
CUTOFF=datetime.fromisoformat('2026-11-18T16:30:00+09:00').timestamp()
EXTRA=('scripts/diag_p106b_babylm_semantics_long_v3.py',
    'scripts/test_diag_p106b_babylm_semantics_long_v3.py',
    'run_P106B_Stage8sem4Wc_long_semantics.sh')

def signature():
    files=dict(base.signature()['files'])
    for name in EXTRA:files[name]=prior.digest(ROOT/name)
    return dict(files=files,sha256=prior.object_sha(files))

def admit_wall(now,hard=HARD,cutoff=CUTOFF):
    if now+hard+60>cutoff:raise Hold('whole model hard interval does not fit new Nov18 cutoff')

def remaining_wall(elapsed,now,hard=HARD,cutoff=CUTOFF):
    return min(hard-elapsed,cutoff-now-30)

def verify_profile():
    profile=prior.read(PROFILE)
    if profile['sources']!=signature():raise ValueError('new frozen execution source changed')
    if profile['user_directive']!=161 or profile['policy']['new_model_cutoff']!=CUTOFF:
        raise ValueError('current authority and deadline required')
    for name,expected in profile['pins'].items():
        if prior.digest(ROOT/name)!=expected:raise ValueError('new frozen input changed: '+name)
    return profile

def prepare():
    if prior.digest(INHERITED)!=INHERITED_SHA:raise ValueError('closed inherited CPU profile differs')
    old=base.verify_profile()
    if (old['policy']['all_decoded_rows']!=97808 or len(old['files'])!=7
            or set(old['tokenizer_sweeps'])!={'native','falcon'}
            or set(old['models'])!=set(runtime.MODELS)):
        raise ValueError('exact prior full sweep/model scope required')
    for sweep in old['tokenizer_sweeps'].values():
        if sum(item['rows'] for item in sweep.values())!=97808 or len(sweep)!=7:
            raise ValueError('closed tokenizer whole denominator differs')
    authority=prior.read(AUTHORITY)
    if authority['goal']['threadId']!='01a1e647-7b7c-7e13-a222-c6b467937c77':
        raise ValueError('own current goal proof required')
    profile=copy.deepcopy(old)
    profile.update(schema='P106B_BABYLM_SEMANTICS_LONG_V3',tag=TAG,user_directive=161,
        UTC=datetime.now(timezone.utc).isoformat(),sources=signature(),
        inherited_cpu_sweep=dict(path=str(INHERITED.relative_to(ROOT)),sha256=INHERITED_SHA,
            complete_rows_per_tokenizer=97808,recomputed=False,
            evidence='EXACT_FROZEN_PROFILE_AND_ALL_OLD_PINS_RECHECKED'),
        authority_receipt=str(AUTHORITY.relative_to(ROOT)))
    profile['pins'].update({str(INHERITED.relative_to(ROOT)):INHERITED_SHA,
        str(AUTHORITY.relative_to(ROOT)):prior.digest(AUTHORITY)})
    profile['policy'].update(per_model_max_wall_seconds=HARD,new_model_cutoff=CUTOFF,
        authority='USER161_CURRENT_EXPLICIT_LONG_GPU_PERMISSION',
        outer_timeout_seconds=HARD+60,post_timeout_kill_grace_seconds=60)
    profile['CPU_contracts']['new_long_controller']=3
    OUT.mkdir(parents=True,exist_ok=False);prior.write(PROFILE,profile)
    print('LONG_PROFILE',prior.digest(PROFILE),profile['sources']['sha256'],flush=True)

def actual(model):
    started=time.perf_counter();profile=verify_profile();cache=base.config()
    if model not in profile['models']:raise ValueError('unregistered model')
    admit_wall(time.time())
    directory=OUT/model;directory.mkdir(exist_ok=False)
    report=dict(tag=TAG,model=model,user_directive=161,status='STARTED',returncode=1,PID=os.getpid(),
        started_at=datetime.now(timezone.utc).isoformat(),profile_sha256=prior.digest(PROFILE),
        source_sha256=profile['sources']['sha256'],cost_files={},full_files={},training_updates=0,
        checkpoint_writes=0,forecast_admitted=False,all_97808_complete=False,cache_policy=cache)
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
        if remaining_wall(time.perf_counter()-started,time.time())<=0:raise Hold('current long wall/clock cap')
        if torch.cuda.memory_allocated()>8*1024**3:raise Hold('predeclared owned allocator cap')
    def interrupt(_sig,_frame):raise Hold('owned wall-clock signal')
    old_signal=signal.signal(signal.SIGINT,interrupt)
    try:
        report['GPU_entry']=require_idle_gpu();check()
        official,proof=core.load_official(prior.SOURCE,torch,device='cuda');report['official_AST']=proof
        sweep=profile['tokenizer_sweeps']['falcon' if model=='falcon90m' else 'native']
        with runtime.model_runtime(model,torch) as (lm,model_proof):
            try:
                report['model_proof']=model_proof
                forward=prior.FullLogits(lm,torch,check)
                processor=TextProcessor(lm.tokenizer,native=hasattr(lm,'core'),vocab=forward.vocab)
                pad=lm.core.pad_id if hasattr(lm,'core') else lm.tokenizer.pad_token_id
                if type(pad)is not int or not 0<=pad<forward.vocab:raise ValueError('actual native PAD required')
                report['native_policy']=dict(vocab=forward.vocab,pad_id=pad,manual_BOS=False,chat_template=False)
                from torch.nn.attention import sdpa_kernel,SDPBackend
                with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                    report['synthetic_oracle']=prior.numerical_canary(official,lm,forward,torch,processor,pad)
                    report['real_phrase_oracle']=base.real_phrase_oracle(
                        official,torch,forward,processor,pad,profile,sweep)
                    for spec in profile['files']:
                        name=Path(spec['path']).stem
                        report['cost_files'][name]=base.score_file(official,torch,forward,processor,pad,
                            spec,sweep[name],'cost',directory,check,byte_counter)
                    seconds=base.forecast(report['cost_files'],sweep)
                    report['forecast_seconds']=seconds
                    remaining=remaining_wall(time.perf_counter()-started,time.time())
                    if seconds>remaining:raise Hold('measured whole97808 forecast exceeds remaining long interval')
                    report['forecast_admitted']=True
                    print('FORECAST_ADMITTED',model,seconds,remaining,flush=True)
                    for task in profile['policy']['task_order']:
                        torch.manual_seed(1337)
                        for spec in profile['files']:
                            if spec['task']!=task:continue
                            name=Path(spec['path']).stem
                            report['full_files'][name]=base.score_file(official,torch,forward,processor,pad,
                                spec,sweep[name],'full',directory,check,byte_counter)
                    report['full_forward_calls']=forward.calls
                    report['full_forward_native_positions']=forward.input_tokens
                    report['all_97808_complete']=sum(r['rows'] for r in report['full_files'].values())==97808
                    if not report['all_97808_complete']:raise ValueError('whole formal suite missing rows')
            finally:
                # Clear caller aliases even on an oracle/HOLD exception before the strict owner closes.
                if forward is not None:forward.lm=None
                forward=processor=lm=None
        report.update(status='FULL_COMPS_ENTITY_COMPLETE',returncode=0)
    except BaseException as exc:
        report.update(status='HOLD' if isinstance(exc,Hold) else 'ERROR',
            returncode=8 if isinstance(exc,Hold) else 1,
            error=dict(type=type(exc).__name__,message=str(exc)[:2000]))
        print('ACTUAL_ERROR',report['error'],flush=True)
    finally:
        signal.signal(signal.SIGINT,old_signal)
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


