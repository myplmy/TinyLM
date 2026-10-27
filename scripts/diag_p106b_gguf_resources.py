#!/usr/bin/env python3
"""Native GPT2 generation resources; independent from immutable Core6 scoring."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import statistics
import struct
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import p106b_native_core6 as native
from scripts import diag_p106b_resource_matrix as resource

TAG='p106b_gpt2_generation_resources_v1_20261027'
SCHEMA='P106B_NATIVE_GPT2_GENERATION_RESOURCES_V1'
OWN=('scripts/diag_p106b_gguf_resources.py','scripts/p106b_native_generation_worker.cpp','scripts/test_p106b_gguf_resources.py')
need=resource.need

def identity():
    files=dict(native.identity()['files'])
    files.update({name:resource.digest(resource.safe(name)) for name in (*OWN,*resource.OWN)})
    return dict(files=files,sha256=resource.sha(files))

def same_generation(a,b):
    need(a['generated_ids']==b['generated_ids'] and a['finish_reason']==b['finish_reason']
         and a['final_kv_position']==b['final_kv_position'],'native observed/unobserved IDs/stop/KV differ')
    return True

def accept_generation(ids,cap,natural,reason,final_pos,prefix_length,events):
    need(1<=len(ids)<=cap and all(type(x) is int and 0<=x<50257 for x in ids),'complete bounded native IDs required')
    eos=natural and ids[-1]==50256
    need(reason==int(eos) and (eos or len(ids)==cap),'native length/EOS contract differs')
    need(final_pos==prefix_length+len(ids)-2,'native cache length differs')
    if events:
        need(len(events)==len(ids) and [e['index'] for e in events]==list(range(len(ids)))
             and [e['token_id'] for e in events]==ids,'native stream ID/event alignment differs')
        need(all(e['native_seconds']>0 and e['wall_seconds']>0 for e in events)
             and all(a['native_seconds']<=b['native_seconds'] and a['wall_seconds']<=b['wall_seconds']
                     for a,b in zip(events,events[1:])),'native event clock order differs')
    return 'EOS' if eos else ('MAX_NEW' if natural else 'MAX_NEW_EOS_DISABLED')

class Worker(native.Worker):
    def __init__(self,assets,build,stop,writer,proof,device):
        super().__init__(assets,build,stop,writer,proof);self.device=device

    def close(self):
        try:super().close()
        finally:
            self.proof['numeric_logit_rows_serialized']=self.proof.get('native_logits_rows_copied')
            self.proof['logit_copy_counter_scope']='NUMERIC_OP8_OP9_WIRE_ROWS_ONLY; NOT_GENERATION_D2H_TRANSFERS_OR_BYTES'

    def __enter__(self):
        from scripts.diag_p106_vram_sample import read_memory
        from scripts.diag_p106b_mtp_teacher import owned_rss
        began=time.monotonic()
        command=[str(resource.safe(self.build['worker'])),'--execute',self.assets['path'],self.device,str(self.stop)]
        self.proof.update(command=command,model_load_attempted=False,worker_cleanup_complete=False,
                          CPU_lane_has_native_backend_discovery_and_NVML=True)
        try:
            self.memory_reader=self.retrying_memory(read_memory,emit=lambda line:print(line,flush=True))
            baseline,free=self.memory_reader()
            need(free>=2048,'native resource lane requires startup headroom')
            self.proof['baseline_gpu_used_mib']=baseline
            self.process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,bufsize=0,start_new_session=True,
                env=dict(os.environ,LD_LIBRARY_PATH=str(native.ENGINE)))
            self.proof.update(owned_pid=self.process.pid,model_load_attempted=True)
            def drain():
                for line in self.process.stderr:
                    value=line[:4000].decode('utf-8','replace').rstrip();self.tail.append(value);del self.tail[:-200]
                    if 'offload' in value.lower() or 'buffer size' in value.lower():
                        self.offload_line_count+=1
                        if len(self.offload_lines)<64:self.offload_lines.append(value)
            self.thread=threading.Thread(target=drain,daemon=True);self.thread.start()
            def sample():
                while not self.sample_stop.is_set():
                    try:self.observe_memory(self.memory_reader,owned_rss)
                    except Exception as exc:self.sampling_error(exc);return
                    self.sample_stop.wait(.5)
            self.proof['sampling_started_at']=datetime.now(timezone.utc).isoformat()
            self.sampler=threading.Thread(target=sample,daemon=True);self.sampler.start()
            reader=native.Reader(self.rpc(1));keys=('vocab_size','training_context','context','n_batch','n_ubatch','bos_id','eos_id')
            info=dict(zip(keys,reader.unpack('<5I2i')))
            info.update(zip(('add_bos','add_eos','vocab_type'),reader.unpack('<3I')))
            info.update(zip(('parameters','logical_model_tensor_bytes'),reader.unpack('<2Q')))
            info.update(architecture=reader.string().decode(),device_backend=reader.string().decode(),
                        tokenizer_model=reader.string().decode(),tokenizer_pre=reader.string().decode());reader.end()
            need((info['vocab_size'],info['context'],info['n_batch'],info['n_ubatch'],info['eos_id'])==(50257,1024,512,512,50256)
                 and info['architecture']=='gpt2','native generation runtime differs')
            need((self.device=='cpu')==(info['device_backend']=='CPU_OFFLOAD0'),'native placement differs')
            self.info=info;self.proof.update(native_info=info,model_loaded=True,startup_seconds=time.monotonic()-began)
            return self
        except BaseException:
            try:self.close()
            except BaseException as exc:self.proof['startup_cleanup_error']=dict(type=type(exc).__name__,message=str(exc)[:1000])
            raise

    def generation(self,prefix,cap,*,natural,observed):
        need(not self.telemetry_errors,'native telemetry failed before generation')
        self.request_id+=1;number=self.request_id;events=[]
        request=struct.pack('<II',7,number)+native.ints(prefix)+struct.pack('<II',cap,int(natural)+2*int(observed))
        self.writer.append(dict(event='generation_request',id=number,prefix_ids=prefix,cap=cap,natural=natural,observed=observed))
        began=time.perf_counter();self.transfer(self.process.stdin.fileno(),data=struct.pack('<I',len(request))+request)
        while True:
            size=struct.unpack('<I',self.transfer(self.process.stdout.fileno(),4))[0]
            need(12<=size<=native.MAX_FRAME,'bounded generation response required')
            raw=self.transfer(self.process.stdout.fileno(),size);wall=time.perf_counter()-began
            reader=native.Reader(raw);op,actual,status=reader.unpack('<III')
            need((op,actual)==(7,number),'generation response identity differs')
            if status==1:
                message=reader.string().decode('utf-8','replace');reader.end();raise RuntimeError(message)
            if status==2:
                need(observed,'unobserved generation emitted observer events')
                index,token=reader.unpack('<II');stamp=reader.unpack('<d')[0];reader.end()
                events.append(dict(index=index,token_id=token,native_seconds=stamp,wall_seconds=wall));continue
            need(status==0,'unknown generation status')
            count=reader.u32();need(1<=count<=cap,'generation count exceeds cap')
            ids=list(reader.unpack('<'+'i'*count));reason,final_pos=reader.unpack('<II')
            first,native_seconds=reader.unpack('<2d');reader.end();break
        finish=accept_generation(ids,cap,natural,reason,final_pos,len(prefix),events)
        need(not observed or len(events)==count,'complete observer stream required')
        need(0<first<=native_seconds and wall>0,'native timing bound differs')
        result=dict(generated_ids=ids,finish_reason=finish,final_kv_position=final_pos,prompt_tokens=len(prefix),
                    events=events,wall_seconds=wall,native_seconds=native_seconds,native_ttft_seconds=first,
                    observed_wall_ttft_seconds=events[0]['wall_seconds'] if observed else None,
                    timing_scope='WALL_INCLUDES_IPC_AND_NATIVE_CLEAR; NATIVE_PICK_CLOCK_SEPARATE; TOKENIZATION_DECODE_EXCLUDED')
        self.writer.append(dict(event='generation_result',id=number,**result));return result

    def numeric(self,prefix,tail=None):
        import numpy as np
        op=8 if tail is None else 9;request=native.ints(prefix)
        if tail is not None:request+=native.ints(tail)
        reader=native.Reader(self.rpc(op,request));rows,vocab=reader.unpack('<II')
        need(vocab==50257 and rows==(1 if tail is None else len(tail)+1),'numeric response shape differs')
        result=np.frombuffer(reader.take(rows*vocab*4),dtype='<f4').copy().reshape(rows,vocab);reader.end();return result

def numeric_canary(worker,prefix,rows,workload):
    import numpy as np
    # Exercise real bulk sizes:128 and509+3=512, not an8-token proxy.
    prefix=prefix[:min(len(prefix),509)];tail=[13,262,318]
    cached=worker.numeric(prefix,tail)
    for i,actual in enumerate(cached):
        expected=worker.numeric(prefix+tail[:i])[0]
        row=dict(workload=workload,prefix_tokens=len(prefix),step=i,max_abs=float(np.max(np.abs(actual-expected))),
                 allclose=bool(np.allclose(actual,expected,atol=native.ATOL,rtol=native.RTOL)),
                 argmax_equal=int(actual.argmax())==int(expected.argmax()),
                 atol=native.ATOL,rtol=native.RTOL)
        rows.append(row)
    need(all(x['allclose'] and x['argmax_equal'] for x in rows),'native cache/fullprefix numeric canary differs')
    return rows

def run_suite(worker,texts,budget,report):
    prompts=[]
    for row in texts['workloads']:
        content=row['text'];tokens=worker.tokenize(content)
        while len(tokens)<row['prompt_tokens']:
            content+=row['text'];tokens=worker.tokenize(content)
        prompts.append(dict(id=row['id'],language=row['language'],ids=tokens[:row['prompt_tokens']]))
    report['numeric_canary']=[]
    for row in prompts:numeric_canary(worker,row['ids'],report['numeric_canary'],row['id'])
    report['cost_probes']=[worker.generation(prompts[i]['ids'],2,natural=False,observed=False) for i in (0,2)]
    forecast=max(x['wall_seconds']/2 for x in report['cost_probes'])*(4*7*32+4*64)*3+60
    remaining=budget.seconds-(time.monotonic()-budget.started)
    report['cost_admission']=dict(conservative_seconds=forecast,remaining_seconds=remaining)
    if forecast>remaining:report['status']='BUDGET_HOLD_NOT_FULL_SUITE';return 8
    for row in prompts:
        budget.check();record=dict(**row,status='STARTED',unobserved=[],observed=[])
        report['workloads'].append(record)
        warm=worker.generation(row['ids'],32,natural=False,observed=False);record['warmup']=warm
        unobserved,observed=record['unobserved'],record['observed']
        for _ in range(3):unobserved.append(worker.generation(row['ids'],32,natural=False,observed=False))
        for _ in range(3):observed.append(worker.generation(row['ids'],32,natural=False,observed=True))
        for value in unobserved+observed:same_generation(warm,value)
        decoded=worker.detokenize(warm['generated_ids']);seconds=statistics.median(x['wall_seconds'] for x in unobserved)
        record.update(dict(status='COMPLETE',
            median_wall_seconds=seconds,tokens_per_second=32/seconds,bytes_per_second=len(decoded)/seconds,
            chars_per_second=len(decoded.decode('utf-8','replace'))/seconds,
            median_wall_ttft_seconds=statistics.median(x['observed_wall_ttft_seconds'] for x in observed)))
        print(json.dumps(dict(workload=row['id'],completed=True)),flush=True)
    for case in texts['answer_cases']:
        budget.check();prefix=worker.tokenize(case['question'])
        result=worker.generation(prefix,64,natural=True,observed=True)
        display=result['generated_ids'][:-1] if result['finish_reason']=='EOS' else result['generated_ids']
        report['answers'].append(dict(case=dict(case,mode='plain'),generation=result,
            actual_answer=worker.detokenize(display).decode('utf-8','replace'),
            full_text=worker.detokenize(prefix+result['generated_ids']).decode('utf-8','replace')))
    report['status']='NATIVE_GENERATION_RESOURCES_COMPLETE_NOT_QUALITY';return 0

def validate(profile,args):
    need(profile.get('schema')==SCHEMA and profile.get('tag')==TAG and profile.get('root_approved') is True
         and profile.get('authority_directive')==96 and profile.get('source_sha256')==identity()['sha256']
         and args.device in ('cpu','cuda') and args.max_wall_sec==profile['max_worker_seconds']==1800,
         'exact native resource source/device/cap required')
    need(profile.get('deadline')=='2026-10-27T08:00:00+00:00'
         and (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds()>1980,'full native phase and closure cannot fit')
    build=resource.read_ref(profile['build']);binary=resource.safe(build['worker'])
    need(resource.digest(binary)==build['worker_sha256'] and build['cpp_sha256']==resource.digest(resource.safe(OWN[1]))
         and build['wire_cpp_sha256']==resource.digest(resource.safe('scripts/p106b_native_llama_worker.cpp')),
         'native binary/current source differs')
    assets=native.asset_identity('gpt2_q4km');old=resource.read_ref(profile['closed_report']);terminal=resource.read_ref(profile['terminal'])
    need(old['assets']==assets and terminal['status']=='NATIVE_WINDOW_FULL_COMPLETE' and terminal['returncode']==0
         and terminal['report_sha256']==profile['closed_report']['sha256'],'same completed official execution required')
    return build,assets,resource.read_ref(profile['texts'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True);parser.add_argument('--profile-sha256',required=True)
    parser.add_argument('--device',choices=('cpu','cuda'),required=True);parser.add_argument('--max-wall-sec',type=int,required=True)
    action=parser.add_mutually_exclusive_group();action.add_argument('--execute',action='store_true');action.add_argument('--check-only',action='store_true')
    args=parser.parse_args();profile=resource.read_ref(dict(path=args.profile,sha256=args.profile_sha256))
    build,assets,texts=validate(profile,args)
    if args.check_only:print(json.dumps(dict(status='NATIVE_GENERATION_METADATA_ONLY',model_loads=0,gpu_calls=0)));return 0
    need(args.execute,'explicit native generation execution required')
    from scripts.p106b_shards import ShardWriter
    from scripts.interactive_research_infer import require_idle_gpu
    source=identity();budget=resource.Budget(args.max_wall_sec)
    output=resource.safe('test_result/evidence/'+TAG+'/'+args.device+'/report.json')
    raw=resource.safe('runs/eval/'+TAG+'/'+args.device+'/wire');need(not output.exists() and not raw.exists(),'new native output namespace required')
    report=dict(schema=SCHEMA,tag=TAG,source=source,profile_sha256=args.profile_sha256,device=args.device,
        assets=assets,build=profile['build'],quality_claim=False,training_updates=0,checkpoint_writes=0,
        exact_native_tensor_storage='NOT_MEASURED_NO_PUBLIC_BUFFER_HANDLE',
        exact_native_KV_storage='NOT_MEASURED; CAPACITY_LOGS_AND_POSITION_SEPARATE',
        status='STARTED',workloads=[],answers=[],proof={},started_at=datetime.now(timezone.utc).isoformat())
    writer=ShardWriter(raw,'wire',limit=19_999_999);worker=None;rc=9
    try:
        with resource.wall(args.max_wall_sec):
            report['idle_before']=require_idle_gpu()
            with Worker(assets,build,min(time.time()+args.max_wall_sec,resource.DEADLINE.timestamp()),writer,report['proof'],args.device) as worker:
                rc=run_suite(worker,texts,budget,report)
            need(report['proof'].get('worker_returncode')==0 and report['proof'].get('worker_cleanup_complete') is True
                 and not report['proof'].get('cleanup_diagnostics') and not report['proof'].get('telemetry_errors'),
                 'native worker exit/cleanup/telemetry differs')
            report['idle_after']=require_idle_gpu()
            need(identity()==source and native.asset_identity('gpt2_q4km')==assets,'native source/assets changed')
    except BaseException as exc:
        report['status']='ERROR_NOT_COMPLETE';report['error']=dict(type=type(exc).__name__,message=str(exc)[:2000]);rc=9
    finally:
        report['wire_manifest']=writer.close(lineage=dict(schema=SCHEMA,complete=rc==0))
        report.update(exit_code=rc,seconds=time.monotonic()-budget.started,ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output,report);print(json.dumps(dict(status=report['status'],exit_code=rc,seconds=report['seconds'])))
    return rc

if __name__=='__main__':raise SystemExit(main())
