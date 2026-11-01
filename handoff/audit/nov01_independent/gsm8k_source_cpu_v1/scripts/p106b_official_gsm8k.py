"""GSM8K 고정 원문/공식 task/생성 경계. import는 stdlib만 사용한다."""
from collections import Counter
import copy
import dataclasses
import json
from pathlib import Path
import sysconfig
from types import SimpleNamespace

from scripts.p106b_official_mmlu import digest, canonical

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data_cache/p106b_gsm8k_official_v1_20261101'
OUTPUT = ROOT / 'test_result/evidence/p106b_gsm8k_official_v1_20261101'
REVISION = '740312add88f781978c0658806c59bc2815b9866'
MODELS = ('native595-q', 'new595-broad-q')
COUNT, FEWSHOT, MAX_NEW, MAX_CONTEXT = 1319, 5, 256, 1024
OFFICIAL_PY = ['lm_eval/evaluator.py', 'lm_eval/evaluator_utils.py', 'lm_eval/api/task.py',
    'lm_eval/api/metrics.py', 'lm_eval/api/registry.py', 'lm_eval/api/samplers.py',
    'lm_eval/tasks/_yaml_loader.py', 'lm_eval/filters/__init__.py',
    'lm_eval/filters/extraction.py', 'lm_eval/filters/selection.py', 'lm_eval/models/utils.py']


