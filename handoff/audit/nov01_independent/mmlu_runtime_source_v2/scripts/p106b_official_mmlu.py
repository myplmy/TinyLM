"""고정 MMLU 공식 task와 로컬 test/dev의 저장 연결. import는 stdlib만 사용한다."""
from collections import Counter
import copy
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sysconfig
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'c30699e8356da336a370243923dbaf21066bb9fe'
REPO = ROOT / 'HF/datasets--cais--mmlu'
CACHE = ROOT / 'data_cache/p106b_mmlu_official_v1_20261101'
OUTPUT = ROOT / 'test_result/evidence/p106b_mmlu_official_v1_20261101'
MODELS = ('native595-q', 'new595-broad-q')
COUNT = 14042
SHOTS = (0, 5)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest().upper()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def row_digest(rows):
    h = hashlib.sha256()
    for row in rows:
        h.update(canonical(row) + bytes([10]))
    return h.hexdigest().upper()


def validate_rows(rows, subjects, split, *, total=None):
    if split not in ('test', 'dev') or not subjects or len(subjects) != len(set(subjects)):
        raise ValueError('고정 test/dev와 중복 없는 subject 필요')
    grouped = {name: [] for name in subjects}
    for row in rows:
        if (not isinstance(row, dict) or row.get('subject') not in grouped
                or type(row.get('answer')) is not int or not 0 <= row['answer'] < 4
                or not isinstance(row.get('question'), str) or not row['question'].strip()
                or not isinstance(row.get('choices'), list) or len(row['choices']) != 4
                or any(not isinstance(choice, str) or not choice.strip() for choice in row['choices'])):
            raise ValueError('원 MMLU subject/질문/4후보/정수label 계약 오류')
        if set(row) != {'question', 'subject', 'choices', 'answer'}:
            raise ValueError('예상과 다른 원문 열')
        grouped[row['subject']].append(row)
    if any(not group or split == 'dev' and len(group) != 5 for group in grouped.values()):
        raise ValueError('subject 누락 또는 dev5 불일치')
    if total is not None and sum(map(len, grouped.values())) != total:
        raise ValueError('공식 전체 분모가 다름')
    return grouped


def official_sources():
    from scripts.p106b_official_lm_adapter import SOURCE, MANIFEST, verify_harness_source
    receipt = verify_harness_source()
    directory = SOURCE / 'lm_eval/tasks/mmlu/default'
    subjects = sorted(path.stem.removeprefix('mmlu_') for path in directory.glob('mmlu_*.yaml'))
    if len(subjects) != 57 or any(not name.replace('_', '').isalpha() for name in subjects):
        raise ValueError('공식57 subject YAML 필요')
    files = ['lm_eval/tasks/mmlu/README.md'] + [
        str(path.relative_to(SOURCE)) for path in directory.iterdir() if path.is_file()]
    wanted, found = set(files), {}
    archive = Path(json.loads(MANIFEST.read_text())['archive_path'])
    with tarfile.open(archive, 'r:gz') as package:
        for member in package:
            parts = PurePosixPath(member.name).parts
            relative = '/'.join(parts[1:])
            if relative not in wanted:
                continue
            if not member.isfile() or member.size > 2_000_000 or relative in found or '..' in parts:
                raise ValueError('공식 archive member 오류')
            with package.extractfile(member) as stream:
                raw = stream.read(2_000_001)
            path = SOURCE / relative
            if path.is_symlink() or path.read_bytes() != raw:
                raise ValueError('고정 archive와 다른 공식task: ' + relative)
            found[relative] = hashlib.sha256(raw).hexdigest().upper()
    if set(found) != wanted:
        raise ValueError('공식 template/group/57task/README 누락')
    return subjects, found, receipt


def original(split):
    if split not in ('test', 'dev') or (REPO / 'refs/main').read_text().strip() != REVISION:
        raise ValueError('고정 revision의 test/dev만 허용')
    path = REPO / 'snapshots' / REVISION / 'all' / (split + '-00000-of-00001.parquet')
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise ValueError('고정 일반 snapshot 파일 필요')
    return path


