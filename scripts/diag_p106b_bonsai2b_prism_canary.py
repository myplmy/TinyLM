"""Owned offline Bonsai2B localhost raw-likelihood admission, never a benchmark."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import traceback
import unittest
from urllib.error import URLError

import tinylm
from scripts.p106b_prism_http import (PrismHTTP, ProtocolHold, completion_request,
    completion_probabilities, full_distribution, compare_forced_to_full)
from scripts.p106b_mtp_teacher import gguf_metadata
from scripts.p106b_shards import ShardWriter

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'test_result/evidence/p106b_bonsai2b_prism_canary_v1_20261117'
PROFILE = BASE/'profile.json'
ASSETS = ROOT/'test_result/evidence/p106b_bonsai2b_prism_assets_v1_20261117/report.json'
CONTRACTS = ROOT/'handoff/audit/research_20261117_01a1e647/CPU_NEW_METHOD_CONTRACTS_v1.json'
PLAN = ROOT/'test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md'
SOURCES = ('scripts/diag_p106b_bonsai2b_prism_canary.py',
    'scripts/test_diag_p106b_bonsai2b_prism_canary.py', 'scripts/p106b_prism_http.py',
    'scripts/p106b_mtp_teacher.py', 'scripts/p106b_shards.py', 'scripts/interactive_research_infer.py')
CUTOFF = datetime(2026,11,17,7,40,tzinfo=timezone.utc)
SCHEMA = 'P106B_BONSAI2B_PRISM_RAW_LIKELIHOOD_CANARY_V1'
PROMPT_A = 'The capital of France is'
PROMPT_B = '한국의 수도는'

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest().upper()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    data = (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(data) >= 20_000_000:raise ProtocolHold('owned JSON must remain below20MB')
    with Path(path).open('xb') as stream:stream.write(data)

def guard(start=None):
    if datetime.now(timezone.utc) >= CUTOFF:raise TimeoutError('user158 new-compute cutoff')
    if (BASE/'STOP').exists():raise TimeoutError('owned canary STOP')
    if start is not None and time.monotonic()-start >= 1080:raise TimeoutError('owned canary compute cap')

def vocabulary_size(layout):
    if layout['metadata'].get('general.architecture') != 'qwen35':
        raise ProtocolHold('exact2B qwen35 architecture required')
    embedding = layout['tensors'].get('token_embd.weight',{}).get('shape')
    if not isinstance(embedding,list) or len(embedding)!=2 or not 32000<=embedding[1]<=300000:
        raise ProtocolHold('bounded native embedding vocabulary required')
    output = layout['tensors'].get('output.weight',{}).get('shape',embedding)
    if output != embedding:raise ProtocolHold('native output and embedding vocabulary differ')
    return embedding[1]

def server_command(profile):
    return [str(Path(profile['assets']['bundle'])/'llama-server'),
        '--offline','--model',str(ROOT/profile['assets']['model']),
        '--host','127.0.0.1','--port',str(profile['port']), '--no-ui',
        '--parallel','1','--ctx-size','1024','--batch-size','512','--ubatch-size','512',
        '--threads','4','--threads-batch','4','--threads-http','1','--gpu-layers','all',
        '--fit','off','--flash-attn','off','--cache-ram','0','--cache-reuse','0',
        '--no-cache-prompt','--no-context-shift','--no-warmup','--no-mmproj']

def validate_context(reply, ids):
    if reply.get('tokens_evaluated') != len(ids) or reply.get('truncated') is not False:
        raise ProtocolHold('exact native prompt length without truncation required')
    if reply.get('timings',{}).get('prompt_n') != len(ids):
        raise ProtocolHold('all native prompt tokens must be processed without cache reuse')
    settings = reply.get('generation_settings',{})
    if settings.get('post_sampling_probs') is not False:
        raise ProtocolHold('observed pre-sampling raw probability mode required')

def close_owned_process(proc, *, getpgid=os.getpgid, killpg=os.killpg):
    if proc is None or proc.poll() is not None:
        return dict(terminal=True,returncode=None if proc is None else proc.returncode,signals=[])
    if getpgid(proc.pid) != proc.pid:
        raise RuntimeError('refuse to signal any process group except our own new-session child')
    sent = []
    killpg(proc.pid,signal.SIGTERM);sent.append('SIGTERM')
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        killpg(proc.pid,signal.SIGKILL);sent.append('SIGKILL');proc.wait(timeout=5)
    return dict(terminal=proc.poll() is not None,pid=proc.pid,returncode=proc.returncode,signals=sent)

def check_assets(assets):
    model = ROOT/assets['model']
    if model.is_symlink() or not model.is_file() or model.stat().st_size != assets['model_bytes']:
        raise ProtocolHold('exact2B model file absent, linked or changed size')
    if digest(model) != assets['model_sha256']:raise ProtocolHold('exact2B model SHA changed')
    bundle = Path(assets['bundle'])
    for name, entry in assets['runtime_files'].items():
        path = bundle/name
        if path.is_symlink() or digest(path) != entry['sha256']:
            raise ProtocolHold('existing pinned Prism runtime changed: '+name)

def prepare():
    guard()
    if BASE.exists():raise FileExistsError('preserve canary namespace')
    assets, contracts = read(ASSETS),read(CONTRACTS)
    if assets['actual_exit_code'] != 0 or assets['model_bytes'] != 429183456:
        raise ProtocolHold('closed exact2B metadata gate required')
    if (not contracts['successful'] or contracts['contracts_by_module']['PRISM_HTTP'] != 10
            or contracts['source_SHA256']['scripts/p106b_prism_http.py'] != digest(ROOT/'scripts/p106b_prism_http.py')):
        raise ProtocolHold('unchanged existing10 protocol contracts required')
    check_assets(assets)
    with (ROOT/assets['model']).open('rb') as stream:layout=gguf_metadata(stream)
    vocab = vocabulary_size(layout)
    suite = unittest.defaultTestLoader.loadTestsFromName('scripts.test_diag_p106b_bonsai2b_prism_canary')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun != 5:raise RuntimeError('all5 new native-lifetime contracts required')
    help_text = (ASSETS.parent/'llama-server_help.txt').read_text(encoding='utf-8')
    profile = dict(schema=SCHEMA,authority_directive=158,cutoff=CUTOFF.isoformat(),
        assets=assets,assets_receipt_sha256=digest(ASSETS),CPU_contract_receipt_sha256=digest(CONTRACTS),
        inherited_protocol_contracts=10,new_lifetime_contracts=5,port=19861,native_vocab_size=vocab,
        gguf_metadata=layout['metadata'],gguf_header_bytes=layout['header_bytes'],
        sources={name:digest(ROOT/name) for name in SOURCES},
        prompt_A=PROMPT_A,prompt_B=PROMPT_B,forced_rank_indices=[0,7,vocab//2],
        atol=1e-5,rtol=1e-4,mass_atol=5e-4,max_compute_seconds=1080,max_phase_seconds=1200,
        startup_seconds=300,request_seconds=60,max_response_bytes=64_000_000,
        max_total_output_bytes=180_000_000,minimum_free_vram_bytes=8*1024**3,
        prompt_add_special=True,native_integer_prompt=True,cache_prompt=False,
        original_distribution='FULL_VOCAB_FP32_SOFTMAX_BEFORE_SAMPLERS',
        formal_benchmark=False,quality_claim=False,model_loads=0)
    command = server_command(profile)
    for flag in command:
        if flag.startswith('--') and flag not in help_text:raise ProtocolHold('flag absent from exact existing help: '+flag)
    BASE.mkdir()
    with (BASE/'initial_plan.md').open('xb') as stream:stream.write(PLAN.read_bytes())
    profile['initial_plan_sha256']=digest(BASE/'initial_plan.md')
    write(PROFILE,profile)
    print('[PRISM2B_PREPARED] exact2B assets, inherited10/new5 contracts;no model loaded;V='+str(vocab),flush=True)

def verify():
    guard()
    p=read(PROFILE)
    if (p['schema'] != SCHEMA or p['cutoff'] != CUTOFF.isoformat() or p['authority_directive'] != 158
            or p['initial_plan_sha256'] != digest(BASE/'initial_plan.md')
            or p['assets_receipt_sha256'] != digest(ASSETS)
            or p['CPU_contract_receipt_sha256'] != digest(CONTRACTS)
            or p['sources'] != {name:digest(ROOT/name) for name in SOURCES}):
        raise ProtocolHold('frozen profile/source/input mismatch')
    check_assets(p['assets'])
    return p

@contextmanager
def phase_alarm(seconds):
    previous=signal.getsignal(signal.SIGALRM)
    def expired(*_):raise TimeoutError('owned localhost phase wall cap')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def actual():
    start=time.monotonic();guard()
    out=BASE/'actual';out.mkdir()
    proc=log=None;p=None
    report=dict(schema=SCHEMA,authority_directive=158,status='INCOMPLETE',returncode=9,
        started_UTC=datetime.now(timezone.utc).isoformat(),comparisons=[],formal_benchmark=False,
        quality_claim=False,model_load_attempted=False,training_steps=0,optimizer_updates=0,
        checkpoint_writes=0,downloads=0,installations=0,closure_errors=[])
    try:
        with phase_alarm(1080):
            p=verify()
            if datetime.now(timezone.utc).timestamp()+1200 >= CUTOFF.timestamp():raise TimeoutError('whole phase does not fit cutoff')
            from scripts.interactive_research_infer import require_idle_gpu
            report['GPU_idle_point']=require_idle_gpu()
            memory=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
                capture_output=True,text=True,timeout=10,check=True)
            free_bytes=int(memory.stdout.strip())*1024**2
            if free_bytes < p['minimum_free_vram_bytes']:raise ProtocolHold('requires free8GiB at admission point')
            report['free_vram_point_bytes']=free_bytes
            with socket.socket() as bound:
                bound.bind(('127.0.0.1',p['port']))
            command=server_command(p);report['server_command']=command
            env={key:value for key,value in os.environ.items() if not key.startswith(('LLAMA_ARG_','GGML_'))}
            env.update(CUDA_CACHE_DISABLE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
            log=(out/'server.txt').open('xb')
            proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            report.update(model_load_attempted=True,owned_server_pid=proc.pid)
            api=PrismHTTP('http://127.0.0.1:'+str(p['port']),timeout=60)
            until=time.monotonic()+p['startup_seconds']
            while True:
                guard(start)
                if proc.poll() is not None:raise RuntimeError('owned Prism server exited during startup: '+str(proc.returncode))
                if (out/'server.txt').stat().st_size > 10_000_000:raise ProtocolHold('owned server log cap')
                try:
                    if api.request('/health').get('status')=='ok':break
                except (URLError,TimeoutError,ConnectionError):pass
                if time.monotonic()>=until:raise TimeoutError('owned server startup cap')
                time.sleep(.25)
            props=api.request('/props');write(out/'props.json',props)
            if Path(props['model_path']) != ROOT/p['assets']['model'] or props['total_slots'] != 1:
                raise ProtocolHold('observed owned exact model/slot identity differs')
            tokens={}
            for name,text in (('A',p['prompt_A']),('B',p['prompt_B'])):
                plain=api.request('/tokenize',dict(content=text,add_special=False,parse_special=False))['tokens']
                if api.request('/detokenize',dict(tokens=plain))['content'] != text:
                    raise ProtocolHold('native ordinary tokenization is not lossless')
                native=api.request('/tokenize',dict(content=text,add_special=True,parse_special=False))['tokens']
                if not native or any(type(i)is not int or not 0<=i<p['native_vocab_size'] for i in native):
                    raise ProtocolHold('native encoded IDs outside model vocabulary')
                tokens[name]=native
                write(out/('tokenization_'+name+'.json'),dict(text=text,plain_ids=plain,native_ids=native))
            def completion(name,ids,*,target=None,n_probs=1):
                guard(start)
                request=completion_request(ids,forced_token=target,n_probs=n_probs)
                write(out/(name+'_request.json'),request)
                before=time.monotonic();reply=api.request('/completion',request)
                elapsed=time.monotonic()-before
                if n_probs==p['native_vocab_size']:
                    entry=reply.get('completion_probabilities',[{}])[0]
                    top=entry.get('top_logprobs',[])
                    writer=ShardWriter(out,'full_distribution')
                    for row in top:writer.append(row)
                    manifest=writer.close(lineage=dict(profile_sha256=digest(PROFILE),request=name))
                    header=dict(reply);header['completion_probabilities']=[{k:v for k,v in entry.items() if k!='top_logprobs'}]
                    header['top_logprobs_manifest']=manifest
                    write(out/(name+'_reply_header.json'),header)
                    report['full_probability_shards']=manifest
                else:write(out/(name+'_reply.json'),reply)
                validate_context(reply,ids)
                report.setdefault('requests',[]).append(dict(name=name,wall_seconds=elapsed,
                    native_prompt_tokens=len(ids),tokens_evaluated=reply['tokens_evaluated'],
                    actual_processed_tokens=reply['timings']['prompt_n']))
                if sum(path.stat().st_size for path in out.iterdir() if path.is_file()) > p['max_total_output_bytes']:
                    raise ProtocolHold('owned canary total output cap')
                return reply
            full_reply=completion('A_full',tokens['A'],n_probs=p['native_vocab_size'])
            full=full_distribution(full_reply,vocab_size=p['native_vocab_size'],mass_atol=p['mass_atol'])
            report['full_distribution']=dict(vocab_size=p['native_vocab_size'],mass=full['mass'],
                zero_sentinel_count=full['zero_sentinel_count'],greedy_token=full['greedy_token'])
            targets=[full['sorted_token_ids'][rank] for rank in p['forced_rank_indices']]
            report['predeclared_rank_targets']=list(zip(p['forced_rank_indices'],targets))
            for ordinal,target in enumerate(targets):
                reply=completion('A_forced_'+str(ordinal),tokens['A'],target=target)
                compared=compare_forced_to_full(reply,full,target=target,vocab_size=p['native_vocab_size'],atol=p['atol'],rtol=p['rtol'])
                report['comparisons'].append(compared)
                if not compared['passed']:raise ProtocolHold('forced target raw probability differs from full distribution')
            completion('B_interposed',tokens['B'])
            again=completion('A_after_B',tokens['A'],target=targets[1])
            isolated=compare_forced_to_full(again,full,target=targets[1],vocab_size=p['native_vocab_size'],atol=p['atol'],rtol=p['rtol'])
            report['state_isolation']=isolated
            if not isolated['passed']:raise ProtocolHold('hybrid interposed-context state isolation failed')
            report.update(status='RAW_LIKELIHOOD_CANARY_COMPLETE_NOT_FORMAL_BENCHMARK',returncode=0)
    except BaseException as error:
        report.update(status='RAW_LIKELIHOOD_HOLD' if isinstance(error,ProtocolHold) else 'RAW_LIKELIHOOD_ERROR',
            returncode=8 if isinstance(error,ProtocolHold) else 1,
            error=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        try:report['owned_server_closure']=close_owned_process(proc)
        except BaseException as error:report['closure_errors'].append(str(error))
        if log is not None:log.close()
        if p is not None:
            try:check_assets(p['assets']);report['original_assets_unchanged']=True
            except BaseException as error:report['closure_errors'].append(str(error))
        try:
            from scripts.interactive_research_infer import require_idle_gpu
            report['GPU_exit_point']=require_idle_gpu()
        except BaseException as error:report['closure_errors'].append(str(error))
        if report['closure_errors']:report.update(status='CANARY_CLOSURE_ERROR',returncode=9)
        report['source_unchanged']={name:digest(ROOT/name) for name in SOURCES}==({} if p is None else p['sources'])
        if not report['source_unchanged']:
            report['closure_errors'].append('frozen source mismatch at exit')
            report.update(status='CANARY_CLOSURE_ERROR',returncode=9)
        report['wall_seconds']=time.monotonic()-start
        write(out/'report.json',report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('error','assets')},ensure_ascii=False),flush=True)
    return report['returncode']

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','check','actual'))
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='check':verify();print('[PRISM2B_CHECK]frozen profile matched;no model load')
    else:raise SystemExit(actual())

if __name__=='__main__':main()
