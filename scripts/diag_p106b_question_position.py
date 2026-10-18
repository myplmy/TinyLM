#!/usr/bin/env python3
"""같은 지문에서 질문 위치와 반복만 바꾸는 독립 무학습 진단.

공개 execute는 언제나 회귀/선결/실행의 공용 3단계를 거친다. 실제
prepare/evaluate/readback은 총괄이 실행하며, check-only/help는 자료와
토크나이저/모델을 읽지 않는다. 기존 보고·소스·체크포인트는 불변이다.
"""
from __future__ import annotations

from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
import random
import re
import subprocess
import time
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_question_position_v1_s1337'
VERSION = 'P106B_QUESTION_POSITION_V1'
LOCAL = ROOT / 'test_result/evidence/local' / TAG
CORPUS = LOCAL / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
AUTHORITY_END = END
CONTEXT, MAX_NEW = 1024, 128
ENDPOINTS = ('cpt_unique32k', 'unique32k')
CONDITIONS = ('CQ', 'QC', 'QCQ', 'CQQ')
MODES = ('prepare', 'preflight', 'evaluate', 'readback')
SOURCE_FIELDS = ('language', 'root', 'article_id', 'source_sha256', 'context', 'question', 'aliases')
LANGUAGES = ('ko', 'en')
EXPECTED_SOURCE_ROOTS, PER_QUARTILE = 512, 16
EXPECTED_ROOTS, EXPECTED_RESPONSES = 128, 512
ACTIVE_LIMIT, RECORD_RESERVE = 3600, 600
SLOTS = {'prepare': 300, 'evaluate_cpt_unique32k': 1200,
         'evaluate_unique32k': 1200, 'readback': 300}
OWN_CODE = ('scripts/diag_p106b_question_position.py', 'scripts/test_p106b_question_position.py')
SOURCE_REPORT = 'test_result/evidence/p106b_cpt_unique32k_v1_s1337/evaluate/cpt_unique32k_report.json'
SOURCE_REPORT_SHA = 'A32AD9FB84BC62D7E19DEDC3E441D5C40DAE1984039805E40E3509A42549F996'
SOURCE_READBACK = 'test_result/evidence/p106b_cpt_unique32k_v1_s1337/evaluate/paired_readback.json'
SOURCE_READBACK_SHA = '54B1D9813CBB4FBDB3366B3D423CC0D1C95FA0F70E4CF9DE625F748D0F7E65D4'
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
TOK_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
SOURCE_SHA = {'ko': '40D5115879A701751781DF721D901ABFA736D8DB5F89000F2619433F39BF2DD2',
              'en': '68DCFBB971BD3E96D5B46C7177B16C1A4E7D4BDEF19FB204502738552DEDE002'}
SOURCE_SCHEMAS = {'cpt_unique32k': 'P106B_CPT_UNIQUE32K_EVAL_V1',
                  'unique32k': 'P106B_NIGHT_DIVERSITY_SCOPE_EVALUATION_V2'}
SOURCE_TAGS = {'cpt_unique32k': 'p106b_cpt_unique32k_v1_s1337',
               'unique32k': 'p106b_night_diversity_scope_v2_s1337'}
PROTOCOL = dict(precision='FP32_MATH', temperature=0., top_k=1,
                use_cache=True, mtp=False, max_new=128, candidate_answers_supplied=False)
LANES = frozenset(('natural', 'cube', 'role', 'recovery', 'code', 'public', 'native32', 'native256'))


class Pending(RuntimeError):
    """미실행/부족은 0점이나 도구 성공으로 바꾸지 않는다."""


