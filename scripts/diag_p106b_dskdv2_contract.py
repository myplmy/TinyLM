"""Model-free DSKDv2 exact-position inventory on the unchanged TRAIN128."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
from scripts import p106b_dskdv2_contract as d
from scripts.p106b_shards import ShardWriter,verify as verify_shards

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'test_result/evidence/p106b_actd_top128_v1_20261113'
BASE=ROOT/'test_result/evidence/p106b_dskdv2_contract_v1_20261113'
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SOURCES=('scripts/p106b_dskdv2_contract.py','scripts/test_p106b_dskdv2_contract.py',
    'scripts/diag_p106b_dskdv2_contract.py','scripts/p106b_shards.py',
    'tinylm/model/transformer.py','tinylm/train/mtp_sft.py')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8')as f:f.write(json.dumps(obj,ensure_ascii=False,indent=2)+chr(10))


def main():
    start=time.perf_counter()
    if (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:raise TimeoutError('authority cleanup reserve')
    if BASE.exists():raise FileExistsError('fresh DSKDv2 namespace required')
    p=read(SOURCE/'profile.json');w=read(SOURCE/'ROOT_PREPARE_EXIT_v1.json')
    if w.get('actual_process_exit_code')!=0 or w.get('profile_sha256')!=digest(SOURCE/'profile.json'):
        raise ValueError('closed same original prepared rows required')
    manifest=read(SOURCE/'prepared_shards_manifest.json');verify_shards(SOURCE,manifest)
    references={str((SOURCE/n).relative_to(ROOT)):digest(SOURCE/n) for n in
                ('profile.json','ROOT_PREPARE_EXIT_v1.json','prepare_report.json','prepared_shards_manifest.json')}
    for shard in manifest['shards']:references[str((SOURCE/shard['path']).relative_to(ROOT))]=digest(SOURCE/shard['path'])
    profile=dict(schema='P106B_DSKDV2_CPU_CONTRACT_V1',tag=BASE.name,authority_directive=115,
        deadline=DEADLINE.isoformat(),sources={n:digest(ROOT/n) for n in SOURCES},references=references,
        original_student_checkpoint=p['student_checkpoint'],teacher_vocab=248320,student_vocab=32768,
        original_ce_preserved=True,partial_token_fallback=False,future_prefix_alignment=False,
        observed_aligned_gold_is_candidate_upper_bound=True,model_calls=0,gpu_calls=0,
        optimizer_updates=0,checkpoint_writes=0,quality_claim=False)
    write(BASE/'profile.json',profile);writer=ShardWriter(BASE,'positions',limit=3_000_000)
    counts=Counter();per_language={};failure=None
    try:
        for shard in manifest['shards']:
            for line in (SOURCE/shard['path']).read_text().splitlines():
                if time.perf_counter()-start>300 or (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
                    raise TimeoutError('CPU phase/authority reserve')
                row=json.loads(line);pack=row['packed'];s=pack['student'];teacher=row['teacher']
                if row['teacher_oversized']:raise ValueError('prepared teacher sequence must fit unchanged1024')
                ce=sum(x!=-100 for x in s['labels'][1:])
                if ce!=row['ce_targets'] or len(s['ids'])-1!=s['x_tokens']:
                    raise ValueError('same original one-shift CE and x required')
                pairs,holds=d.exact_pairs(pack['text'],s['byte_spans'],teacher['byte_spans'])
                if len(pairs)+len(holds)!=ce:raise ValueError('every original CE target needs exact/HOLD accounting')
                for pair in pairs:
                    i=pair['student_predictor_raw_index'];j=pair['teacher_predictor_raw_index']
                    if s['labels'][i+1]!=pair['student_target_id'] or teacher['ids'][j+1]!=pair['teacher_target_id']:
                        raise ValueError('single-shift aligned native target changed')
                lang=per_language.setdefault(row['language'],Counter())
                for counter in (counts,lang):
                    counter.update(rows=1,actual_x_tokens=s['x_tokens'],original_ce_targets=ce,
                        exact_gold_candidates=len(pairs),not_exact_holds=len(holds),actual_native_top1_verified=0,
                        zero_lookahead_pairs=sum(x['lookahead_bytes']==0 for x in pairs))
                writer.append(dict(row_id=row['row_id'],frozen_index=row['frozen_index'],language=row['language'],
                    source_row_sha256=row['source_row_sha256'],record_sha256=row['record_sha256'],ce_targets=ce,
                    exact_gold_candidates=pairs,holds=holds,actual_teacher_top1_status='NOT_COLLECTED_FOR_DSKD',
                    original_ce_unchanged=True))
        if counts['rows']!=128 or counts['actual_x_tokens']!=32216 or counts['original_ce_targets']!=772:
            raise ValueError('original frozen TRAIN128 inventory changed')
        for name,sha in dict(profile['sources'],**references).items():
            if digest(ROOT/name)!=sha:raise ValueError('pinned source/original prepared artifact changed: '+name)
        status='CPU_INVENTORY_COMPLETE_TEACHER_HEAD_VJP_NOT_RUN'
    except BaseException as exc:status='ERROR';failure=exc
    finally:
        m=writer.close(lineage=dict(tag=BASE.name,profile_sha256=digest(BASE/'profile.json')));verify_shards(BASE,m)
        report=dict(status=status,counts=dict(counts),language_counts={k:dict(v)for k,v in per_language.items()},
            seconds=time.perf_counter()-start,profile_sha256=digest(BASE/'profile.json'),model_calls=0,gpu_calls=0,
            optimizer_updates=0,checkpoint_writes=0,quality_claim=False,native_head_adapter_verified=False,
            actual_teacher_top1_verified=False,projectors_fitted_to_actual_heads=False,
            student_factored_head_rank_upper_bound=256,student_hidden_width=768,
            sources_assets_unchanged=failure is None,error=None if failure is None else repr(failure))
        write(BASE/'report.json',report)
    if failure is not None:raise failure
    print('[DSKDV2_CPU_FINAL] '+json.dumps(dict(status=status,counts=dict(counts),seconds=report['seconds'])),flush=True)


if __name__=='__main__':main()
