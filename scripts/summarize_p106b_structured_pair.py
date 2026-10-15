#!/usr/bin/env python3
"""CPU fixed-model paired clusters; bilingual views of one pair stay together."""
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
SPECS={'p106b_state_update_aux_v1_s1337':('STATE_AUX_FRESH_TEST_COLLECTED','aux0'),
       'p106b_joint_decimal_v1_s1337':('JOINT_DECIMAL_FRESH_TEST_COLLECTED','digits0')}


def signature(row):return hashlib.sha256(json.dumps(row['messages'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def paired_roots(left,right,repetitions=2000):
    a={signature(r):r for r in left};b={signature(r):r for r in right}
    if len(a)!=len(left) or len(b)!=len(right) or a.keys()!=b.keys():raise ValueError('same complete unique actual questions required')
    roots=defaultdict(list)
    for key,row in a.items():
        other=b[key]
        if row['gold']!=other['gold'] or type(row['exact_code_contract']) is not bool or type(other['exact_code_contract']) is not bool:
            raise ValueError('same code gold and boolean judgments required')
        m=row['meta'];roots[(m['kind'],m['semantic_root_id'])].append((m['language'],int(other['exact_code_contract'])-int(row['exact_code_contract'])))
    strata=defaultdict(list)
    for (kind,root),values in roots.items():
        languages=tuple(sorted({v[0] for v in values}));strata[(kind,languages)].append(sum(v[1] for v in values))
    rng=random.Random(20261015);draws=[];den=len(left)
    for _ in range(repetitions):draws.append(sum(sum(rng.choices(v,k=len(v))) for _,v in sorted(strata.items()))/den)
    draws.sort();point=sum(sum(v) for v in strata.values())/den
    return dict(right_minus_left=point,ci95=[draws[int((repetitions-1)*.025)],draws[int((repetitions-1)*.975)]],
        repetitions=repetitions,seed=20261015,root_groups=len(roots),
        unit='task plus semantic root; observed root-language set stratum; bilingual views sampled together',
        scope='fixed models/current producer corpus; not trained-seed sigma/general intelligence')


def summary(rows):
    counts=Counter();tasks=defaultdict(Counter)
    for row in rows:
        if type(row['exact_code_contract']) is not bool:raise ValueError('structured code cases only')
        values=dict(cases=1,exact=int(row['exact_code_contract']),empty=int(not row['answer'].strip()),
            max_new=int(row['generation']['finish_reason'] in ('MAX_NEW','MAX_NEW_EOS_DISABLED')))
        counts.update(values);m=row['meta'];tasks[m['language']+':'+m['kind']].update(values)
    return dict(counts=dict(counts),by_task={k:dict(v) for k,v in tasks.items()})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag',choices=tuple(SPECS),required=True)
    p.add_argument('--execute',action='store_true',required=True);args=p.parse_args()
    if not args.execute:p.error('explicit completed-collection readback required')
    root=ROOT/'test_result/evidence'/args.tag/'fresh_test';source=root/'report.json';r=json.loads(source.read_text())
    status,control=SPECS[args.tag]
    if r['status']!=status:raise ValueError('completed structured collection required')
    target=root/'paired_summary.json'
    if target.exists():raise FileExistsError('previous paired summary preserved')
    actual={}
    for arm,value in r['arms'].items():
        directory=ROOT/value['raw_directory'];manifest=value['raw_manifest'];verify(directory,manifest)
        actual[arm]=[json.loads(line) for spec in manifest['shards'] for line in (directory/spec['path']).read_text().splitlines()]
        if len(actual[arm])!=r['cases_per_arm']:raise ValueError('actual case count differs')
    summaries={a:summary(v) for a,v in actual.items()}
    intervals={a:paired_roots(actual[control],v) for a,v in actual.items() if a not in ('parent',control)}
    result=dict(schema='P106B_STRUCTURED_PAIRED_ROOTS_V1',tag=args.tag,control=control,summaries=summaries,paired_intervals=intervals,
        native_ce={a:v['native']['ce'] for a,v in r['arms'].items()},
        source_report_sha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),models_loaded=0,optimizer_updates=0,raw_modified=False)
    body=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if len(body.encode())>=20_000_000:raise ValueError('20MB report bound')
    with target.open('x',encoding='utf-8') as stream:stream.write(body)
    print('[STRUCTURED_PAIRED_READBACK] '+json.dumps(result,ensure_ascii=False),flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
