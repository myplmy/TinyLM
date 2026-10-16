#!/usr/bin/env python3
"""Source-defined question-bundle census and existing full-output CPU readback.

No models, new logits, generation, training or source reselection. Full source
censuses live in a new ignored data namespace; Git evidence holds only summaries.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import json
from scripts import p106b_night_question_bundles as method
from scripts import diag_p106b_night_order_probe as probe
from scripts import diag_p106b_night_diversity as original

e, prompt, unique, panel, qa = probe.e, probe.prompt, probe.unique, probe.panel, probe.qa
TAG = 'p106b_night_question_bundles_v1_s1337'
FROZEN = ROOT / 'HF/sft_ready' / TAG / 'source'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
PROVIDERS = ((e, panel.TRAINED), (prompt, prompt.ENDPOINTS), (unique, unique.ENDPOINTS))
CODE = ('scripts/diag_p106b_night_question_bundles.py',
        'scripts/test_p106b_night_question_bundles_runtime.py',
        'scripts/p106b_night_question_bundles.py', 'scripts/test_p106b_night_question_bundles.py',
        *probe.CODE, *original.CODE)


def labels():
    return ['foundation.' + x for x in panel.TRAINED] + ['prompt.' + x for x in prompt.ENDPOINTS] + ['unique.' + x for x in unique.ENDPOINTS]


def info():
    return dict(schema='P106B_NIGHT_QUESTION_BUNDLE_RUNTIME_V1', tag=TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        natural_eval_cpu_sha256=qa.data.digest(e.FROZEN / 'report.json'),
        train32k_cpu_sha256=qa.data.digest(original.CORPUS / 'report.json'),
        endpoints=labels(), source_test_roots=512, source_train_roots=32768,
        source_rule=method.VERSION, model_loaded=False, new_logits=False,
        new_generation=False, optimizer_updates=0, checkpoints_written=0,
        grouping_rule_chosen_after_initial_results=True, grouping_uses_actual_answers=False,
        candidate_class_is_semantic_negative=False, automatic_dataset_rejection=False,
        old_bare_full512_gate_credited=False, evidence_contains_source_text_or_answers=False,
        population_scope='repeatedly observed source QA cohort; exploratory natural question pairs, not causal architecture test')


def safe():
    for target in (FROZEN, EVIDENCE):
        for p in (target, *target.parents):
            if p.is_symlink(): raise ValueError('linked question-bundle namespace')
            if p == ROOT: break


def sources():
    _, _, cases = e.read_inputs(); cpu = qa.required(original.CORPUS / 'report.json')
    if (cpu.get('status') != 'DIVERSITY_CPU_FROZEN' or cpu.get('code_sha256') != original.info()['code_sha256']
            or qa.required(original.EVIDENCE / 'cpu_contract.json') != cpu
            or cpu.get('protected_source') is not False):
        raise ValueError('unchanged pinned public32k source CPU required')
    train = list(original.stream(cpu['manifests']['train'])); test = cases['natural']
    if len(train) != 32768 or len(test) != 512: raise ValueError('complete source populations required')
    if any(r.get('split') != 'train' for r in train) or any(r.get('split') != 'test' for r in test):
        raise ValueError('original TRAIN/TEST identities must be preserved')
    if {r['root'] for r in train} & {r['root'] for r in test}: raise ValueError('TRAIN/TEST roots overlap')
    return train, test


def source_summary(census):
    # Full aliases and individual bundle records remain in the ignored source asset.
    return {k:v for k,v in census.items() if k != 'bundles'}


def compact_result(result, expected_census):
    if result.get('source_census') != expected_census or result.get('source_census_sha256') != method._sha(expected_census):
        raise ValueError('summary source was reselected or changed')
    return {k:v for k,v in result.items() if k != 'source_census'}


def prepare():
    import torch
    safe(); train, test = sources()
    if FROZEN.exists() or EVIDENCE.exists(): raise FileExistsError('old bundle census preserved')
    censuses = {name:method.census(rows) for name,rows in (('train',train),('test',test))}
    if torch.cuda.is_initialized(): raise ValueError('source-only CPU must not initialize CUDA')
    selected = []
    for language in ('ko','en'):
        values = [b for b in censuses['test']['bundles'] if b['language'] == language and b['character_distinct_candidate']]
        selected.extend(b['bundle_id'] for b in sorted(values, key=lambda b:qa.data.sha([20261017,'bundle-review',b['bundle_id']]))[:2])
    for name,value in censuses.items(): qa.write(FROZEN / (name + '_census.json'), value)
    result = dict(info(), status='QUESTION_BUNDLE_CPU_FROZEN', cuda_initialized=False,
        censuses={name:source_summary(value) for name,value in censuses.items()},
        census_sha256={name:qa.data.digest(FROZEN/(name+'_census.json')) for name in censuses},
        review_bundle_ids=sorted(selected), review_selection='source bundle ID hash only; no output selection')
    qa.write(FROZEN/'report.json',result);qa.write(EVIDENCE/'inputs.json',result)
    print('[QUESTION_BUNDLE_CPU] ' + json.dumps({name:value['counts'] for name,value in censuses.items()}),flush=True)
    return 0


def read_inputs():
    safe(); frozen = qa.required(FROZEN/'report.json');train,test=sources()
    if (frozen.get('status') != 'QUESTION_BUNDLE_CPU_FROZEN'
            or any(frozen.get(k) != v for k,v in info().items())
            or frozen.get('cuda_initialized') is not False or qa.required(EVIDENCE/'inputs.json') != frozen):
        raise ValueError('complete source-only same-code CPU proof required')
    for name,rows in (('train',train),('test',test)):
        actual=method.census(rows)
        if (qa.required(FROZEN/(name+'_census.json')) != actual
                or qa.data.digest(FROZEN/(name+'_census.json')) != frozen['census_sha256'][name]
                or source_summary(actual) != frozen['censuses'][name]):
            raise ValueError('complete current source census differs')
    return frozen,test,qa.required(FROZEN/'test_census.json')


def readback():
    frozen,cases,census=read_inputs();target=EVIDENCE/'readback.json'
    if target.exists(): raise FileExistsError('old full bundle readback preserved')
    reports={};identities={};source_reports={}
    # Require every preregistered full endpoint before producing an aggregate.
    for provider,endpoints in PROVIDERS:
        family='foundation' if provider is e else 'prompt' if provider is prompt else 'unique'
        for endpoint in endpoints:
            _,identity,_,report_hash,events=probe.verified_primary(provider,endpoint)
            label=family+'.'+endpoint
            reports[label]=compact_result(method.summarize(events,cases),census)
            source_reports[label]=report_hash;identities.setdefault(identity,[]).append(label)
    if list(reports) != labels(): raise ValueError('all ten fixed complete labels required')
    result=dict(info(),status='QUESTION_BUNDLE_TEN_RAW_RECOUNTED',errors=0,
        input_report_sha256=qa.data.digest(FROZEN/'report.json'),
        endpoint_report_sha256=source_reports,checkpoint_alias_groups=identities,reports=reports,
        incomplete_endpoints_filled_with_zero=False,training_examples_generated=False)
    qa.write(target,result)
    for label,report in reports.items():
        print('[QUESTION_BUNDLE_MODEL] '+json.dumps(dict(endpoint=label,by_language={l:report['by_language'][l]['by_category']['character_distinct_candidate'] for l in ('ko','en')})),flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','readback'),required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU operation required')
    try:return prepare() if a.mode=='freeze' else readback()
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[QUESTION_BUNDLE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
