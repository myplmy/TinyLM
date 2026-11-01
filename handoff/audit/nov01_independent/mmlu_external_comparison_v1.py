"""Compare independently closed full MMLU runs without model calls or retuning."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).parent
TINY = ROOT/'test_result/evidence/p106b_mmlu_official_v1_20261101/readback'
FALCON = ROOT/'test_result/evidence/p106b_falcon_mmlu_v3_20261101/readback'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def compare(existing_only):
    baseline = read(AUDIT/'mmlu_pre_model_baselines_v1.json')
    paths = {name:TINY/('mmlu_'+name+'_full_readback_'+version+'.json')
        for name,version in [('native0','v2'),('broad0','v2'),('native5','v3'),('broad5','v3')]}
    if not existing_only:
        for shot in (0,5):
            path = FALCON/('mmlu_falcon'+str(shot)+'_full_readback_v1.json')
            if path.is_file():
                paths['falcon'+str(shot)] = path
        assert any(name.startswith('falcon') for name in paths), 'External full root evidence required.'
    inputs = {name:read(path) for name,path in paths.items()}
    reference = inputs['native0']['predictions']
    expected_keys = [(r['subject'],r['doc_id'],r['gold']) for r in reference]
    assert len(expected_keys)==14042 and len(set((a,b) for a,b,_ in expected_keys))==14042
    for name,value in inputs.items():
        assert not value['errors'] and value['rows']==14042
        assert [(r['subject'],r['doc_id'],r['gold']) for r in value['predictions']]==expected_keys
        assert value['correct']==sum(r['prediction']==r['gold'] for r in value['predictions'])
        assert math.isclose(value['accuracy'],value['correct']/14042,abs_tol=1e-12)
    truth = {subject:np.asarray([r['gold'] for r in reference if r['subject']==subject],dtype=np.int64)
             for subject in baseline['subjects']}
    predictions = {name:{subject:np.asarray([r['prediction'] for r in value['predictions'] if r['subject']==subject],dtype=np.int64)
                   for subject in truth} for name,value in inputs.items()}
    protocol = baseline['planned_label_permutation']
    repeats = protocol['repeats'];assert repeats==2000
    null = {name:np.zeros(repeats,dtype=np.int64) for name in inputs}
    for subject in sorted(truth):
        seed = protocol['seed']+int(hashlib.sha256(subject.encode()).hexdigest()[:8],16)
        rng = np.random.default_rng(seed)
        shuffled = rng.permuted(np.broadcast_to(truth[subject],(repeats,len(truth[subject]))),axis=1)
        for name in inputs:
            null[name] += (shuffled==predictions[name][subject]).sum(axis=1)
    runs = {}
    for name,value in inputs.items():
        values = null[name]
        tail = (1+int((values>=value['correct']).sum()))/(1+repeats)
        runs[name] = dict(correct=value['correct'],rows=14042,accuracy=value['accuracy'],
            uniform_expectation=.25,posthoc_global_majority_accuracy=baseline['posthoc_global_majority_accuracy'],
            conditional_permutation=dict(repeats=repeats,mean=float(values.mean()),sd=float(values.std(ddof=1)),
                interval95_correct=[float(v) for v in np.quantile(values,[.025,.975])],
                exploratory_upper_tail=tail,interpretation=protocol['interpretation']),
            token_lengths=value['token_lengths'],root_path=str(paths[name].relative_to(ROOT)),
            root_sha256=digest(paths[name]))
    original = read(TINY/'mmlu_four_run_comparison_v3.json')
    for name in ('native0','broad0','native5','broad5'):
        for key in ('mean','sd','exploratory_upper_tail'):
            assert math.isclose(runs[name]['conditional_permutation'][key],
                original['runs'][name]['conditional_permutation'][key],abs_tol=1e-12)
    paired = {}
    for shot in (0,5):
        right = 'falcon'+str(shot)
        if right not in inputs:
            continue
        for family in ('native','broad'):
            left = family+str(shot)
            a = np.asarray([r['correct'] for r in inputs[left]['predictions']])
            b = np.asarray([r['correct'] for r in inputs[right]['predictions']])
            paired[left+'_to_'+right] = dict(rows=14042,gain=int(((a==0)&(b==1)).sum()),
                loss=int(((a==1)&(b==0)).sum()),both_correct=int(((a==1)&(b==1)).sum()),
                delta_accuracy=float((b-a).mean()),scope='DESCRIPTIVE_DIFFERENT_MODELS_NOT_ARCHITECTURE_CAUSAL_EFFECT')
    result = dict(schema='MMLU_EXTERNAL_FROZEN_COMPARISON_V1',runs=runs,paired=paired,
        planned_conditional_protocol=protocol,prior_four_run_statistics_reproduced=True,
        missing_external_full_runs=['falcon'+str(s) for s in (0,5) if 'falcon'+str(s) not in inputs],
        official_protocol='DEFAULT_LETTER_ACC_SIZE_WEIGHTED_1024_CONTEXT',
        tokenizer_pretraining_and_structure_differ=True,benchmark_train_or_teacher_reuse=False,
        all_pretraining_contamination='UNKNOWN',new_model_training=0,new_quality_gain_claim=False,
        auditor_sha256=digest(Path(__file__)),errors=[])
    if not existing_only:
        with (AUDIT/'MMLU_EXTERNAL_COMPARISON_v1.json').open('x') as f:
            json.dump(result,f,ensure_ascii=False,indent=2)
            f.write(chr(10))
    print(json.dumps(dict(mode='EXISTING_CONTRACT_ONLY' if existing_only else 'EXTERNAL_FULL_COMPARISON',
        rows_per_run=14042,runs={n:dict(correct=v['correct'],accuracy=v['accuracy'],
            exploratory_tail=v['conditional_permutation']['exploratory_upper_tail']) for n,v in runs.items()},errors=[])))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-only-check',action='store_true')
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES']=''
    compare(args.existing_only_check)
