"""Full native student head mapping only; no model, weight or CUDA loading."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,signal,sys,time,traceback
from pathlib import Path
import tinylm
from scripts.p106b_dvlm_head import initialization_map
from scripts.p106b_shards import ShardWriter

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'test_result/evidence/p106b_dvlm_head_map_v1_20261117'
PROFILE=BASE/'profile.json'
STUDENT='data_cache/tok-ko-en-32768-chat32.json'
TEACHER='HF/models--Qwen3-0.6B-Base/tokenizer.json'
CONTRACT='handoff/audit/research_20261117_01a1e647/CPU_NEW_METHOD_CONTRACTS_v1.json'
NATIVE='test_result/evidence/p106b_dvlm_native_closure_v3_20261117/actual/report.json'
PLAN='test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md'
SOURCES=('scripts/diag_p106b_dvlm_head_map.py','scripts/p106b_dvlm_head.py',
    'scripts/test_p106b_dvlm_head.py','scripts/p106b_alm_bytes.py','scripts/p106b_dvlm_pts.py','scripts/p106b_shards.py')
CUTOFF=datetime(2026,11,17,7,40,tzinfo=timezone.utc)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
    return h.hexdigest().upper()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path,value):
    data=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(data)>=20_000_000:raise ValueError('owned metadata cap20MB')
    with Path(path).open('xb') as stream:stream.write(data)

def guard():
    if datetime.now(timezone.utc)>=CUTOFF or (BASE/'STOP').exists():raise TimeoutError('head-map cutoff/owned STOP')

def prepare():
    guard()
    if BASE.exists():raise FileExistsError('preserve full head-map namespace')
    contract=read(ROOT/CONTRACT);native=read(ROOT/NATIVE)
    if not contract['successful'] or contract['contracts_by_module']['DVLM_HEAD']!=6:
        raise ValueError('existing6 completed CPU head contracts required')
    for source in ('scripts/p106b_dvlm_head.py','scripts/test_p106b_dvlm_head.py','scripts/p106b_alm_bytes.py'):
        if digest(ROOT/source)!=contract['source_SHA256'][source]:raise ValueError('head contract source changed')
    BASE.mkdir()
    with (BASE/'initial_plan.md').open('xb') as stream:stream.write((ROOT/PLAN).read_bytes())
    profile=dict(schema='P106B_DVLM_FULL_STUDENT_HEAD_MAP_V1',authority_directive=158,
        cutoff=CUTOFF.isoformat(),sources={name:digest(ROOT/name) for name in SOURCES},
        inputs={name:digest(ROOT/name) for name in (STUDENT,TEACHER,CONTRACT,NATIVE)},
        initial_plan_sha256=digest(BASE/'initial_plan.md'),student_native_vocab=32768,
        native_teacher_output_vocab=native['vocab_size'],observed_native_head_source_tensor=native['exact_head_source_tensor'],
        observed_native_head_sha256=native['output_head_weight_sha256'],
        inherited_head_CPU_contracts=6,max_compute_seconds=600,max_phase_seconds=660,
        max_output_bytes=50_000_000,model_loads=0,weight_tensor_reads=0,CUDA=False,
        scope='COMPLETE_VOCABULARY_TOKEN_MAPPING_ONLY;NO_ALLOCATION;HPA_OR_QUALITY_NOT_PROMOTED',
        policies=dict(shared='RAW_NATIVE_BYTES/KIND/ADDED_PROPERTIES',
            unmatched='LOSSLESS_STANDALONE_UTF8_REENCODING',hold='NO_RANDOM_ZERO_FILL_OR_ROW_DROPPING'))
    write(PROFILE,profile);print('[HEAD_MAP_PREPARED]existing6 contracts reused;32768 rows;model/weights/CUDA0')

def verify():
    guard();p=read(PROFILE)
    if (p['cutoff']!=CUTOFF.isoformat() or p['authority_directive']!=158
            or p['sources']!={name:digest(ROOT/name) for name in SOURCES}
            or p['inputs']!={name:digest(ROOT/name) for name in p['inputs']}
            or p['initial_plan_sha256']!=digest(BASE/'initial_plan.md')):
        raise ValueError('frozen head-map profile mismatch')
    return p

def actual():
    guard();p=verify();out=BASE/'actual';out.mkdir();start=time.monotonic()
    report=dict(schema=p['schema'],status='INCOMPLETE',returncode=1,authority_directive=158,
        profile_sha256=digest(PROFILE),model_loads=0,weight_tensor_reads=0,CUDA_initializations=0,
        head_allocations=0,training_steps=0,optimizer_updates=0,checkpoint_writes=0,quality_claim=False)
    previous=signal.getsignal(signal.SIGALRM)
    def expired(*_):raise TimeoutError('full mapping600sec cap;partial evidence retained')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,600)
    try:
        from tokenizers import Tokenizer
        student=Tokenizer.from_file(str(ROOT/STUDENT));teacher=Tokenizer.from_file(str(ROOT/TEACHER))
        mapping=initialization_map(read(ROOT/STUDENT),read(ROOT/TEACHER),
            decode_student=lambda ids:student.decode(ids,skip_special_tokens=False),
            encode_teacher=lambda text:teacher.encode(text,add_special_tokens=False).ids,
            decode_teacher=lambda ids:teacher.decode(ids,skip_special_tokens=False))
        guard()
        records=mapping.pop('records')
        if len(records)!=p['student_native_vocab'] or [r['student_id'] for r in records]!=list(range(32768)):
            raise ValueError('complete original dense32768 student row coverage required')
        if any(r['teacher_ids'] is not None and any(i>=p['native_teacher_output_vocab'] for i in r['teacher_ids']) for r in records):
            raise ValueError('mapped teacher token exceeds observed native head')
        writer=ShardWriter(out,'mapping',limit=1_000_000)
        for row in records:writer.append(row)
        manifest=writer.close(lineage=dict(profile_sha256=digest(PROFILE),native_student_rows=32768))
        reason_counts=dict(Counter(row.get('reason','') for row in records if row['method']=='HOLD'))
        report.update(mapping,manifest=manifest,hold_reason_counts=reason_counts,
            all_original_rows_preserved=True,head_allocation_permitted=mapping['complete'],
            head_forward_backward_permitted=False,
            status='FULL_NATIVE_MAPPING_COMPLETE_COMPONENT_ONLY' if mapping['complete'] else 'FULL_NATIVE_MAPPING_HOLD',
            returncode=0 if mapping['complete'] else 8)
    except BaseException as error:
        report.update(status='FULL_MAPPING_ERROR',returncode=1,
            error=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
        try:verify();report['sources_inputs_unchanged']=True
        except BaseException as error:report.update(sources_inputs_unchanged=False,closure_error=str(error),returncode=9)
        report['wall_seconds']=time.monotonic()-start
        write(out/'report.json',report)
        print(json.dumps(report,ensure_ascii=False),flush=True)
    return report['returncode']

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','check','actual'))
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='check':verify();print('[HEAD_MAP_CHECK]frozen source/input matched;no model/weights')
    else:raise SystemExit(actual())

if __name__=='__main__':main()