def prepare_assets():
    from scripts.prepare_p106b_official_eval import configure_hf_cache, write_report, COMMIT
    configure_hf_cache()
    import pyarrow as pa
    import pyarrow.parquet as pq
    subjects, task_files, framework = official_sources()
    if CACHE.exists() or OUTPUT.exists():
        raise FileExistsError('새 MMLU namespace 필요; 원형을 덮지 않는다')
    tables = {split: pq.read_table(original(split)) for split in ('test', 'dev')}
    inventory = {}
    groups = {}
    for split, total in [('test', COUNT), ('dev', 285)]:
        rows = tables[split].to_pylist()
        groups[split] = validate_rows(rows, subjects, split, total=total)
        path = original(split)
        inventory[split] = dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size,
            sha256=digest(path), rows=total, ordered_rows_sha256=row_digest(rows))
    CACHE.mkdir(parents=True)
    OUTPUT.mkdir(parents=True)
    copies = []
    for subject in subjects:
        folder = CACHE / 'subjects' / subject
        folder.mkdir(parents=True)
        for split in ('test', 'dev'):
            rows = groups[split][subject]
            path = folder / (split + '.parquet')
            pq.write_table(pa.Table.from_pylist(rows, schema=tables[split].schema), path)
            restored = pq.read_table(path).to_pylist()
            if restored != rows or path.stat().st_size >= 20_000_000:
                raise ValueError('subject 복사로 원문/순서 변형 또는 파일크기 초과')
            copies.append(dict(subject=subject, split=split, path=str(path.relative_to(ROOT)),
                sha256=digest(path), bytes=path.stat().st_size, rows=len(rows),
                ordered_rows_sha256=row_digest(rows), label_counts=dict(Counter(row['answer'] for row in rows))))
    manifest = dict(schema='P106B_OFFICIAL_MMLU_ASSETS_V1', status='SUBJECT_COPIES_VERIFIED',
        created_at=datetime.now(timezone.utc).isoformat(), framework_commit=COMMIT, framework=framework,
        dataset_revision=REVISION, original_repo_id='cais/mmlu', original=inventory,
        official_files=task_files, subjects=subjects, copies=copies,
        storage_transform='SUBJECT_FILTER_ONLY_KEEP_ORIGINAL_ORDER_AND_ALL_FIELDS',
        benchmark_variant='DEFAULT_MULTIPLE_CHOICE_LETTERS', training=0, model_loads=0,
        downloads=0, installs=0, auxiliary_train_or_validation_read=False)
    write_report(CACHE / 'assets.json', manifest)
    write_report(OUTPUT / 'assets_report.json', manifest)
    return manifest


def verify_assets():
    manifest = json.loads((CACHE / 'assets.json').read_text())
    subjects, files, _ = official_sources()
    if manifest['subjects'] != subjects or manifest['official_files'] != files or manifest['dataset_revision'] != REVISION:
        raise ValueError('고정 task/자료 manifest 다름')
    for spec in [*manifest['original'].values(), *manifest['copies']]:
        path = ROOT / spec['path']
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or digest(path) != spec['sha256']:
            raise ValueError('원본/복사 원형 불일치: ' + spec['path'])
    return manifest


