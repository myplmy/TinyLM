"""Actual-history and supplied-error relation evaluation, never a live filter."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
from collections import Counter
from scripts import p106b_relation_fields as factory
from scripts import diag_p106b_dualqa_eval as reference
from tinylm.chat.canonical import normalize,validate


def collect(row,emit):
    m=row['meta'];g=m['producer_graph'];language=m['language'];view=m['view']
    if row!=factory.make(g,language,view):raise ValueError('exact producer graph and row required')
    messages=row['messages'];events=[]
    def event(prefix,turn,history):
        prefix=validate(normalize(dict(messages=copy.deepcopy(prefix))))['messages']
        answer,generation=emit(prefix)
        if not isinstance(answer,str):raise ValueError('actual answer string, including empty, required')
        value=dict(root=m['neutral_root'],language=language,view=view,scenario=m['scenario'],turn=turn,history=history,
            messages=prefix,answer=answer,gold=factory_text(messages[2*turn-1]),generation=generation,
            target_key=g['other'] if view==2 and turn==2 else g['base'],producer_graph=g,
            source_truth='DECLARED_FICTIONAL_GRAPH_ONLY',auxiliary_used=False)
        events.append(value);return answer
    if view==3:
        event(messages[:3],2,'PROVIDED_WRONG_HISTORY')
    else:
        first=event(messages[:1],1,'ACTUAL_MODEL')
        prefix=[messages[0],dict(role='assistant',content=first),messages[2]]
        event(prefix,2,'ACTUAL_MODEL')
        event(messages[:3],2,'GOLD_REFERENCE')
    for value in events:value['scores']=score(value)
    return events


def factory_text(message):return ''.join(x['text'] for x in message['content'])


def score(event):
    answer,gold=event['answer'].strip(),event['gold'].strip();finish=event['generation']['finish_reason']
    graph=event['producer_graph'];language=event['language'];key=event['target_key']
    if gold!=factory.answer(graph,language,key):raise ValueError('gold does not match producer target field')
    # This finite, producer-known set describes wrong-field copying. It is not
    # a blacklist, semantic truth test, regeneration rule or training exclusion.
    others={factory.answer(graph,language,k) for k in graph['order'] if k!=key}
    return dict(cases=1,literal=int(answer==gold),lexical_f1=reference.metrics.token_f1(answer,gold),
        exact_other_field=int(answer in others),empty=int(not answer),
        max_new=int(finish.startswith('MAX_NEW')),context_exhausted=int(finish=='CONTEXT_BUDGET_EXHAUSTED'))


def summarize(events):
    totals={};seen=set()
    for e in events:
        key=(e['root'],e['language'],e['view'],e['turn'],e['history'])
        if key in seen:raise ValueError('duplicate evaluation event')
        seen.add(key)
        if e['scores']!=score(e):raise ValueError('raw score mismatch')
        lane=f"{e['scenario']}:{e['language']}:{e['history']}:turn{e['turn']}"
        totals.setdefault(lane,Counter()).update(e['scores'])
    return {k:dict(v) for k,v in sorted(totals.items())}


def paired(left,right,metric='literal',seed=1337,draws=4000):
    import numpy as np
    def grouped(events):
        out={}
        for e in events:
            if e['history']=='GOLD_REFERENCE':continue
            k=(e['root'],e['language'],e['view'],e['turn'],e['history'])
            if k in out:raise ValueError('duplicate paired key')
            out[k]=e
        return out
    a,b=grouped(left),grouped(right)
    if set(a)!=set(b):raise ValueError('same complete root/language/view/turn coverage required')
    clusters={}
    for k in sorted(a):
        x,y=a[k],b[k]
        if x['gold']!=y['gold'] or x['target_key']!=y['target_key']:raise ValueError('same targets required')
        clusters.setdefault(k[0],[]).append(y['scores'][metric]-x['scores'][metric])
    values=np.asarray([sum(v)/len(v) for _,v in sorted(clusters.items())],dtype=float)
    if not len(values):raise ValueError('nonempty paired roots required')
    rng=np.random.default_rng(seed);samples=values[rng.integers(len(values),size=(draws,len(values)))].mean(axis=1)
    return dict(metric=metric,right_minus_left=float(values.mean()),ci95=np.quantile(samples,[.025,.975]).tolist(),
        roots=len(values),events=len(a),bootstrap_draws=draws,seed=seed,
        scope='fixed fictional root clusters include both language children; not training-seed or world generalization')
