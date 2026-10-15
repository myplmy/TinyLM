"""History/field-separated raw readback; no model judgment or live exclusion."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter,defaultdict
from scripts import p106b_relation_evaluation as method


def key(e):return e['root'],e['language'],e['view'],e['turn'],e['history']


def index(events):
    result={}
    for e in events:
        k=key(e)
        if k in result:raise ValueError('duplicate raw event')
        if method.score(e)!=e['scores']:raise ValueError('raw score mismatch')
        result[k]=e
    return result


def lanes(e):
    h=e['history']
    return (h+'/all',h+'/scenario='+e['scenario'],h+'/language='+e['language'],
        h+'/turn='+str(e['turn']),h+'/field='+e['target_key'][1])


def counts(events):
    index(events);out=defaultdict(Counter)
    for e in events:
        for lane in lanes(e):out[lane].update(e['scores'])
    return {k:dict(v) for k,v in sorted(out.items())}


def first_invariance(events):
    indexed=index(events);groups=defaultdict(dict)
    for e in indexed.values():
        if e['history']=='ACTUAL_MODEL' and e['turn']==1:groups[e['root'],e['language']][e['view']]=e
    different=0
    for versions in groups.values():
        if set(versions)!={0,1,2}:raise ValueError('all three same-first-prompt views required')
        base=versions[0]
        if any(v['messages']!=base['messages'] or v['gold']!=base['gold'] for v in versions.values()):raise ValueError('first inputs/targets differ by view')
        different+=int(any(v['answer']!=base['answer'] for v in versions.values()))
    return dict(root_language_groups=len(groups),first_output_disagreements=different,
        scope='same endpoint, exact first prefix, FP32 greedy; not a semantic score')


def weighted_pair(left,right,metric='literal',draws=4000,seed=1337):
    import numpy as np
    a,b=index(left),index(right)
    if set(a)!=set(b) or not a:raise ValueError('same nonempty full paired keys required')
    totals=defaultdict(lambda:[0.,0])
    for k,x in a.items():
        y=b[k]
        if x['gold']!=y['gold'] or x['target_key']!=y['target_key'] or x['producer_graph']!=y['producer_graph']:raise ValueError('same producer targets required')
        totals[k[0]][0]+=y['scores'][metric]-x['scores'][metric];totals[k[0]][1]+=1
    values=np.asarray([v for _,v in sorted(totals.items())],dtype=float)
    ids=np.random.default_rng(seed).integers(len(values),size=(draws,len(values)))
    selected=values[ids];sample=selected[:,:,0].sum(axis=1)/selected[:,:,1].sum(axis=1)
    return dict(metric=metric,right_minus_left=float(values[:,0].sum()/values[:,1].sum()),
        ci95=np.quantile(sample,[.025,.975]).tolist(),events=len(a),neutral_roots=len(values),seed=seed,draws=draws,
        scope='resample neutral roots with both language children; ratio of total paired score differences to total cases; no multiplicity adjustment or seed generalization')


def pairs_by_lane(left,right,draws=4000):
    a,b=index(left),index(right)
    if set(a)!=set(b):raise ValueError('complete endpoint coverage required')
    groups=defaultdict(list)
    for k,e in a.items():
        if e['history']=='GOLD_REFERENCE':continue
        for lane in lanes(e):groups[lane].append(k)
    return {lane:{metric:weighted_pair([a[k] for k in keys],[b[k] for k in keys],metric,draws=draws)
        for metric in ('literal','lexical_f1','exact_other_field')} for lane,keys in sorted(groups.items())}
