#!/usr/bin/env python3
"""Raw event recheck and whole-document paired readback, never semantic grading."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import json
import random
from scripts import diag_p106b_dualqa_eval as evaluate
from scripts.p106b_shards import verify,ShardWriter
from scripts import p101a_sft_mtp_data as public


def key(row):return row['root'],row['order'],row['turn'],row['history']


def indexed(rows,documents=256):
    result={};groups=defaultdict(set);languages={}
    for row in rows:
        k=key(row)
        if k in result:raise ValueError('duplicate source/order/turn/history event')
        if row['order'] not in (0,1) or row['turn'] not in (1,2):raise ValueError('two orders and two turns required')
        if row['history'] not in ('ACTUAL_MODEL','GOLD_REFERENCE') or (row['history']=='GOLD_REFERENCE' and row['turn']!=2):
            raise ValueError('gold reference is second-turn-only diagnostic')
        if row['scores']!=evaluate.score(row):raise ValueError('raw score differs from stored score')
        if languages.setdefault(row['root'],row['language'])!=row['language']:raise ValueError('document language changed')
        groups[row['root']].add(k[1:]);result[k]=row
    expected={(p,t,'ACTUAL_MODEL') for p in (0,1) for t in (1,2)}|{(p,2,'GOLD_REFERENCE') for p in (0,1)}
    if len(groups)!=documents or any(v!=expected for v in groups.values()):raise ValueError('all document views required without slicing')
    return result


def compare(left,right,*,language=None,history='ACTUAL_MODEL',turn=None,repetitions=2000):
    if set(left)!=set(right):raise ValueError('same paired event set required')
    grouped=defaultdict(list)
    for k,a in sorted(left.items()):
        b=right[k]
        if a['gold']!=b['gold'] or a['language']!=b['language']:raise ValueError('same source target/language required')
        user=lambda r:[m for m in r['messages'] if m['role']=='user']
        if user(a)!=user(b):raise ValueError('same source and user questions required')
        if a['history']=='GOLD_REFERENCE' and a['messages']!=b['messages']:raise ValueError('identical gold history required')
        if a['turn']==1 and a['messages']!=b['messages']:raise ValueError('first-turn prompt must be identical')
        if a['history']!=history or (turn and a['turn']!=turn) or (language and a['language']!=language):continue
        x,y=evaluate.score(a),evaluate.score(b)
        grouped[a['root']].append((y['literal']-x['literal'],y['lexical_f1']-x['lexical_f1']))
    if not grouped:raise ValueError('nonempty comparison required')
    values=[tuple(sum(v[i] for v in group)/len(group) for i in (0,1)) for root,group in sorted(grouped.items())]
    rng=random.Random(20261016);n=len(values);boot=[[],[]]
    for _ in range(repetitions):
        sample=rng.choices(values,k=n)
        for i in (0,1):boot[i].append(sum(v[i] for v in sample)/n)
    outcome={}
    for i,name in enumerate(('literal','lexical_f1')):
        v=sorted(boot[i]);outcome[name]=dict(delta=sum(x[i] for x in values)/n,
            bootstrap95=[v[int(.025*repetitions)],v[int(.975*repetitions)-1]])
    return dict(documents=n,events=sum(map(len,grouped.values())),history=history,turn=turn,language=language,
        seed=20261016,repetitions=repetitions,metrics=outcome,
        scope='whole fixed document roots; not training-seed uncertainty, semantic truth or independent views')


def load(spec):
    directory=ROOT/spec['directory']
    if directory.is_symlink() or not directory.resolve().is_relative_to(evaluate.LOCAL.resolve()):raise ValueError('only current private namespace')
    verify(directory,spec['manifest'])
    return list(public.stream_rows(directory,spec['manifest']))


def summarize():
    path=evaluate.EVIDENCE/'report.json';report=json.loads(path.read_text())
    target=evaluate.EVIDENCE/'paired_readback.json'
    if target.exists():raise FileExistsError('old paired readback preserved')
    names=('parent','repeat','contrast')
    if report['status']!='DUALQA_FRESH_ACTUAL_HISTORY_EVALUATED' or set(report['endpoints'])!=set(names):raise ValueError('three completed endpoints required')
    indices={};totals={}
    for name in names:
        spec=report['endpoints'][name]['metrics']['source'];rows=load(spec);indices[name]=indexed(rows)
        counts=defaultdict(Counter);languages={r['root']:r['language'] for r in rows}
        if Counter(languages.values())!=dict(ko=128,en=128):raise ValueError('all fresh128/128 documents required')
        for row in rows:
            counts[row['history']+':'+row['language']+':turn'+str(row['turn'])].update(evaluate.score(row))
        if {k:dict(v) for k,v in counts.items()}!=spec['counts']:raise ValueError('source aggregate differs from raw events')
        totals[name]={k:dict(v,mean_lexical_f1=v['lexical_f1']/v['cases']) for k,v in counts.items()}
    pairs={}
    for left,right in (('parent','repeat'),('parent','contrast'),('repeat','contrast')):
        pairs[left+'_to_'+right]={}
        for language in (None,'ko','en'):
            lane=language or 'all';pairs[left+'_to_'+right][lane]={
                'actual_all':compare(indices[left],indices[right],language=language),
                'actual_first':compare(indices[left],indices[right],language=language,turn=1),
                'actual_second':compare(indices[left],indices[right],language=language,turn=2),
                'gold_second':compare(indices[left],indices[right],language=language,history='GOLD_REFERENCE',turn=2)}
    writer=ShardWriter(evaluate.LOCAL/'fixed_source_sample8','review')
    for language in ('ko','en'):
        roots=sorted({r['root'] for r in indices['parent'].values() if r['language']==language})
        for index in (0,32,64,96):
            root=roots[index];first=indices['parent'][root,0,1,'ACTUAL_MODEL'];second=indices['parent'][root,0,2,'ACTUAL_MODEL']
            writer.append(dict(root=root,language=language,first_user=first['messages'][0],second_user=second['messages'][-1],
                teacher_pseudo_targets=[first['gold'],second['gold']],
                actual_answers={name:[indices[name][root,0,t,'ACTUAL_MODEL']['answer'] for t in (1,2)] for name in names},
                finishes={name:[indices[name][root,0,t,'ACTUAL_MODEL']['generation']['finish_reason'] for t in (1,2)] for name in names},
                review='NOT_RUN; 8source contexts/48actual replies, not automatic truth grading'))
    manifest=writer.close(lineage=dict(selection='sorted root positions0/32/64/96 per language, order0 both turns; independent of correctness',scope='offline sample only'))
    value=dict(schema='P106B_DUALQA_DOCUMENT_PAIRED_READBACK_V1',tag=evaluate.TAG,source_report_sha256=public.digest(path),
        code_sha256={p:public.digest(ROOT/p) for p in ('scripts/summarize_p106b_dualqa_eval.py','scripts/test_summarize_p106b_dualqa_eval.py')},
        counts=totals,comparisons=pairs,sample8_manifest=manifest,
        sample8_directory=str((evaluate.LOCAL/'fixed_source_sample8').relative_to(ROOT)),
        models_loaded=0,training=False,semantic_truth='NOT_RUN',automatic_selection=False,
        final_epoch4_primary=True,old_known_code_is_development_not_new_test=True,
        source_target='TEACHER_PSEUDO_UNVERIFIED; aliases and source relations require separate reading')
    evaluate.course.training.write(target,value)
    print('[DUALQA_DOCUMENT_PAIRED] '+json.dumps(dict(counts=totals,comparisons=pairs)),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit write-once readback required')
    try:summarize();return 0
    except FileNotFoundError as exc:print('[DUALQA_READBACK_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_READBACK_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
