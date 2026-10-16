#!/usr/bin/env python3
"""Independent CPU-only raw recount; no primary scorer/model imports."""
from __future__ import annotations
from collections import Counter
from decimal import Decimal
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'test_result/evidence/p106b_authorized_validation_v1_s1337'
LOCAL=ROOT/'test_result/evidence/local/p106b_authorized_validation_v1_s1337/public_benchmark'
FROZEN=ROOT/'HF/sft_ready/p106b_authorized_validation_v1_s1337/public_benchmark'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest().upper()


def records(folder,manifest):
    total=hashlib.sha256();rows=[]
    for part in manifest['shards']:
        path=folder/part['path'];raw=path.read_bytes()
        assert len(raw)==part['bytes'] and len(raw)<20_000_000
        assert hashlib.sha256(raw).hexdigest().upper()==part['sha256']
        total.update(raw);lane=[json.loads(s) for s in raw.decode('utf-8').splitlines()]
        assert len(lane)==part['rows'];rows.extend(lane)
    assert len(rows)==manifest['rows'] and total.hexdigest().upper()==manifest['concat_sha256']
    return rows


def text_key(s):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s).casefold()).strip()


def numeric(s):
    value=s.split('####')[-1].strip().replace(',','')
    if not re.fullmatch(r'[+-]?[0-9]+(?:\.[0-9]+)?',value):return None
    return Decimal(value)


def recount(row):
    if row.get('skipped'):return None
    if 'sum_nll' in row:
        sums=row['sum_nll'];means=row['mean_nll'];counts=row['n_tokens']
        assert all(math.isfinite(x) for x in sums+means+row['score'])
        assert all(c>0 for c in counts)
        for total,mean,n in zip(sums,means,counts):
            assert abs(total/n-mean)<1e-4
        best=min(enumerate(sums),key=lambda pair:pair[1])[0]
        assert best==row['pred_harness']
        assert min(range(len(sums)),key=lambda i:sums[i]/row['n_chars'][i])==row['pred_harness_norm']
        assert min(range(len(sums)),key=lambda i:row['score'][i])==row['pred_internal']
        return int(best==row['gold'])
    answer=row['answer'];golds=row['golds']
    exact=int(any(text_key(answer)==text_key(g) for g in golds))
    assert exact==row['scores']['whitespace_nfkc_exact']
    if row['task']=='gsm8k_free':
        guess=numeric(answer);gold=numeric(golds[0]);value=int(guess is not None and guess==gold)
        assert value==row['scores']['numeric_exact'];return value
    return exact


def interval(differences,groups,draws=2000):
    grouped={}
    for ident,value in differences.items():grouped.setdefault(groups[ident],[]).append(value)
    keys=sorted(grouped)
    if len(keys)<2:return dict(delta=sum(differences.values())/len(differences),ci=None,groups=len(keys))
    rnd=random.Random(20261016);samples=[]
    totals={k:(sum(grouped[k]),len(grouped[k])) for k in keys}
    for _ in range(draws):
        selected=[totals[rnd.choice(keys)] for _ in keys]
        samples.append(sum(x[0] for x in selected)/sum(x[1] for x in selected))
    samples.sort()
    return dict(delta=sum(differences.values())/len(differences),
                ci=[samples[int(.025*(draws-1))],samples[int(.975*(draws-1))]],groups=len(keys))


