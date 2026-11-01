"""총괄이 읽고 결정한 판독만 기록한다. 답을 판독/수정하는 자동 모델이 아니다."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_final_holdout as data
from scripts.p106b_shards import verify
from scripts.prepare_p106b_official_eval import write_report

BASE = ROOT / 'test_result/evidence/p106b_final200_v2_20261101'
CACHE = ROOT / 'data_cache/p106b_final200_v2_20261101'
PROFILE_SHA = 'DD4E185752771528AE009C73D7BD6FEC00CF6C53E3A725CDAEDF091015C475AD'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(model):
    assert model in data.MODELS
    assert sha(CACHE / 'manifest.json') == PROFILE_SHA
    manifest = json.loads((CACHE / 'manifest.json').read_text())
    cases = json.loads((CACHE / 'final.json').read_text())
    assert data.digest(cases) == manifest['contract']['final_sha256']
    path = BASE / model / 'report.json'
    report = json.loads(path.read_text())
    assert report['final_exit'] == 0 and report['completed_rows'] == 200
    assert report['profile_sha256'] == PROFILE_SHA and report['final_input_sha256'] == data.digest(cases)
    assert report['parent_unchanged'] and report['source_unchanged'] and not report['final_verification_errors']
    directory = BASE / model / 'answers'
    assert json.loads((directory / 'responses_shards_manifest.json').read_text()) == report['answers']
    verify(directory, report['answers'])
    rows = [json.loads(line) for shard in report['answers']['shards']
            for line in (directory / shard['path']).read_text().splitlines()]
    assert len(rows) == len(cases) == 200
    for case, row in zip(cases, rows, strict=True):
        assert all(row[key] == value for key, value in case.items())
        assert row['model'] == model and row['semantic_review'] == 'NOT_RUN'
    return rows, dict(report_sha256=sha(path), input_sha256=data.digest(cases),
                      response_concat_sha256=report['answers']['concat_sha256'])


def packet(model, language, category, *, stable, responsive, correct, reason, notes=None,
           reasons=None, all_raw_answers_read=False):
    assert all_raw_answers_read is True, '총괄이 실제 전량을 읽고 명시한 판독만 기록한다'
    assert language in ('ko', 'en') and category in data.CATEGORIES and reason.strip()
    rows, proof = load(model)
    selected = [row for row in rows if row['language'] == language and row['category'] == category]
    assert len(selected) == 20
    chosen = [set(values) for values in (stable, responsive, correct)]
    assert all(all(type(v) is int and 0 <= v < 20 for v in group) for group in chosen)
    notes, reasons = notes or {}, reasons or {}
    assert set(notes) <= set(range(20)) and set(reasons) <= set(range(20))
    result = []
    for index, row in enumerate(selected):
        assert row['id'].endswith(f'_{index:02d}')
        flags = [index in group for group in chosen]
        if flags[0]:
            assert row['answer'].strip() and row['metadata']['finish_reason'] in ('EOS', 'STOP_SEQUENCE')
        result.append(dict(id=row['id'], stable=flags[0], responsive=flags[1], correct=flags[2],
                           usable=all(flags), raw_answer_sha256=data.digest(row['answer']),
                           reason=reasons.get(index, reason), note=notes.get(index, '')))
    folder = BASE / 'readback/packets'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{model}_{language}_{category}.json'
    report = dict(schema='P106B_FINAL200_ROOT_THREE_AXIS_PACKET_V1', model=model, language=language,
                  category=category, review_kind='GPT_ROOT_READ_ALL_RAW_ANSWERS', external_human_review='NOT_RUN',
                  reviewed_at=datetime.now(timezone.utc).isoformat(),
                  rubric_sha256=sha(ROOT / 'handoff/audit/nov01_independent/final200_semantic_rubric_v1.md'),
                  proof=proof, rows=result)
    write_report(path, report)
    print(json.dumps(dict(model=model, language=language, category=category,
                          counts={key:sum(row[key] for row in result) for key in ('stable', 'responsive', 'correct', 'usable')})))
    return report


def aggregate(model):
    rows, proof = load(model)
    decisions, packets = {}, []
    for language in ('ko', 'en'):
        for category in data.CATEGORIES:
            path = BASE / 'readback/packets' / f'{model}_{language}_{category}.json'
            value = json.loads(path.read_text())
            assert value['model'] == model and value['language'] == language and value['category'] == category
            assert value['proof'] == proof and len(value['rows']) == 20
            assert value['rubric_sha256'] == sha(ROOT / 'handoff/audit/nov01_independent/final200_semantic_rubric_v1.md')
            packets.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path)))
            for case in value['rows']:
                assert case['id'] not in decisions
                assert all(type(case[k]) is bool for k in ('stable', 'responsive', 'correct', 'usable'))
                assert case['usable'] == (case['stable'] and case['responsive'] and case['correct'])
                decisions[case['id']] = case
    assert set(decisions) == {row['id'] for row in rows} and len(decisions) == 200
    for row in rows:
        assert decisions[row['id']]['raw_answer_sha256'] == data.digest(row['answer'])
    keys = ('stable', 'responsive', 'correct', 'usable')
    metrics = {}
    for language in ('ko', 'en'):
        group = [row for row in rows if row['language'] == language]
        metrics[language] = dict(total=100, **{key:sum(decisions[row['id']][key] for row in group) for key in keys},
            finish_reasons=dict(Counter(row['metadata']['finish_reason'] for row in group)),
            exact_matches=sum(row['reference_match'] is True for row in group),
            categories={cat:dict(total=20, **{key:sum(decisions[row['id']][key] for row in group if row['category'] == cat)
                                             for key in keys}) for cat in data.CATEGORIES})
        text = [f'# {model} / {language} — FINAL100 실제 질문과 첫 답',
                '총괄 GPT의 세축 판독이며 외부 인간검증·공식 benchmark가 아니다. 원답은 그대로 보존했다.']
        for row in group:
            decision = decisions[row['id']]
            text += ['', '## ' + row['id'], '질문: ' + row['prompt'], '',
                     '답변:', row['answer'], '', '참고 정답/요청: ' + json.dumps(row['reference'], ensure_ascii=False),
                     '내용 기준: ' + row['rubric'], '종료: ' + row['metadata']['finish_reason'],
                     '판독: ' + ', '.join(key + '=' + str(decision[key]) for key in keys),
                     '근거: ' + decision['reason'], '메모: ' + decision['note']]
        target = BASE / 'readback' / f'{model}_{language}_questions_answers.md'
        raw = (chr(10).join(text) + chr(10)).encode()
        assert len(raw) < 20_000_000
        with target.open('xb') as stream:
            stream.write(raw)
    result = dict(schema='P106B_FINAL200_ROOT_THREE_AXIS_AGGREGATE_V1', model=model,
                  status='ALL200_ROOT_REVIEWED', proof=proof, packets=packets, metrics=metrics,
                  rubric='PREDECLARED_SEPARATE_STABILITY_RESPONSIVENESS_CONTENT', external_human_review='NOT_RUN',
                  formal_benchmark=False, new_training=0, train_or_teacher_reuse='PROHIBITED')
    write_report(BASE / 'readback' / f'{model}_summary.json', result)
    print(json.dumps(dict(model=model, metrics=metrics)))
    return result
