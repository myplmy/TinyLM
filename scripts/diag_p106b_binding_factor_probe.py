#!/usr/bin/env python3
"""Offline CPU factor probes on frozen features; no base-model forward/training."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
import copy
import json
import time
from collections import Counter
from scripts import diag_p106b_prefix_probe as source
TAG='p106b_binding_factor_probe_v1_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG
FACTORS=('requested','first','last','requested_is_first')
FEATURES=('hidden768','projected256','layer07','layer10')
CODE=('scripts/diag_p106b_binding_factor_probe.py','scripts/test_p106b_binding_factor_probe.py')


def labels_for(row):
    m=row['meta'];gold=source.course.base.data.text(row,-1)
    mapping=m['mapping'];ordered=m['ordered_entities']
    if len(ordered)!=2 or len(set(mapping.values()))!=2 or gold!=mapping[m['requested_entity']]:
        raise ValueError('registered two-distinct-value producer required')
    if m['first_value']!=mapping[ordered[0]]:
        raise ValueError('first-value metadata differs from actual source order')
    return dict(requested=gold,first=mapping[ordered[0]],last=mapping[ordered[-1]],
        requested_is_first=str(int(m['requested_entity']==ordered[0])))


def classifier(features,labels,metadata,classes,steps=500):
    import torch
    torch.manual_seed(20261015)
    train,(dev,test),mean,scale=source.standardize(features['train'],[features['dev'],features['test']])
    model=torch.nn.Linear(train.shape[1],classes)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.01,weight_decay=.01)
    best=None;trace=[]
    for step in range(1,steps+1):
        optimizer.zero_grad(set_to_none=True)
        loss=torch.nn.functional.cross_entropy(model(train),labels['train']);loss.backward();optimizer.step()
        if step%20==0:
            with torch.no_grad():dev_ce=float(torch.nn.functional.cross_entropy(model(dev),labels['dev']))
            trace.append(dict(step=step,train_ce=float(loss.detach()),dev_ce=dev_ce))
            if best is None or dev_ce<best[0]:best=(dev_ce,step,copy.deepcopy(model.state_dict()))
    if best is None:raise ValueError('at least one preregistered dev checkpoint required')
    model.load_state_dict(best[2]);scores={}
    with torch.no_grad():
        for split,x in (('train',train),('dev',dev),('test',test)):
            scores[split]=source.summarize_predictions(metadata[split],model(x).argmax(-1).tolist())
    return dict(classes=classes,selected_step=best[1],selected_dev_ce=best[0],scores=scores,trace=trace,
        classifier='linear',saved_weights=False)


def run(args):
    import numpy as np
    import torch
    from scripts.p106b_gate_runtime import wall_limit
    source.course.base.deadline();torch.set_num_threads(4)
    path=EVIDENCE/'report.json'
    if path.exists():raise FileExistsError('factor report preserved')
    capture_path=source.EVIDENCE/'capture.json';capture=json.loads(capture_path.read_text())
    if capture['status']!='FROZEN_PREFIX_CAPTURED' or capture['code_sha256']!=source.info()['code_sha256']:
        raise ValueError('same frozen feature/capture code required')
    rows=source.source_rows()
    known={source.course.base.data.sha(row['messages']):row for values in rows.values() for row in values}
    results={};began=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        for subject,record in capture['subjects'].items():
            indices={};derived={}
            for split in ('train','dev','test'):
                f=record['files'][split+'_index'];p=source.OUTPUT/f['path']
                if source.course.base.training.data.digest(p)!=f['sha256']:raise ValueError('index changed')
                indices[split]=json.loads(p.read_text());derived[split]=[]
                for item in indices[split]:
                    row=known[item['source_signature']]
                    values=labels_for(row)
                    if values['requested']!=item['label'] or values['first']!=item['first_value']:
                        raise ValueError('capture/producer join differs')
                    derived[split].append(values)
            results[subject]={}
            for feature in FEATURES:
                arrays={}
                for split in indices:
                    f=record['files'][split+'_'+feature];p=source.OUTPUT/f['path']
                    if source.course.base.training.data.digest(p)!=f['sha256']:raise ValueError('feature changed')
                    arrays[split]=torch.from_numpy(np.load(p,allow_pickle=False))
                result={}
                for group in sorted({i['group'] for i in indices['train']}):
                    keep={s:[n for n,item in enumerate(values) if item['group']==group] for s,values in indices.items()}
                    result[group]={}
                    for factor in FACTORS:
                        source.course.base.deadline()
                        names=sorted({derived['train'][i][factor] for i in keep['train']})
                        label_ids={name:i for i,name in enumerate(names)}
                        if len(names)!=(2 if factor=='requested_is_first' else 6):raise ValueError('label cardinality differs')
                        labels={s:torch.tensor([label_ids[derived[s][i][factor]] for i in keep[s]]) for s in indices}
                        metadata={s:[dict(root=indices[s][i]['root'],label=int(labels[s][n]))
                            for n,i in enumerate(keep[s])] for s in indices}
                        result[group][factor]=classifier({s:a[keep[s]] for s,a in arrays.items()},labels,metadata,len(names))
                        result[group][factor]['label_names']=names
                    print('[BINDING_FACTORS] '+json.dumps(dict(subject=subject,feature=feature,group=group,
                        test={k:v['scores']['test'] for k,v in result[group].items()})),flush=True)
                results[subject][feature]=result
    output=dict(tag=TAG,status='OFFLINE_FACTOR_PROBE_COLLECTED',results=results,whole_sec=time.perf_counter()-began,
        code_sha256={p:source.course.base.training.data.digest(ROOT/p) for p in CODE},
        capture_sha256=source.course.base.training.data.digest(capture_path),
        base_model_forward=0,base_model_updates=0,teacher_requests=0,gpu_used=False,checkpoint_saved=False,
        scope='same bounded code diagnostic development; supplied-label classifier not free answer or causal proof',
        requested_first_baseline=.5)
    source.course.base.training.write(path,output)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-wall-sec',type=int,default=600)
    p.add_argument('--execute',action='store_true',required=True)
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=1200:p.error('bounded60..1200')
    if not args.execute:p.error('explicit CPU report execution required')
    return run(args)


if __name__=='__main__':raise SystemExit(main())
