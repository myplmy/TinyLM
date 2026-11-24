"""Read-only admission audit: never import IFEval's downloading utility."""
import argparse
import ast
import hashlib
from importlib import metadata, util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def audit():
    spec = util.find_spec('lm_eval')
    if spec is None or spec.origin is None:raise RuntimeError('existing lm_eval runtime required')
    directory = Path(spec.origin).parent/'tasks/ifeval'
    files = {name:(directory/name).read_text(encoding='utf-8') for name in (
        'ifeval.yaml', 'utils.py', 'instructions.py', 'instructions_util.py', 'instructions_registry.py')}
    task = files['ifeval.yaml']
    metrics = re.findall(r'^\s+- metric:\s*(\S+)',task,re.M)
    if (not re.search(r'^dataset_path:\s*google/IFEval\s*$',task,re.M) or
            not re.search(r'^test_split:\s*train\s*$',task,re.M) or
            metrics != ['prompt_level_strict_acc','inst_level_strict_acc','prompt_level_loose_acc','inst_level_loose_acc']):
        raise ValueError('official dataset/split/metric contract differs')
    requirements = [r for r in metadata.distribution('lm_eval').requires or [] if 'extra == "ifeval"' in r]
    packages = {}
    for name in ('lm_eval','langdetect','nltk','immutabledict','six','click','joblib','regex','tqdm'):
        try:packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError:packages[name]=None
    missing = [name for name in ('langdetect','nltk','immutabledict') if packages[name] is None]
    tree = ast.parse(files['instructions_util.py'])
    top_download = any(isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and
        isinstance(node.value.func,ast.Name) and node.value.func.id=='download_nltk_resources' for node in tree.body)
    return dict(schema='P108B_IFEVAL_EXISTING_RUNTIME_ADMISSION_V1',
        status='DEPENDENCIES_MISSING_NO_MODEL_RUN' if missing else 'IMPORT_AND_DATA_ADMISSION_STILL_REQUIRED',
        python=sys.executable,installed_versions=packages,official_optional_extra_requirements=requirements,
        missing_direct_packages=missing,required_nltk_resource='punkt_tab',
        official_task_source_sha256={name:hashlib.sha256(text.encode()).hexdigest().upper() for name,text in files.items()},
        source_directory=str(directory),framework_install_origin=json.loads(metadata.distribution('lm_eval').read_text('direct_url.json') or '{}'),
        source_level_metrics=metrics,dataset='google/IFEval',split='train',required_expected_rows=541,
        actual_dataset_rows='NOT_CHECKED',dataset_revision='NOT_ADMITTED',
        official_max_generation_tokens=1280,official_num_fewshot=0,
        import_can_download_nltk_resource=top_download,official_checker_import_executed=False,
        model_context_compatibility='NOT_VERIFIED; native1024 and official1280 generation require explicit protocol',
        model_calls=0,gpu_calls=0,package_installs=0,downloads=0,
        ready_for_official_model_evaluation=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    target=Path(args.output).resolve();allowed=ROOT/'handoff/audit/nov16_pm_p108b'
    if target.is_symlink() or not target.is_relative_to(allowed.resolve()):
        raise ValueError('owned afternoon audit destination required')
    result=audit();target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8')as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:result[k]for k in ('status','missing_direct_packages','import_can_download_nltk_resource','model_calls','downloads')},ensure_ascii=False))


if __name__=='__main__':main()
