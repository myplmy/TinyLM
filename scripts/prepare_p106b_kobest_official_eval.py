#!/usr/bin/env python3
"""로컬 KoBEST 공식 test만 준비한다. 설치/네트워크/HF import/모델/GPU는 없다."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_official_lm_adapter import SOURCE, MANIFEST, COMMIT, verify_harness_source, sha256_file
from scripts.prepare_p106b_official_eval import write_report

REVISION = 'a5ea15e3ac77ed694b79f6204eb31889a2ba989f'
REPO = ROOT / 'HF/datasets--skt--kobest_v1'
ASSETS = ROOT / 'data_cache/p106b_kobest_official_assets_v2_20261101'
EVIDENCE = ROOT / 'test_result/evidence/p106b_kobest_official_v2_20261101'
EVAL_PYTHON = ROOT / 'data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python'
SPECS = {
    'boolq': (1404, 2, ('paragraph', 'question')),
    'copa': (1000, 2, ('premise', 'question', 'alternative_1', 'alternative_2')),
    'hellaswag': (500, 4, ('context', 'ending_1', 'ending_2', 'ending_3', 'ending_4')),
    'sentineg': (397, 2, ('sentence',)),
    'wic': (1260, 2, ('word', 'context_1', 'context_2')),
}


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('중복 JSON key: ' + key)
        value[key] = item
    return value


def local_test(repo, revision, family):
    if family not in SPECS or revision != REVISION:
        raise ValueError('고정 test 과제/revision만 허용')
    if repo.is_symlink() or (repo / 'refs/main').read_text().strip() != revision:
        raise ValueError('원 데이터 repo/revision이 다름')
    path = repo / 'snapshots' / revision / family / 'test.jsonl'
    resolved = path.resolve(strict=True)
    blobs = (repo / 'blobs').resolve(strict=True)
    if path.is_symlink():
        if not resolved.is_relative_to(blobs) or resolved.parent != blobs or (repo / 'blobs').is_symlink():
            raise ValueError('고정 HF blob 외부 링크는 거부')
    elif resolved != path.absolute() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('고정 snapshot 일반 파일의 부모 링크는 거부')
    if not resolved.is_file():
        raise ValueError('고정 test 일반 파일이 아님')
    if resolved.is_symlink() or path.stat().st_size >= 20_000_000:
        raise ValueError('원 test 파일 크기/링크 계약')
    return path, resolved


def scan_test(path, family, expected_count=None):
    count, choices, fields = SPECS[family]
    if expected_count is not None:
        count = expected_count
    labels, unique, ordered = Counter(), set(), hashlib.sha256()
    total = 0
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            doc = json.loads(line, object_pairs_hook=unique_object)
            if type(doc.get('label')) is not int or not 0 <= doc['label'] < choices:
                raise ValueError('공식 label 형식/범위 오류')
            if any(not isinstance(doc.get(key), str) or not doc[key].strip() for key in fields):
                raise ValueError('공식 문항 필수 문자열 누락/비어 있음')
            if family == 'copa' and doc['question'].strip() not in ('원인', '결과'):
                raise ValueError('공식 COPA 연결어가 아님')
            raw = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            ordered.update(raw + bytes([10]))
            unique.add(hashlib.sha256(raw).digest())
            labels[doc['label']] += 1
            total += 1
    if total != count:
        raise ValueError(f'공식 test 분모 불일치: {family} {total} != {count}')
    return dict(task='kobest_' + family, split='test', rows=total, label_counts=dict(labels),
                duplicate_rows_preserved=total - len(unique), ordered_json_sha256=ordered.hexdigest().upper())


def task_sources(source, archive):
    wanted = {f'lm_eval/tasks/kobest/{name}' for name in
              ['_kobest.yaml', 'utils.py'] + ['kobest_' + family + '.yaml' for family in SPECS]}
    found = {}
    with tarfile.open(archive, 'r:gz') as package:
        for member in package:
            parts = PurePosixPath(member.name).parts
            relative = '/'.join(parts[1:])
            if relative not in wanted:
                continue
            if relative in found or not member.isfile() or member.size > 2_000_000 or '..' in parts:
                raise ValueError('공식 task archive 계약 오류')
            with package.extractfile(member) as stream:
                raw = stream.read(2_000_001)
            file = source / relative
            if file.is_symlink() or not file.is_file() or file.read_bytes() != raw:
                raise ValueError('공식 task source가 고정 archive와 다름: ' + relative)
            found[relative] = hashlib.sha256(raw).hexdigest().upper()
    if set(found) != wanted:
        raise ValueError('다섯 공식 YAML/group/utils가 전부 없음')
    return found


def dependencies(python=EVAL_PYTHON):
    # 실행 파일을 고정하며 HF/모델 패키지는 import하지 않는다.
    program = '''import importlib.metadata as m,json,sys
names=("lm_eval","datasets","pyarrow","numpy","evaluate","scikit-learn","scipy","joblib","threadpoolctl")
out={}
for name in names:
 try:
  d=m.distribution(name);out[name]={"version":d.version,"root":str(d.locate_file("")),"requires":d.requires or []}
 except m.PackageNotFoundError:out[name]=None
print(json.dumps({"python":sys.executable,"python_version":sys.version,"packages":out}))
'''
    completed = subprocess.run([str(python), '-I', '-B', '-c', program], check=True,
                               capture_output=True, text=True, timeout=15)
    value = json.loads(completed.stdout)
    value['missing'] = [key for key, package in value['packages'].items() if package is None]
    value['installation_performed'] = False
    return value


def prepare(execute=False):
    provenance = verify_harness_source()
    original = json.loads(MANIFEST.read_text())
    functions = task_sources(SOURCE, Path(original['archive_path']))
    inventory = []
    for family in SPECS:
        path, blob = local_test(REPO, REVISION, family)
        row = scan_test(blob, family)
        row.update(snapshot_path=str(path.relative_to(ROOT)), blob_path=str(blob.relative_to(ROOT)),
                   bytes=blob.stat().st_size, sha256=sha256_file(blob), family=family)
        inventory.append(row)
    report = dict(schema='P106B_KOBEST5_OFFICIAL_ASSET_PREP_V1', status='READ_ONLY_INVENTORY_COMPLETE',
                  created_at=datetime.now(timezone.utc).isoformat(), source_commit=COMMIT,
                  dataset_revision=REVISION, original_repo_id='skt/kobest_v1', provenance=provenance,
                  official_task_files=functions, tests=inventory, total_test_rows=sum(r['rows'] for r in inventory),
                  dependencies=dependencies(), train_or_validation_read=False, downloads=0, installs=0,
                  model_loads=0, gpu_runs=0, official_task_init='NOT_RUN', model_scores='NOT_RUN',
                  group_aggregation='OFFICIAL_SIZE_WEIGHTED_ACC_ACC_NORM_F1_NOT_CORE6_UNWEIGHTED',
                  metric_dependencies='OFFICIAL_MACRO_F1_REQUIRES_SKLEARN; YAML_HF_EVALUATE_INIT_PATH_UNVERIFIED')
    if not execute:
        return report
    deadline = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
    if (deadline - datetime.now(timezone.utc)).total_seconds() < 150:
        raise RuntimeError('사용자104의 마감 전 CPU 실행/정리 여유가 부족함')
    if ASSETS.exists() or EVIDENCE.exists():
        raise FileExistsError('원형 또는 이전 실행을 덮어쓰지 않음')
    ASSETS.mkdir(parents=True)
    EVIDENCE.mkdir(parents=True)
    for row in inventory:
        path = ASSETS / (row['family'] + '_test.jsonl')
        shutil.copyfile(ROOT / row['blob_path'], path)
        if sha256_file(path) != row['sha256'] or sha256_file(ROOT / row['blob_path']) != row['sha256']:
            raise ValueError('복사본/원 test 사후 SHA 불일치')
        row['local_path'] = str(path.relative_to(ROOT))
        row['storage_overrides'] = dict(dataset_path='json', dataset_name=None,
            dataset_kwargs=dict(data_files={'test': str(path)}), test_split='test',
            training_split=None, validation_split=None, num_fewshot=0, fewshot_split=None,
            fewshot_config=dict(samples=[]))
        row['semantic_fields_unchanged'] = ['doc_to_text', 'doc_to_target', 'doc_to_choice',
                                             'process_docs', 'metric_list', 'target_delimiter']
    report['status'] = 'TEST_ASSETS_PREPARED_OFFICIAL_TASK_AND_MODEL_NOT_RUN'
    report['metrics_dependency_status'] = 'MISSING' if report['dependencies']['missing'] else 'PRESENT_NOT_EXECUTED'
    write_report(ASSETS / 'manifest.json', report)
    write_report(EVIDENCE / 'asset_report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.execute == args.check_only:
        parser.error('실행/읽기 전용 모드를 하나만 지정')
    value = prepare(args.execute)
    print(json.dumps(dict(status=value['status'], total_test_rows=value['total_test_rows'],
                          missing_packages=value['dependencies']['missing'], model_scores='NOT_RUN'), ensure_ascii=False))


if __name__ == '__main__':
    main()
