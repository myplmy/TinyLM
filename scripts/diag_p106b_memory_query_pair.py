"""Bounded teacher-only paired memory instrumentation, old production unchanged."""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import copy
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_mtp_production as original
from scripts import diag_p106b_gemma_telemetry_resume as telemetry
from scripts import p106b_memory_stream as stream
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
from scripts.p106b_shards import ShardWriter,verify
TARGET=ROOT/'test_result/evidence/p106b_memory_query_v1_s1337'


def check():
    if TARGET.exists() or TARGET.is_symlink():raise FileExistsError('old diagnostic is immutable')
    units,sha=original.sources('production')
    return units,dict(schema='P106B_MEMORY_BACKEND_PAIR_V1',source_raw_sha256=sha,
        source_ids=[u['source_group_id'] for u in units],requested_loop_ms=2000,
        mtp=True,max_output=3072,thinking_budget=1024,context=8192,
        same_payload_seed_sampler=True,student_training='NOT_RUN',download=False,
        code_sha256={name:original.digest(ROOT/name) for name in
            ('scripts/diag_p106b_memory_query_pair.py','scripts/p106b_memory_stream.py',
             'scripts/test_p106b_memory_stream.py','scripts/p106b_gemma_teacher.py',
             'scripts/diag_p106b_qwen_coload.py','scripts/diag_p106b_mtp_teacher.py')})


def execute(args):
    units,info=check();idle_before_gpu();TARGET.mkdir(parents=True,exist_ok=False)
    raw=ShardWriter(TARGET,'teacher_raw');began=time.perf_counter();arms=[];rc=9
    try:
        with wall_limit(args.max_wall_sec):
            for repeat in (0,1):
                for backend in (('one_shot','persistent') if repeat==0 else ('persistent','one_shot')):
                    arm=dict(repeat=repeat,backend=backend,status='STARTED',requests=[])
                    arms.append(arm)
                    with ExitStack() as stack:
                        source=(stack.enter_context(stream.PersistentMemory()) if backend=='persistent'
                                else telemetry.memory_source.read_memory)
                        latencies=[]
                        def observed():
                            tick=time.perf_counter()
                            try:return source()
                            finally:latencies.append(time.perf_counter()-tick)
                        reader=telemetry.RetryingMemoryReader(observed,emit=lambda line:print(line,flush=True))
                        stack.enter_context(stream.stream_session_scope(reader) if backend=='persistent'
                            else telemetry.telemetry_scope(reader))
                        session=stack.enter_context(original.teacher.GemmaSession(True))
                        arm['startup_sec']=session.startup_sec
                        for unit in units:
                            session.check();payload=copy.deepcopy(unit['request'])
                            tick=time.perf_counter();reply=session.request('/v1/chat/completions',payload,timeout=180)
                            seconds=time.perf_counter()-tick
                            parsed=original.teacher.parsed_response(reply,unit['language'])
                            error=None
                            try:turn,trace,_=original.rendered(unit,reply)
                            except ValueError as exc:turn,trace=None,None;error=str(exc)
                            record=dict(repeat=repeat,backend=backend,id=unit['id'],payload=payload,
                                source_group_id=unit['source_group_id'],reply=reply,parsed=parsed,
                                rendered=turn,output_trace=trace,structure_error=error,request_sec=seconds)
                            raw.append(record)
                            summary=dict(id=unit['id'],seconds=seconds,wire_complete=turn is not None,
                                finish_reason=parsed['finish_reason'],structure_error=error)
                            arm['requests'].append(summary)
                            print('[MEMORY_PAIR_ANSWER] '+json.dumps(dict(summary,repeat=repeat,backend=backend,
                                teacher_final=parsed.get('teacher_final_content')),ensure_ascii=False),flush=True)
                        arm.update(memory=session.memory(),telemetry=reader.snapshot(),
                            query_attempt_latency_sec=latencies,
                            persistent_frames=source.snapshot() if backend=='persistent' else None,
                            owned_query_process_starts=(1 if backend=='persistent' else
                                reader.successes+reader.timeouts+reader.failed))
                        arm['status']='COMPLETE'
        rc=0;status='MEMORY_BACKEND_PAIR_COMPLETE'
    except BaseException as exc:
        status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'EXECUTION_ERROR'
        rc=130 if isinstance(exc,KeyboardInterrupt) else 9
        info['error']=dict(type=type(exc).__name__,message=str(exc)[:1000])
    finally:
        manifest=raw.close(lineage=info)
        verify(TARGET,manifest)
        original.write_json(TARGET/'report.json',dict(info,status=status,returncode=rc,arms=arms,
            raw_manifest=manifest,whole_sec=time.perf_counter()-began,
            adopted=False,semantic_truth='NOT_REVIEWED',continuous_peak_verified=False,
            interpretation='instrumentation/source transport collection only; no automatic production switch'))
    return rc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=900)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=1800:p.error('bounded diagnostic required')
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(check()[1]));return 0
    return execute(a)

if __name__=='__main__':raise SystemExit(main())
