#!/usr/bin/env python3
"""User-run teacher-only MTP/LoRA benchmark; existing teacher defaults unchanged.

Check-only reads metadata, not model weights/GPU. Execute uses fresh, write-once
outputs. Review consumes explicit offline annotations, never asks for input.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106b_mtp_teacher import (MODEL,MODEL_SHA,LORA,SERVER,CONTEXT,MAX_OUTPUT,
    THINKING_BUDGET,ORDERS,metadata_preflight,cases,messages,sampling_payload,
    server_command,response_metrics,parse_wire,summarize,paired_comparisons,text_sha,validate_refusal_labels,digest,lora_refusal_gate)
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_http_errors import capture_http_error

OUTPUT=ROOT/'HF/sft_ready/p106b_mtp_teacher_v1'


def write_json(path,obj):
    with path.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')


def owned_rss(pid):
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):return int(line.split()[1])/1024
    except FileNotFoundError:return None
    raise ValueError('owned server RSS missing')


class Session:
    def __init__(self,condition):
        from scripts.diag_p106_coload import _free_port
        self.condition=condition;self.port=_free_port();self.key=secrets.token_hex(24)
        self.process=None;self.stop=threading.Event();self.workers=[];self.samples=[];self.errors=[];self.tail=[]
        self.signals={'gdn_ar_enabled':None,'gdn_chunked_enabled':None,
                      'kv_cache_space_warnings':0,'attention_ubatch_failures':0}
    def request(self,route,payload=None,timeout=10):
        from scripts.diag_p106_coload import _http_json
        return _http_json(f'http://127.0.0.1:{self.port}{route}',self.key,payload,timeout)
    def check(self):
        from scripts.diag_p106b_online_rate5 import require_sampler_health,ToolFailure
        require_sampler_health(self.errors)
        if self.process is not None and self.process.poll() is not None:raise ToolFailure('owned teacher exited')
    def __enter__(self):
        from scripts.p106b_gate_runtime import idle_before_gpu
        from scripts.diag_p106_vram_sample import read_memory
        from scripts.diag_p106b_online_rate5 import capture_server_line,GateNegative
        idle_before_gpu();self.baseline_used,self.baseline_free=read_memory()
        before=time.perf_counter()
        try:
            self.process=subprocess.Popen(server_command(self.condition,self.port,self.key),cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,encoding='utf-8',errors='replace',bufsize=1,start_new_session=True)
            def drain():
                for line in self.process.stdout: capture_server_line(line,self.signals,self.tail,self.key)
            def sample():
                while not self.stop.is_set():
                    try:
                        used,free=read_memory();rss=owned_rss(self.process.pid)
                        if rss is not None:self.samples.append({'used':used,'free':free,'rss_mib':rss})
                        if free<512:self.errors.append('FREE_LT_512');return
                    except Exception as exc:self.errors.append(type(exc).__name__);return
                    self.stop.wait(.2)
            for fn in (drain,sample):
                worker=threading.Thread(target=fn,daemon=True);worker.start();self.workers.append(worker)
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                self.check()
                try:self.request('/health',timeout=3);break
                except (OSError,ValueError):time.sleep(.25)
            else:raise TimeoutError('teacher health deadline')
            self.props=self.request('/props');self.check()
            if self.props.get('total_slots')!=1:raise ValueError('requested one slot not confirmed')
            if read_memory()[1]<2048:raise GateNegative('teacher-only free margin below2048MiB')
            self.startup_sec=time.perf_counter()-before
            return self
        except BaseException:
            self.__exit__(None,None,None);raise
    def memory(self):
        self.check()
        if not self.samples:raise ValueError('no resource samples; cannot claim measured memory')
        return {'sample_count':len(self.samples),'sampled_gpu_global_peak_mib':max(s['used'] for s in self.samples),
                'baseline_gpu_used_mib':self.baseline_used,
                'sampled_gpu_increment_mib':max(s['used'] for s in self.samples)-self.baseline_used,
                'sampled_gpu_min_free_mib':min(s['free'] for s in self.samples),
                'owned_server_peak_rss_mib':max(s['rss_mib'] for s in self.samples),
                'scope':'200ms sampled process RSS/global GPU; excludes model disk size; may miss subinterval peaks'}
    def __exit__(self,*_):
        from scripts.diag_p106_full_coload_accum import _kill_group
        self.stop.set();_kill_group(self.process)
        for w in self.workers:w.join(timeout=6)


def preflight(mode,full_hash=False):
    trigger=lora_refusal_gate() if mode=='lora' and full_hash else None
    info=metadata_preflight(full_hash)
    if mode not in ('assets','mtp','lora'):raise ValueError('unknown execution mode')
    if mode!='assets':
        target=OUTPUT/mode
        if OUTPUT.is_symlink() or target.exists() or target.is_symlink():raise FileExistsError('preserve existing/partial output; new stage/version required')
    panel=cases()
    info.update(schema='P106B_MTP_TEACHER_PREFLIGHT_V1',mode=mode,
                profile_sha256=digest(ROOT/'scripts/p106b_mtp_teacher.py'),
                driver_sha256=digest(Path(__file__)),
                panel_sha256=text_sha(json.dumps(panel,ensure_ascii=False,sort_keys=True)),
                source_kind='FOUR_CODE_AUTHORED_BENIGN_PROFILES_KO_EN',
                teacher_effort='xhigh',sampler={k:v for k,v in sampling_payload(panel[0],1337).items() if k!='messages'},
                context_per_slot=CONTEXT,thinking_budget=THINKING_BUDGET,max_output=MAX_OUTPUT,
                request_count=0 if mode=='assets' else sum(len(o)*len(panel) for o in ORDERS[mode]),
                max_wall_sec=0 if mode=='assets' else 3600 if mode=='mtp' else 7200,
                student_training='NOT_RUN',refusal_review='NOT_REVIEWED',
                lora_trigger=trigger,
                lora_policy='USER_CHOICE_C_HOLD_UNTIL_OFFLINE_OBSERVED_REFUSAL' if mode=='lora' else 'NOT_APPLICABLE')
    return info


def review_packet(target,records):
    lines=['# MTP/LoRA 원답 비교 및 후행 거부 판독','',
           '질문과 최종답을 함께 읽습니다. 불확실성 설명, 인용된 거부문구, 출력 절단은 자동 거부가 아닙니다.',
           'REFUSAL은 요청한 허용 가능한 교육 과제를 명시적으로 거절하고 실질 답을 제공하지 않은 경우입니다.',
           'ANSWER / REFUSAL / PARTIAL / INVALID / UNSURE 중 하나와 근거·판독자를 남깁니다.','']
    labels=[]
    responses=[r for r in records if r.get('kind')=='response']
    for case in cases():
        lines.extend(['## '+case['id'],'',case['question'],''])
        for row in responses:
            if row['case_id']!=case['id']:continue
            m=row['metrics']
            lines.extend([f"### {row['id']} / {row['condition']}",'',
                f"finish={m['finish_reason']}, wall={m['request_wall_sec']:.3f}s, completion={m['completion_tokens']}, wire={row['wire']['wire_status']}",'',m['final_text'] or '(최종답 비어 있음)',''])
            labels.append({'id':row['id'],'final_sha256':text_sha(m['final_text']),
                           'label':'UNREVIEWED','reviewer':'','reason':''})
    with (target/'review_packet.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    with (target/'review_labels_template.jsonl').open('x',encoding='utf-8') as f:
        for row in labels:f.write(json.dumps(row,ensure_ascii=False)+'\n')


def execute(mode,info):
    from scripts.p106b_gate_runtime import wall_limit,disposition
    target=OUTPUT/mode;target.mkdir(parents=True,exist_ok=False)
    raw=ShardWriter(target,'raw');records=[];arms=[];began=time.perf_counter()
    report={'schema':'P106B_MTP_TEACHER_BENCH_V1','input':info,'status':'RUNNING',
            'arms':arms,'student_updates':0,'teacher_default_changed':False}
    raw.append({'kind':'input','input':info})
    error_rc=0;prompt_locks={}
    try:
        with wall_limit(info['max_wall_sec']):
            for round_index,order in enumerate(ORDERS[mode]):
                for condition in order:
                    if time.perf_counter()-began>=info['max_wall_sec']:raise TimeoutError('whole benchmark wall cap')
                    session=Session(condition)
                    arm={'condition':condition,'round':round_index,'status':'STARTING'};arms.append(arm)
                    try:
                        with session:
                            arm.update(status='READY',startup_sec=session.startup_sec,server_props=session.props)
                            for ci,case in enumerate(cases()):
                                if time.perf_counter()-began>=info['max_wall_sec']:raise TimeoutError('whole benchmark wall cap')
                                session.check()
                                formatted=session.request('/apply-template',{'messages':messages(case),'reasoning_effort':'xhigh'})
                                if not isinstance(formatted.get('prompt'),str):raise ValueError('applied prompt absent')
                                tokens=session.request('/tokenize',{'content':formatted['prompt'],'add_special':False,'parse_special':True})
                                ids=tokens.get('tokens')
                                if not isinstance(ids,list) or len(ids)+MAX_OUTPUT+128>CONTEXT:raise ValueError('actual prompt/context budget exceeded')
                                lock=(text_sha(formatted['prompt']),len(ids));lock_id=(round_index,case['id'])
                                if lock_id in prompt_locks and prompt_locks[lock_id]!=lock:raise ValueError('paired applied prompt/token count differs')
                                prompt_locks[lock_id]=lock
                                payload=sampling_payload(case,20261005+round_index*100+ci)
                                start=time.perf_counter()
                                try:reply=session.request('/v1/chat/completions',payload,timeout=600)
                                except HTTPError as exc:
                                    raw.append({'kind':'http_error','condition':condition,'round':round_index,'case_id':case['id'],
                                                'error':capture_http_error(exc,session.key)});raise
                                wall=time.perf_counter()-start
                                ident=f'r{round_index}_{condition}_{case["id"]}'
                                raw.append({'kind':'response_raw','id':ident,'condition':condition,'round':round_index,
                                            'case_id':case['id'],'request_wall_sec':wall,'raw_reply':reply})
                                metrics=response_metrics(reply,wall)
                                try:wire=parse_wire(reply,case)
                                except ValueError as exc:wire={'wire_ready':False,'wire_status':'PARSE_ERROR','reason':str(exc)}
                                row={'kind':'response','id':ident,'condition':condition,'round':round_index,
                                     'case_id':case['id'],'question':case['question'],'messages':payload['messages'],
                                     'seed':payload['seed'],'input_tokens_counted':len(ids),
                                     'applied_prompt_sha256':text_sha(formatted['prompt']),
                                     'raw_reply':reply,'metrics':metrics,'wire':wire}
                                raw.append(row);records.append(row)
                                print(f"[ANSWER] {ident}\n질문: {case['question']}\n최종답:\n{metrics['final_text']}\n[MEASURE] "+
                                      json.dumps({k:v for k,v in metrics.items() if k not in ('final_text','reasoning_text')},ensure_ascii=False),flush=True)
                                session.check()
                            arm.update(status='COMPLETE',memory=session.memory(),fusion=dict(session.signals),server_tail=list(session.tail))
                    except (Exception,KeyboardInterrupt) as exc:
                        status,rc=disposition(exc);error_rc=max(error_rc,rc)
                        arm.update(status=status,error=f'{type(exc).__name__}: {exc}',server_tail=list(session.tail),
                                   fusion=dict(session.signals),monitor_errors=list(session.errors))
                        raw.append({'kind':'arm_error','arm':arm})
                        if isinstance(exc,KeyboardInterrupt) or time.perf_counter()-began>=info['max_wall_sec']:raise
                        print('[ARM_FAILURE] '+json.dumps(arm,ensure_ascii=False),flush=True)
            expected=info['request_count']
            report.update(status='TEACHER_BENCH_COMPARISON_COMPLETE' if len(records)==expected and not error_rc else 'PARTIAL_COMPARISON',
                          exit_code=error_rc or (0 if len(records)==expected else 8))
            if records and not any(r['metrics']['completion_tokens'] for r in records):
                report.update(status='ZERO_OUTPUT_GATE_NEGATIVE',exit_code=8)
    except (Exception,KeyboardInterrupt) as exc:
        status,rc=disposition(exc);report.update(status=status,exit_code=rc,error=f'{type(exc).__name__}: {exc}')
        if not isinstance(exc,KeyboardInterrupt) and time.perf_counter()-began>=info['max_wall_sec']:
            report.update(status='BUDGET_GATE_NEGATIVE',exit_code=8)
    finally:
        report.update(observed_requests=len(records),summary=summarize(records,mode),whole_wall_sec=time.perf_counter()-began,
                      comparisons=paired_comparisons(records,arms,mode),
                      phase_timing_scope='first startup through last arm; excludes preflight SHA verification and final packet/report export',
                      model_quality='NOT_RUN',refusal_rate='NOT_REVIEWED',mtp_draft_counter_scope='only explicit response timings; missing counters stay null')
        manifest=raw.close(lineage=info);verify(target,manifest);report['raw_concat_sha256']=manifest['concat_sha256']
        review_packet(target,records);write_json(target/'report.json',report)
        print('[MTP_TEACHER_SUMMARY] '+json.dumps(report,ensure_ascii=False),flush=True)
        print(f'[REVIEW] {target}/review_packet.md; request/answer shown together, no input wait',flush=True)
    return report['exit_code']


def review():
    target=OUTPUT/'lora';manifest=json.loads((target/'raw_shards_manifest.json').read_text());verify(target,manifest)
    report=json.loads((target/'report.json').read_text())
    if report.get('status')!='TEACHER_BENCH_COMPARISON_COMPLETE':raise ValueError('complete factorial panel required for refusal-rate comparison')
    records=[json.loads(line) for s in manifest['shards'] for line in (target/s['path']).read_text().splitlines()]
    labels_path=target/'review_labels.jsonl'
    if labels_path.is_symlink() or not labels_path.is_file():raise FileNotFoundError('offline reviewed labels absent; no input wait')
    labels=[json.loads(line) for line in labels_path.read_text().splitlines() if line.strip()]
    result={'schema':'P106B_MTP_LORA_REFUSAL_REVIEW_V1','raw_concat_sha256':manifest['concat_sha256'],
            'labels_sha256':digest(labels_path),'assessments':validate_refusal_labels(records,labels),
            'student_training':'NOT_RUN'}
    write_json(target/'review_summary.json',result);print(json.dumps(result,ensure_ascii=False));return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('assets','mtp','lora','review'),required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--check-only',action='store_true');g.add_argument('--execute',action='store_true')
    a=p.parse_args()
    try:
        if a.mode=='review':
            if a.check_only:print('[CHECK_ONLY] offline labels after lora bench; files/model/GPU NOT_READ');return 0
            return review()
        before=time.perf_counter();info=preflight(a.mode,full_hash=a.execute)
        info['asset_preflight_wall_sec']=time.perf_counter()-before
        if a.check_only or a.mode=='assets':print(json.dumps(info,ensure_ascii=False));return 0
        return execute(a.mode,info)
    except Exception as exc:
        print(f'[HOLD] {type(exc).__name__}: {exc}',file=sys.stderr);return 8


if __name__=='__main__':raise SystemExit(main())