def load_tasks(shots):
    if shots not in SHOTS:
        raise ValueError('사전 지정0/5shot만 허용')
    from scripts.prepare_p106b_official_eval import configure_hf_cache, SOURCE
    from scripts.p106b_official_lm_adapter import prepare_harness
    configure_hf_cache()
    _, framework = prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
    manifest = verify_assets()
    from lm_eval.tasks._yaml_loader import load_yaml
    from lm_eval.api.task import ConfigurableTask
    tasks = {}
    for subject in manifest['subjects']:
        official = SOURCE / 'lm_eval/tasks/mmlu/default' / ('mmlu_' + subject + '.yaml')
        config = load_yaml(str(official), resolve_func=True, recursive=True)
        preserved = {key: copy.deepcopy(config.get(key)) for key in
            ('doc_to_text', 'doc_to_target', 'doc_to_choice', 'metric_list', 'description', 'fewshot_config')}
        rows = [row for row in manifest['copies'] if row['subject'] == subject]
        expected = {row['split']: row['rows'] for row in rows}
        files = {row['split']: str(ROOT / row['path']) for row in rows}
        config.update(dataset_path='parquet', dataset_name=None,
            dataset_kwargs=dict(data_files=files, cache_dir=str(CACHE / 'loader' / subject)),
            training_split=None, validation_split=None, test_split='test', fewshot_split='dev', num_fewshot=shots)
        task = ConfigurableTask(config=config)
        task.set_fewshot_seed(1337)
        if set(task.dataset) != {'test', 'dev'} or len(task.eval_docs) != expected['test'] or len(task.fewshot_docs()) != 5:
            raise ValueError('공식task split/분모/dev5 오류')
        if not preserved_fields_match(preserved, task.config):
            raise ValueError('원문 prompt/선택지/target/metric/fewshot가 변형됨')
        tasks[config['task']] = task
    return tasks, manifest, framework


def preserved_fields_match(preserved, actual):
    """공식 FewshotConfig의 객체화/상속 기본값과 원 YAML의 명시값을 구분한다."""
    for key, value in preserved.items():
        if value is None:
            continue
        observed = getattr(actual, key)
        if key == 'fewshot_config':
            observed = dataclasses.asdict(observed) if dataclasses.is_dataclass(observed) else observed
            if not isinstance(observed, dict) or any(observed.get(k) != v for k, v in value.items()):
                return False
        elif observed != value:
            return False
    return True


def requests(task, doc, shots, index):
    if shots not in SHOTS:
        raise ValueError('고정 shot 필요')
    ctx = task.fewshot_context(doc, num_fewshot=shots, apply_chat_template=False,
        fewshot_as_multiturn=False, system_instruction=None)
    result = task.construct_requests(doc=doc, ctx=ctx,
        metadata=(task.config.task, index, task.config.repeats), apply_chat_template=False)
    if len(result) != 4 or task.doc_to_choice(doc) != ['A', 'B', 'C', 'D']:
        raise ValueError('공식4후보 문자 task 필요')
    if any(row.request_type != 'loglikelihood' or len(row.args) != 2 or not row.args[0]
           or not row.args[1].strip() for row in result):
        raise ValueError('전체 공식 likelihood 요청이 아님')
    return result


def independent_scores(rows, expected):
    """원label/4후보 점수의 별도 정답 집계. 공식 metric 자체를 바꾸지 않는다."""
    if len(rows) != expected or [row['doc_id'] for row in rows] != list(range(expected)):
        raise ValueError('전체 문항 분모/순서 누락; 부분 점수는 금지')
    correct, labels, predictions = 0, Counter(), Counter()
    for row in rows:
        label = row['doc']['answer']
        if type(label) is not int or not 0 <= label < 4:
            raise ValueError('정수4지선다 정답 필요')
        values = row['filtered_resps']
        if len(values) != 4:
            raise ValueError('후보 채점 누락')
        import math
        if any(not isinstance(value, (list, tuple)) or len(value) != 2
               or isinstance(value[0], bool) or not isinstance(value[0], (int, float))
               or not math.isfinite(value[0]) or value[0] > 0 for value in values):
            raise ValueError('전체 유한 sum loglikelihood 필요')
        prediction = max(range(4), key=lambda index: values[index][0])
        value = int(prediction == label)
        if row['acc'] != value:
            raise ValueError('공식 per-item acc와 원형 재집계 불일치')
        correct += value
        labels[label] += 1
        predictions[prediction] += 1
    return dict(rows=expected, correct=correct, accuracy=correct / expected,
        labels=dict(labels), predictions=dict(predictions), uniform_expected_correct=expected / 4,
        posthoc_majority_correct=max(labels.values()),
        majority_scope='POSTHOC_DIAGNOSTIC_NOT_PRIOR_OR_TRAINED_BASELINE')
