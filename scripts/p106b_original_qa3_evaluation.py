"""Actual three-turn history, gold-history diagnostics, and source fidelity only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
from collections import Counter,defaultdict
from scripts import p106b_grounded_span as metric
from tinylm.chat.canonical import normalize,validate


def text(message):return ''.join(x['text'] for x in message['content'])


def score(event):
    answer,gold=event['answer'],event['gold'];finish=event['generation']['finish_reason']
    return dict(cases=1,literal=int(answer.strip()==gold.strip()),lexical_f1=metric.token_f1(answer,gold),
        empty=int(not answer.strip()),max_new=int(finish.startswith('MAX_NEW')),context_exhausted=int(finish=='CONTEXT_BUDGET_EXHAUSTED'))


def collect(row,emit):
    messages=row['messages'];meta=row['meta']
    if len(messages)!=6 or [m['role'] for m in messages]!=['user','assistant']*3:raise ValueError('exact original three QA roles required')
    events=[];history=[]
    def event(prefix,turn,kind):
        prefix=validate(normalize(dict(messages=copy.deepcopy(prefix))))['messages'];answer,generation=emit(prefix)
        if not isinstance(answer,str):raise ValueError('actual string including empty required')
        value=dict(root=meta['semantic_root_id'],language=meta['language'],turn=turn,history=kind,messages=prefix,
            answer=answer,gold=text(messages[2*turn-1]),generation=generation,source_truth='ORIGINAL_PUBLIC_UNVERIFIED')
        value['scores']=score(value);events.append(value);return answer
    for turn in range(1,4):
        history.append(messages[2*turn-2]);answer=event(history,turn,'ACTUAL_MODEL')
        history.append(dict(role='assistant',content=answer))
    for turn in (2,3):event(messages[:2*turn-1],turn,'GOLD_REFERENCE')
    return events


def counts(events):
    seen=set();out=defaultdict(Counter)
    for e in events:
        key=(e['root'],e['turn'],e['history'])
        if key in seen:raise ValueError('duplicate root/turn/history')
        seen.add(key)
        if score(e)!=e['scores']:raise ValueError('raw score mismatch')
        for lane in (e['history']+'/all',e['history']+'/language='+e['language'],e['history']+'/turn='+str(e['turn'])):out[lane].update(e['scores'])
    return {k:dict(v) for k,v in sorted(out.items())}


def paired(left,right,draws=4000,seed=1337):
    import numpy as np
    def indexed(rows):
        counts(rows);return {(r['root'],r['turn'],r['history']):r for r in rows}
    a,b=indexed(left),indexed(right)
    if set(a)!=set(b):raise ValueError('same complete natural roots and histories required')
    groups=defaultdict(list)
    for k,x in a.items():
        if x['gold']!=b[k]['gold'] or x['language']!=b[k]['language']:raise ValueError('same source targets required')
        if x['history']=='ACTUAL_MODEL':groups[x['root']].append(k)
    totals=np.asarray([[sum(b[k]['scores']['literal']-a[k]['scores']['literal'] for k in keys),
        sum(b[k]['scores']['lexical_f1']-a[k]['scores']['lexical_f1'] for k in keys),len(keys)] for _,keys in sorted(groups.items())],dtype=float)
    if not len(totals):raise ValueError('nonempty actual roots required')
    ids=np.random.default_rng(seed).integers(len(totals),size=(draws,len(totals)));picked=totals[ids]
    result={}
    for j,m in enumerate(('literal','lexical_f1')):
        values=picked[:,:,j].sum(axis=1)/picked[:,:,2].sum(axis=1)
        result[m]=dict(right_minus_left=float(totals[:,j].sum()/totals[:,2].sum()),ci95=np.quantile(values,[.025,.975]).tolist())
    return dict(metrics=result,source_roots=len(totals),actual_events=int(totals[:,2].sum()),draws=draws,seed=seed,
        scope='fixed public source roots; translation/pretraining overlap not audited; not semantic truth or seed generalization')
