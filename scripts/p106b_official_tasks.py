"""Exact pinned Core6 YAML tasks with local evaluation-only storage overrides.

Pure import; explicit load requires the approved, source-verified lm_eval.
No model/backend is opened. Never change prompt/choice/process/metric functions.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sysconfig

from scripts.p106b_official_lm_adapter import prepare_harness, sha256_file
from scripts.prepare_p106b_official_eval import (ASSETS, MANIFEST_SHA, SOURCE,
    CACHE, task_specs, verify_assets, configure_hf_cache)


def load_tasks():
    configure_hf_cache()
    _,provenance=prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
    if sha256_file(ASSETS/'manifest.json')!=MANIFEST_SHA:
        raise ValueError('pinned Core6 data manifest differs')
    specs=task_specs(json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8')))
    verify_assets(specs)
    from lm_eval.tasks._yaml_loader import load_yaml
    from lm_eval.api.task import ConfigurableTask
    tasks={}
    for spec in specs:
        task_config=load_yaml(spec['official_yaml'],resolve_func=True,recursive=True)
        if task_config['task']!=spec['task']:raise ValueError('official task identity differs')
        before={k:task_config.get(k) for k in ('doc_to_text','doc_to_choice','doc_to_target','process_docs','metric_list','target_delimiter')}
        task_config.update(copy.deepcopy(spec['overrides']))
        task_config['dataset_kwargs']['cache_dir']=str(CACHE/spec['task'])
        task=ConfigurableTask(config=task_config)
        if set(task.dataset)!={next(iter(spec['overrides']['dataset_kwargs']['data_files']))}:
            raise ValueError('unexpected dataset split after official task init')
        if len(task.eval_docs)!=spec['expected_rows']:
            raise ValueError('official processed evaluation denominator differs')
        # Constructor defaults may fill a delimiter, but a specified prompt,
        # function, choice, label or metric must not change.
        for key,value in before.items():
            if value is not None and getattr(task.config,key)!=value:
                raise ValueError('official task field changed: '+key)
        tasks[spec['task']]=task
    return tasks,specs,provenance


def task_requests(task,doc,index=0):
    ctx=task.fewshot_context(doc,num_fewshot=0,apply_chat_template=False,
        fewshot_as_multiturn=False,system_instruction=None)
    requests=task.construct_requests(doc=doc,ctx=ctx,
        metadata=(task.config.task,index,task.config.repeats),apply_chat_template=False)
    if not isinstance(requests,list):requests=[requests]
    choices=task.doc_to_choice(doc)
    if len(requests)!=len(choices) or not requests:
        raise ValueError('not exactly one likelihood request per official choice')
    if any(r.request_type!='loglikelihood' or len(r.args)!=2
           or any(not isinstance(v,str) for v in r.args) for r in requests):
        raise ValueError('unexpected official request type/shape')
    return ctx,choices,requests


def dummy_metric_oracle(task,doc,choices):
    """Independent argmax and original-choice character denominator check."""
    gold=task.doc_to_text(doc) if task.multiple_input else task.doc_to_target(doc)
    if type(gold) is not int or not 0<=gold<len(choices):
        raise ValueError('Core6 single-label integer target required')
    scores=[-(i+1.) for i in range(len(choices))]
    observed=task.process_results(doc,[(score,False) for score in scores])
    expected={'acc':int(gold==0)}
    if 'acc_norm' in observed:
        if any(len(choice)==0 for choice in choices):raise ValueError('empty official choice')
        index=max(range(len(choices)),key=lambda i:scores[i]/len(choices[i]))
        expected['acc_norm']=int(gold==index)
    for key,value in expected.items():
        if observed[key]!=value:raise ValueError('official metric differs from independent oracle')
    return dict(gold_index=gold,dummy_likelihoods=scores,observed=observed,
                expected=expected,character_denominator=[len(c) for c in choices])


def contract_report():
    tasks,specs,provenance=load_tasks();rows=[]
    for name,task in tasks.items():
        examples=[]
        for i in range(2):
            doc=task.eval_docs[i];context,choices,requests=task_requests(task,doc,i)
            examples.append(dict(doc_index=i,context=context,choices=choices,
                request_args=[list(r.args) for r in requests],
                metric_oracle=dummy_metric_oracle(task,doc,choices)))
        rows.append(dict(task=name,rows=len(task.eval_docs),multiple_input=bool(task.multiple_input),
            dataset_splits=list(task.dataset),examples=examples))
    return dict(schema='P106B_OFFICIAL_TASK_CPU_CONTRACT_V1',status='OFFICIAL_TASK_CONTRACT_COMPLETE',
        framework_provenance=provenance,task_specs=specs,tasks=rows,
        num_fewshot=0,chat_template=False,models=0,installs=0,
        source_sha256=sha256_file(Path(__file__)),official_model_score='NOT_RUN')
