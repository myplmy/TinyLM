"""실제 400첫답과 총괄의 400개 판독을 별도 산술·원형 검산한다. 새 판독/모델 실행 없음."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'test_result/evidence/p106b_final200_v2_20261101'
CACHE = ROOT / 'data_cache/p106b_final200_v2_20261101'


def raw_sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            result.update(block)
    return result.hexdigest().upper()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def read(path):
    return json.loads(path.read_text())


def main():
    manifest = read(CACHE / 'manifest.json')
    assert raw_sha(CACHE / 'manifest.json') == 'DD4E185752771528AE009C73D7BD6FEC00CF6C53E3A725CDAEDF091015C475AD'
    assert manifest == read(BASE / 'prepare/report.json')
    cases = read(CACHE / 'final.json')
    dev = read(CACHE / 'dev.json')
    assert len(cases) == 200 and len(dev) == 20
    assert len({row['id'] for row in cases + dev}) == 220
    assert not ({row['prompt'] for row in cases} & {row['prompt'] for row in dev})
    assert object_sha(cases) == manifest['contract']['final_sha256']
    assert object_sha(dev) == manifest['contract']['dev_sha256']
    source = manifest['source']
    assert len(source['files']) == 45 and object_sha(source['files']) == source['sha256']
    for name, expected in source['files'].items():
        assert raw_sha(ROOT / name) == expected, name
    rubric = raw_sha(ROOT / 'handoff/audit/nov01_independent/final200_semantic_rubric_v1.md')
    findings = {}
    category_names = ('context', 'extract', 'format', 'reasoning', 'everyday')
    for model, stage in [('native595-q', 'Stage12bWc_final200_native_v2'),
                         ('new595-broad-q', 'Stage12bWd_final200_broad_v2')]:
        folder = BASE / model
        report = read(folder / 'report.json')
        summary_path = BASE / 'readback' / (model + '_summary.json')
        summary = read(summary_path)
        assert report['final_exit'] == 0 and report['completed_rows'] == 200
        assert report['source'] == source and report['source_unchanged'] and report['parent_unchanged']
        assert not report['final_verification_errors']
        assert report['training'] == report['checkpoint_writes'] == 0
        assert report['model_metadata'] == manifest['models'][model]
        parent = ROOT / report['model_metadata']['checkpoint']
        assert raw_sha(parent) == report['model_metadata']['checkpoint_sha256']
        assert parent.stat().st_size == report['model_metadata']['checkpoint_bytes']
        assert report['actual_model']['core_sha256'] == report['model_metadata']['core_sha256']
        assert report['resource_limit_bytes'] == 8_000_000_000
        assert max(report['peak_allocated_bytes'], report['peak_reserved_bytes']) < 8_000_000_000
        assert report['vram_watch']['maximum_additional_bytes'] < 8_000_000_000
        assert report['vram_watch']['query_errors'] == 0 and report['vram_watch']['thread_stopped']
        assert report['final_cuda_cleanup']['allocated_bytes'] == report['final_cuda_cleanup']['reserved_bytes'] == 0
        answer_manifest = read(folder / 'answers/responses_shards_manifest.json')
        assert answer_manifest == report['answers']
        raw, rows = b'', []
        for shard in answer_manifest['shards']:
            path = folder / 'answers' / shard['path']
            part = path.read_bytes()
            assert len(part) == shard['bytes'] < 20_000_000 and raw_sha(path) == shard['sha256']
            records = [json.loads(line) for line in part.splitlines()]
            assert len(records) == shard['rows']
            raw += part
            rows.extend(records)
        assert len(rows) == answer_manifest['rows'] == 200
        assert len(raw) == answer_manifest['bytes'] and hashlib.sha256(raw).hexdigest().upper() == answer_manifest['concat_sha256']
        assert [row['id'] for row in rows] == [case['id'] for case in cases]
        decisions, packet_refs = {}, []
        for language in ('ko', 'en'):
            for category in category_names:
                path = BASE / 'readback/packets' / f'{model}_{language}_{category}.json'
                packet = read(path)
                assert packet['rubric_sha256'] == rubric and packet['external_human_review'] == 'NOT_RUN'
                assert packet['proof'] == summary['proof'] and len(packet['rows']) == 20
                assert packet['model'] == model and packet['language'] == language and packet['category'] == category
                packet_refs.append(dict(path=str(path.relative_to(ROOT)), sha256=raw_sha(path)))
                for decision in packet['rows']:
                    assert decision['id'] not in decisions
                    assert all(type(decision[key]) is bool for key in ('stable', 'responsive', 'correct', 'usable'))
                    assert decision['usable'] == all(decision[key] for key in ('stable', 'responsive', 'correct'))
                    decisions[decision['id']] = decision
        assert set(decisions) == {row['id'] for row in rows}
        assert packet_refs == summary['packets']
        assert summary['proof'] == dict(input_sha256=object_sha(cases), report_sha256=raw_sha(folder / 'report.json'),
            response_concat_sha256=answer_manifest['concat_sha256'])
        metrics = {}
        for language in ('ko', 'en'):
            group = [row for row in rows if row['language'] == language]
            metrics[language] = dict(total=len(group),
                **{key:sum(decisions[row['id']][key] for row in group) for key in ('stable', 'responsive', 'correct', 'usable')},
                finish_reasons=dict(Counter(row['metadata']['finish_reason'] for row in group)),
                exact_matches=sum(row['reference_match'] is True for row in group),
                categories={cat:dict(total=20, **{key:sum(decisions[row['id']][key] for row in group if row['category'] == cat)
                    for key in ('stable', 'responsive', 'correct', 'usable')}) for cat in category_names})
        assert metrics == summary['metrics']
        for case, row in zip(cases, rows):
            assert all(row[key] == value for key, value in case.items())
            assert decisions[row['id']]['raw_answer_sha256'] == object_sha(row['answer'])
            assert row['metadata']['max_new'] == 96 and row['metadata']['mtp'] is False
            assert row['metadata']['prompt_tokens'] + 96 <= 1024
            if decisions[row['id']]['stable']:
                assert row['metadata']['finish_reason'] in ('EOS', 'STOP_SEQUENCE')
        log = ROOT / ('test_result/101_log_20261101_P106B_' + stage + '.txt')
        text = log.read_text()
        assert '[runlog] 종료코드 0' in text and 'actual_exit=0;' in text
        findings[model] = dict(metrics=metrics, report_sha256=raw_sha(folder / 'report.json'),
            summary_sha256=raw_sha(summary_path), raw_log=str(log.relative_to(ROOT)), raw_log_sha256=raw_sha(log),
            response_seconds=sum(row['seconds'] for row in rows),
            generated_tokens=sum(row['metadata']['generated_tokens'] for row in rows),
            max_reserved_bytes=report['peak_reserved_bytes'],
            shared_sample_increment_bytes=report['vram_watch']['maximum_additional_bytes'])
    child = read(ROOT / 'test_result/evidence/p106b_native595_broad_v1_s1337/train_ternary/report.json')
    parent_core = manifest['models']['native595-q']['core_sha256']
    assert child['initial_core_sha256'] == child['parent_core_sha256'] == parent_core
    assert child['parent_checkpoint_sha256'] == manifest['models']['native595-q']['checkpoint_sha256']
    assert child['status'] == 'TRAIN_COMPLETE' and child['updates'] == 704
    files = [path for path in BASE.rglob('*') if path.is_file()]
    assert all(path.stat().st_size < 20_000_000 for path in files)
    result = dict(schema='P106B_FINAL200_INDEPENDENT_ROOT_CLOSURE_V1',
        checked_at=datetime.now(timezone.utc).isoformat(), actual_rows=400, root_manual_decisions=400,
        source_files_unchanged=45, same_parent_core_verified=True, models=findings,
        artifact_count=len(files), largest_artifact_bytes=max(path.stat().st_size for path in files),
        evaluation_only=True, new_training=0, official_benchmark=False, external_human_review='NOT_RUN',
        semantic_truth_revalidated_by_this_script=False, errors=[])
    output = ROOT / 'handoff/audit/nov01_independent/final200_actual_root_readback_v1.json'
    with output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write(chr(10))
    print(json.dumps(dict(actual_rows=400, decisions=400, source_files=45, errors=[])))


if __name__ == '__main__':
    main()
