"""Only tokenizer/JSON CPU experiment for a disclosed optional byte policy."""
from __future__ import annotations
import argparse,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.diag_p106b_dvlm_head_map import digest,read,write,STUDENT,TEACHER
from scripts.p106b_shards import verify,ShardWriter
from scripts.p106b_dvlm_head_bytes import extend_invalid_utf8
BASE=ROOT/'test_result/evidence/p106b_dvlm_head_bytes_v1_20261117'
OLD=ROOT/'test_result/evidence/p106b_dvlm_head_map_v1_20261117'
SOURCES=('scripts/diag_p106b_dvlm_head_bytes.py','scripts/p106b_dvlm_head_bytes.py',
    'scripts/test_p106b_dvlm_head_bytes.py','scripts/p106b_dvlm_head.py','scripts/p106b_dvlm_pts.py',
    'scripts/p106b_alm_bytes.py','scripts/p106b_shards.py','scripts/diag_p106b_dvlm_head_map.py')
def load_old():
    p=read(OLD/'profile.json');r=read(OLD/'actual/report.json')
    if r['returncode']!=8 or r['counts'].get('HOLD')!=205 or r['student_vocab_size']!=32768:
        raise ValueError('exact original strict full map HOLD205 required')
    for name,sha in {**p['sources'],**p['inputs']}.items():
        if digest(ROOT/name)!=sha:raise ValueError('original strict inputs/source changed')
    verify(OLD/'actual',r['manifest'])
    rows=[]
    for shard in r['manifest']['shards']:
        rows.extend(json.loads(line) for line in (OLD/'actual'/shard['path']).read_text(encoding='utf-8').splitlines())
    mapping={key:r[key] for key in ('counts','student_vocab_size','teacher_native_vocab_size','complete','shared_matching','unmatched_policy','quality_claim')}
    mapping['records']=rows
    return p,r,mapping
def prepare():
    old,r,_mapping=load_old()
    inputs={str((OLD/name).relative_to(ROOT)):digest(OLD/name)for name in ('profile.json','actual/report.json')}
    inputs.update({name:digest(ROOT/name)for name in (STUDENT,TEACHER)})
    for shard in r['manifest']['shards']:
        path=OLD/'actual'/shard['path'];inputs[str(path.relative_to(ROOT))]=digest(path)
    p=dict(UTC=datetime.now(timezone.utc).isoformat(),user_directive=158,CPU_contracts=5,
        sources={n:digest(ROOT/n)for n in SOURCES},inputs=inputs,original_counts=r['counts'],
        original_HPA='NEGATIVE_UNCHANGED;ORIGINAL7_NOT_RUN',model_loads=0,weight_tensor_reads=0,GPU=0,
        policy='ONLY_INVALID_UTF8_ORDINARY_HOLD205;EXACT_NATIVE_BYTE_BPE_DECOMPOSITION;NO_RANDOM_ZERO_OR_LOSSY_FILL')
    BASE.mkdir(exist_ok=False);write(BASE/'profile.json',p)
    print('BYTE_PROFILE',digest(BASE/'profile.json'),flush=True)
def actual():
    start=time.perf_counter();p=read(BASE/'profile.json')
    def check():
        if datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-17T16:40:00+09:00'):
            raise TimeoutError('current CPU experiment cutoff')
        if p['sources']!={n:digest(ROOT/n)for n in SOURCES}:raise ValueError('frozen byte-policy source changed')
        for n,sha in p['inputs'].items():
            if digest(ROOT/n)!=sha:raise ValueError('original strict source changed')
    check();directory=BASE/'actual';directory.mkdir(exist_ok=False)
    report=dict(status='STARTED',returncode=1,user_directive=158,model_loads=0,weight_tensor_reads=0,
        GPU_calls=0,head_allocations=0,training_steps=0,optimizer_updates=0,checkpoint_writes=0,quality_claim=False)
    try:
        _old,_r,mapping=load_old();student=read(ROOT/STUDENT);teacher=read(ROOT/TEACHER)
        from tokenizers import Tokenizer
        tokenizer=Tokenizer.from_file(str(ROOT/TEACHER))
        result=extend_invalid_utf8(mapping,student,teacher,
            bpe_tokenize=lambda spelling:[token.id for token in tokenizer.model.tokenize(spelling)])
        old_rows=mapping['records'];new_rows=result['records'];changed=[]
        for old,new in zip(old_rows,new_rows):
            if old!=new:
                if old['method']!='HOLD' or new['method']!='MEAN_NATIVE_BYTE_BPE':raise ValueError('nonhold row changed')
                changed.append(old['student_id'])
        if len(changed)!=205 or len(new_rows)!=32768 or not result['complete']:
            raise ValueError('whole205 changes and complete32768 required')
        writer=ShardWriter(directory,'mapping',limit=1_000_000)
        for row in new_rows:writer.append(row)
        manifest=writer.close(lineage=dict(profile_sha256=digest(BASE/'profile.json'),
            original_strict_report_sha256=digest(OLD/'actual/report.json'),new_policy=True))
        verify(directory,manifest)
        report.update(status='OPTIONAL_BYTE_MAPPING_COMPLETE',returncode=0,manifest=manifest,
            counts=result['counts'],original_counts=result['original_strict_counts'],complete=True,
            student_rows=32768,changed_rows=205,unchanged_nonhold_rows=32563,
            changed_ids=changed,changes=result['changes'],byte_policy=result['unmatched_policy'],
            original_strict_HOLD205_preserved=True,original_HPA_negative_preserved=True,
            original_PTS_admission_unchanged=True,actual_head_initialization='NOT_RUN')
        check();report['sources_inputs_unchanged']=True
    except BaseException as exc:
        report.update(status='BYTE_MAPPING_ERROR',returncode=1,error=dict(type=type(exc).__name__,message=str(exc)))
    report['wall_seconds']=time.perf_counter()-start;write(directory/'report.json',report)
    print('BYTE_TERMINAL',report['status'],report['returncode'],report.get('counts'),report['wall_seconds'],flush=True)
    return report['returncode']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','actual'));args=parser.parse_args()
    if args.action=='prepare':prepare();return 0
    return actual()
if __name__=='__main__':raise SystemExit(main())
