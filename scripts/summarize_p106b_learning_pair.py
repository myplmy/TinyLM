"""CPU paired readback of completed code-task generations, never a truth model."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import random
from scripts.p106b_shards import verify
SPECS={
 'p106b_context_replay_v2_s1337':('sealed_test','SEALED_CODE_TEST_COLLECTED','sft_only'),
 'p106b_context_orpo_v1_s1337':('fresh_test','FRESH_CODE_TEST_COLLECTED','pair_zero')}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def key(row):
    return hashlib.sha256(json.dumps(row['messages'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def summarize(rows):
    counts=Counter();kinds=defaultdict(Counter);roots=defaultdict(list)
    for row in rows:
        if row['exact_code_contract'] is None:raise ValueError('code test cannot contain unscored public answers')
        m=row['meta'];ok=row['exact_code_contract'] is True
        counts.update(cases=1,exact=int(ok),empty=int(not row['answer'].strip()),
            max_new=int(row['generation']['finish_reason'] in ('MAX_NEW','MAX_NEW_EOS_DISABLED')))
        kinds[m['language']+':'+m['kind']].update(cases=1,exact=int(ok))
        if m['kind'].startswith('binding_'):
            roots[m['semantic_root_id']].append(ok)
            counts['first_value_baseline_binding']+=int(row['gold']==m['first_value'])
    if any(len(v)!=4 for v in roots.values()):raise ValueError('binding must have complete quadruples')
    counts['binding_roots']=len(roots);counts['all4_exact_roots']=sum(all(v) for v in roots.values())
    return dict(counts=dict(counts),by_kind={k:dict(v) for k,v in kinds.items()})


def paired_interval(left,right,repetitions=2000):
    a={key(r):r for r in left};b={key(r):r for r in right}
    if a.keys()!=b.keys():raise ValueError('different actual cases')
    strata=defaultdict(lambda:defaultdict(list))
    for k,row in a.items():
        other=b[k]
        if row['gold']!=other['gold']:raise ValueError('gold differs')
        m=row['meta'];stratum=(m['language'],m['kind'])
        delta=int(other['exact_code_contract'] is True)-int(row['exact_code_contract'] is True)
        strata[stratum][m['semantic_root_id']].append(delta)
    groups=[[sum(v) for v in family.values()] for _,family in sorted(strata.items())]
    rng=random.Random(20261015);samples=[];den=len(a)
    for _ in range(repetitions):
        samples.append(sum(sum(rng.choices(g,k=len(g))) for g in groups)/den)
    samples.sort();point=sum(sum(g) for g in groups)/den
    return dict(right_minus_left=point,ci95=[samples[int((repetitions-1)*.025)],samples[int((repetitions-1)*.975)]],
        repetitions=repetitions,seed=20261015,unit='semantic root within language/task stratum',
        percentile='discrete order statistics',scope='fixed trained models/producer tasks only; training-seed sigma NOT_MEASURED')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tag',choices=tuple(SPECS),required=True)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if args.check_only:print('[CHECK_ONLY] bounded CPU readback; models0');return 0
    section,status,control=SPECS[args.tag];root=ROOT/'test_result/evidence'/args.tag
    source=root/section/'report.json';report=json.loads(source.read_text())
    if report['status']!=status:raise ValueError('completed generation collection required')
    out=root/section/'paired_summary.json'
    if out.exists():raise FileExistsError('readback preserved')
    actual={}
    for arm,value in report['arms'].items():
        folder=ROOT/value['raw_directory'];verify(folder,value['raw_manifest'])
        actual[arm]=[json.loads(line) for shard in value['raw_manifest']['shards']
                     for line in (folder/shard['path']).read_text().splitlines()]
        if len(actual[arm])!=report['cases_per_arm']:raise ValueError('case count mismatch')
    summaries={arm:summarize(rows) for arm,rows in actual.items()}
    intervals={arm:paired_interval(actual[control],rows) for arm,rows in actual.items() if arm not in ('parent',control)}
    result=dict(schema='P106B_PAIRED_CODE_LEARNING_READBACK_V1',tag=args.tag,control=control,
        source_report_sha256=digest(source),code_sha256=digest(Path(__file__)),summaries=summaries,
        paired_root_intervals=intervals,native_ce={arm:r['native']['ce'] for arm,r in report['arms'].items()},
        models_loaded=0,optimizer_updates=0,raw_modified=False,
        interpretation='strict producer output contracts; not arbitrary semantic truth or general intelligence')
    body=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if len(body.encode())>=20_000_000:raise ValueError('20MB evidence bound')
    with out.open('x',encoding='utf-8') as stream:stream.write(body)
    print('[PAIRED_CODE_READBACK] '+json.dumps(dict(summaries=summaries,native=result['native_ce'],intervals=intervals),ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
