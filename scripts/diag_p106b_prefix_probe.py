#!/usr/bin/env python3
"""Frozen pre-answer feature diagnostic; never a free-answer quality score.

Base models are read-only. Small CPU classifiers see only training labels.
No protected data, teacher request, downloads or model load on import.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter, defaultdict
import copy
import json
import time
from scripts import diag_p106b_conditional_orpo as course

TAG = 'p106b_prefix_probe_v2_s1337'
OUTPUT = ROOT/'HF/sft_ready'/TAG
EVIDENCE = ROOT/'test_result/evidence'/TAG
SUBJECTS = ('parent', 'replay100', 'pair030')
LAYER_INDICES = (0,3,7,10,13)
CODE = ('scripts/diag_p106b_prefix_probe.py', 'scripts/test_p106b_prefix_probe.py')


def prepare_model(model):
    """Transient quant caches are not buffers: move parameters before freezing."""
    model.clear_quant();model.eval();model.requires_grad_(False)
    model=model.cuda();model.freeze_quant()
    device=next(model.parameters()).device
    for module in model._tlinear_cache:
        if module._wq is None or module._wq.device!=device:
            raise ValueError('quant cache and model device differ')
    return model


class LayerCapture:
    """Read-only last-prefix observations. Reject repeated visits, never conflate them."""
    def __init__(self,model,indices):
        self.model=model;self.indices=tuple(indices);self.handles=[];self.values={}
    def __enter__(self):
        for index in self.indices:
            def observe(module,args,output,index=index):
                if index in self.values:raise ValueError('unexpected repeated logical layer visit')
                value=output[0] if isinstance(output,tuple) else output
                self.values[index]=value[:,-1,:].detach().clone()
            self.handles.append(self.model.layers[index].register_forward_hook(observe))
        return self
    def take(self):
        if set(self.values)!=set(self.indices):raise ValueError('missing logical layer observation')
        result=self.values;self.values={};return result
    def __exit__(self,*args):
        for handle in self.handles:handle.remove()
        self.handles=[];self.values={}


def info():
    return dict(tag=TAG,code_sha256={p:course.base.training.data.digest(ROOT/p) for p in CODE},
        base_code_sha256=course.info()['code_sha256'],source_tag=course.TAG,
        precision='FP32_MATH_NO_TF32',cache=True,batch_size=1,teacher_requests=0,
        intermediate_logical_layers=list(LAYER_INDICES),intermediate_scope='last prefix position after full layer; observational not causal',
        backbone_training=False,checkpoint_saved=False,scope='SUPPLIED_SIX_LABEL_PROBE_NOT_FREE_GENERATION')


def prompt(row):
    from tinylm.chat.serialize import serialize
    if len(row['messages']) != 2 or row['messages'][-1]['role'] != 'assistant':
        raise ValueError('single-answer registered binding only')
    return serialize(dict(messages=copy.deepcopy(row['messages'][:-1])), 'chatml', add_generation_prompt=True)


def groups(rows):
    result = defaultdict(list)
    for row in rows:
        m = row['meta']
        if m['kind'] not in ('binding_color', 'binding_department'):
            continue
        if m['rubric'] != 'EXACT_SCALAR' or len(m['mapping']) != 2:
            raise ValueError('unambiguous code binding required')
        gold = course.base.data.text(row, -1)
        if gold != m['mapping'][m['requested_entity']]:
            raise ValueError('producer label mismatch')
        result[m['language']+':'+m['kind']].append(row)
    return dict(result)


def source_rows():
    report,original,rows,pairs,test = course.read_course()
    selected = dict(train=[r for g in groups(rows['train']).values() for r in g],
        dev=[r for g in groups(rows['dev']).values() for r in g],
        test=[r for g in groups(test).values() for r in g])
    if {s:len(v) for s,v in selected.items()} != dict(train=4096,dev=512,test=512):
        raise ValueError('planned binding split sizes required')
    roots = {s:{r['meta']['semantic_root_id'] for r in values} for s,values in selected.items()}
    if any(roots[a]&roots[b] for a,b in (('train','dev'),('train','test'),('dev','test'))):
        raise ValueError('binding root leakage')
    return selected


def checkpoints():
    result = dict(parent=dict(path=str(course.base.training.PARENT.relative_to(ROOT)),
        sha256=course.base.training.PARENT_SHA))
    for arm,folder in (('replay100',course.base.EVIDENCE),('pair030',course.EVIDENCE)):
        r = json.loads((folder/arm/'report.json').read_text())
        path = ROOT/r['checkpoint']
        if course.base.training.data.digest(path) != r['checkpoint_sha256']:
            raise ValueError('subject checkpoint changed')
        result[arm] = dict(path=r['checkpoint'],sha256=r['checkpoint_sha256'])
    return result


def summarize_predictions(metadata,predictions):
    if len(metadata) != len(predictions):
        raise ValueError('prediction count mismatch')
    roots = defaultdict(list)
    for m,p in zip(metadata,predictions):
        roots[m['root']].append(bool(p == m['label']))
    if any(len(values) != 4 for values in roots.values()):
        raise ValueError('four-view roots required')
    return dict(cases=len(metadata),exact=sum(sum(v) for v in roots.values()),
        accuracy=sum(sum(v) for v in roots.values())/len(metadata),
        roots=len(roots),all4_exact_roots=sum(all(v) for v in roots.values()))


def standardize(train,others):
    """Training-only moments. The floor is fixed, not selected on test."""
    import torch
    mean = train.mean(0)
    scale = train.std(0,unbiased=False).clamp_min(.01)
    return (train-mean)/scale,[(x-mean)/scale for x in others],mean,scale


def capture(args):
    import numpy as np
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.infer.generate import _strip
    course.base.deadline()
    actual = json.loads((course.EVIDENCE/'fresh_test/report.json').read_text())
    if actual['status'] != 'FRESH_CODE_TEST_COLLECTED':
        raise ValueError('four-arm first-answer collection required before diagnostic use')
    rows = source_rows();subjects = checkpoints()
    if OUTPUT.exists() or (EVIDENCE/'capture.json').exists():
        raise FileExistsError('new probe namespace required')
    idle_before_gpu();OUTPUT.mkdir(parents=True,exist_ok=False)
    began=time.perf_counter();results={}
    with wall_limit(args.max_wall_sec):
        for subject in SUBJECTS:
            course.base.deadline()
            torch,model,cfg,tok,initial = course.base.training.load_runtime('parent_ntp')
            if subject != 'parent':
                state=torch.load(ROOT/subjects[subject]['path'],map_location='cpu',weights_only=True)
                model.load_state_dict(_strip(state['model']),strict=True);del state
            before=course.base.training.state_fingerprint(model)
            model=prepare_model(model)
            if model.visit_schedule()!=list(range(14)):
                raise ValueError('single-visit dense14 schedule required for this diagnostic')
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            wrapped=PrecisionForward(model,'fp32_math')
            target=OUTPUT/subject;target.mkdir();files={};seconds=time.perf_counter()
            with torch.no_grad(),LayerCapture(model,LAYER_INDICES) as layers:
                for split,values in rows.items():
                    hidden=[];projected=[];metadata=[];parity=[]
                    intermediate={i:[] for i in LAYER_INDICES}
                    for index,row in enumerate(values):
                        course.base.deadline()
                        text=prompt(row);ids=tok.encode(text).ids
                        x=torch.tensor([ids],device='cuda')
                        logits,h,kv=wrapped(x,use_cache=True,logits_last_only=True,return_mtp_hidden=True)
                        observed=layers.take()
                        if h.shape != (1,1,768) or model.emb_up is None:
                            raise ValueError('declared dense14 feature geometry differs')
                        z=torch.nn.functional.linear(h,model._emb_up_w().t())
                        hidden.append(h[0,0].cpu().numpy());projected.append(z[0,0].cpu().numpy())
                        layer_values=torch.stack([observed[i][0] for i in LAYER_INDICES]).cpu().numpy()
                        for position,index_layer in enumerate(LAYER_INDICES):
                            intermediate[index_layer].append(layer_values[position])
                        m=row['meta'];label=course.base.data.text(row,-1)
                        metadata.append(dict(group=m['language']+':'+m['kind'],root=m['semantic_root_id'],
                            label=label,first_value=m['first_value'],source_signature=course.base.data.sha(row['messages']),
                            prefix_sha256=course.base.data.sha(ids),prefix_tokens=len(ids)))
                        if index == 0:
                            plain,_=wrapped(x,use_cache=True,logits_last_only=True)
                            layers.take()
                            same=torch.equal(logits,plain)
                            if not same:raise ValueError('capture flag changed first-position logits')
                            parity.append(dict(first_logits_bit_equal=same,token_count=len(ids),gold_answer_body_appended=False,
                                source_facts_visible=True))
                        del logits,h,z,kv
                        if (index+1)%256==0:
                            print('[PREFIX_CAPTURE] '+json.dumps(dict(subject=subject,split=split,rows=index+1)),flush=True)
                    arrays=[('hidden768',np.stack(hidden)),('projected256',np.stack(projected))]
                    arrays.extend((f'layer{i:02d}',np.stack(intermediate[i])) for i in LAYER_INDICES)
                    for name,array in arrays:
                        if not np.isfinite(array).all():raise ValueError('nonfinite captured feature')
                        path=target/(split+'_'+name+'.npy')
                        with path.open('xb') as stream:np.save(stream,array,allow_pickle=False)
                        if path.stat().st_size>=20000000:raise ValueError('cache shard exceeds20MB')
                        files[split+'_'+name]=dict(path=str(path.relative_to(OUTPUT)),sha256=course.base.training.data.digest(path),
                            shape=list(array.shape),bytes=path.stat().st_size)
                    course.base.training.write(target/(split+'_index.json'),metadata)
                    files[split+'_index']=dict(path=str((target/(split+'_index.json')).relative_to(OUTPUT)),
                        sha256=course.base.training.data.digest(target/(split+'_index.json')),parity=parity)
            model.clear_quant();model=model.cpu()
            after=course.base.training.state_fingerprint(model)
            if before!=after:raise ValueError('backbone state changed during feature capture')
            results[subject]=dict(checkpoint=subjects[subject],state_before=before,state_after=after,
                files=files,whole_sec=time.perf_counter()-seconds,model_optimizer_steps=0,
                logical_schedule=list(range(14)),kv_owners=list(model.owner))
            del model,wrapped
            import gc
            gc.collect();torch.cuda.empty_cache()
    result=dict(info(),status='FROZEN_PREFIX_CAPTURED',subjects=results,counts={s:len(v) for s,v in rows.items()},
        prior_answer_report_sha256=course.base.training.data.digest(course.EVIDENCE/'fresh_test/report.json'),
        whole_sec=time.perf_counter()-began)
    course.base.training.write(EVIDENCE/'capture.json',result)
    print('[PREFIX_FINAL] '+json.dumps(dict(status=result['status'],whole_sec=result['whole_sec'])),flush=True)
    return 0


def fit_one(features,labels,metadata,kind,shuffle=False):
    import torch
    torch.manual_seed(20261015)
    train,(dev,test),mean,scale=standardize(features['train'],[features['dev'],features['test']])
    y=labels['train'].clone()
    if shuffle:y=y[torch.randperm(len(y),generator=torch.Generator().manual_seed(20261016))]
    model=(torch.nn.Linear(train.shape[1],6) if kind=='linear' else
        torch.nn.Sequential(torch.nn.Linear(train.shape[1],16),torch.nn.Tanh(),torch.nn.Linear(16,6)))
    optimizer=torch.optim.AdamW(model.parameters(),lr=.01,weight_decay=.01)
    best=None;trace=[]
    for step in range(1,501):
        optimizer.zero_grad(set_to_none=True)
        loss=torch.nn.functional.cross_entropy(model(train),y);loss.backward();optimizer.step()
        if step%20==0:
            with torch.no_grad():dev_loss=float(torch.nn.functional.cross_entropy(model(dev),labels['dev']))
            trace.append(dict(step=step,train_ce=float(loss),dev_ce=dev_loss))
            if best is None or dev_loss<best[0]:best=(dev_loss,step,copy.deepcopy(model.state_dict()))
    model.load_state_dict(best[2]);scores={}
    with torch.no_grad():
        fitted_label_accuracy=float(model(train).argmax(-1).eq(y).float().mean())
        for split,x in (('train',train),('dev',dev),('test',test)):
            prediction=model(x).argmax(-1).tolist()
            scores[split]=summarize_predictions(metadata[split],prediction)
    return dict(classifier=kind,shuffled_train_labels=shuffle,selected_step=best[1],
        selected_dev_ce=best[0],scores=scores,trace=trace,
        train_only_moment_sha256=course.base.data.sha([mean.tolist(),scale.tolist()]),
        classifier_parameters=sum(p.numel() for p in model.parameters()),saved_weights=False,
        train_fitted_label_accuracy=fitted_label_accuracy,
        shuffled_control_scope='train labels permuted; dev/test labels unchanged; not the paper type-control replication')


def fit(args):
    import numpy as np
    import torch
    course.base.deadline();torch.set_num_threads(4)
    target=EVIDENCE/'probe_report.json'
    if target.exists():raise FileExistsError('preserve previous probe result')
    capture_report=json.loads((EVIDENCE/'capture.json').read_text())
    if capture_report['status']!='FROZEN_PREFIX_CAPTURED' or capture_report['code_sha256']!=info()['code_sha256']:
        raise ValueError('same-code complete capture required')
    began=time.perf_counter();results={}
    from scripts.p106b_gate_runtime import wall_limit
    with wall_limit(args.max_wall_sec):
        for subject,r in capture_report['subjects'].items():
            indices={}
            for split in ('train','dev','test'):
                item=r['files'][split+'_index'];path=OUTPUT/item['path']
                if course.base.training.data.digest(path)!=item['sha256']:raise ValueError('index changed')
                indices[split]=json.loads(path.read_text())
            results[subject]={}
            for name in ('hidden768','projected256','random256',*(f'layer{i:02d}' for i in LAYER_INDICES)):
                arrays={}
                for split in indices:
                    stored='hidden768' if name=='random256' else name
                    item=r['files'][split+'_'+stored];path=OUTPUT/item['path']
                    if course.base.training.data.digest(path)!=item['sha256']:raise ValueError('feature changed')
                    arrays[split]=torch.from_numpy(np.load(path,allow_pickle=False))
                if name=='random256':
                    generator=torch.Generator().manual_seed(20261015)
                    projection=torch.linalg.qr(torch.randn(768,256,generator=generator),mode='reduced').Q
                    arrays={split:value@projection for split,value in arrays.items()}
                group_results={}
                for group in sorted({m['group'] for m in indices['train']}):
                    course.base.deadline()
                    keep={s:[i for i,m in enumerate(values) if m['group']==group] for s,values in indices.items()}
                    names=sorted({indices['train'][i]['label'] for i in keep['train']})
                    if len(names)!=6:raise ValueError('six training labels required')
                    label_ids={label:i for i,label in enumerate(names)}
                    metadata={s:[dict(indices[s][i],label=label_ids[indices[s][i]['label']],
                        label_text=indices[s][i]['label']) for i in keep[s]] for s in indices}
                    labels={s:torch.tensor([m['label'] for m in values]) for s,values in metadata.items()}
                    features={s:arrays[s][keep[s]] for s in arrays}
                    majority=int(torch.bincount(labels['train'],minlength=6).argmax())
                    controls={s:dict(constant=summarize_predictions(metadata[s],[majority]*len(metadata[s])),
                        first_value=summarize_predictions(metadata[s],[label_ids[indices[s][i]['first_value']] for i in keep[s]])) for s in metadata}
                    fits=[fit_one(features,labels,metadata,kind,shuffle) for kind in ('linear','mlp16') for shuffle in (False,True)]
                    group_results[group]=dict(label_names=names,controls=controls,classifiers=fits)
                    print('[PREFIX_PROBE] '+json.dumps(dict(subject=subject,feature=name,group=group,
                        test=[dict(classifier=f['classifier'],shuffle=f['shuffled_train_labels'],**f['scores']['test']) for f in fits])),flush=True)
                results[subject][name]=group_results
    result=dict(info(),status='CPU_PROBE_COLLECTED',results=results,whole_sec=time.perf_counter()-began,
        capture_sha256=course.base.training.data.digest(EVIDENCE/'capture.json'),
        test_scope='current code test is diagnostic development now; label prediction is not free generation',
        causal_claim='NOT_ESTABLISHED',general_intelligence='NOT_ESTABLISHED')
    course.base.training.write(target,result)
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('capture','fit'),required=True)
    parser.add_argument('--max-wall-sec',type=int,default=900)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if not 60<=args.max_wall_sec<=1800:parser.error('bounded60..1800')
    if args.check_only:
        print('[CHECK_ONLY] '+json.dumps(info()));return 0
    return capture(args) if args.mode=='capture' else fit(args)


if __name__=='__main__':raise SystemExit(main())