def main():
    complete=json.loads((EVIDENCE/'benchmark_report.json').read_text(encoding='utf-8'))
    assert complete['status']=='COMPLETE'
    assert complete['driver_sha256']==sha(ROOT/'scripts/diag_p106b_authorized_benchmark.py')
    frozen=json.loads((FROZEN/'report.json').read_text(encoding='utf-8'))
    assert complete['inputs_sha256']==sha(FROZEN/'report.json')
    cases=records(FROZEN,frozen['manifest']);inputs={}
    for row in cases:
        ident=row['item']['_iid'] if row['kind']=='mc' else row['id']
        key=(row['task'],ident);assert key not in inputs;inputs[key]=row
    groups={}
    for (task,ident),row in inputs.items():
        if task=='korquad_free':root=row['prompt'].split('\n질문:',1)[0]
        elif task=='klue_nli':root=row['item']['ctx'].split('\n가설:',1)[0]
        else:root=ident
        groups[(task,ident)]=hashlib.sha256(root.encode()).hexdigest()
    models={};out={};raw_rows=0
    for spec in frozen['models']:
        name=spec['name'];summary=complete['models'][name]
        assert sha(ROOT/spec['checkpoint'])==spec['sha256']
        rows=records(LOCAL/name,summary['raw_manifest']);raw_rows+=len(rows)
        indexed={}
        for row in rows:
            key=(row['task'],row['id']);assert key not in indexed and key in inputs
            original=inputs[key]
            if row.get('skipped'):
                if row['task'] in ('korquad_free','gsm8k_free'):
                    assert original['prompt_tokens']+128>1024
            elif row['task'] in ('korquad_free','gsm8k_free'):
                assert (row['prompt'],row['golds'])==(original['prompt'],original['golds'])
            else:assert row['source_item']==original['item']
            indexed[key]=recount(row)
        assert set(indexed)==set(inputs)
        models[name]=indexed;counts={}
        for task,s in summary['tasks'].items():
            values=[v for (t,_),v in indexed.items() if t==task and v is not None]
            skipped=sum(v is None for (t,_),v in indexed.items() if t==task)
            assert len(values)==s['n'] and skipped==s['skipped'] and sum(values)==s['correct']
            assert abs(sum(values)/len(values)-s['accuracy'][0])<1e-12
            if task in frozen['mc_tasks']:
                actual=[r for r in rows if r['task']==task and not r.get('skipped')]
                assert abs(sum(r['pred_harness_norm']==r['gold'] for r in actual)/len(actual)-s['accuracy_char_norm'])<1e-12
                assert abs(sum(r['pred_internal']==r['gold'] for r in actual)/len(actual)-s['internal_pmi_accuracy'])<1e-12
            counts[task]=dict(correct=sum(values),n=len(values),skipped=skipped)
        out[name]=counts
    pairs={}
    for left,right in itertools.combinations(models,2):
        per={}
        for task in frozen['sources']:
            keys=[k for k in inputs if k[0]==task and models[left][k] is not None and models[right][k] is not None]
            assert keys
            per[task]=interval({k:models[right][k]-models[left][k] for k in keys},groups)
        pairs[right+'-minus-'+left]=dict(tasks=per,
            claim='DIRECT_PAIRED' if (left,right)==('sft_only','orpo010') else 'DESCRIPTIVE_ONLY')
    result=dict(schema='P106B_AUTHORIZED_PUBLIC_BENCHMARK_RECOUNT_V1',status='RAW_RECOUNT_PASSED',
        primary_report_sha256=sha(EVIDENCE/'benchmark_report.json'),driver_sha256=sha(Path(__file__)),
        models=out,pairs=pairs,actual_raw_rows=raw_rows,unique_frozen_cases=len(inputs),
        mc_records=sum(s['n'] for c in out.values() for t,s in c.items() if t in frozen['mc_tasks']),
        generated_scored=sum(s['n'] for c in out.values() for t,s in c.items() if t not in frozen['mc_tasks']),
        bootstrap='2000 paired resamples; KorQuAD paragraph and NLI premise groups, otherwise case IDs',
        limit='Training seed uncertainty and multiplicity are not corrected. Evaluation grouping alone does not establish architecture causality.',
        optimizer_updates=0,model_loaded=False,gpu_used=False,default_model_adopted=False)
    target=EVIDENCE/'benchmark_readback.json'
    with target.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print('[PUBLIC_BENCHMARK_RECOUNT] '+json.dumps(dict(models=len(out),raw_rows=raw_rows,
        mc_scored=result['mc_records'],free_scored=result['generated_scored'],errors=0)),flush=True)
    for name,counts in out.items():print(name,json.dumps(counts,ensure_ascii=False))


if __name__=='__main__':main()
