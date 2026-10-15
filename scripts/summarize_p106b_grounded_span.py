#!/usr/bin/env python3
"""Read-only raw-answer matching; write-once paired metrics, never a truth judge."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import json
import random
from scripts.p106b_shards import verify,ShardWriter
from scripts import p106b_grounded_span as metric
from scripts.p101a_sft_mtp_data import digest
TAG='p106b_grounded_span_exec_v3_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG/'evaluate'
LOCAL=ROOT/'test_result/evidence/local'/TAG/'evaluate'


def indexed(rows):
    result={}
    for row in rows:
        key=row['meta']['semantic_root_id']
        if key in result:raise ValueError('one first-QA per exact document root required')
        result[key]=row
    return result


def paired(left,right,language=None,repetitions=2000):
    if set(left)!=set(right):raise ValueError('paired root set differs')
    values=[]
    for key,a in sorted(left.items()):
        b=right[key]
        if a['messages']!=b['messages'] or a['gold']!=b['gold']:raise ValueError('same question/reference/target required')
        if language is not None and a['meta']['language']!=language:continue
        values.append(float(b['answer'].strip()==b['gold'].strip())-float(a['answer'].strip()==a['gold'].strip()))
    if not values:raise ValueError('nonempty paired language required')
    rng=random.Random(20261016);n=len(values);boot=sorted(sum(rng.choices(values,k=n))/n for _ in range(repetitions))
    return dict(documents=n,delta_literal=sum(values)/n,bootstrap95=[boot[int(.025*repetitions)],boot[int(.975*repetitions)-1]],
        repetitions=repetitions,seed=20261016,scope='fixed model exact-document-root paired bootstrap; not training-seed variance or semantic truth')


def load(spec):
    directory=ROOT/spec['directory']
    if directory.is_symlink() or not directory.resolve().is_relative_to(LOCAL.resolve()):raise ValueError('expected private answer namespace only')
    verify(directory,spec['manifest'])
    rows=[json.loads(line) for s in spec['manifest']['shards'] for line in (directory/s['path']).read_text().splitlines()]
    return rows


def summarize():
    rp=EVIDENCE/'report.json'
    if not rp.is_file():raise FileNotFoundError('completed same-course evaluation required')
    if (EVIDENCE/'paired_readback.json').exists():raise FileExistsError('old readback preserved')
    report=json.loads(rp.read_text());names=('parent','span0','span03')
    if report['status']!='GROUNDED_SPAN_EVALUATED' or set(report['arms'])!=set(names):raise ValueError('complete three endpoints required')
    actual={};counts={}
    for name in names:
        spec=report['arms'][name]['test'];rows=load(spec);actual[name]=indexed(rows);counter=defaultdict(Counter)
        if len(rows)!=256 or Counter(r['meta']['language'] for r in rows)!=dict(ko=128,en=128):raise ValueError('exact balanced test256 required')
        for row in rows:
            same=row['answer'].strip()==row['gold'].strip()
            if row['literal']!=same:raise ValueError('stored literal flag differs from actual text')
            counter[row['meta']['language']].update(cases=1,literal=int(same),f1_sum=metric.token_f1(row['answer'],row['gold']),
                empty=int(not row['answer'].strip()),max_new=int(row['generation']['finish_reason'].startswith('MAX_NEW')))
        counts[name]={l:dict(v,mean_f1=v['f1_sum']/v['cases']) for l,v in counter.items()}
        for lang,v in counts[name].items():
            original=spec['counts'][lang+':natural_first_qa']
            if v['cases']!=original['cases'] or v['literal']!=original['literal'] or abs(v['f1_sum']-original['token_f1'])>1e-8:
                raise ValueError('raw/source aggregate mismatch')
    comparisons={}
    for left,right in (('parent','span0'),('parent','span03'),('span0','span03')):
        comparisons[left+'_to_'+right]={lang or 'all':paired(actual[left],actual[right],lang) for lang in (None,'ko','en')}
    # Fixed language/position sample, selected independently of output correctness.
    sample=[]
    for language in ('ko','en'):
        roots=[k for k,row in actual['parent'].items() if row['meta']['language']==language]
        roots.sort()
        for index in (0,32,64,96):
            root=roots[index];base=actual['parent'][root]
            sample.append(dict(root=root,language=language,messages=base['messages'],source_gold=base['gold'],
                answers={name:actual[name][root]['answer'] for name in names},
                finishes={name:actual[name][root]['generation']['finish_reason'] for name in names},
                source_truth='UNVERIFIED',review='NOT_RUN; no automatic exclusion/retry'))
    writer=ShardWriter(LOCAL/'fixed_sample8','review')
    for row in sample:writer.append(row)
    manifest=writer.close(lineage=dict(selection='four sorted document-root positions0/32/64/96 per language; independent of output',scope='8questions x3models; NOT_REVIEWED'))
    value=dict(schema='P106B_GROUNDED_SPAN_PAIRED_READBACK_V1',tag=TAG,source_report_sha256=digest(rp),
        code_sha256=digest(Path(__file__)),counts=counts,comparisons=comparisons,
        sample8_manifest=manifest,sample8_directory=str((LOCAL/'fixed_sample8').relative_to(ROOT)),
        models_loaded=0,training=False,source_answers_modified=False,automatic_model_selection=False,
        semantic_truth='NOT_RUN',cross_language_semantic_overlap='NOT_AUDITED',
        precision='paired same FP32_MATH greedy answer path; native32crop not whole-pool retention',
        scope='source-literal fidelity and lexical overlap only; no broad intelligence certificate')
    body=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if len(body.encode())>20_000_000:raise ValueError('20MB cap')
    with (EVIDENCE/'paired_readback.json').open('x',encoding='utf-8') as stream:stream.write(body)
    print('[GROUNDED_SPAN_PAIRED] '+json.dumps(dict(counts=counts,comparisons=comparisons),ensure_ascii=False),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit write-once readback --execute required')
    try:summarize();return 0
    except FileNotFoundError as exc:print('[GROUNDED_SPAN_READBACK_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[GROUNDED_SPAN_READBACK_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
