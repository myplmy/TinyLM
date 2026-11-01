#!/usr/bin/env python3
"""Pin Core6 local evaluation-only task configs; optional existing-CPU loader.

No installation/registration, lm_eval import, model, GPU or network path.
Official source and downloaded originals are never edited. The loader writes
only a fresh, explicit runtime cache and a bounded evidence report.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
_HF_CACHE_CONFIGURED=False
SOURCE=ROOT/'data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source'
ASSETS=ROOT/'data_cache/p106b_official_eval_assets/core6_d6de816_20261023'
MANIFEST_SHA='431A096364D44980A7D0C6E072E8A06C2FAA109946FAA07E56F7687CADFEA60B'
COMMIT='d6de81643928d653435c431bae19945d41d32520'
TASKS={
    'piqa':('piqa/piqa.yaml','validation',1838,('goal','sol1','sol2','label')),
    'arc_easy':('arc/arc_easy.yaml','test',2376,('question','choices','answerKey')),
    'arc_challenge':('arc/arc_challenge.yaml','test',1172,('question','choices','answerKey')),
    'hellaswag':('hellaswag/hellaswag.yaml','validation',10042,('ctx_a','ctx_b','endings','label','activity_label')),
    'winogrande':('winogrande/default.yaml','validation',1267,('sentence','option1','option2','answer')),
    'boolq':('super_glue/boolq/default.yaml','validation',3270,('passage','question','label')),
}
OUTPUT=ROOT/'test_result/evidence/p106b_official_assets_cpu_v1'
CACHE=ROOT/'data_cache/p106b_official_eval_runtime/core6_loader_v1'


def configure_hf_cache():
    """Apply the existing project cache policy before any HF library loads.

    Import remains stdlib-only. Explicit callers get an auditable receipt;
    external path overrides and late configuration are rejected, not hidden.
    """
    global _HF_CACHE_CONFIGURED
    expected=dict(HF_HOME=str(ROOT/'HF'),HF_HUB_CACHE=str(ROOT/'HF/hub'),
                  HF_DATASETS_CACHE=str(ROOT/'HF/datasets'))
    for key,target in (('TINYLM_DIR',ROOT),('TINYLM_HF',ROOT/'HF')):
        if key in os.environ and Path(os.environ[key]).resolve()!=target:
            raise ValueError('evaluation cache override outside approved project: '+key)
    if not _HF_CACHE_CONFIGURED:
        if any(name.split('.')[0] in {'datasets','transformers','huggingface_hub'} for name in sys.modules):
            raise RuntimeError('HF library already imported before project cache policy')
        from tinylm import paths
        if paths.ROOT.resolve()!=ROOT or paths.HF_DIR.resolve()!=ROOT/'HF':
            raise ValueError('loaded project cache module has a different root')
        if any(os.environ.get(key)!=value for key,value in expected.items()) or 'TRANSFORMERS_CACHE' in os.environ:
            raise ValueError('project cache policy did not take effect before HF import')
        _HF_CACHE_CONFIGURED=True
    if any(os.environ.get(key)!=value for key,value in expected.items()) or 'TRANSFORMERS_CACHE' in os.environ:
        raise ValueError('project cache environment changed after initial configuration')
    return dict(policy='EXISTING_TINYLM_PATHS_BEFORE_HF_IMPORT',environment=expected,
                process_only=True,external_environment_files_modified=False)


def digest(path):
    if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
        raise ValueError('explicit regular nonsymlink file required')
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
    return h.hexdigest().upper()


def local_path(root,relative):
    p=Path(relative)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('repository-relative asset path required')
    value=root/p
    if value.is_symlink() or any(x.is_symlink() for x in value.parents):
        raise ValueError('linked asset path refused')
    return value


def task_specs(manifest,*,assets=ASSETS,source=SOURCE):
    """Only storage and unused fewshot data differ from each official YAML.

    At execution the official YAML loader must resolve include/!function. Merge
    these overrides into that full config, not into an empty task definition.
    """
    if manifest.get('harness_revision')!=COMMIT:
        raise ValueError('unexpected official framework revision')
    rows=[r for r in manifest['files'] if r.get('kind')=='evaluation_parquet']
    if len(rows)!=len(TASKS) or {r['task'] for r in rows}!=set(TASKS):
        raise ValueError('exact six evaluation task files required')
    result=[]
    for task,(relative,split,count,columns) in TASKS.items():
        row=next(r for r in rows if r['task']==task)
        if row.get('split')!=split or row.get('expected_rows')!=count:
            raise ValueError('evaluation split/denominator differs')
        data=local_path(assets,row['local_relative_path'])
        yaml=local_path(source/'lm_eval/tasks',relative)
        result.append(dict(task=task,official_yaml=str(yaml),dataset_revision=row['revision'],
            original_repo_id=row['repo_id'],original_config=row['config'],
            expected_rows=count,required_columns=list(columns),data_file=str(data),
            data_sha256=row['sha256'].upper(),official_yaml_sha256=digest(yaml),
            overrides=dict(dataset_path='parquet',dataset_name=None,
                dataset_kwargs=dict(data_files={split:str(data)}),
                training_split=None,validation_split=split if split=='validation' else None,
                test_split=split if split=='test' else None,num_fewshot=0,
                fewshot_split=None,fewshot_config=dict(samples=[])),
            unchanged='official process_docs, prompt, choices, target, metrics, aggregation'))
    return result


def verify_assets(specs):
    for spec in specs:
        if digest(Path(spec['data_file']))!=spec['data_sha256']:
            raise ValueError('evaluation data SHA mismatch: '+spec['task'])


def validate_loaded(spec,dataset_dict):
    split=next(iter(spec['overrides']['dataset_kwargs']['data_files']))
    if set(dataset_dict)!= {split}:
        raise ValueError('loader produced an unexpected/train split')
    data=dataset_dict[split]
    if len(data)!=spec['expected_rows'] or not set(spec['required_columns'])<=set(data.column_names):
        raise ValueError('loaded row denominator/schema differs: '+spec['task'])
    h=hashlib.sha256()
    for row in data:
        h.update((json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
    return dict(task=spec['task'],split=split,rows=len(data),columns=data.column_names,
        features=data.features.to_dict(),ordered_row_json_sha256=h.hexdigest().upper())


def write_report(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    if len(raw)>=20_000_000:raise ValueError('result file must be below20MB')
    with path.open('xb') as stream:stream.write(raw)


def prepare(execute=False):
    if digest(ASSETS/'manifest.json')!=MANIFEST_SHA:
        raise ValueError('asset manifest identity differs')
    specs=task_specs(json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8')))
    verify_assets(specs)
    if not execute:
        return dict(status='ASSET_CONFIG_READY_LOADER_NOT_RUN',framework_commit=COMMIT,
            manifest_sha256=MANIFEST_SHA,task_specs=specs,installs=0,models=0,
            official_task_init='NOT_RUN',metric_and_prompt_parity='NOT_RUN')
    if OUTPUT.exists() or CACHE.exists():raise FileExistsError('prior output/cache preserved')
    cache_policy=configure_hf_cache()
    # No remote repo ID is passed to the CPU loader. All six data files are local.
    os.environ['HF_HUB_OFFLINE']='1';os.environ['HF_DATASETS_OFFLINE']='1'
    OUTPUT.mkdir(parents=True,exist_ok=False);CACHE.mkdir(parents=True,exist_ok=False)
    report=dict(schema='P106B_OFFICIAL_CORE6_CPU_ASSET_PREP_V1',status='STARTED',
        started_at=datetime.now(timezone.utc).isoformat(),framework_commit=COMMIT,
        manifest_sha256=MANIFEST_SHA,source_sha256=digest(Path(__file__)),task_specs=specs,
        installs=0,network_requests=0,model_loads=0,checkpoint_writes=0,
        official_task_init='NOT_RUN',metric_and_prompt_parity='NOT_RUN',loaded=[],
        cache_policy=cache_policy)
    tick=time.monotonic()
    try:
        from datasets import load_dataset
        report['datasets_version']=importlib.metadata.version('datasets')
        report['pyarrow_version']=importlib.metadata.version('pyarrow')
        for spec in specs:
            d=load_dataset('parquet',data_files=spec['overrides']['dataset_kwargs']['data_files'],
                           cache_dir=str(CACHE/spec['task']))
            report['loaded'].append(validate_loaded(spec,d))
        verify_assets(specs)
        if digest(ASSETS/'manifest.json')!=MANIFEST_SHA:raise ValueError('manifest changed during load')
        report.update(status='LOCAL_EVAL_SPLITS_LOADED',source_assets_unchanged=True,
                      total_rows=sum(x['rows'] for x in report['loaded']))
    except BaseException as exc:
        report.update(status='PREPARATION_ERROR',error_type=type(exc).__name__,error=str(exc)[:2000])
        raise
    finally:
        report.update(ended_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-tick)
        write_report(OUTPUT/'report.json',report)
    return dict(status=report['status'],total_rows=report['total_rows'],output=str(OUTPUT),
                wall_seconds=report['wall_seconds'],official_evaluation='NOT_RUN')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    a=p.parse_args();print(json.dumps(prepare(a.execute),ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()