def sha(value):
    """기존 생성 영수증과 같은 JSON wire SHA. 원문 byte SHA와 구별한다."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()


def hex_sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9A-F]{64}', value) is not None


def safe(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('해결되지 않은 경로')
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError('저장소 밖의 연구 경로') from exc
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('심볼릭 링크인 연구 경로')
        if item == ROOT:
            break
    return path


def digest(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('필요 파일 미실행/누락: ' + str(path.relative_to(ROOT)))
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest().upper()


def required(path):
    path = safe(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise Pending('완료되지 않은 선결 파일: ' + str(path.relative_to(ROOT)))
    if path.stat().st_size >= 20_000_000:
        raise ValueError('소형 JSON 상한 초과')
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path = safe(path)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) >= 20_000_000:
        raise ValueError('20MB 미만 소형 증거 필요')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def read_shards(directory, manifest, stem):
    directory = safe(directory)
    if (manifest.get('schema') != 'P106B_WRITE_ONCE_SHARDS_V1'
            or type(manifest.get('rows')) is not int or manifest['rows'] < 1
            or not manifest.get('shards')):
        raise Pending('비어 있거나 미완료인 원형 shard')
    for index, spec in enumerate(manifest['shards']):
        if (spec.get('path') != stem + '_%06d.jsonl' % index
                or type(spec.get('bytes')) is not int or not 0 < spec['bytes'] < 20_000_000):
            raise ValueError('원형 shard 이름/길이 위반')
        path = safe(directory / spec['path'])
        if not path.is_file():
            raise Pending('이전 원형 shard 미실행/누락')
    verify(directory, manifest)
    rows = []
    for spec in manifest['shards']:
        for line in (directory / spec['path']).read_text(encoding='utf-8').splitlines():
            rows.append(json.loads(line))
    return rows


def dependencies():
    """실물 동작에서만 기존 helper를 import한다. import 자체로 모델을 만들지 않는다."""
    from scripts import diag_p106b_cpt_unique32k_eval as cpt
    from scripts import diag_p106b_night_diversity_scope_eval_v2 as base
    return cpt, base


def score(answer, aliases, language):
    from scripts.p106b_night_learning import qa_scores
    return qa_scores(answer, aliases, language)


def prompt(messages):
    from tinylm.chat.serialize import serialize
    return serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)


def old_user(context, question, language, view):
    from scripts.p106b_night_qa_data import _user
    return _user(context, question, language, view)


def check_projection(row):
    if not isinstance(row, dict) or set(row) != set(SOURCE_FIELDS):
        raise ValueError('선정 입력은 source/question/context/alias/root 전용 schema')
    if row['language'] not in LANGUAGES or row['source_sha256'] != SOURCE_SHA[row['language']]:
        raise ValueError('고정 한영 원천 지문 필요')
    if any(not hex_sha(row[k]) for k in ('root', 'article_id', 'source_sha256')):
        raise ValueError('정확한 원천/root/기사 지문 필요')
    if any(not isinstance(row[k], str) or not row[k].strip() for k in ('context', 'question')):
        raise ValueError('빈 지문/질문은 허용하지 않음')
    aliases = row['aliases']
    if (not isinstance(aliases, list) or not aliases
            or any(not isinstance(a, str) or not a.strip() or a not in row['context'] for a in aliases)):
        raise ValueError('원문에 존재하는 원형 alias 필요')


def project_natural(events, expected_roots=EXPECTED_SOURCE_ROOTS):
    """이전 answer/scores/generation에 접근하지 않는 선정 입력 분리 경계."""
    grouped = defaultdict(dict)
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('원형 QA 행 필요')
        row = {key: event[key] for key in SOURCE_FIELDS}
        check_projection(row)
        view = event.get('view')
        if type(view) is not int or view not in (0, 1, 2):
            raise ValueError('원형 세 view만 허용')
        key = (row['language'], row['root'])
        if view in grouped[key]:
            raise ValueError('원형 root/view 중복')
        grouped[key][view] = row
    if not grouped or len(grouped) != expected_roots:
        raise Pending('원형 root 부족: 관측%d/필수%d' % (len(grouped), expected_roots))
    sources = []
    for key, views in sorted(grouped.items()):
        if set(views) != {0, 1, 2}:
            raise Pending('원형 3view 미완료: ' + str(key))
        if views[0] != views[1] or views[0] != views[2]:
            raise ValueError('원형 view 간 질문/사실/alias/계보 변조')
        sources.append(views[0])
    expected_each = expected_roots // 2
    if Counter(s['language'] for s in sources) != {'ko': expected_each, 'en': expected_each}:
        raise ValueError('원형 한영 root 분모 위반')
    return sources


def source_key(row):
    check_projection(row)
    return sha([TAG, 'SOURCE_ROOT', row['source_sha256'], row['language'], row['article_id'], row['root']])


def render_layout(row, condition):
    check_projection(row)
    if condition not in CONDITIONS:
        raise ValueError('고정 네 조건 필요')
    if row['language'] == 'ko':
        instruction, c_label, q_label = '자료를 읽고 질문의 답만 짧게 쓰세요.', '자료:\n', '질문:\n'
    else:
        instruction = 'Read the reference and give only the short answer.'
        c_label, q_label = 'Reference:\n', 'Question:\n'
    pieces, spans = [instruction], []
    for item in condition:
        label, value = (c_label, row['context']) if item == 'C' else (q_label, row['question'])
        start = sum(len(p) for p in pieces) + 1 + len(label)
        pieces.append('\n' + label + value)
        spans.append(dict(kind=item, start=start, end=start + len(value)))
    body = ''.join(pieces)
    return body, spans


def encode_case(row, condition, tokenizer):
    """실제 전체 prompt의 BPE 길이/offset. 답/후보를 입력에 붙이지 않는다."""
    body, spans = render_layout(row, condition)
    messages = [dict(role='user', content=body)]
    serialized = prompt(messages)
    head = '<|im_start|>user\n'
    if serialized != head + body + '<|im_end|>\n<|im_start|>assistant\n':
        raise ValueError('동결 ChatML generation prefix 변경')
    if getattr(tokenizer, 'truncation', None) is not None or getattr(tokenizer, 'padding', None) is not None:
        raise ValueError('토크나이저의 암묵적 자르기/패딩 금지')
    encoding = tokenizer.encode(serialized)
    ids, offsets = list(encoding.ids), list(encoding.offsets)
    eot = tokenizer.token_to_id('<|im_end|>')
    if (type(eot) is not int or tokenizer.encode('<|im_end|>').ids != [eot]
            or not ids or len(ids) != len(offsets)
            or any(type(t) is not int for t in ids)
            or any(not 0 <= a <= b <= len(serialized) for a, b in offsets)
            or max(b for a, b in offsets) != len(serialized)):
        raise ValueError('전체 prompt/EOT token coverage 위반')
    for name in ('<unk>', '<|unk|>'):
        unknown = tokenizer.token_to_id(name)
        if unknown is not None and unknown in ids:
            raise ValueError('선정 prompt에 unknown token 존재')
    ranges = []
    for span in spans:
        a, b = len(head) + span['start'], len(head) + span['end']
        covered = [i for i, (start, end) in enumerate(offsets) if start < b and end > a]
        if not covered:
            raise ValueError('전체 지문/질문 span의 token coverage 누락')
        ranges.append(dict(kind=span['kind'], char_start=a, char_end=b,
                           token_start=min(covered), token_end=max(covered) + 1,
                           tokens_after_end=len(ids) - max(covered) - 1))
    result = dict(prompt_sha256=sha(serialized), prompt_ids_sha256=sha(ids),
        prompt_tokens=len(ids), context_tokens=len(tokenizer.encode(row['context']).ids),
        question_tokens=len(tokenizer.encode(row['question']).ids),
        user_chars=len(body), question_occurrences=condition.count('Q'),
        full_context_occurrences=1, offsets=ranges, stop_token_sequences=[[eot]],
        complete_unclipped_context=True, gold_in_generation_prefix=False,
        max_new=MAX_NEW, context_limit=CONTEXT)
    owned = {k: list(v) if k == 'aliases' else v for k, v in row.items()}
    return dict(schema=VERSION, tag=TAG, case_id=sha([TAG, row['language'], row['root'], condition]),
                **owned, condition=condition, source_projection_sha256=sha(row),
                messages=messages, encoding=result)


def select_cases(sources, tokenizer, per_quartile=PER_QUARTILE):
    """적합 집합 -> 순위 사분위 -> source hash. 성적에 따른 교체는 없다."""
    if type(per_quartile) is not int or per_quartile < 1:
        raise ValueError('양의 사분위별 모집량 필요')
    seen, candidates, excluded = set(), defaultdict(list), []
    for row in sources:
        check_projection(row)
        key = (row['language'], row['root'])
        if key in seen:
            raise ValueError('중복 source root')
        seen.add(key)
        cases = [encode_case(row, condition, tokenizer) for condition in CONDITIONS]
        bad = {c['condition']: c['encoding']['prompt_tokens'] for c in cases
               if c['encoding']['prompt_tokens'] + MAX_NEW > CONTEXT}
        if bad:
            excluded.append(dict(language=row['language'], root=row['root'],
                                 reason='ANY_CONDITION_FULL_CONTEXT_BUDGET', prompt_tokens=bad))
            continue
        candidates[row['language']].append((row, cases))
    selected, strata, shortages = [], {}, {}
    for language in LANGUAGES:
        ordered = sorted(candidates[language], key=lambda pair: (pair[1][0]['encoding']['context_tokens'], source_key(pair[0])))
        buckets = [[] for _ in range(4)]
        for rank, pair in enumerate(ordered):
            buckets[min(3, 4 * rank // len(ordered))].append(pair)
        counts = [len(bucket) for bucket in buckets]
        if any(n < per_quartile for n in counts):
            shortages[language] = dict(eligible=len(ordered), quartile_supply=counts,
                required_per_quartile=per_quartile,
                missing_per_quartile=[max(0, per_quartile - n) for n in counts])
        strata[language] = []
        for quartile, bucket in enumerate(buckets):
            chosen = sorted(bucket, key=lambda pair: source_key(pair[0]))[:per_quartile]
            lengths = [p[1][0]['encoding']['context_tokens'] for p in bucket]
            strata[language].append(dict(quartile=quartile, eligible_roots=len(bucket),
                context_tokens_min=min(lengths) if lengths else None,
                context_tokens_max=max(lengths) if lengths else None,
                chosen_roots=[p[0]['root'] for p in chosen]))
            for row, cases in chosen:
                for case in cases:
                    selected.append(dict(case, length_quartile=quartile))
    if shortages:
        raise Pending('사분위 공급 부족; 축소/대체 금지: ' + json.dumps(shortages, ensure_ascii=False, sort_keys=True))
    proof = dict(selection_uses_previous_answers=False, selection_uses_scores_or_generation=False,
        source_projection_sha256=sha(sorted(sources, key=lambda r: (r['language'], r['root']))),
        source_roots=len(sources), eligible_roots={k: len(candidates[k]) for k in LANGUAGES},
        excluded=excluded, by_language_quartile=strata,
        quartile_rule='적합한 언어별 root를 (context_tokens, source_key)로 정렬; q=min(3,4*rank//N), 동률 경계는 source_key로 분할',
        hash_rule="SHA256(JSON([TAG,'SOURCE_ROOT',source_sha256,language,article_id,root])) 대문자 오름차순",
        ordered_selection_sha256=sha([[c['language'], c['root'], c['length_quartile'], c['condition']] for c in selected]),
        cases_sha256=sha(selected), roots=len(selected) // 4, cases=len(selected),
        relative_length_strata_not_randomized_length=True,
        no_source_crop=True, no_candidate_hint=True)
    return selected, proof


def validate_cases(cases):
    """한영64/사분위16/네 조건을 고정한다. 부분 분모를 성공으로 세지 않는다."""
    if not cases or len(cases) != EXPECTED_RESPONSES:
        raise Pending('동결 입력 부족: 관측%d/필수512' % len(cases))
    roots, seen = defaultdict(dict), set()
    for case in cases:
        row = {k: case[k] for k in SOURCE_FIELDS}; check_projection(row)
        condition = case.get('condition'); body, spans = render_layout(row, condition)
        key = (row['language'], row['root']); identity = sha([TAG, *key, condition])
        encoding = case.get('encoding', {})
        if (case.get('schema') != VERSION or case.get('tag') != TAG
                or case.get('case_id') != identity or identity in seen
                or case.get('source_projection_sha256') != sha(row)
                or case.get('messages') != [dict(role='user', content=body)]
                or encoding.get('prompt_sha256') != sha(prompt(case['messages']))
                or not hex_sha(encoding.get('prompt_ids_sha256'))
                or type(case.get('length_quartile')) is not int or case['length_quartile'] not in range(4)):
            raise ValueError('동결 입력의 유일성/source/prefix/사분위 변조')
        for field in ('prompt_tokens', 'context_tokens', 'question_tokens'):
            if type(encoding.get(field)) is not int or encoding[field] < 1:
                raise ValueError('명시적인 양의 전체 BPE 길이 필요')
        if (encoding['prompt_tokens'] + MAX_NEW > CONTEXT
                or encoding.get('user_chars') != len(body)
                or encoding.get('question_occurrences') != condition.count('Q')
                or encoding.get('full_context_occurrences') != 1
                or encoding.get('complete_unclipped_context') is not True
                or encoding.get('gold_in_generation_prefix') is not False
                or encoding.get('max_new') != MAX_NEW or encoding.get('context_limit') != CONTEXT
                or not isinstance(encoding.get('stop_token_sequences'), list)
                or len(encoding['stop_token_sequences']) != 1
                or len(encoding['stop_token_sequences'][0]) != 1
                or type(encoding['stop_token_sequences'][0][0]) is not int):
            raise ValueError('전체 지문/출력128/EOT/답 분리 계약 변경')
        offsets = encoding.get('offsets', [])
        if len(offsets) != len(spans) or [s.get('kind') for s in offsets] != list(condition):
            raise ValueError('전체 질문/지문 offset 누락')
        head = len('<|im_start|>user\n')
        for span, offset in zip(spans, offsets):
            if (offset.get('char_start') != head + span['start'] or offset.get('char_end') != head + span['end']
                    or type(offset.get('token_start')) is not int or type(offset.get('token_end')) is not int
                    or not 0 <= offset['token_start'] < offset['token_end'] <= encoding['prompt_tokens']
                    or offset.get('tokens_after_end') != encoding['prompt_tokens'] - offset['token_end']):
                raise ValueError('질문/지문 token 거리 계약 변경')
        roots[key][condition] = case; seen.add(identity)
    if len(roots) != EXPECTED_ROOTS or any(set(v) != set(CONDITIONS) for v in roots.values()):
        raise ValueError('각 root의 네 조건 모두 필요')
    for values in roots.values():
        first = values['CQ']
        if any(any(c[k] != first[k] for k in (*SOURCE_FIELDS, 'length_quartile')) for c in values.values()):
            raise ValueError('한 root 조건 간 원문/질문/alias/사분위 변경')
    for language in LANGUAGES:
        for quartile in range(4):
            if sum(key[0] == language and value['CQ']['length_quartile'] == quartile for key, value in roots.items()) != PER_QUARTILE:
                raise ValueError('언어별 사분위16root 고정 분모 변경')
    ordered = sorted(cases, key=lambda c: (LANGUAGES.index(c['language']), c['length_quartile'],
                     source_key({k: c[k] for k in SOURCE_FIELDS}), CONDITIONS.index(c['condition'])))
    if cases != ordered:
        raise ValueError('선정 해시/조건의 동결 출력 순서 변경')
    return roots


def bind_endpoint(report, summary, endpoint, expected_path):
    """고정 paired readback과 final endpoint를 연결하는 순수 계약 검사."""
    if (endpoint not in ENDPOINTS or report.get('endpoint') != endpoint
            or report.get('status') != 'ACTUAL_EVALUATION_COMPLETE'
            or report.get('body_unchanged') is not True
            or report.get('updates') != 0 or report.get('checkpoints_written') != 0
            or report.get('checkpoint') != expected_path
            or report.get('checkpoint_sha256') != summary.get('checkpoint_sha256')
            or report.get('initial_core_sha256') != summary.get('initial_core_sha256')
            or not hex_sha(report.get('checkpoint_sha256'))
            or not hex_sha(report.get('initial_core_sha256'))
            or report.get('outputs') != summary.get('outputs')
            or set(report.get('outputs', {})) != LANES
            or set(report.get('receipt_sha256', {})) != LANES):
        raise ValueError('완료 final endpoint/원형/체크포인트/본체 계약 위반')
    if report.get('schema') != SOURCE_SCHEMAS[endpoint] or report.get('tag') != SOURCE_TAGS[endpoint]:
        raise ValueError('고정 두 final의 schema/tag 변경')
    if report.get('selection') != 'final640 primary; separate DEV CE minimum, never TEST-selected':
        raise ValueError('final640 primary 외 새 DEV/TEST 선택 금지')
    required_protocol = dict(precision='FP32_MATH', temperature=0., top_k=1,
                             use_cache=True, mtp=False, max_new_natural=128)
    if any(report.get(k) != v for k, v in required_protocol.items()):
        raise ValueError('원형과 동일한 greedy FP32/KV/EOT 경로 필요')
    if not isinstance(report.get('code_sha256'), dict) or not report['code_sha256']:
        raise ValueError('원형 코드 지문 필요')
    return dict(checkpoint=expected_path, checkpoint_sha256=report['checkpoint_sha256'],
                initial_core_sha256=report['initial_core_sha256'])


def read_source():
    """root의 명시 동작만 호출한다. 회귀/check-only에서는 호출하지 않는다."""
    from tinylm.chat.canonical import normalize
    cpt, base = dependencies()
    files = {}
    def bound(path, identity=None):
        path = safe(path); actual = digest(path)
        if identity is not None and actual != identity:
            raise ValueError('고정 원천 지문 변경: ' + str(path.relative_to(ROOT)))
        files[str(path.relative_to(ROOT))] = actual
        return actual
    bound(ROOT / SOURCE_REPORT, SOURCE_REPORT_SHA)
    bound(ROOT / SOURCE_READBACK, SOURCE_READBACK_SHA)
    paired = required(ROOT / SOURCE_READBACK)
    if (paired.get('status') != 'RAW_RECOUNTED' or paired.get('errors') != 0
            or paired.get('tag') != 'p106b_cpt_unique32k_v1_s1337'
            or not isinstance(paired.get('endpoints'), dict)):
        raise Pending('완료된 네 조합 원형 판독이 선결')
    rows, projections, identities = {}, {}, {}
    for endpoint, provider in ((ENDPOINTS[0], cpt), (ENDPOINTS[1], base)):
        summary = paired['endpoints'].get(endpoint)
        if not isinstance(summary, dict) or not hex_sha(summary.get('report_sha256')):
            raise Pending('final endpoint의 완료 원형 판독 누락')
        path = provider.EVIDENCE / (endpoint + '_report.json')
        bound(path, summary['report_sha256']); report = required(path)
        if endpoint == 'cpt_unique32k' and summary['report_sha256'] != SOURCE_REPORT_SHA:
            raise ValueError('다른 CPT32 endpoint 보고')
        cp = provider.training.checkpoint(False)
        identity = bind_endpoint(report, summary, endpoint, str(cp.relative_to(ROOT)))
        bound(cp, identity['checkpoint_sha256'])
        if bound(provider.FROZEN / 'report.json') != report.get('input_report_sha256'):
            raise ValueError('기존 평가 입력 지문 변경')
        for code, expected in report['code_sha256'].items():
            if (not code.startswith(('scripts/', 'tinylm/')) or not code.endswith('.py')):
                raise ValueError('원형 코드 경로 계약 위반')
            bound(ROOT / code, expected)
        for lane in sorted(LANES):
            receipt_path = provider.receipt_path(endpoint, lane)
            bound(receipt_path, report['receipt_sha256'][lane]); receipt = required(receipt_path)
            body = receipt.get('body_proof', {})
            if (receipt.get('status') != 'LANE_COMPLETE' or receipt.get('endpoint') != endpoint
                    or receipt.get('lane') != lane or receipt.get('output') != report['outputs'][lane]
                    or receipt.get('checkpoint_sha256') != identity['checkpoint_sha256']
                    or receipt.get('initial_core_sha256') != identity['initial_core_sha256']
                    or body.get('initial_core_sha256') != identity['initial_core_sha256']
                    or body.get('final_core_sha256') != identity['initial_core_sha256']):
                raise ValueError('기존 원형 영수증/본체 계보 변경')
        directory = provider.LOCAL / endpoint
        if report.get('directory') != str(directory.relative_to(ROOT)):
            raise ValueError('다른 원형 디렉터리')
        manifest = report['outputs']['natural']['manifest']
        manifest_path = directory / 'natural_shards_manifest.json'
        bound(manifest_path)
        if required(manifest_path) != manifest:
            raise ValueError('원형 natural manifest 변경')
        events = read_shards(directory, manifest, 'natural')
        for shard in manifest['shards']:
            bound(directory / shard['path'], shard['sha256'])
        sources = project_natural(events)
        for event in events:
            expected = normalize(dict(messages=[dict(role='user', content=old_user(
                event['context'], event['question'], event['language'], event['view']))]))['messages']
            if event['messages'] != expected:
                raise ValueError('기존 전체 user prompt 변경')
            cpt.evaluation.generation_proof(event, expected)
        if cpt.evaluation.method.summarize_natural(events) != report['outputs']['natural']['counts']:
            raise ValueError('기존 natural1536 원점수/종료 재계수 불일치')
        rows[endpoint] = events; projections[endpoint] = sources
        identities[endpoint] = dict(identity, report_sha256=summary['report_sha256'],
            natural_manifest_sha256=files[str(manifest_path.relative_to(ROOT))],
            natural_concat_sha256=manifest['concat_sha256'])
    if projections[ENDPOINTS[0]] != projections[ENDPOINTS[1]]:
        raise ValueError('두 final의 512root/1536view 원형 질문·본문·alias가 다름')
    sources = projections[ENDPOINTS[0]]
    return dict(source_report_sha256=SOURCE_REPORT_SHA, paired_readback_sha256=SOURCE_READBACK_SHA,
        source_projection_sha256=sha(sources), source_roots=512, original_views=1536,
        endpoints=identities, immutable_files=files), sources, rows


def syntax_info():
    return dict(schema=VERSION, tag=TAG, conditions=list(CONDITIONS), endpoints=list(ENDPOINTS),
        context_limit=CONTEXT, max_new=MAX_NEW, roots=128, responses_per_endpoint=512,
        protocol=PROTOCOL, optimizer_updates=0, checkpoints_written=0,
        teacher_calls=0, active_limit_seconds=ACTIVE_LIMIT,
        active_slot_seconds=SLOTS, record_reserve_seconds=RECORD_RESERVE,
        time_basis='driver worker active seconds plus unrun worker reservations; no prepare+1h calendar expiry',
        wrapper_regression_preflight_overhead_excluded_from_active_budget=True,
        stdout_example_rule='언어와 길이 사분위마다 source_key 최솟값1root; 새 답/점수/종료 참조0',
        stdout_example_roots=8, stdout_example_is_performance_estimate=False,
        authority_end_utc=END.isoformat(), answer_quality_certificate='NOT_ESTABLISHED', automatic_adoption=False)


def info():
    cpt, base = dependencies()
    paths = sorted(set((*OWN_CODE, *cpt.CODE, *base.CODE, *cpt.qa.CODE,
        'scripts/p106b_stage_receipt.py', 'scripts/p106b_shards.py',
        'tinylm/chat/canonical.py', 'tinylm/chat/serialize.py', 'tinylm/infer/generate.py')))
    return dict(syntax_info(), code_sha256={path: digest(ROOT / path) for path in paths},
        source_report_sha256=SOURCE_REPORT_SHA, source_readback_sha256=SOURCE_READBACK_SHA,
        tokenizer_sha256=TOK_SHA,
        metric='기존 p106b_night_learning.qa_scores 변경 없음; 공식 scorer 아님',
        numeric_alias_limit='0.25%/.25%의 기존 0점 가능성을 조용히 정정하지 않음',
        scientific_scope='반복 관측 개발 cohort; 같은 CP 내 위치/반복 진단, 학습seed 일반화·native 인과 분리 아님')


def store_rows(stem, rows, lineage):
    safe(CORPUS)
    writer = ShardWriter(CORPUS, stem, limit=19_999_999)
    for row in rows:
        writer.append(row)
    manifest = writer.close(lineage=lineage)
    return manifest, digest(CORPUS / (stem + '_shards_manifest.json'))


def public_cpu(report):
    return dict(info(), status='CPU_POSITION_PREPARED_MODEL_NOT_RUN',
        corpus_report_sha256=digest(CORPUS / 'report.json'), source=report['source'],
        selection=report['selection'], case_manifest_sha256=report['case_manifest_sha256'],
        cases_sha256=report['selection']['cases_sha256'], token_length_summary=report['token_length_summary'],
        stdout_example_selection=report['stdout_example_selection'],
        raw_contexts_questions_aliases_copied_to_public=False,
        model_loaded=False, tokenizer_loaded=True, source_read=True, answers_generated=0)


def token_length_summary(cases):
    result = {}
    for language in LANGUAGES:
        result[language] = {}
        for condition in CONDITIONS:
            values = [c for c in cases if c['language'] == language and c['condition'] == condition]
            if not values:
                raise Pending('비어 있는 길이 구간')
            lengths = [c['encoding']['prompt_tokens'] for c in values]
            distances = [offset['tokens_after_end'] for c in values for offset in c['encoding']['offsets'] if offset['kind'] == 'Q']
            result[language][condition] = dict(n=len(values), prompt_tokens_min=min(lengths),
                prompt_tokens_max=max(lengths), prompt_tokens_sum=sum(lengths),
                question_occurrences=condition.count('Q'),
                question_distance_to_generation_min=min(distances),
                question_distance_to_generation_max=max(distances),
                distance_definition='전체 prompt token열에서 해당 질문 내용 마지막 token 뒤의 token 수; assistant prefix 포함')
    return result


def stdout_example_selection(cases):
    """답이 생기기 전에 고정 가능한8root. 공개 계약에는 질문/본문 대신 SHA만."""
    roots = validate_cases(cases); selected = []
    for language in LANGUAGES:
        for quartile in range(4):
            candidates = [views for (lang, _), views in roots.items()
                          if lang == language and views['CQ']['length_quartile'] == quartile]
            chosen = min(candidates, key=lambda views: source_key({k: views['CQ'][k] for k in SOURCE_FIELDS}))
            case = chosen['CQ']
            selected.append(dict(language=language, length_quartile=quartile, root=case['root'],
                source_key_sha256=source_key({k: case[k] for k in SOURCE_FIELDS}),
                source_sha256=case['source_sha256'], context_sha256=sha(case['context']),
                question_sha256=sha(case['question']),
                case_ids={condition: chosen[condition]['case_id'] for condition in CONDITIONS}))
    return dict(roots=8, selected=selected, selection_sha256=sha(selected),
        rule='동결128root 안의 언어×길이사분위별 source_key 최솟값1root; 정오/답/종료 무참조',
        text_hash_encoding='UTF-8 canonical JSON SHA256; sha(context/question)',
        source_context_text_published=False, outcome_based_replacement=False)


def example_comparisons(cases, events, endpoint, raw_directory, manifest, expected_selection=None):
    """검증된 원답을 읽기만 하는 비교표. 재생성/재채점/성공 표본 교체0."""
    if endpoint not in ENDPOINTS:
        raise ValueError('예시의 정확한 final endpoint 필요')
    selection = stdout_example_selection(cases)
    if expected_selection is not None and sha(selection) != sha(expected_selection):
        raise ValueError('CPU 사전고정 예시 root/선정SHA 변경')
    if len(events) < EXPECTED_RESPONSES:
        raise Pending('완료512답 없이 빈 예시/0답으로 대체하지 않음')
    if len(events) > EXPECTED_RESPONSES:
        raise ValueError('예시 입력의 전체답 분모 초과')
    directory = Path(raw_directory)
    if directory.is_absolute():
        try:
            directory = directory.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError('다른 raw namespace') from exc
    expected_directory = Path('test_result/evidence/local') / TAG / 'evaluate' / endpoint
    if directory != expected_directory:
        raise ValueError('예시 raw의 고정 endpoint 경로 변경')
    if (manifest.get('schema') != 'P106B_WRITE_ONCE_SHARDS_V1'
            or type(manifest.get('rows')) is not int or manifest['rows'] != EXPECTED_RESPONSES
            or not manifest.get('shards')):
        raise ValueError('완료512답 manifest가 예시 출력의 선결')
    locators = []
    for index, shard in enumerate(manifest['shards']):
        if (shard.get('path') != 'answers_%06d.jsonl' % index
                or type(shard.get('rows')) is not int or not 1 <= shard['rows'] <= EXPECTED_RESPONSES):
            raise ValueError('예시 raw shard/행 연결 변경')
        locators.extend(dict(raw_path=str(directory / shard['path']), raw_line_number_1based=line)
                        for line in range(1, shard['rows'] + 1))
    if len(locators) != len(events):
        raise ValueError('예시 raw 행 locator의 전체 분모 변경')
    indexed = {}
    for case, event, locator in zip(cases, events, locators):
        if (event.get('case_id') != case['case_id'] or event['case_id'] in indexed
                or event.get('endpoint') != endpoint
                or sha({key: event.get(key) for key in case}) != sha(case)
                or not isinstance(event.get('answer'), str)
                or not isinstance(event.get('generation'), dict)
                or not isinstance(event['generation'].get('finish_reason'), str)
                or not event['generation']['finish_reason']
                or type(event['generation'].get('generated_tokens')) is not int):
            raise ValueError('예시의 원문/순서/endpoint/실제답/종료 결손 또는 변조')
        indexed[event['case_id']] = (event, locator)
    output = []
    for chosen in selection['selected']:
        first = indexed[chosen['case_ids']['CQ']][0]
        answers = {}
        for condition in CONDITIONS:
            event, locator = indexed[chosen['case_ids'][condition]]
            answers[condition] = dict(answer=event['answer'], finish_reason=event['generation']['finish_reason'],
                generated_tokens=event['generation']['generated_tokens'], case_id=event['case_id'], **locator)
        output.append(dict(endpoint=endpoint, language=chosen['language'], length_quartile=chosen['length_quartile'],
            root=chosen['root'], question=first['question'], context_sha256=chosen['context_sha256'],
            source_key_sha256=chosen['source_key_sha256'], answers=answers))
    return dict(selection=selection, examples=output, endpoint=endpoint, displayed_roots=8,
        full_response_denominator=EXPECTED_RESPONSES, full_root_denominator=EXPECTED_ROOTS,
        full_context_included=False, performance_estimate=False, new_model_calls=0)


def print_answer_examples(cases, events, endpoint, raw_directory, manifest, expected_selection, note=None):
    values = example_comparisons(cases, events, endpoint, raw_directory, manifest, expected_selection)
    note = (lambda line: print(line, flush=True)) if note is None else note
    header = {key: values[key] for key in ('endpoint', 'displayed_roots', 'full_response_denominator',
                                          'full_root_denominator', 'full_context_included', 'performance_estimate', 'new_model_calls')}
    header['selection_sha256'] = values['selection']['selection_sha256']
    header['rule'] = values['selection']['rule']
    note('[QUESTION_POSITION_EXAMPLE_SELECTION] ' + json.dumps(header, ensure_ascii=False))
    for row in values['examples']:
        note('[QUESTION_POSITION_EXAMPLE] ' + json.dumps(row, ensure_ascii=False))
    return values


def prepare():
    from tokenizers import Tokenizer
    if safe(CORPUS).exists() or safe(EVIDENCE / 'cpu_contract.json').exists():
        raise FileExistsError('기존 완료/부분 CPU 원형 보존')
    source, sources, _ = read_source()
    if digest(TOKENIZER) != TOK_SHA:
        raise ValueError('동결 토크나이저 byte SHA 변경')
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    cases, selection = select_cases(sources, tokenizer)
    validate_cases(cases)
    if (selection['roots'] != EXPECTED_ROOTS or len(cases) != EXPECTED_RESPONSES
            or any(c['messages'] != [dict(role='user', content=old_user(c['context'], c['question'], c['language'], 0))]
                   for c in cases if c['condition'] == 'CQ')):
        raise ValueError('고정128root/512조건/CQ byte 일치 위반')
    lineage = dict(tag=TAG, code_sha256=info()['code_sha256'], source=source, purpose='EVALUATION_ONLY_NO_TRAIN')
    safe(CORPUS).mkdir(parents=True, exist_ok=False)
    manifest, manifest_sha = store_rows('cases', cases, lineage)
    result = dict(info(), status='CPU_POSITION_PREPARED_MODEL_NOT_RUN', source=source,
        selection=selection, case_manifest=manifest, case_manifest_sha256=manifest_sha,
        stdout_example_selection=stdout_example_selection(cases),
        token_length_summary=token_length_summary(cases), model_loaded=False,
        tokenizer_loaded=True, source_read=True, cuda_initialized=False)
    write(CORPUS / 'report.json', result)
    write(EVIDENCE / 'cpu_contract.json', public_cpu(result))
    print('[QUESTION_POSITION_CPU] 고정128root/512입력; 모델 품질 NOT_RUN', flush=True)
    return 0


def read_prepared():
    report = required(CORPUS / 'report.json')
    if report.get('status') != 'CPU_POSITION_PREPARED_MODEL_NOT_RUN':
        raise Pending('완료된 새 CPU 동결 필요')
    if any(report.get(k) != v for k, v in info().items()):
        raise ValueError('새 CPU 코드/계약 변경')
    source, sources, originals = read_source()
    if source != report.get('source') or digest(TOKENIZER) != TOK_SHA:
        raise ValueError('동결 후 source/CP/토크나이저 변경')
    manifest_path = CORPUS / 'cases_shards_manifest.json'
    if digest(manifest_path) != report.get('case_manifest_sha256'):
        raise ValueError('새 CPU manifest 지문 변경')
    manifest = required(manifest_path)
    if manifest != report.get('case_manifest') or manifest.get('lineage') != dict(
            tag=TAG, code_sha256=info()['code_sha256'], source=source, purpose='EVALUATION_ONLY_NO_TRAIN'):
        raise ValueError('새 CPU manifest 계보 변경')
    cases = read_shards(CORPUS, manifest, 'cases')
    validate_cases(cases)
    if len(cases) != EXPECTED_RESPONSES or sha(cases) != report['selection'].get('cases_sha256'):
        raise ValueError('새 동결512입력 변경')
    source_map = {(r['language'], r['root']): r for r in sources}
    seen, roots = set(), defaultdict(set)
    for case in cases:
        row = {k: case[k] for k in SOURCE_FIELDS}; key = (case['language'], case['root'])
        if row != source_map.get(key) or case.get('source_projection_sha256') != sha(row):
            raise ValueError('선정한 root의 원문/질문/alias 변경')
        condition = case.get('condition'); body, _ = render_layout(row, condition)
        if (case.get('case_id') != sha([TAG, *key, condition]) or case['case_id'] in seen
                or case.get('messages') != [dict(role='user', content=body)]
                or case['encoding'].get('prompt_sha256') != sha(prompt(case['messages']))
                or case['encoding'].get('prompt_tokens', CONTEXT) + MAX_NEW > CONTEXT
                or type(case.get('length_quartile')) is not int or case['length_quartile'] not in range(4)):
            raise ValueError('동결 prompt/분모/길이 계약 변경')
        seen.add(case['case_id']); roots[key].add(condition)
    if (len(roots) != EXPECTED_ROOTS or any(v != set(CONDITIONS) for v in roots.values())
            or report['selection'].get('ordered_selection_sha256') != sha(
                [[c['language'], c['root'], c['length_quartile'], c['condition']] for c in cases])
            or report['selection'].get('source_projection_sha256') != sha(sources)
            or report.get('stdout_example_selection') != stdout_example_selection(cases)
            or token_length_summary(cases) != report.get('token_length_summary')
            or required(EVIDENCE / 'cpu_contract.json') != public_cpu(report)):
        raise ValueError('CPU 분모/공개 요약/조건 변경')
    return report, cases, originals


def cq_comparison(answer, generation, original):
    keys = sorted(set(generation) | set(original['generation']))
    different = [k for k in keys if k not in generation or k not in original['generation']
                 or sha(generation[k]) != sha(original['generation'][k])]
    return dict(reference_event_sha256=sha(original), answer_exact_equal=answer == original['answer'],
        generation_receipt_exact_equal=not different, generation_differing_keys=different,
        reference_prompt_sha256=original['generation']['actual_prompt_sha256'],
        reference_answer_sha256=sha(original['answer']))


def validate_generation(answer, generation, case):
    if not isinstance(answer, str) or not isinstance(generation, dict):
        raise ValueError('실제 답과 영수증 필요; 빈 문자열과 누락을 구분')
    expected = dict(actual_prompt_sha256=case['encoding']['prompt_sha256'],
        raw_answer_sha256=sha(answer), prompt_tokens=case['encoding']['prompt_tokens'],
        requested_max_new=MAX_NEW, max_new=MAX_NEW,
        stop_token_sequences=case['encoding']['stop_token_sequences'],
        eos_token_available=True, stop_at_eos_requested=True, stop_at_eos_effective=True)
    if any(generation.get(k) != v for k, v in expected.items()):
        raise ValueError('실제 전체 prompt/답/FP32 helper 영수증 변경')
    if (any(type(generation.get(k)) is not int for k in ('prompt_tokens', 'requested_max_new', 'max_new'))
            or any(type(generation.get(k)) is not bool for k in
                   ('eos_token_available', 'stop_at_eos_requested', 'stop_at_eos_effective'))):
        raise ValueError('생성 영수증의 정수/불리언 wire형 변경')
    stops = generation['stop_token_sequences']; matched = generation.get('matched_stop_sequence')
    if (not isinstance(stops, list) or any(not isinstance(seq, list) or any(type(i) is not int for i in seq) for seq in stops)
            or matched is not None and (not isinstance(matched, list) or any(type(i) is not int for i in matched))):
        raise ValueError('EOT/stop token ID의 정수 wire형 변경')
    n, reason = generation.get('generated_tokens'), generation.get('finish_reason')
    if type(n) is not int or not 1 <= n <= MAX_NEW or reason not in ('EOS', 'STOP_SEQUENCE', 'MAX_NEW'):
        raise ValueError('생성 종료/길이 계약 위반')
    if reason == 'STOP_SEQUENCE' and generation.get('matched_stop_sequence') not in expected['stop_token_sequences']:
        raise ValueError('EOT 종료 영수증 불일치')
    if reason == 'MAX_NEW' and (n != MAX_NEW or generation.get('matched_stop_sequence') is not None):
        raise ValueError('상한 종료 영수증 불일치')


def event_for_case(case, endpoint, answer, generation, original=None):
    if endpoint not in ENDPOINTS:
        raise ValueError('정확한 final endpoint 필요')
    validate_generation(answer, generation, case)
    if case['condition'] == 'CQ' and original is None:
        raise Pending('동일 CP의 원래 CQ답 누락')
    return dict(case, endpoint=endpoint, answer=answer, generation=generation,
        generation_protocol=PROTOCOL, scores=score(answer, case['aliases'], case['language']),
        cq_reference=cq_comparison(answer, generation, original) if case['condition'] == 'CQ' else None)


def collect_answers(cases, endpoint, originals, emit, encode_actual, append, guard):
    """실제 GPU와 합성 fixture가 공유하는 전체512수집/분모/receipt 경로."""
    validate_cases(cases)
    references = {(e['language'], e['root']): e for e in originals if e['view'] == 0}
    values = []
    for case in cases:
        guard()
        if encode_actual(case) != {k: v for k, v in case.items() if k != 'length_quartile'}:
            raise ValueError('실제 tokenizer/full prefix/길이가 CPU 동결과 다름')
        answer, generation = emit(case['messages'])
        event = event_for_case(case, endpoint, answer, generation,
                               references.get((case['language'], case['root'])))
        append(event); values.append(event)
    return values


def recount(events, cases, endpoint, originals):
    validate_cases(cases)
    expected = {c['case_id']: c for c in cases}
    if len(expected) != len(cases) or not cases:
        raise ValueError('고유한 비어 있지 않은 동결 조건 필요')
    references = {(e['language'], e['root']): e for e in originals if e['view'] == 0}
    seen = set()
    for event in events:
        identity = event.get('case_id')
        if identity not in expected or identity in seen:
            raise ValueError('알 수 없는/중복 답')
        seen.add(identity); case = expected[identity]
        if any(event.get(k) != v for k, v in case.items()) or event.get('endpoint') != endpoint:
            raise ValueError('다른 endpoint/원문/질문/gold/분모')
        original = references.get((case['language'], case['root']))
        rebuilt = event_for_case(case, endpoint, event.get('answer'), event.get('generation'), original)
        if sha(event) != sha(rebuilt):
            raise ValueError('원답 기반 점수/전체 receipt 재계수 불일치')
    if seen != set(expected):
        raise Pending('추가답 미완료: 관측%d/필수%d' % (len(seen), len(expected)))
    ordered = sorted(events, key=lambda e: (e['language'], e['root'], CONDITIONS.index(e['condition'])))
    def aggregate(values):
        n = len(values)
        if not n:
            raise Pending('비어 있는 평가 구간')
        result = dict(n=n, roots=len({e['root'] for e in values}), articles=len({e['article_id'] for e in values}))
        for metric in ('em', 'f1', 'raw_exact'):
            total = sum(e['scores'][metric] for e in values)
            result[metric + '_sum'], result[metric] = total, total / n
        reasons = Counter(e['generation']['finish_reason'] for e in values)
        result.update(empty=sum(not e['answer'].strip() for e in values),
            stop=sum(reasons[r] for r in ('STOP_SEQUENCE', 'EOS')),
            max_new=reasons['MAX_NEW'], finish_reasons=dict(sorted(reasons.items())),
            generated_tokens_sum=sum(e['generation']['generated_tokens'] for e in values))
        return result
    by_language = {}
    for language in LANGUAGES:
        values = [e for e in ordered if e['language'] == language]
        by_language[language] = dict(roots=len({e['root'] for e in values}),
            articles=len({e['article_id'] for e in values}),
            by_condition={c: aggregate([e for e in values if e['condition'] == c]) for c in CONDITIONS},
            by_length_quartile={str(q): {c: aggregate([e for e in values if e['condition'] == c and e['length_quartile'] == q])
                                        for c in CONDITIONS} for q in range(4)})
    cq = [e['cq_reference'] for e in ordered if e['condition'] == 'CQ']
    agreement = dict(n=len(cq), answer_exact_equal=sum(c['answer_exact_equal'] for c in cq),
        receipt_exact_equal=sum(c['generation_receipt_exact_equal'] for c in cq),
        both_equal=sum(c['answer_exact_equal'] and c['generation_receipt_exact_equal'] for c in cq))
    return dict(status='POSITION_RAW_RECOUNTED', cases=len(ordered), roots=len(ordered) // 4,
        by_language=by_language, cq_reproduction=agreement,
        cq_reproduction_interpretation_hold=agreement['both_equal'] != agreement['n'],
        aggregation_order='언어 문자열/root/조건 CQ,QC,QCQ,CQQ 정렬 후 Python sum; 조건별 root 가중 평균',
        local_scores_unchanged=True, official_scorer=False, automatic_adoption=False)


def paired_articles(events, draws=2000, seed=1337):
    """고정 개발 기사 단위의 대응 기술구간. 정오 규칙은 새로 만들지 않는다."""
    if type(draws) is not int or draws < 1 or type(seed) is not int:
        raise ValueError('양의 재표본 수와 정수 seed 필요')
    comparisons = (('CQ', 'QC'), ('CQ', 'QCQ'), ('CQ', 'CQQ'), ('QCQ', 'CQQ'))
    output = {}
    for language in LANGUAGES:
        roots = defaultdict(dict)
        for event in events:
            if event['language'] == language:
                if event['condition'] in roots[event['root']]:
                    raise ValueError('대응 조건 중복')
                roots[event['root']][event['condition']] = event
        if not roots or any(set(v) != set(CONDITIONS) for v in roots.values()):
            raise Pending('네 조건 모두 있어야 대응 가능')
        result = {}
        for left, right in comparisons:
            articles = defaultdict(lambda: [0., 0., 0])
            for root, values in sorted(roots.items()):
                a, b = values[left], values[right]
                if any(a[k] != b[k] for k in SOURCE_FIELDS):
                    raise ValueError('대응 원문/질문/alias 변경')
                v = articles[a['article_id']]
                v[0] += b['scores']['em'] - a['scores']['em']
                v[1] += b['scores']['f1'] - a['scores']['f1']; v[2] += 1
            matrix = [v for _, v in sorted(articles.items())]
            rng = random.Random(seed); samples = [[], []]
            for _ in range(draws):
                chosen = [matrix[rng.randrange(len(matrix))] for _ in matrix]
                denominator = sum(v[2] for v in chosen)
                for j in (0, 1):
                    samples[j].append(sum(v[j] for v in chosen) / denominator)
            def quantile(values, p):
                ordered = sorted(values); x = (len(ordered) - 1) * p; i = int(x)
                return ordered[i] + (ordered[min(i + 1, len(ordered) - 1)] - ordered[i]) * (x - i)
            result[left + '__' + right] = dict(n=len(roots), articles=len(matrix),
                single_article_interval_degenerate=len(matrix) == 1,
                metrics={metric: dict(right_minus_left=sum(v[j] for v in matrix) / len(roots),
                    ci95=[quantile(samples[j], .025), quantile(samples[j], .975)]) for j, metric in enumerate(('em', 'f1'))})
        output[language] = result
    return dict(by_language=output, draws=draws, seed=seed,
        cluster_unit='언어별 article_id; 동일 root 네 조건 유지',
        aggregation='기사 재표본 안에서 질문 수 가중 평균',
        learning_seed_uncertainty_measured=False, exploratory_development_only=True)


def activity_key(mode, endpoint=None):
    key = 'evaluate_' + str(endpoint) if mode == 'evaluate' else mode
    if key not in SLOTS:
        raise ValueError('정확한 active 단계 필요')
    return key


def activity_path(key):
    if key not in SLOTS:
        raise ValueError('등록되지 않은 active 단계')
    return EVIDENCE / ('activity_' + key + '.json')


def activities():
    values = {}
    for key in SLOTS:
        path = safe(activity_path(key))
        if path.exists():
            value = required(path)
            if (value.get('schema') != VERSION or value.get('tag') != TAG or value.get('stage') != key
                    or value.get('status') not in ('COMPLETE', 'HOLD', 'TOOL_ERROR', 'INTERRUPTED')
                    or value.get('returncode') != {'COMPLETE': 0, 'HOLD': 8, 'TOOL_ERROR': 9, 'INTERRUPTED': 130}.get(value.get('status'))
                    or type(value.get('active_seconds')) not in (int, float)
                    or not math.isfinite(value['active_seconds']) or value['active_seconds'] < 0):
                raise ValueError('active 시간 영수증 변조')
            if value.get('own_code_sha256') != {p: digest(ROOT / p) for p in OWN_CODE}:
                raise ValueError('active 시간 영수증의 코드 지문 변경')
            if value['status'] == 'COMPLETE' and digest(stage_output_path(key)) != value.get('output_report_sha256'):
                raise ValueError('완료 active 시간과 실제 산출물 연결 변경')
            values[key] = value
    return values


def stage_output_path(key):
    if key == 'prepare':
        return CORPUS / 'report.json'
    if key == 'readback':
        return EVIDENCE / 'readback.json'
    if key in ('evaluate_' + endpoint for endpoint in ENDPOINTS):
        return EVIDENCE / (key[len('evaluate_'):] + '_report.json')
    raise ValueError('미등록 단계 산출물')


def admission(mode, endpoint, requested, previous, now=None, elapsed=0.):
    key = activity_key(mode, endpoint)
    if type(requested) is not int or not 60 <= requested <= 1200:
        raise ValueError('60..1200초 bounded wall 필요')
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError('유효한 현재 active 경과 필요')
    if key in previous:
        raise Pending('완료/부분 단계 보존; 재실행 덮어쓰기 금지')
    if set(previous) - set(SLOTS):
        raise ValueError('알 수 없는 active 단계')
    prerequisites = [] if mode == 'prepare' else ['prepare']
    if mode == 'readback':
        prerequisites += ['evaluate_' + e for e in ENDPOINTS]
    if any(previous.get(p, {}).get('status') != 'COMPLETE' for p in prerequisites):
        raise Pending('완료된 앞 단계의 active 영수증 필요')
    if any(v.get('status') != 'COMPLETE' for v in previous.values()):
        raise Pending('부분/오류 단계를 정상 완료로 승격하지 않음')
    spent = sum(v['active_seconds'] for v in previous.values())
    cap = min(requested, SLOTS[key])
    if elapsed >= cap:
        raise TimeoutError('현재 driver active wall 초과; 부분 증거 보존')
    future = sum(seconds for stage, seconds in SLOTS.items() if stage not in previous and stage != key)
    reserved = spent + cap + future + RECORD_RESERVE
    if reserved > ACTIVE_LIMIT:
        raise Pending('active 합+미실행 예약+기록 예비가3600초 초과')
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('시간대 있는 현재시각 필요')
    calendar_remaining = (END - now).total_seconds()
    required_calendar = cap - elapsed + future + RECORD_RESERVE
    if calendar_remaining < required_calendar:
        raise Pending('20일17시 절대권한과 미실행/기록600초 예비 미충족')
    return dict(stage=key, slot_seconds=cap, previous_active_seconds=spent,
        future_worker_reservations_seconds=future, record_reserve_seconds=RECORD_RESERVE,
        total_study_reserved_active_seconds=reserved,
        calendar_remaining_seconds=calendar_remaining,
        calendar_expiry_is_not_prepare_plus_one_hour=True,
        wrapper_regression_preflight_excluded=True)


def evaluate(endpoint, max_wall_sec, guard=lambda: None):
    if endpoint not in ENDPOINTS:
        raise ValueError('final endpoint 선택 필요')
    report, cases, originals = read_prepared()
    identity = report['source']['endpoints'][endpoint]
    target = safe(EVIDENCE / (endpoint + '_report.json'))
    directory = safe(LOCAL / 'evaluate' / endpoint)
    if target.exists() or directory.exists():
        raise FileExistsError('기존 완료/부분512답 보존')
    guard()
    from scripts.p106b_gate_runtime import idle_before_gpu
    idle_before_gpu(); guard()
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    cpt, _ = dependencies()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    cp = safe(ROOT / identity['checkpoint'])
    if digest(cp) != identity['checkpoint_sha256'] or digest(TOKENIZER) != TOK_SHA:
        raise ValueError('GPU admission 직전 CP/토크나이저 변경')
    guard(); directory.mkdir(parents=True, exist_ok=False)
    model = None; began = time.perf_counter()
    try:
        model, cfg, device = load_model(arch='dense', ckpt_path=str(cp), device='cuda')
        if cfg.max_seq_len != CONTEXT:
            raise ValueError('고정1024 본체 필요; 생성은 기존 helper의 단일 token MTPoff 경로')
        initial = cpt.training.foundation.runtime.state_fingerprint(model)
        if initial != identity['initial_core_sha256']:
            raise ValueError('strict load한 final 본체 지문 불일치')
        tok = Tokenizer.from_file(str(TOKENIZER))
        emit = cpt.emit_function(model, cfg, tok, max_new=MAX_NEW)
        writer = ShardWriter(directory, 'answers', limit=19_999_999)
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            events = collect_answers(cases, endpoint, originals[endpoint], emit,
                lambda case: encode_case({k: case[k] for k in SOURCE_FIELDS}, case['condition'], tok),
                writer.append, guard)
        final = cpt.training.foundation.runtime.state_fingerprint(model)
        if final != initial or digest(cp) != identity['checkpoint_sha256']:
            raise ValueError('무학습 평가가 가중치/본체를 바꿈')
        output = dict(manifest=writer.close(lineage=dict(info(), endpoint=endpoint,
            input_report_sha256=digest(CORPUS / 'report.json'))),
            counts=recount(events, cases, endpoint, originals[endpoint]))
        result = dict(info(), status='ACTUAL_POSITION_EVALUATION_COMPLETE', endpoint=endpoint,
            checkpoint=identity['checkpoint'], checkpoint_sha256=identity['checkpoint_sha256'],
            initial_core_sha256=initial, final_core_sha256=final, body_unchanged=True,
            source=report['source'], input_report_sha256=digest(CORPUS / 'report.json'),
            directory=str(directory.relative_to(ROOT)), output=output,
            answer_manifest_sha256=digest(directory / 'answers_shards_manifest.json'),
            model_loaded=True, tokenizer_loaded=True, source_read=True,
            optimizer_updates=0, checkpoints_written=0,
            whole_seconds=time.perf_counter() - began,
            peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
            condition_effect_conclusion='HOLD_CQ_REPRODUCTION' if output['counts']['cq_reproduction_interpretation_hold'] else 'DESCRIPTIVE_ONLY_NOT_AUTOMATIC_ADOPTION')
        # source/code는 실행 전후에 같아야 한다.
        if read_source()[0] != report['source'] or info()['code_sha256'] != report['code_sha256']:
            raise ValueError('실행 중 source/code 변경')
        guard(); write(target, result)
        print('[QUESTION_POSITION_EVALUATE] ' + json.dumps(dict(endpoint=endpoint,
            cases=len(events), cq=output['counts']['cq_reproduction'])), flush=True)
        print_answer_examples(cases, events, endpoint, directory, output['manifest'], report['stdout_example_selection'])
        return 0
    finally:
        if model is not None:
            del model
        gc.collect(); torch.cuda.empty_cache()


def read_endpoint(endpoint, report, cases, originals):
    path = EVIDENCE / (endpoint + '_report.json'); result = required(path)
    identity = report['source']['endpoints'][endpoint]
    if result.get('status') != 'ACTUAL_POSITION_EVALUATION_COMPLETE':
        raise Pending('완료된512답 보고 필요')
    expected = dict(endpoint=endpoint, checkpoint=identity['checkpoint'],
        checkpoint_sha256=identity['checkpoint_sha256'], initial_core_sha256=identity['initial_core_sha256'],
        final_core_sha256=identity['initial_core_sha256'], body_unchanged=True,
        source=report['source'], input_report_sha256=digest(CORPUS / 'report.json'),
        directory=str((LOCAL / 'evaluate' / endpoint).relative_to(ROOT)),
        model_loaded=True, tokenizer_loaded=True, source_read=True,
        optimizer_updates=0, checkpoints_written=0)
    if (any(result.get(k) != v for k, v in expected.items())
            or any(result.get(k) != v for k, v in info().items() if k != 'model_loaded')):
        raise ValueError('새 endpoint/본체/source/code 보고 변경')
    directory = LOCAL / 'evaluate' / endpoint
    manifest_path = directory / 'answers_shards_manifest.json'
    if digest(manifest_path) != result.get('answer_manifest_sha256'):
        raise ValueError('새답 manifest 지문 변경')
    manifest = required(manifest_path)
    if (manifest != result['output']['manifest']
            or manifest.get('lineage') != dict(info(), endpoint=endpoint,
                input_report_sha256=digest(CORPUS / 'report.json'))):
        raise ValueError('새답 manifest 계보 변경')
    events = read_shards(directory, manifest, 'answers')
    counts = recount(events, cases, endpoint, originals)
    if counts != result['output'].get('counts'):
        raise ValueError('512답 원점수/종료 재계수 불일치')
    return result, events


def readback():
    report, cases, originals = read_prepared()
    target = safe(EVIDENCE / 'readback.json')
    if target.exists():
        raise FileExistsError('기존 원형 판독 보존')
    reports, values, summaries, paired, manifests = {}, {}, {}, {}, {}
    for endpoint in ENDPOINTS:
        result, events = read_endpoint(endpoint, report, cases, originals[endpoint])
        reports[endpoint] = digest(EVIDENCE / (endpoint + '_report.json'))
        values[endpoint] = events; summaries[endpoint] = result['output']['counts']
        manifests[endpoint] = result['output']['manifest']
        paired[endpoint] = paired_articles(events)
    hold = any(v['cq_reproduction_interpretation_hold'] for v in summaries.values())
    result = dict(info(), status='RAW_RECOUNT_COMPLETE_CQ_HOLD' if hold else 'RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION',
        errors=0, endpoint_report_sha256=reports, source=report['source'],
        input_report_sha256=digest(CORPUS / 'report.json'), summaries=summaries,
        stdout_example_selection=report['stdout_example_selection'],
        paired_within_checkpoint=paired, total_new_responses=2 * EXPECTED_RESPONSES,
        raw_publication=False, condition_effect_conclusion='HOLD_CQ_REPRODUCTION' if hold else 'DESCRIPTIVE_ONLY',
        cross_checkpoint_native_effect_causally_separated=False,
        length_and_repetition_confound_remains=True,
        automatic_prompt_adoption=False, student_general_intelligence='NOT_ESTABLISHED')
    write(target, result)
    for endpoint in ENDPOINTS:
        print_answer_examples(cases, values[endpoint], endpoint, LOCAL / 'evaluate' / endpoint,
            manifests[endpoint], report['stdout_example_selection'])
    print('[QUESTION_POSITION_READBACK] 완료 원형 재계수; ' + ('CQ 재현 불일치 HOLD8' if hold else '자동 채택0'), flush=True)
    return 8 if hold else 0


def failure_status(exc):
    if isinstance(exc, KeyboardInterrupt):
        return 'INTERRUPTED', 130
    if isinstance(exc, Pending):
        return 'HOLD', 8
    if type(exc).__name__ in ('PrerequisiteHold', 'PrerequisitePending'):
        return 'HOLD', 8
    if type(exc).__module__.startswith('torch') and type(exc).__name__ == 'OutOfMemoryError':
        return 'HOLD', 8
    return 'TOOL_ERROR', 9


def run_worker(mode, endpoint=None, max_wall_sec=1200):
    if mode == 'preflight':
        if (END - datetime.now(timezone.utc)).total_seconds() < RECORD_RESERVE:
            raise Pending('절대 종료/기록600초 예비 필요')
        read_prepared()
        print('[QUESTION_POSITION_PREFLIGHT] source/code/CP/원형 검산; 모델0', flush=True)
        return 0
    previous = activities()
    budget = admission(mode, endpoint, max_wall_sec, previous)
    key = budget['stage']; start = time.perf_counter(); started_utc = datetime.now(timezone.utc).isoformat()
    rc, status = 9, 'TOOL_ERROR'
    def guard():
        return admission(mode, endpoint, max_wall_sec, previous, elapsed=time.perf_counter() - start)
    try:
        from scripts.p106b_gate_runtime import wall_limit
        with wall_limit(budget['slot_seconds']):
            guard()
            if mode == 'prepare':
                rc = prepare()
            elif mode == 'evaluate':
                rc = evaluate(endpoint, max_wall_sec, guard)
            elif mode == 'readback':
                rc = readback()
            else:
                raise ValueError('미등록 worker mode')
            guard()
        status = 'COMPLETE' if rc == 0 else 'HOLD' if rc == 8 else 'TOOL_ERROR'
        return rc
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        status, rc = failure_status(exc)
        print('[QUESTION_POSITION_WORKER] %s%d: %s' % (status, rc, str(exc)), flush=True)
        return rc
    finally:
        receipt = dict(schema=VERSION, tag=TAG, stage=key, status=status, returncode=rc,
            active_seconds=time.perf_counter() - start, started_utc=started_utc,
            ended_utc=datetime.now(timezone.utc).isoformat(), admission=budget,
            wrapper_regression_preflight_excluded=True, includes_worker_source_load_and_model_load=True,
            queued_calendar_time_charged=False,
            own_code_sha256={p: digest(ROOT / p) for p in OWN_CODE},
            output_report_sha256=digest(stage_output_path(key)) if status == 'COMPLETE' else None,
            own_receipt_write_within_record_reserve=True)
        write(activity_path(key), receipt)


def phase_commands(mode, endpoint=None, max_wall_sec=1200):
    if mode not in MODES:
        raise ValueError('명시적인 진단 mode 필요')
    if ((mode == 'evaluate' and endpoint not in ENDPOINTS)
            or (mode != 'evaluate' and endpoint is not None)):
        raise ValueError('evaluate만 하나의 final endpoint를 선택')
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 1200:
        raise ValueError('60..1200초 상한 필요')
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/diag_p106b_question_position.py']
    command = driver + ['--mode', mode, '--max-wall-sec', str(max_wall_sec), '--worker']
    if endpoint is not None:
        command += ['--endpoint', endpoint]
    preflight = (driver + ['--mode', 'prepare', '--check-only', '--worker'] if mode == 'prepare'
                 else driver + ['--mode', 'preflight', '--execute', '--worker', '--max-wall-sec', '300'])
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_question_position', '-v']),
            ('PREFLIGHT', preflight), ('EXECUTE', command + ['--execute'])]


def run_pipeline(mode, endpoint=None, max_wall_sec=1200):
    phases = phase_commands(mode, endpoint, max_wall_sec)
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        env = dict(os.environ)
        for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            env[name] = '2'
        try:
            cap = 300 if '-m' in command or '--mode' in command and command[command.index('--mode') + 1] in ('prepare', 'preflight', 'readback') else max_wall_sec
            return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                timeout=cap + 30, env=env).returncode
        except (subprocess.TimeoutExpired, OSError):
            print('[QUESTION_POSITION_CHILD] 부분 원형 보존; TOOL_ERROR9', flush=True)
            return 9
        except KeyboardInterrupt:
            return 130
    return pipeline(phases, launch, lambda line: print(line, flush=True),
        experiment='P106B_QUESTION_POSITION_' + mode + '_' + str(endpoint or 'all'))['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--endpoint', choices=ENDPOINTS)
    parser.add_argument('--max-wall-sec', type=int, default=1200)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.endpoint, args.max_wall_sec)
    except ValueError as exc:
        parser.error(str(exc))
    if args.check_only:
        print('[QUESTION_POSITION_CHECK_ONLY] ' + json.dumps(dict(syntax_info(), phases=phases,
            model_loaded=False, tokenizer_loaded=False, source_read=False, gpu_initialized=False), ensure_ascii=False))
        return 0
    try:
        if args.worker:
            return run_worker(args.mode, args.endpoint, args.max_wall_sec)
        return run_pipeline(args.mode, args.endpoint, args.max_wall_sec)
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        status, code = failure_status(exc)
        print('[QUESTION_POSITION_FINAL] %s%d: %s' % (status, code, str(exc)), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
