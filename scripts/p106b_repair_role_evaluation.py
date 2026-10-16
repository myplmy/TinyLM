"""Actual three-turn traces and source/producer-separated paired statistics."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import defaultdict
from scripts import p106b_original_qa3_evaluation as source


def collect(row,emit):
    events=source.collect(row,emit)
    if row['meta'].get('kind')=='role_bridge':
        meta=row['meta'];first=source.text(row['messages'][1])
        for event in events:
            event.update(neutral_root=meta['neutral_root'],view=meta['view'],question_style=meta['question_style'],
                producer_contract=meta['known_output_contract'],source_truth='GIVEN_PROGRAM_PRODUCER_RECORD_ONLY',
                target_same_as_first=event['gold']==first)
    return events


def counts(events):
    base=source.counts(events);groups=defaultdict(list)
    for event in events:
        if 'neutral_root' not in event:continue
        for lane in ('view='+str(event['view']),'style='+str(event['question_style']),
                     'same_first_target='+str(event['target_same_as_first'])):
            groups[lane].append(event)
    return dict(base=base,producer_slices={k:source.counts(v) for k,v in sorted(groups.items())})


def paired(left,right,*,neutral=False,draws=4000,seed=1337):
    import numpy as np
    source.counts(left);source.counts(right)
    def index(rows):return {(r['root'],r['turn'],r['history']):r for r in rows}
    a,b=index(left),index(right)
    if set(a)!=set(b):raise ValueError('same complete endpoint cases required')
    groups=defaultdict(lambda:[0.,0.,0])
    for key,x in a.items():
        y=b[key]
        if x['gold']!=y['gold'] or x['language']!=y['language']:raise ValueError('same source or producer target required')
        if x['history']!='ACTUAL_MODEL':continue
        group=x['neutral_root'] if neutral else x['root']
        if neutral and group!=y['neutral_root']:raise ValueError('same neutral graph required')
        g=groups[group];g[0]+=y['scores']['literal']-x['scores']['literal'];g[1]+=y['scores']['lexical_f1']-x['scores']['lexical_f1'];g[2]+=1
    if not groups:raise ValueError('nonempty actual cases required')
    values=np.asarray([v for _,v in sorted(groups.items())],dtype=float)
    ids=np.random.default_rng(seed).integers(len(values),size=(draws,len(values)));selected=values[ids];metrics={}
    for j,name in enumerate(('literal','lexical_f1')):
        samples=selected[:,:,j].sum(1)/selected[:,:,2].sum(1)
        metrics[name]=dict(right_minus_left=float(values[:,j].sum()/values[:,2].sum()),ci95=np.quantile(samples,[.025,.975]).tolist())
    return dict(metrics=metrics,group_roots=len(values),actual_events=int(values[:,2].sum()),neutral_language_style_grouping=neutral,
        draws=draws,seed=seed,scope='fixed source/neutral-graph paired descriptive interval; no multiple-comparison/learning-seed/world-truth claim')