def declared_equal(expected, observed):
    if dataclasses.is_dataclass(observed):
        observed = dataclasses.asdict(observed)
    if isinstance(expected, dict):
        return isinstance(observed, dict) and all(key in observed and declared_equal(value, observed[key]) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(observed, list) and len(expected) == len(observed) and all(declared_equal(a, b) for a, b in zip(expected, observed))
    return expected == observed


def validate_rows(rows, expected):
    if len(rows) != expected:
        raise ValueError('공식 split 분모 오류')
    if any(set(row) != {'question', 'answer'} or any(not isinstance(row[k], str) or not row[k].strip()
               for k in ('question', 'answer')) for row in rows):
        raise ValueError('원 질문/답 문자열 오류')
    return dict(rows=len(rows), duplicate_rows_preserved=len(rows) - len({canonical(row) for row in rows}),
                references_without_final_marker=sum('#### ' not in row['answer'] for row in rows))


def official():
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    from scripts.p106b_official_lm_adapter import SOURCE, MANIFEST, prepare_harness
    from scripts.p106b_official_archive import verify_files
    _, framework = prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
    archive = Path(json.loads(MANIFEST.read_text())['archive_path'])
    functions = verify_files(OFFICIAL_PY, archive=archive, source=SOURCE,
                             runtime=Path(sysconfig.get_paths()['purelib']))
    task = verify_files(['lm_eval/tasks/gsm8k/gsm8k.yaml'], archive=archive, source=SOURCE)
    return framework, functions, task


def prepare_assets():
    from scripts.prepare_p106b_official_eval import write_report
    framework, functions, task = official()
    import pyarrow.parquet as pq
    if CACHE.exists() or OUTPUT.exists():
        raise FileExistsError('새 GSM8K namespace 필요')
    repo = ROOT / 'HF/datasets--openai--gsm8k'
    if repo.is_symlink() or (repo / 'refs/main').read_text().strip() != REVISION:
        raise ValueError('고정 원문 snapshot 필요')
    records = []
    for split, count in [('test', COUNT), ('train', 7473)]:
        original = repo / 'snapshots' / REVISION / 'main' / (split + '-00000-of-00001.parquet')
        if original.is_symlink() or any(parent.is_symlink() for parent in original.parents):
            raise ValueError('원문 일반 파일 필요')
        raw = original.read_bytes()
        if len(raw) >= 20_000_000:
            raise ValueError('원본 복사 상한')
        info = validate_rows(pq.read_table(original).to_pylist(), count)
        records.append(dict(split=split, original=str(original.relative_to(ROOT)),
            path=str((CACHE / (split + '.parquet')).relative_to(ROOT)), sha256=digest(original), bytes=len(raw), **info))
    CACHE.mkdir(parents=True)
    OUTPUT.mkdir(parents=True)
    for spec in records:
        with (ROOT / spec['path']).open('xb') as stream:
            stream.write((ROOT / spec['original']).read_bytes())
        if digest(ROOT / spec['path']) != spec['sha256']:
            raise ValueError('바이트 복사 오류')
    report = dict(schema='P106B_OFFICIAL_GSM8K_ASSETS_V1', status='OFFICIAL_ASSETS_VERIFIED',
        framework=framework, official_functions=functions, official_task=task, files=records,
        original_repo_id='openai/gsm8k', revision=REVISION, new_training=0,
        train_split_use='OFFICIAL_FEWSHOT_IN_PROMPT_ONLY_NOT_WEIGHT_UPDATES', downloads=0, installs=0)
    write_report(CACHE / 'assets.json', report)
    write_report(OUTPUT / 'assets_report.json', report)
    return report


def verify_assets():
    value = json.loads((CACHE / 'assets.json').read_text())
    framework, functions, task = official()
    if value['framework'] != framework or value['official_functions'] != functions or value['official_task'] != task:
        raise ValueError('고정 공식 source/runtime 다름')
    for spec in value['files']:
        for key in ('original', 'path'):
            path = ROOT / spec[key]
            if path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or digest(path) != spec['sha256']:
                raise ValueError('원본/복사 정합 실패')
    return value


def load_task():
    value = verify_assets()
    from scripts.prepare_p106b_official_eval import SOURCE
    from lm_eval.tasks._yaml_loader import load_yaml
    from lm_eval.api.task import ConfigurableTask
    task_settings = load_yaml(str(SOURCE / 'lm_eval/tasks/gsm8k/gsm8k.yaml'), resolve_func=True, recursive=True)
    before = copy.deepcopy(task_settings)
    task_settings.update(dataset_path='parquet', dataset_name=None,
        dataset_kwargs=dict(data_files={row['split']:str(ROOT / row['path']) for row in value['files']},
                            cache_dir=str(CACHE / 'loader')))
    task = ConfigurableTask(config=task_settings)
    task.set_fewshot_seed(1337)
    for key in ('doc_to_text', 'doc_to_target', 'metric_list', 'generation_kwargs', 'filter_list', 'num_fewshot',
                'fewshot_split', 'test_split', 'training_split', 'output_type'):
        if key in before and not declared_equal(before[key], getattr(task.config, key)):
            raise ValueError('원문 task 의미가 바뀜: ' + key)
    if len(task.eval_docs) != COUNT or len(task.training_docs()) != 7473 or task.config.num_fewshot != 5:
        raise ValueError('공식 split/fewshot 분모 오류')
    return task, value


def options(raw, *, normalize=None, stops=None, eos=''):
    if normalize is None or stops is None:
        from lm_eval.models.utils import normalize_gen_kwargs, handle_stop_sequences
        normalize, stops = normalize_gen_kwargs, handle_stop_sequences
    value = normalize(copy.deepcopy(raw), MAX_NEW)
    until = stops(value.pop('until', None), eos=eos)
    maximum = value.pop('max_gen_toks')
    do_sample = value.pop('do_sample')
    temperature = value.pop('temperature')
    if value or type(maximum) is not int or not 1 <= maximum <= MAX_NEW or do_sample is not False or temperature != 0:
        raise ValueError('기존 greedy/최대256 외 생성 설정은 지원하지 않는다')
    if any(not isinstance(term, str) for term in until):
        raise ValueError('정식 문자열 stop 필요')
    return maximum, until


def emit_plain(active, context, generation_kwargs, *, use_cache=True, tools=None, postprocess=None):
    """원 sampler를 그대로 쓰고 실제 token prefix와 공식 text stop만 연결한다."""
    from scripts import interactive_research_infer as manual
    if not isinstance(context, str) or not context:
        raise ValueError('공식 raw prompt 필요')
    maximum, until = options(generation_kwargs, eos=active['tokenizer'].decode([2]))
    tokenizer = active['tokenizer']
    if active['cfg'].max_seq_len != MAX_CONTEXT:
        raise ValueError('공통1024 문맥 모델 필요')
    original = tokenizer.encode(context, add_special_tokens=False).ids
    prefix = original[-(MAX_CONTEXT - maximum):]
    from tinylm.infer.dialogue import validate_input_ids
    validate_input_ids(prefix, active['cfg'].vocab_size)
    sampler, capture_type, forward_type = tools or manual.generation_tools()
    capture = capture_type(tokenizer)
    def encode(text):
        if text != context:
            raise ValueError('sampler가 받은 원prompt가 다름')
        return SimpleNamespace(ids=list(prefix))
    capture.encode = encode
    active['route'].assert_active()
    with active['torch'].no_grad():
        _, metadata = sampler(forward_type(active['model'], 'fp32_math'), active['cfg'], capture, context,
            max_new=maximum, temperature=0., top_k=1, device='cuda', use_cache=use_cache,
            logits_last_only=False, return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]])
    active['route'].assert_active()
    _, checked = manual.answer_from_tokens(tokenizer, prefix, capture.decoded_ids, metadata, maximum)
    content = checked['generated_ids'][:-1] if checked['terminal_ids'] else checked['generated_ids']
    raw = tokenizer.decode(content, skip_special_tokens=True)
    if postprocess is None:
        from lm_eval.models.utils import postprocess_generated_text
        postprocess = postprocess_generated_text
    output = postprocess(generation=raw, stop=until, think_end_token=None)
    return output, dict(checked, original_prompt_tokens=len(original), kept_prompt_tokens=len(prefix),
        removed_prompt_tokens=len(original) - len(prefix), actual_prefix_ids=prefix,
        raw_decoded_generation=raw, until=until, raw_prompt_preserved=True,
        stop_scope='NATIVE_EOS_EOT_PLUS_UPSTREAM_TEXT_POSTPROCESS_AFTER_GENERATION',
        compute_after_text_stop_possible=True, precision='FP32_MATH', tf32=False, mtp=False,
        use_cache=use_cache, temperature=0., top_k=1, max_context=1024)


def metric_oracle(task):
    from lm_eval.api.instance import Instance
    original = task._instances
    checks = []
    try:
        for response, strict, flexible in [('work #### 1,234', 1, 1), ('1234', 0, 1), ('unknown', 0, 0)]:
            doc = dict(question='CPU synthetic metric contract', answer='work #### 1234')
            item = Instance(request_type='generate_until', doc=doc, arguments=('synthetic', {}), idx=0,
                            metadata=('gsm8k', 0, 1))
            item.resps = [response]
            task._instances = [item]
            task.apply_filters()
            observed = {name:task.process_results(doc, [value])['exact_match'] for name,value in item.filtered_resps.items()}
            if observed != {'strict-match':strict, 'flexible-extract':flexible}:
                raise ValueError('공식 strict/flexible 추출·내장 metric oracle 실패')
            checks.append(dict(response=response, expected=dict(strict=strict, flexible=flexible), observed=observed))
    finally:
        task._instances = original
    return checks
