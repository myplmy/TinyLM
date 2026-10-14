"""Bounded16 actual public source QA with exact selected reference in student input."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import p106b_visible_source as contract
from scripts import p106b_gemma_labels as teacher
from scripts import diag_p101a_sft_mtp as files
from scripts import diag_p106b_gemma_mtp_production as locked
from scripts import diag_p106b_gemma_telemetry_resume as telemetry
from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
from scripts.diag_p106b_gemma_ac import count_prompt
from scripts.p106b_shards import ShardWriter,verify
TARGET=ROOT/'test_result/evidence/p106b_visible_source16_v2_s1337'
KO=ROOT/'HF/sft_ready/p106b_gemma_deficit_mtp_v4/batch_000005'


def read_raw(directory,manifest):
    verify(directory,manifest)
    return [json.loads(l) for shard in manifest['shards'] for l in (directory/shard['path']).read_text().splitlines()]


def sources():
    kr=json.loads((KO/'report.json').read_text());ko=read_raw(KO,kr['raw_manifest']);selected={}
    for row in ko:
        if row.get('language')!='ko' or row.get('task')!='qa' or row.get('turn')!=1:continue
        source=row['source'];sid=source['meta']['source_id']
        selected.setdefault(sid,dict(language='ko',source=source,source_id=sid))
    required=['train-00000-of-00002.parquet:10652','train-00000-of-00002.parquet:10655']
    if not all(k in selected for k in required):raise FileNotFoundError('reported real cases required')
    chosen=[selected[k] for k in required]
    extras=sorted([v for k,v in selected.items() if k not in required],key=lambda r:contract.sha(r['source']['messages']))
    chosen+=extras[:6]
    rp=locked.SOURCE/'report.json'
    if locked.digest(rp)!=locked.SOURCE_SHA:raise ValueError('original family64 changed')
    report=json.loads(rp.read_text());raw=read_raw(locked.SOURCE,report['raw_manifest']);english={}
    for row in raw:
        job=row['job']
        if job['language']=='en' and job['task']=='qa':
            source=job['original'];sid=source['meta']['source_id']
            english.setdefault(sid,dict(language='en',source=source,source_id=sid))
    chosen+=sorted(english.values(),key=lambda r:contract.sha(r['source']['messages']))[:8]
    if len(chosen)!=16:raise FileNotFoundError('exact8KO/8EN actual source panel required')
    return chosen,dict(ko_report_sha256=files.data.digest(KO/'report.json'),
        family64_sha256=locked.SOURCE_SHA,source_originals_sha256=contract.sha(chosen))


def preflight():
    if TARGET.exists() or TARGET.is_symlink():raise FileExistsError('old source panel is immutable')
    selected,identity=sources()
    if files.data.digest(files.data.TOKENIZER)!=files.data.TOK_SHA:raise ValueError('tokenizer changed')
    for item in selected:contract.source_spans(item['source'])
    return selected,dict(identity,schema=contract.VERSION,source_count=16,language_rows={'ko':8,'en':8},
        max_attempts_per_source=3,maximum_physical_requests=48,mtp=True,
        sampler=teacher.SAMPLER,context=teacher.CONTEXT,total_output=teacher.MAX_OUTPUT,thinking_budget=teacher.THINKING,
        tokenizer_sha256=files.data.TOK_SHA,student_training='NOT_RUN',source_quality='PSEUDO_UNVERIFIED',
        code_sha256={p:files.data.digest(ROOT/p) for p in ('scripts/p106b_visible_source.py',
            'scripts/diag_p106b_visible_source16.py','scripts/test_p106b_visible_source.py',
            'scripts/p106b_gemma_labels.py','scripts/p106b_gemma_teacher.py','scripts/p106b_memory_stream.py',
            'scripts/diag_p106b_gemma_ac.py')})


def input_budget(session,payload):
    return count_prompt(session,payload['messages'],teacher.CONTEXT,teacher.MAX_OUTPUT)


def execute(args):
    from tokenizers import Tokenizer
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    panel,info=preflight();idle_before_gpu();TARGET.mkdir(parents=True,exist_ok=False)
    raw=ShardWriter(TARGET,'teacher_raw');candidates=ShardWriter(TARGET,'canonical')
    tok=Tokenizer.from_file(str(files.data.TOKENIZER));started=time.perf_counter();results=[];rc=9;status='STARTED';metrics={}
    try:
        with wall_limit(args.max_wall_sec),PersistentMemory() as source:
            reader=telemetry.RetryingMemoryReader(source,emit=lambda line:print(line,flush=True))
            with stream_session_scope(reader),teacher.GemmaSession(True) as session:
                for i,item in enumerate(panel):
                    spans=contract.source_spans(item['source']);feedback='';accepted=False
                    for attempt in range(1,contract.MAX_ATTEMPTS+1):
                        session.check();payload=contract.payload(spans,item['language'],202610141000+i*10+attempt,feedback)
                        budget=input_budget(session,payload)
                        tokens=budget['prompt_tokens']
                        if tokens+teacher.MAX_OUTPUT+128>teacher.CONTEXT:raise ValueError('teacher input/output budget exceedscontext; no silent crop')
                        tick=time.perf_counter();reply=session.request('/v1/chat/completions',payload,timeout=180)
                        parsed=teacher.parsed_response(reply,item['language']);candidate=None;reason=''
                        try:
                            if parsed['format_status']!=teacher.COMPLETE:raise ValueError(parsed.get('parse_error') or parsed['format_status'])
                            candidate=contract.wrap(parsed['parsed_content'],spans,item['source'],item['language'],tok)
                        except ValueError as exc:reason=str(exc)
                        record=dict(source=item['source'],source_id=item['source_id'],language=item['language'],
                            attempt=attempt,payload=payload,input_budget=budget,reply=reply,parsed=parsed,
                            canonical=candidate,structural_reason=reason,seconds=time.perf_counter()-tick,
                            raw_reasoning_in_student=False)
                        raw.append(record)
                        print('[VISIBLE_SUPPORT_ANSWER] '+json.dumps(dict(source_id=item['source_id'],language=item['language'],
                            attempt=attempt,final=parsed.get('teacher_final_content'),reason=reason,
                            student_question=contract.text(candidate['messages'][0]) if candidate else None,
                            student_answer=contract.text(candidate['messages'][1]) if candidate else None),ensure_ascii=False),flush=True)
                        if candidate is not None:
                            candidates.append(candidate);accepted=True;break
                        feedback=reason
                    results.append(dict(source_id=item['source_id'],language=item['language'],accepted=accepted,attempts=attempt))
                metrics=dict(memory=session.memory(),telemetry=reader.snapshot(),persistent=source.snapshot())
        status='VISIBLE_SOURCE16_COLLECTION_COMPLETE';rc=0
    except BaseException as exc:
        rc=130 if isinstance(exc,KeyboardInterrupt) else 9;status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR'
        metrics['error']=dict(type=type(exc).__name__,reason=str(exc)[:1000])
    finally:
        rawmanifest=raw.close(lineage=info);verify(TARGET,rawmanifest)
        candidate_manifest=candidates.close(lineage=info);verify(TARGET,candidate_manifest)
        files.write(TARGET/'report.json',dict(info,status=status,returncode=rc,results=results,
            accepted_groups=sum(r['accepted'] for r in results),raw_manifest=rawmanifest,candidate_manifest=candidate_manifest,
            metrics=metrics,whole_sec=time.perf_counter()-started,bulk_adopted=False,
            semantics='PENDING_OFFLINE_REVIEW; source ID byte checks not semantic support or independent truth',
            original_generation14_and_batches_mutated=False))
    return rc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=900)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=1800:p.error('bounded teacher-only panel required')
    if a.check_only:print('[CHECK_ONLY] '+json.dumps(preflight()[1]));return 0
    return execute(a)

if __name__=='__main__':raise SystemExit(main())
