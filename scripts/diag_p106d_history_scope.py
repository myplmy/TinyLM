#!/usr/bin/env python3
"""닫힌 규칙의 기초답/완전명시/gold이력/실제이력을 분리하는 무학습 진단.

공개 execute는 회귀/선결/실행의3단계다. 실물 source/토크나이저/CP는
총괄의 실행만 읽고, 합성 회귀와 check-only는 이를 읽지 않는다.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import argparse
from collections import Counter, defaultdict
import copy
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
import re
import subprocess
import time
from types import SimpleNamespace
from scripts import diag_p106b_question_position as common
from scripts.p106b_shards import ShardWriter
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106d_history_scope_v1_s1337'
VERSION = 'P106D_HISTORY_SCOPE_V1'
LOCAL = ROOT / 'test_result/evidence/local' / TAG
CORPUS = LOCAL / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
SOURCE_TAG = 'p106d_ruleviews_v3_length_s1337'
SOURCE_CORPUS = ROOT / 'HF/sft_ready' / SOURCE_TAG / 'corpus'
SOURCE_EVIDENCE = ROOT / 'test_result/evidence' / SOURCE_TAG
AUDIT = ROOT / 'handoff/audit/WIP_20261019_RULE_CURRICULUM_PRIOR_EVIDENCE.json'
AUDIT_SHA = 'F7D146C1B488DE489CD02C3794FFD6A4BFFC2A43C2BFB6C53CE5F03271319524'
SOURCE_REPORT_SHAS = dict(
    prepare='1ECA440C38642755B33BC0B1ED600046EDC08EE5BC3CC96138736AB7EE9B3FC9',
    fixed='887F5A829F637C03EEFCF91774F51C56BDF8FB0D3CA12DF5A8CB884DEDBC4F48',
    views='DF43D5B03D74C33E25A57036F56D45291C6FC1549BD92410D05793354C7AEEF8',
    readback='0FD848F4FB37201F3DB08E51F8AA96E681F16BE000B0311193B0E2B240455A30')
PARENT = ROOT / 'runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
TOKENIZER, TOK_SHA = common.TOKENIZER, common.TOK_SHA
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
ENDPOINTS = ('parent', 'fixed', 'views')
CONDITIONS = ('INITIAL_DIRECT', 'CURRENT_DIRECT', 'GOLD_HISTORY', 'ACTUAL_HISTORY')
COHORTS = ('old', 'fresh')
FAMILIES = ('arithmetic', 'boolean', 'lookup', 'format')
LANGUAGES = ('ko', 'en')
MODES = ('prepare', 'preflight', 'evaluate', 'readback')
CONTEXT, MAX_NEW, EXPECTED = 1024, 128, 546
ACTIVE_LIMIT, RECORD_RESERVE = 5400, 600
SLOTS = dict(prepare=600, evaluate_parent=1200, evaluate_fixed=1200, evaluate_views=1200, readback=600)
OWN_CODE = ('scripts/diag_p106d_history_scope.py', 'scripts/test_p106d_history_scope.py')
PROTOCOL = dict(common.PROTOCOL, answer_body='authenticated final EOT/EOS ID removal only; decode skip_special_tokens=False',
                helper_answer_and_generation_preserved=True, full_ids_observed_not_regenerated=True,
                body_protocol_revision='P106D_TERMINAL_VISIBLE_V1')
KEYS = ('answer', 'value', 'result', 'reply')
MINIMAL_QUESTIONS = (('1+1은 얼마인가요? 숫자만 답하세요.', '2'), ('2+2는 얼마인가요? 숫자만 답하세요.', '4'))
GENERATED = 'ACTUAL_MODEL_GENERATED'
UNSAFE = 'ACTUAL_HISTORY_NOT_RUN_UNSAFE'
OVERFLOW = 'ACTUAL_HISTORY_NOT_RUN_INPUT_BUDGET'
Pending = common.Pending
sha, safe, digest, required, write = common.sha, common.safe, common.digest, common.required, common.write


def producers():
    from scripts import diag_p106d_views as legacy
    from scripts import p106d_views as small
    from scripts import p106d_expanded_views as expanded
    from scripts import p106b_rule_views as rules
    return legacy, small, expanded, rules


def canonical(messages):
    from tinylm.chat.canonical import normalize, validate
    return validate(normalize(dict(messages=copy.deepcopy(messages))))['messages']


def chatml_control_markers():
    """정본에 실제 정의된8개만 취급하는 payload 경계; 의미오류 사전이 아니다."""
    from tinylm.chat.serialize import SPECS
    spec = SPECS['chatml']
    markers = (spec['start'], spec['end'], *spec['think'], *spec['call'], *spec['result'])
    if len(markers) != 8 or len(set(markers)) != 8 or any(not isinstance(m, str) or not m for m in markers):
        raise ValueError('동결 ChatML 제어표지 정본 변경')
    return markers


def text(message):
    blocks = message.get('content')
    if (not isinstance(blocks, list) or len(blocks) != 1 or not isinstance(blocks[0], dict)
            or set(blocks[0]) != {'type', 'text'} or blocks[0]['type'] != 'text'
            or not isinstance(blocks[0]['text'], str)):
        raise ValueError('정확한 단일 canonical text block 필요')
    return blocks[0]['text']


def strict_json(body):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('중복 JSON key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('비유한 JSON 상수')
    return json.loads(body, object_pairs_hook=pairs, parse_constant=constant)


def parse_boolean(expression):
    tokens, position = [], 0
    pattern = re.compile(r'\s*(NOT|AND|OR|XOR|IMPLIES|EQ|true|false|[A-D]|\(|\))')
    while position < len(expression):
        found = pattern.match(expression, position)
        if not found:
            raise Pending('지원된 Boolean producer 문법 아님')
        tokens.append(found.group(1)); position = found.end()
    index = 0
    def take(expected=None):
        nonlocal index
        if index >= len(tokens):
            raise Pending('Boolean 문법 미완료')
        value = tokens[index]; index += 1
        if expected is not None and value != expected:
            raise Pending('Boolean producer 괄호/연산 불일치')
        return value
    def node(depth=0):
        if depth > 8:
            raise ValueError('Boolean AST 상한 초과')
        token = take()
        if token in tuple('ABCD'):
            return token
        if token in ('true', 'false'):
            return token == 'true'
        if token == 'NOT':
            take('('); child = node(depth + 1); take(')')
            return dict(op='not', args=[child])
        if token == '(':
            left = node(depth + 1); op = take()
            if op not in ('AND', 'OR', 'XOR', 'IMPLIES', 'EQ'):
                raise Pending('지원되지 않은 Boolean 이항 연산')
            right = node(depth + 1); take(')')
            return dict(op=op.lower(), args=[left, right])
        raise Pending('Boolean producer의 정확한 식 필요')
    result = node()
    if index != len(tokens):
        raise Pending('Boolean 식 뒤의 미해석 문자')
    return result


def parse_initial(question, language):
    """전체 producer 문법만 허용하고 반드시 원래 renderer로 재확인한다."""
    if language not in LANGUAGES or not isinstance(question, str):
        raise ValueError('선언된 언어/기초질문 필요')
    ko = language == 'ko'
    patterns = dict(
        arithmetic=r'(-?\d+) ([+*-]) (-?\d+)의 값만 정수로 답하세요\.' if ko else r'Return only the integer value of (-?\d+) ([+*-]) (-?\d+)\.',
        boolean=r'변수 (\{.*\})일 때 논리식 (.*)의 값만 true 또는 false로 답하세요\.' if ko else r'Variables (\{.*\})\. Return only true or false for (.*)\.',
        lookup=r'표 (\[.*\])에서 (.+)에 해당하는 값만 쓰세요\.' if ko else r'Table (\[.*\])\. Return only the value for (.+)\.',
        format=r'기록 값은 (\d+)입니다\. 이 값만 읽어 쓰세요\.' if ko else r'The recorded value is (\d+)\. Return only that value\.')
    matched = [(family, re.fullmatch(pattern, question)) for family, pattern in patterns.items()]
    matched = [(family, value) for family, value in matched if value is not None]
    if len(matched) != 1:
        raise Pending('정확한 단일 기초 producer 문법을 복원할 수 없음')
    family, found = matched[0]
    if family == 'arithmetic':
        a, op, b = found.groups(); data = dict(family=family, a=int(a), b=int(b), op=op)
    elif family == 'boolean':
        values = strict_json(found.group(1))
        if not isinstance(values, dict) or set(values) != set('ABCD') or any(type(v) is not bool for v in values.values()):
            raise ValueError('producer의 A/B/C/D Boolean 상태 필요')
        data = dict(family=family, values=values, expression=parse_boolean(found.group(2)))
    elif family == 'lookup':
        entries, target = strict_json(found.group(1)), found.group(2)
        if not isinstance(entries, list) or len(entries) != 2 or any(not isinstance(e, list) or len(e) != 2 for e in entries):
            raise ValueError('producer의 두 행 표 필요')
        colors = ('빨강', '파랑', '초록', '노랑') if ko else ('red', 'blue', 'green', 'yellow')
        first = re.fullmatch(('가' if ko else 'A') + r'(\d+)', entries[0][0])
        second = re.fullmatch(('나' if ko else 'B') + r'(\d+)', entries[1][0])
        if (first is None or second is None or first.group(1) != second.group(1)
                or any(e[1] not in colors for e in entries) or target not in [e[0] for e in entries]):
            raise ValueError('producer의 이름/색/대상 문법 변경')
        data = dict(family=family, name_index=int(first.group(1)), color1=colors.index(entries[0][1]),
                    color2=colors.index(entries[1][1]), target=[e[0] for e in entries].index(target))
    else:
        data = dict(family=family, value=int(found.group(1)))
    return data


def parse_follow(spec, question):
    _, _, _, rules = producers()
    kind, ko, original = spec['kind'], spec['language'] == 'ko', spec['payload']
    if kind == 'verbatim_qa':
        pattern = (r'앞서 한 답변의 문자열 전체를 (answer|value|result|reply) 항목 하나에 넣은 JSON 객체만 출력하세요\. 내용을 고치거나 요약하지 마세요\.' if ko else
            r'Return only one JSON object with exactly one (answer|value|result|reply) key containing your entire previous answer string\. Do not correct or summarize its content\.')
        found = re.fullmatch(pattern, question)
        if found is None:
            raise Pending('C3의 정확한 producer key/전체문법 필요')
        return dict(literal=original['answer'], key=found.group(1))
    result = copy.deepcopy(original)
    if kind == 'integer_arithmetic':
        pattern = (r'앞의 계산에서 첫 수를 (-?\d+), 둘째 수를 (-?\d+)로 바꾸세요\. 연산과 출력 형식은 유지하고 새 답만 쓰세요\.' if ko else
            r'In the previous calculation change the first number to (-?\d+) and the second to (-?\d+)\. Keep the operation and output format; return only the new answer\.')
        found = re.fullmatch(pattern, question)
        if found is None:
            raise Pending('C1 산수 후속 producer 문법 필요')
        result.update(a=int(found.group(1)), b=int(found.group(2)))
    elif kind == 'boolean_expression':
        pattern = (r'앞의 논리식은 유지하고 변수 값을 (\{.*\})로 바꾸세요\. 같은 출력 형식으로 새 값만 답하세요\.' if ko else
            r'Keep the previous expression, change variables to (\{.*\}), and return only its new value in the same format\.')
        found = re.fullmatch(pattern, question)
        if found is None:
            raise Pending('C1 Boolean 후속 producer 문법 필요')
        values = strict_json(found.group(1))
        if not isinstance(values, dict) or set(values) != set(original['values']) or any(type(v) is not bool for v in values.values()):
            raise ValueError('C1 Boolean 상태계약 변경')
        result['values'] = values
    else:
        pattern = (r'앞 표의 값은 유지하고 행 순서를 (\[.*\])로 바꾸세요\. 이번에는 (.+)의 값만 같은 형식으로 답하세요\.' if ko else
            r"Keep the previous table values, reorder rows as (\[.*\]), and return only (.+)'s value in the same format\.")
        found = re.fullmatch(pattern, question)
        if found is None:
            raise Pending('C1 조회 후속 producer 문법 필요')
        order, target = strict_json(found.group(1)), found.group(2)
        entries = {entry[0]: entry for entry in original['entries']}
        if not isinstance(order, list) or len(order) != len(entries) or set(order) != set(entries) or target not in entries:
            raise ValueError('C1 원표 보존/순서/대상 계약 변경')
        result.update(entries=[copy.deepcopy(entries[name]) for name in order], target=target)
    if rules.condition_question(spec, result) != question:
        raise ValueError('후속 질문의 producer byte 왕복 불일치')
    return result


def literal_question(literal, key, language):
    value = json.dumps(literal, ensure_ascii=False)
    if language == 'ko':
        return f'입력 문자열: {value}\n{key} 키 하나만 있는 JSON 객체를 출력하세요. 입력 문자열 전체를 변경 없이 그 키의 문자열 값으로 넣으세요.'
    return f'Input string: {value}\nReturn one JSON object with exactly one {key} key whose string value preserves the complete input string unchanged.'


def recover_probe(row, cohort):
    legacy, small, expanded, rules = producers()
    if cohort not in COHORTS or not isinstance(row, dict):
        raise ValueError('명시적인 old/fresh 원형 필요')
    messages, meta = row.get('messages'), row.get('meta', {})
    if not isinstance(messages, list) or len(messages) != 4 or [m.get('role') for m in messages] != ['user', 'assistant', 'user', 'assistant']:
        raise ValueError('원형 U/A/U/A 네 턴 필요')
    q0, a0, q1, a1 = [text(m) for m in messages]
    language = meta.get('language'); data = parse_initial(q0, language)
    family = data['family']; root = sha(data)
    if (meta.get('root_concept_id') != root or meta.get('split') != 'val'
            or meta.get('source_license') != 'repository-code-generated' or int(root[:8], 16) % 5 != 0):
        raise ValueError('producer 중립root/VAL/권리 metadata 불일치')
    if family == 'arithmetic' and any(not 2 <= data[k] <= (19 if cohort == 'old' else 65) for k in ('a', 'b')):
        raise ValueError('기초 피연산자의 producer 범위 변경')
    if family == 'format' and not 0 <= data['value'] < (2048 if cohort == 'old' else 65536):
        raise ValueError('recorded literal producer 범위 변경')
    spec = small.spec_for(data, language, 'val') if cohort == 'old' else expanded.make_spec(data, language, 'val')
    if rules._render(spec, spec['payload']) != (q0, a0):
        raise ValueError('기초 질문/정답의 producer byte 왕복 불일치')
    current = parse_follow(spec, q1); key = current.get('key') if family == 'format' else None
    if cohort == 'old' and family != 'format':
        expected_current = copy.deepcopy(spec['payload'])
        if family == 'arithmetic':
            expected_current['a'] += 21; expected_current['b'] += 21
        elif family == 'boolean':
            expected_current['values']['A'] = not expected_current['values']['A']
        else:
            expected_current['target'] = spec['payload']['entries'][1 - data['target']][0]
        if current != expected_current:
            raise ValueError('old64의 고정 producer 상태개입 불일치')
    if family == 'format':
        if cohort == 'old' and key != 'reply':
            raise ValueError('old64 C3의 고정 reply key 변경')
        rebuilt = small.format_probe(spec, key)
        expected_gold = json.dumps({key: spec['payload']['answer']}, ensure_ascii=False, separators=(',', ':'))
        current_q = literal_question(current['literal'], key, language)
        current_contract = 'FORMAT_LITERAL_INPUT'
        neutral_current = current
    else:
        rebuilt = small.closed_row(spec, current, probe=True)
        current_q, expected_gold = rules._render(spec, current)
        current_contract = 'CODE_CURRENT_STATE'
        if family == 'lookup':
            names = [e[0] for e in spec['payload']['entries']]
            neutral_current = dict(row_order=[names.index(e[0]) for e in current['entries']], target=names.index(current['target']))
        else:
            neutral_current = current
    if a1 != expected_gold or small.text_at(rebuilt, 2) != q1:
        raise ValueError('후속 질문/정답의 producer byte 왕복 불일치')
    if cohort == 'old':
        expected_meta = dict(source='p106d_prior_diagnostic', source_family='p106d_prior_closed64',
            root_concept_id=root, language=language, split='val', source_license='repository-code-generated',
            diagnostic_reuse='known failures, not new blind generalization')
        from tinylm.chat.canonical import normalize, validate
        expected = validate(normalize(dict(messages=copy.deepcopy(messages), meta=expected_meta)))
    else:
        expected = rebuilt
    if sha(expected) != sha(row):
        raise ValueError('원형의 정확한 producer metadata/grammar 불일치')
    policy = 'FORMAT_LITERAL_WRAP' if family == 'format' else 'ANSWER_CHANGED' if a0 != a1 else 'ANSWER_UNCHANGED'
    return dict(schema=VERSION, probe_id=sha([TAG, cohort, language, root]), cohort=cohort,
        language=language, family=family, neutral_root_id=root, neutral_definition=data,
        neutral_current=neutral_current, answer_change_policy=policy,
        source_row_sha256=sha(row), source_meta_sha256=sha(meta), source_row=copy.deepcopy(row),
        recovery_path='OLD_PRIOR_EXACT_GRAMMAR' if cohort == 'old' else 'FRESH_PRODUCER_METADATA_AND_GRAMMAR',
        original_source_sha256=meta.get('source_sha256'), initial_payload=copy.deepcopy(spec['payload']),
        current_payload=current, initial_question=q0, initial_gold=a0, follow_question=q1, follow_gold=a1,
        current_question=current_q, current_contract=current_contract, format_key=key,
        followup_kind='C3_VERBATIM_FORMAT' if family == 'format' else 'C1_CONDITION_UPDATE')


def validate_probes(probes):
    if len(probes) != 128:
        raise Pending('old64+fresh64 전량128 probe 필요')
    seen, neutral = set(), defaultdict(dict)
    for probe in probes:
        if probe.get('probe_id') in seen:
            raise ValueError('중복 probe')
        seen.add(probe.get('probe_id'))
        if sha(recover_probe(probe['source_row'], probe['cohort'])) != sha(probe):
            raise ValueError('복원 상태/질문/정답 변조')
        key = (probe['cohort'], probe['neutral_root_id'])
        if probe['language'] in neutral[key]:
            raise ValueError('중립root 언어 중복')
        neutral[key][probe['language']] = probe
    for cohort in COHORTS:
        for family in FAMILIES:
            for language in LANGUAGES:
                if sum(p['cohort'] == cohort and p['family'] == family and p['language'] == language for p in probes) != 8:
                    raise ValueError('cohort/family/language 각8개 고정 분모 변경')
    for languages in neutral.values():
        if set(languages) != set(LANGUAGES):
            raise ValueError('중립root의 한영쌍 필요')
        a, b = languages['ko'], languages['en']
        if a['neutral_definition'] != b['neutral_definition'] or a['neutral_current'] != b['neutral_current']:
            raise ValueError('한영 중립상태/조건 변경')
    old = {p['neutral_root_id'] for p in probes if p['cohort'] == 'old'}
    fresh = {p['neutral_root_id'] for p in probes if p['cohort'] == 'fresh'}
    if old & fresh or len(old) != 32 or len(fresh) != 32:
        raise ValueError('old/fresh32중립root 분리 위반')


def make_cases(probes):
    validate_probes(probes)
    cases, compact = [], []
    for probe in sorted(probes, key=lambda p: (COHORTS.index(p['cohort']), p['neutral_root_id'], p['language'])):
        for condition in CONDITIONS:
            if condition == 'INITIAL_DIRECT':
                messages, target = probe['source_row']['messages'][:1], probe['initial_gold']
            elif condition == 'CURRENT_DIRECT':
                messages, target = canonical([dict(role='user', content=probe['current_question'])]), probe['follow_gold']
            elif condition == 'GOLD_HISTORY':
                messages, target = probe['source_row']['messages'][:3], probe['follow_gold']
            else:
                messages, target = None, None if probe['family'] == 'format' else probe['follow_gold']
            cases.append(dict(schema=VERSION, tag=TAG, case_id=sha([TAG, probe['probe_id'], condition]),
                probe_id=probe['probe_id'], cohort=probe['cohort'], family=probe['family'], language=probe['language'],
                neutral_root_id=probe['neutral_root_id'], source_row_sha256=probe['source_row_sha256'],
                answer_change_policy=probe['answer_change_policy'], condition=condition,
                messages=copy.deepcopy(messages), target=target,
                requires_initial_event=condition == 'ACTUAL_HISTORY',
                truth_scope='FORMAT_LITERAL_INPUT' if condition == 'CURRENT_DIRECT' and probe['family'] == 'format' else 'CLOSED_CODE_CONTRACT',
                new_independent_root=False))
        if probe['family'] == 'arithmetic':
            p = probe['initial_payload']; condition = 'MATH_COMPACT_INITIAL'
            compact.append(dict(schema=VERSION, tag=TAG, case_id=sha([TAG, probe['probe_id'], condition]),
                probe_id=probe['probe_id'], cohort=probe['cohort'], family='arithmetic', language=probe['language'],
                neutral_root_id=probe['neutral_root_id'], source_row_sha256=probe['source_row_sha256'],
                answer_change_policy=probe['answer_change_policy'], condition=condition,
                messages=canonical([dict(role='user', content=f"{p['a']}{p['op']}{p['b']}=?")]),
                target=probe['initial_gold'], requires_initial_event=False, truth_scope='COMPACT_INITIAL_DEVELOPMENT',
                new_independent_root=False))
    cases.extend(compact)
    for index, (question, target) in enumerate(MINIMAL_QUESTIONS):
        cases.append(dict(schema=VERSION, tag=TAG, case_id=sha([TAG, 'MINIMAL_KO', index]), probe_id=None,
            cohort='minimal_development', family='arithmetic', language='ko', neutral_root_id=None,
            source_row_sha256=None, answer_change_policy='NOT_APPLICABLE', condition='MINIMAL_KO',
            messages=canonical([dict(role='user', content=question)]), target=target,
            requires_initial_event=False, truth_scope='DEVELOPMENT_PROMPT_NOT_USER_ORIGINAL_WORDING', new_independent_root=False))
    if (len(cases) != EXPECTED or len({c['case_id'] for c in cases}) != EXPECTED
            or Counter(c['language'] for c in cases) != {'ko': 274, 'en': 272}
            or Counter(c['condition'] for c in cases) != dict.fromkeys(CONDITIONS, 128) | {'MATH_COMPACT_INITIAL': 32, 'MINIMAL_KO': 2}):
        raise ValueError('546 case/한영/조건 분모 변경')
    return cases


def encoding(messages, target, tokenizer):
    if getattr(tokenizer, 'truncation', None) is not None or getattr(tokenizer, 'padding', None) is not None:
        raise ValueError('자동 토크나이저 자르기/패딩 금지')
    serialized = common.prompt(messages); ids = list(tokenizer.encode(serialized).ids)
    eot = tokenizer.token_to_id('<|im_end|>')
    if type(eot) is not int or tokenizer.encode('<|im_end|>', add_special_tokens=False).ids != [eot] or not ids:
        raise ValueError('전체 generation prefix와 원자적 EOT 필요')
    count = None if target is None else len(tokenizer.encode(target + '<|im_end|>', add_special_tokens=False).ids)
    return dict(prompt_sha256=sha(serialized), prompt_ids_sha256=sha(ids), prompt_tokens=len(ids),
        stop_token_sequences=[[eot]], context_limit=CONTEXT, max_new=MAX_NEW,
        canonical_target_tokens_with_eot=count, canonical_target_fits_budget=None if count is None else count <= MAX_NEW,
        canonical_reference_basis='standalone canonical reference+EOT without automatic special tokens; not minimum over equivalent JSON',
        final_target_appended_to_generation_prefix=False,
        prior_assistant_turn_present=any(m['role'] == 'assistant' for m in messages))


class DecodeObserver:
    """원 tokenizer 호출/반환값을 변경하지 않는 최종 decode 관찰자."""
    def __init__(self, tokenizer):
        self.tokenizer, self.calls = tokenizer, []

    def __getattr__(self, name):
        return getattr(self.tokenizer, name)

    def reset(self):
        self.calls = []

    def decode(self, ids, *args, **kwargs):
        output = self.tokenizer.decode(ids, *args, **kwargs)
        self.calls.append(dict(ids=list(ids), args=list(args), kwargs=copy.deepcopy(kwargs), output=output))
        return output


class DecodeObservationError(ValueError):
    def __init__(self, reason, evidence):
        super().__init__(reason)
        self.evidence = evidence


def observe_helper(emit, observer, messages):
    observer.reset(); result = emit(messages)
    evidence = dict(decode_calls=copy.deepcopy(observer.calls), helper_return_type=type(result).__name__,
        original_helper_answer=result[0] if isinstance(result, (tuple, list)) and len(result) == 2 and isinstance(result[0], str) else None,
        original_helper_generation=copy.deepcopy(result[1]) if isinstance(result, (tuple, list)) and len(result) == 2 and isinstance(result[1], dict) else None)
    try:
        if not isinstance(result, tuple) or len(result) != 2:
            raise ValueError('기존 helper의 원래 두 반환값 누락/형상 변경')
        body, observation = observed_emission(messages, result[0], result[1], observer.calls, observer.tokenizer)
    except Exception as exc:
        raise DecodeObservationError(str(exc), evidence) from exc
    return body, result[1], observation


def observed_emission(messages, helper_answer, generation, calls, tokenizer):
    """종료ID만 제외한다. helper 원답과 차이가 다른 내용이면 추정 복구하지 않는다."""
    if not isinstance(helper_answer, str) or not isinstance(generation, dict) or len(calls) != 2:
        raise ValueError('기존 sample full-decode/prefix-decode 두 관찰과 원래 반환값 필요')
    common.validate_generation(helper_answer, generation, dict(encoding=encoding(messages, None, tokenizer)))
    full, prefix = copy.deepcopy(calls)
    for call in (full, prefix):
        if (set(call) != {'ids', 'args', 'kwargs', 'output'} or call['args'] != [] or call['kwargs'] != {}
                or not isinstance(call['output'], str) or not isinstance(call['ids'], list)
                or any(type(i) is not int or i < 0 for i in call['ids'])
                or tokenizer.decode(call['ids']) != call['output']):
            raise ValueError('원 decoder 관찰의 호출/IDS/원문 변경')
    expected_prefix = list(tokenizer.encode(common.prompt(messages)).ids)
    if prefix['ids'] != expected_prefix or full['ids'][:len(expected_prefix)] != expected_prefix:
        raise ValueError('실제 final fullIDS와 generation prefixIDS 불일치')
    eos = tokenizer.token_to_id('<eos>')
    if type(eos) is not int or eos < 0 or eos == tokenizer.token_to_id('<|im_end|>'):
        raise ValueError('원 receipt의 EOS 가능성과 실제 tokenizer 종료ID 불일치')
    generated = full['ids'][len(expected_prefix):]
    if (type(generation.get('generated_tokens')) is not int or len(generated) != generation['generated_tokens']
            or not 1 <= len(generated) <= MAX_NEW or not full['output'].startswith(prefix['output'])):
        raise ValueError('실제 continuation IDS 길이와 원 meta 불일치')
    if full['output'][len(prefix['output']):].split('<|im_end|>', 1)[0] != helper_answer:
        raise ValueError('관찰한 원 helper extraction과 원래 answer 반환 불일치')
    reason, terminal = generation.get('finish_reason'), []
    if reason == 'STOP_SEQUENCE':
        eot = tokenizer.token_to_id('<|im_end|>')
        if (generation.get('matched_stop_sequence') != [eot] or generation.get('stop_token_sequences') != [[eot]]
                or generated[-1:] != [eot]):
            raise ValueError('실제 마지막 EOT와 stop receipt 불일치')
        terminal = [eot]
    elif reason == 'EOS':
        if (generated[-1] != eos
                or generation.get('matched_stop_sequence') is not None):
            raise ValueError('실제 마지막 EOS와 finish receipt 불일치')
        terminal = [eos]
    elif reason != 'MAX_NEW':
        raise ValueError('지원된 EOT/EOS/MAX_NEW 종료만 관찰 가능')
    content_ids = generated[:-len(terminal)] if terminal else generated
    known_terminal_ids = {tokenizer.token_to_id('<|im_end|>'), tokenizer.token_to_id('<eos>')}
    if any(token in known_terminal_ids for token in content_ids):
        raise ValueError('즉시정지 sampler와 맞지 않는 본문 중간의 실제 EOT/EOS ID')
    body = tokenizer.decode(content_ids, skip_special_tokens=False)
    terminal_text = tokenizer.decode(terminal, skip_special_tokens=False) if terminal else ''
    if helper_answer == body:
        relation = 'HELPER_ALREADY_BODY'
    elif terminal and helper_answer == body + terminal_text:
        relation = 'HELPER_RETAINS_AUTHENTICATED_TERMINAL'
    else:
        raise ValueError('helper와 visible body 차이가 인증된 마지막 종료경계만이 아님')
    observation = dict(schema='P106D_OBSERVED_TERMINAL_IDS_V1', decode_calls=[full, prefix],
        full_ids=full['ids'], full_ids_sha256=sha(full['ids']), prefix_ids_sha256=sha(prefix['ids']),
        generated_ids=generated, generated_ids_sha256=sha(generated), generated_tokens=len(generated),
        content_ids_sha256=sha(content_ids), content_tokens=len(content_ids), terminal_ids=terminal,
        terminal_text=terminal_text, terminal_removed_from_continuation_ids=bool(terminal),
        original_helper_answer=helper_answer, original_helper_answer_sha256=sha(helper_answer),
        original_helper_generation_sha256=sha(generation), message_content_sha256=sha(body),
        helper_to_visible_relation=relation, finish_reason=reason,
        whitespace_json_and_middle_tokens_not_corrected=True)
    return body, observation


def validate_observation(case, answer, generation, observation, tokenizer):
    if not isinstance(observation, dict) or tokenizer is None:
        raise ValueError('실제 decode/IDS 관찰 누락')
    helper_answer = observation.get('original_helper_answer')
    common.validate_generation(helper_answer, generation, case)
    body, rebuilt = observed_emission(case['messages'], helper_answer, generation,
                                     observation.get('decode_calls', []), tokenizer)
    if body != answer or sha(observation) != sha(rebuilt):
        raise ValueError('visible body/원답/원 meta/IDS SHA 관찰 변경')


def encode_static_cases(cases, tokenizer):
    result = []
    for case in cases:
        proof = None if case['requires_initial_event'] else encoding(case['messages'], case['target'], tokenizer)
        if proof is not None and (proof['prompt_tokens'] + MAX_NEW > CONTEXT or not proof['canonical_target_fits_budget']):
            raise Pending('정적 전체 prefix/출력128 계약 부족: ' + case['case_id'])
        result.append(dict(case, encoding=proof, actual_history_template_only=case['requires_initial_event']))
    return result


def strict_format(answer, key, actual_string):
    try:
        value = strict_json(answer)
    except (ValueError, TypeError):
        return False
    return isinstance(value, dict) and set(value) == {key} and type(value[key]) is str and value[key] == actual_string


def classify_metrics(case, probe, answer, target, initial=None):
    legacy, _, _, _ = producers()
    fixed = None if case['condition'] == 'ACTUAL_HISTORY' and probe['family'] == 'format' else bool(legacy.classify(answer, target))
    wrapped = None
    if probe is not None and probe['family'] == 'format' and case['condition'] in ('CURRENT_DIRECT', 'GOLD_HISTORY', 'ACTUAL_HISTORY'):
        literal = initial['answer'] if case['condition'] == 'ACTUAL_HISTORY' else probe['current_payload']['literal']
        wrapped = strict_format(answer, probe['format_key'], literal)
    passed = wrapped if fixed is None else fixed
    return dict(condition_pass=passed, fixed_gold_classify_pass=fixed, strict_c3_format_preserved=wrapped,
        first_fact_correct=bool(legacy.classify(answer, target)) if case['condition'] == 'INITIAL_DIRECT' else None,
        format_success_is_not_fact_recovery=probe is not None and probe['family'] == 'format',
        current_direct_is_literal_input=case['truth_scope'] == 'FORMAT_LITERAL_INPUT')


def initial_reference(case, probe, initial, identity, endpoint, input_sha, tokenizer):
    expected_id = sha([TAG, probe['probe_id'], 'INITIAL_DIRECT'])
    if (not isinstance(initial, dict) or initial.get('case_id') != expected_id
            or initial.get('probe_id') != probe['probe_id'] or initial.get('condition') != 'INITIAL_DIRECT'
            or initial.get('record_status') != GENERATED or initial.get('endpoint') != endpoint
            or initial.get('checkpoint_sha256') != identity['checkpoint_sha256']
            or initial.get('initial_core_sha256') != identity['initial_core_sha256']
            or initial.get('input_report_sha256') != input_sha
            or initial.get('source_row_sha256') != probe['source_row_sha256']
            or not isinstance(initial.get('answer'), str)):
        raise ValueError('같은 CP/probe의 실제 INITIAL_DIRECT 원답만 재사용 가능')
    validate_observation(initial, initial['answer'], initial['generation'], initial.get('decode_observation'), tokenizer)
    if initial.get('original_helper_answer') != initial['decode_observation']['original_helper_answer']:
        raise ValueError('INITIAL event의 원 helper 원답/관찰 내부 불일치')
    return dict(initial_event_sha256=sha(initial), initial_case_id=expected_id,
        initial_message_content_json_sha256=sha(initial['answer']),
        initial_message_content_utf8_sha256=hashlib.sha256(initial['answer'].encode('utf-8')).hexdigest().upper(),
        initial_original_helper_answer_sha256=sha(initial['original_helper_answer']),
        initial_full_ids_sha256=initial['decode_observation']['full_ids_sha256'],
        initial_content_reused_without_strip_or_correction=True)


def materialize(case, probe, tokenizer, initial, identity, endpoint, input_sha):
    messages, target, reference, status = case['messages'], case['target'], None, None
    rejection_reasons = []
    if case['condition'] == 'ACTUAL_HISTORY':
        reference = initial_reference(case, probe, initial, identity, endpoint, input_sha, tokenizer)
        raw = initial['answer']
        messages = canonical([probe['source_row']['messages'][0], dict(role='assistant', content=raw), probe['source_row']['messages'][2]])
        target = json.dumps({probe['format_key']: raw}, ensure_ascii=False, separators=(',', ':')) if probe['family'] == 'format' else probe['follow_gold']
        if any(marker in raw for marker in chatml_control_markers()):
            status = UNSAFE; rejection_reasons.append('CHATML_CONTROL_STRING')
    proof = encoding(messages, target, tokenizer)
    if proof['prompt_tokens'] + MAX_NEW > CONTEXT:
        if case['condition'] != 'ACTUAL_HISTORY':
            raise ValueError('동결 정적 prefix가 runtime 상한을 넘음')
        status = status or OVERFLOW; rejection_reasons.append('FULL_PROMPT_PLUS128_EXCEEDS1024')
    if case['condition'] != 'ACTUAL_HISTORY' and proof != case['encoding']:
        raise ValueError('runtime 토크나이저/prefix가 CPU 동결과 다름')
    return dict(case, messages=messages, target=target, encoding=proof,
                frozen_case_sha256=sha(case), actual_history_template_only=False,
                actual_history_runtime_materialized=case['condition'] == 'ACTUAL_HISTORY',
                initial_event_reference=reference, record_status=status or GENERATED,
                input_rejection_reasons=rejection_reasons)


def finish_event(materialized, probe, endpoint, identity, input_sha, answer=None, generation=None, initial=None,
                 decode_observation=None, tokenizer=None):
    result = dict(materialized, endpoint=endpoint, checkpoint_sha256=identity['checkpoint_sha256'],
        initial_core_sha256=identity['initial_core_sha256'], input_report_sha256=input_sha,
        generation_protocol=PROTOCOL)
    if materialized['record_status'] == GENERATED:
        validate_observation(materialized, answer, generation, decode_observation, tokenizer)
        result.update(answer=answer, generation=generation,
            original_helper_answer=decode_observation['original_helper_answer'], decode_observation=decode_observation,
            metrics=classify_metrics(materialized, probe, answer, materialized['target'], initial))
    elif answer is not None or generation is not None or decode_observation is not None:
        raise ValueError('미실행을 빈답/생성receipt로 꾸미지 않음')
    return result


def collect(cases, probes, tokenizer, endpoint, identity, input_sha, emit, append, guard):
    lookup = {p['probe_id']: p for p in probes}; initials = {}; values = []
    for case in cases:
        guard(); probe = lookup.get(case['probe_id']); initial = initials.get(case['probe_id'])
        actual = materialize(case, probe, tokenizer, initial, identity, endpoint, input_sha)
        if actual['record_status'] == GENERATED:
            try:
                answer, generation, observation = emit(actual['messages'])
            except DecodeObservationError as exc:
                append(dict(actual, endpoint=endpoint, checkpoint_sha256=identity['checkpoint_sha256'],
                    initial_core_sha256=identity['initial_core_sha256'], input_report_sha256=input_sha,
                    record_status='TOOL_ERROR_DECODE_OBSERVATION', protocol_error=copy.deepcopy(exc.evidence),
                    tool_error=str(exc), model_quality_failure=False))
                raise
            event = finish_event(actual, probe, endpoint, identity, input_sha, answer, generation, initial, observation, tokenizer)
        else:
            event = finish_event(actual, probe, endpoint, identity, input_sha)
        append(event); values.append(event)
        if case['condition'] == 'INITIAL_DIRECT':
            if case['probe_id'] in initials:
                raise ValueError('INITIAL_DIRECT 중복 생성')
            initials[case['probe_id']] = event
    return values


def verify_legacy_records(records, probes, label):
    legacy, _, _, _ = producers()
    expected = {(p['neutral_root_id'], p['language']): p for p in probes}
    if len(records) != 128:
        raise Pending('기존 저장128답의 전량 완결이 선결')
    seen, passed = set(), 0
    for record in records:
        key = (record.get('root'), record.get('language'))
        if key in seen or key not in expected:
            raise ValueError('기존 저장답의 중복/다른 root')
        seen.add(key); probe = expected[key]
        if (record.get('label') != label or record.get('gold') != probe['follow_gold']
                or record.get('prompt') != common.prompt(probe['source_row']['messages'][:3])
                or not isinstance(record.get('answer'), str) or not isinstance(record.get('raw_decoded'), str)):
            raise ValueError('기존 gold-history prompt/원답/gold/label 변경')
        correct = bool(legacy.classify(record['answer'], record['gold']))
        meta = record.get('generation', {})
        if (type(record.get('closed_code_contract_pass')) is not bool
                or record['closed_code_contract_pass'] != correct
                or type(meta.get('generated_tokens')) is not int or not 1 <= meta['generated_tokens'] <= 64
                or meta.get('max_new') != 64 or not isinstance(meta.get('finish_reason'), str)):
            raise ValueError('기존 저장답의 closed metric/종료/길이 변경')
        passed += int(correct)
    if seen != set(expected):
        raise Pending('기존 source probe128과 저장답 미대응')
    return dict(questions=128, legacy_gold_history_pass=passed,
        legacy_max_new=64, precision_scope='legacy direct sampler, not explicit FP32_MATH wrapper',
        new_fp32_answer_equality_is_not_a_cache_gate=True)


def read_source():
    """총괄 prepare/검산 전용. source/HF 원형을 수정하거나 재생성하지 않는다."""
    legacy, _, expanded, _ = producers()
    files = {}
    def bind(path, expected=None):
        actual = digest(path)
        if expected is not None and actual != expected:
            raise ValueError('고정 source byteSHA 변경: ' + str(Path(path).relative_to(ROOT)))
        files[str(Path(path).relative_to(ROOT))] = actual
        return actual
    bind(AUDIT, AUDIT_SHA); audit = required(AUDIT)
    if audit.get('근거', {}).get('report_sha256') != SOURCE_REPORT_SHAS:
        raise ValueError('기존 읽기전용 근거 보고의 source 지문 변경')
    reports = {}
    for name, identity in SOURCE_REPORT_SHAS.items():
        path = SOURCE_EVIDENCE / name / 'report.json'; bind(path, identity); reports[name] = required(path)
    prepared = reports['prepare']
    if (prepared.get('schema') != expanded.VERSION or prepared.get('status') != 'CORPUS_READY'
            or prepared.get('ready') is not True or prepared.get('train_rows') != 4096
            or prepared.get('val_rows') != 64 or prepared.get('seed') != 1337
            or prepared.get('tokenizer_sha256') != TOK_SHA):
        raise Pending('완료된 v3 corpus4096/새probe64/seed1337 필요')
    corpus_sha = bind(SOURCE_CORPUS / 'report.json'); corpus = required(SOURCE_CORPUS / 'report.json')
    if sha(corpus) != sha(prepared):
        raise ValueError('기존 public/local corpus 보고의 wire내용 불일치')
    code = prepared.get('input', {}).get('code_sha256', {})
    if set(code) != set(legacy.CODE):
        raise ValueError('기존11 CODE 지문 집합 변경')
    for path, identity in code.items():
        bind(ROOT / path, identity)
    probes = []
    for cohort, stem in (('old', 'prior_probes'), ('fresh', 'val_probes')):
        path = SOURCE_CORPUS / (stem + '_shards_manifest.json'); bind(path); manifest = required(path)
        if manifest != prepared.get('shards', {}).get(stem):
            raise ValueError('기존64probe manifest 계보 변경')
        rows = common.read_shards(SOURCE_CORPUS, manifest, stem)
        if len(rows) != 64:
            raise Pending('old/fresh 각각64행 필요')
        for shard in manifest['shards']:
            bind(SOURCE_CORPUS / shard['path'], shard['sha256'])
        probes.extend(recover_probe(row, cohort) for row in rows)
    validate_probes(probes)
    train_roots = set(prepared.get('roots', {}).get('train', []))
    fresh_roots = set(prepared.get('roots', {}).get('val', []))
    if (len(train_roots) != 2048 or fresh_roots != {p['neutral_root_id'] for p in probes if p['cohort'] == 'fresh'}
            or train_roots & {p['neutral_root_id'] for p in probes}):
        raise ValueError('기존 TRAIN/old/fresh 중립root 격리 변경')
    identities = dict(parent=dict(checkpoint=str(PARENT.relative_to(ROOT)), checkpoint_sha256=PARENT_SHA))
    historical, raw = {}, {}
    for endpoint in ('fixed', 'views'):
        report = reports[endpoint]
        expected_path = 'runs/ckpt/m100s10_ko-en_300M_dense_chat32_' + SOURCE_TAG + '_' + endpoint + '.pt'
        if (report.get('status') != 'STUDENT_GATE_COMPLETE' or report.get('schema') != legacy.SCHEMA
                or report.get('arm') != endpoint or report.get('updates') != 128
                or report.get('data_report_sha256') != corpus_sha or report.get('checkpoint') != expected_path
                or not common.hex_sha(report.get('checkpoint_sha256'))
                or report.get('processed_tokens') != prepared['four_epoch_processed_tokens']
                or report.get('assistant_targets') != 4 * prepared['epoch_assistant_targets']
                or report.get('input', {}).get('code_sha256') != code
                or report.get('input', {}).get('parent_sha256') != PARENT_SHA
                or report.get('input', {}).get('tokenizer_sha256') != TOK_SHA):
            raise ValueError('기존 학생128/source/CP/exposure 계보 변경')
        identities[endpoint] = dict(checkpoint=expected_path, checkpoint_sha256=report['checkpoint_sha256'])
        for label, descriptor in (('parent', 'parent_answers'), ('child', 'child_answers')):
            spec = report[descriptor]; manifest = spec['shards']; stem = 'answers_' + label
            directory = SOURCE_EVIDENCE / endpoint
            path = directory / (stem + '_shards_manifest.json'); bind(path)
            if required(path) != manifest:
                raise ValueError('기존 원답 manifest 불일치')
            events = common.read_shards(directory, manifest, stem)
            for shard in manifest['shards']:
                bind(directory / shard['path'], shard['sha256'])
            counted = verify_legacy_records(events, probes, label)
            if spec.get('questions') != 128 or spec.get('first_answer_pass') != counted['legacy_gold_history_pass']:
                raise ValueError('기존 저장128답의 분모/점수 불일치')
            key = endpoint + '_' + label; historical[key] = counted; raw[key] = events
    if (reports['readback'].get('status') != 'PAIR_READBACK_COMPLETE'
            or sha(reports['readback'].get('arms')) != sha([reports['fixed'], reports['views']])):
        raise ValueError('기존 두팔 판독 계보 변경')
    source = dict(audit_sha256=AUDIT_SHA, report_sha256=SOURCE_REPORT_SHAS, corpus_report_sha256=corpus_sha,
        immutable_files=files, endpoints=identities, historical_gold_history=historical,
        probe_rows=128, neutral_roots=64, probes_sha256=sha(probes),
        old_and_fresh_recovery_paths_separate=True, source_teacher_packet_accessed=False)
    return source, probes, raw


def state_fingerprint(state_or_model):
    from scripts.diag_p101a_sft_mtp import state_fingerprint as original
    if isinstance(state_or_model, dict):
        return original(SimpleNamespace(state_dict=lambda: state_or_model))
    return original(state_or_model)


def inspect_checkpoints(source, guard):
    """총괄 CPU prepare만 호출:3 CP를 순서대로 읽고 NN Module은 만들지 않는다."""
    import torch
    import resource
    from tinylm.infer.generate import _strip
    from tinylm.config import TMTConfig
    if torch.cuda.is_initialized():
        raise ValueError('CPU tensor 지문 준비에서 CUDA가 초기화됨')
    receipts = {}
    for number, endpoint in enumerate(ENDPOINTS, 1):
        guard(); identity = source['endpoints'][endpoint]; path = safe(ROOT / identity['checkpoint'])
        before = digest(path)
        if before != identity['checkpoint_sha256']:
            raise ValueError('CPU checkpoint 검사 직전 byteSHA 변경')
        print('[HISTORY_CPU_CHECKPOINT_LOAD] ' + json.dumps(dict(endpoint=endpoint, attempt=number, map_location='cpu', weights_only=True)), flush=True)
        began = time.perf_counter(); payload = torch.load(path, map_location='cpu', weights_only=True)
        if not isinstance(payload, dict) or not isinstance(payload.get('cfg'), dict) or not isinstance(payload.get('model'), dict):
            raise ValueError('명시 cfg/model tensor checkpoint 필요')
        state = _strip(payload['model'])
        if not state or any(not isinstance(value, torch.Tensor) or value.device.type != 'cpu' for value in state.values()):
            raise ValueError('CPU state tensor만 허용')
        cfg = TMTConfig(**payload['cfg'])
        if cfg.n_layers != 14 or cfg.tie_mlp or cfg.vocab_size != 32768 or cfg.max_seq_len < CONTEXT:
            raise ValueError('원본 dense14/chat32 또는 driver의1024입력예산 지원과 다름')
        if endpoint != 'parent' and (payload.get('step') != 128 or payload.get('epoch') != 4
                or payload.get('source_parent_sha256') != PARENT_SHA
                or payload.get('data_report_sha256') != source['corpus_report_sha256']
                or payload.get('tokenizer_sha256') != TOK_SHA):
            raise ValueError('학생 weight-only checkpoint의 데이터/부모/step 계보 변경')
        if endpoint == 'parent' and payload.get('step') != 2289:
            raise ValueError('완료 원P090B 부모 step2289 필요')
        effective = json.loads(json.dumps(asdict(cfg), ensure_ascii=False, allow_nan=False))
        receipt = dict(identity, initial_core_sha256=state_fingerprint(state), effective_cfg=effective,
            checkpoint_cfg_sha256=sha(payload['cfg']), effective_cfg_sha256=sha(effective),
            state_tensor_entries=len(state), state_tensor_bytes=sum(v.numel() * v.element_size() for v in state.values()),
            torch_load_calls=1, cpu_checkpoint_tensor_read=True, nn_modules_constructed=0,
            optimizers_created=0, checkpoints_written=0, map_location='cpu', weights_only=True,
            checkpoint_file_bytes=path.stat().st_size, torch_cpu_threads=torch.get_num_threads(),
            process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            rss_scope='process high-water RSS includes imports/source/tokenizer; not model-only allocation',
            seconds=time.perf_counter() - began, checkpoint_byte_sha256_before=before,
            fingerprint_definition='scripts.diag_p101a_sft_mtp.state_fingerprint: sorted persistent state_dict name/shape/dtype/uint8bytes; excludes exactly mtp_up2/mtp_up3/mtp_up4',
            transient_cache_policy='state_dict에 없는 runtime/nonpersistent cache는 포함되지 않음; 추가 임의필터0')
        after = digest(path)
        if after != before or torch.cuda.is_initialized():
            raise ValueError('CPU tensor 검사 중 CP 변경/CUDA 초기화')
        receipt.update(checkpoint_byte_sha256_after=after, cuda_initialized=False)
        write(CORPUS / ('checkpoint_' + endpoint + '.json'), receipt); receipts[endpoint] = receipt
        del state, payload, cfg
        gc.collect(); guard()
    return receipts


def syntax_info():
    return dict(schema=VERSION, tag=TAG, conditions=list(CONDITIONS), endpoints=list(ENDPOINTS),
        expected_cases_per_endpoint=EXPECTED, base_probes=128, neutral_source_roots=64,
        compact_initial_cases=32, minimal_korean_cases=2, expected_language_cases=dict(ko=274, en=272),
        protocol=PROTOCOL, optimizer_updates=0, checkpoints_written=0, teacher_calls=0,
        active_limit_seconds=ACTIVE_LIMIT, slots=SLOTS, record_reserve_seconds=RECORD_RESERVE,
        wrapper_regression_preflight_and_queue_wait_excluded=True, authority_end_utc=END.isoformat(),
        actual_history_cpu_contract='template only; runtime same-CP INITIAL event/helper/fullIDS/visible-body/fullprefix bound',
        unsafe_payload_policy='exact8 current SPECS[chatml] start/end/think/call/result; not semantic-error blacklist',
        canonical_reference_budget_is_not_universal_impossibility=True,
        automatic_adoption=False, intelligence='NOT_ESTABLISHED')


def info():
    legacy, _, _, _ = producers()
    paths = set(OWN_CODE) | set(legacy.CODE) | set(common.info()['code_sha256'])
    paths.update(('scripts/diag_p101a_sft_mtp.py', 'tinylm/config.py', 'tinylm/chat/canonical.py'))
    return dict(syntax_info(), code_sha256={path: digest(ROOT / path) for path in sorted(paths)},
        source_report_sha256=SOURCE_REPORT_SHAS, source_audit_sha256=AUDIT_SHA, tokenizer_sha256=TOK_SHA)


def stdout_selection(probes):
    selected = []
    for cohort in COHORTS:
        for family in FAMILIES:
            for language in LANGUAGES:
                rows = [p for p in probes if p['cohort'] == cohort and p['family'] == family and p['language'] == language]
                chosen = min(rows, key=lambda p: sha([TAG, 'STDOUT', p['source_row_sha256']]))
                selected.append(chosen['probe_id'])
    return dict(probe_ids=selected, selection_sha256=sha(selected), outcome_based_selection=False)


def public_cpu(report):
    return dict(info(), status='CPU_HISTORY_PREPARED_NO_INFERENCE',
        corpus_report_sha256=digest(CORPUS / 'report.json'), source=report['source'],
        checkpoints=report['checkpoints'], manifest_sha256=report['manifest_sha256'],
        cases_sha256=report['cases_sha256'], stdout_selection=report['stdout_selection'],
        static_generation_prefixes=418, actual_history_templates=128,
        actual_cpu_checkpoint_tensor_load_calls=3, nn_modules_constructed=0, gpu_initialized=False,
        inference_answers_generated=0)


def prepare(guard):
    if safe(CORPUS).exists() or safe(EVIDENCE / 'cpu_contract.json').exists():
        raise FileExistsError('완료/부분 CPU 원형 보존')
    source, probes, old_answers = read_source(); guard()
    from tokenizers import Tokenizer
    if digest(TOKENIZER) != TOK_SHA:
        raise ValueError('토크나이저 byteSHA 변경')
    tok = Tokenizer.from_file(str(TOKENIZER))
    for records in old_answers.values():
        for row in records:
            prefix = tok.decode(tok.encode(row['prompt']).ids)
            if not row['raw_decoded'].startswith(prefix) or row['raw_decoded'][len(prefix):].split('<|im_end|>', 1)[0] != row['answer']:
                raise ValueError('기존 실제 decoder prefix/원답 추출 왕복 불일치')
    cases = encode_static_cases(make_cases(probes), tok); guard()
    safe(CORPUS).mkdir(parents=True, exist_ok=False)
    checkpoints = inspect_checkpoints(source, guard)
    manifests, manifest_shas = {}, {}
    lineage = dict(tag=TAG, purpose='EVALUATION_ONLY_NO_TRAINING', code_sha256=info()['code_sha256'], source=source)
    for stem, values in (('probes', probes), ('cases', cases)):
        writer = ShardWriter(CORPUS, stem, limit=19_999_999)
        for value in values:
            writer.append(value)
        manifests[stem] = writer.close(lineage=lineage)
        manifest_shas[stem] = digest(CORPUS / (stem + '_shards_manifest.json'))
    result = dict(info(), status='CPU_HISTORY_PREPARED_NO_INFERENCE', source=source,
        checkpoints=checkpoints, manifests=manifests, manifest_sha256=manifest_shas,
        cases_sha256=sha(cases), probes_sha256=sha(probes), stdout_selection=stdout_selection(probes),
        cpu_checkpoint_tensor_load_calls=3, nn_modules_constructed=0, gpu_initialized=False,
        model_inference_run=False, optimizer_created=False)
    guard(); write(CORPUS / 'report.json', result); write(EVIDENCE / 'cpu_contract.json', public_cpu(result))
    print('[HISTORY_CPU] 128probe/546case; 418정적prefix/128실제이력template; CPU CP tensor3회, 모델추론0', flush=True)
    return 0


def read_prepared():
    report = required(CORPUS / 'report.json')
    if report.get('status') != 'CPU_HISTORY_PREPARED_NO_INFERENCE':
        raise Pending('완료 CPU 준비가 선결')
    if any(report.get(k) != v for k, v in info().items()):
        raise ValueError('동결 code/계약 변경')
    source, original_probes, _ = read_source()
    if report.get('source') != source or digest(TOKENIZER) != TOK_SHA:
        raise ValueError('동결 source/토크나이저 변경')
    values = {}
    expected_lineage = dict(tag=TAG, purpose='EVALUATION_ONLY_NO_TRAINING', code_sha256=info()['code_sha256'], source=source)
    for stem in ('probes', 'cases'):
        path = CORPUS / (stem + '_shards_manifest.json')
        if digest(path) != report.get('manifest_sha256', {}).get(stem):
            raise ValueError('CPU manifest 지문 변경')
        manifest = required(path)
        if manifest != report['manifests'][stem] or manifest.get('lineage') != expected_lineage:
            raise ValueError('CPU manifest source 계보 변경')
        values[stem] = common.read_shards(CORPUS, manifest, stem)
    if sha(values['probes']) != sha(original_probes) or sha(values['probes']) != report.get('probes_sha256'):
        raise ValueError('원형128 복원계약 변경')
    cores = make_cases(values['probes'])
    if len(values['cases']) != EXPECTED or sha(values['cases']) != report.get('cases_sha256'):
        raise ValueError('546동결case 결손/변조')
    for core, case in zip(cores, values['cases']):
        if sha({k: v for k, v in case.items() if k not in ('encoding', 'actual_history_template_only')}) != sha(core):
            raise ValueError('동결 상태/입력/gold/순서 변경')
        if case['requires_initial_event']:
            if case['encoding'] is not None or case.get('actual_history_template_only') is not True:
                raise ValueError('실제앞답 전에 ACTUAL prefix/gold를 동결한 것으로 속이지 않음')
        elif (case['encoding'].get('prompt_sha256') != sha(common.prompt(case['messages']))
                or case['encoding'].get('prompt_tokens', CONTEXT) + MAX_NEW > CONTEXT):
            raise ValueError('정적 fullprefix/길이 동결 변경')
    for endpoint, descriptor in report['checkpoints'].items():
        if (endpoint not in ENDPOINTS or required(CORPUS / ('checkpoint_' + endpoint + '.json')) != descriptor
                or any(descriptor.get(k) != v for k, v in source['endpoints'][endpoint].items())
                or digest(ROOT / descriptor['checkpoint']) != descriptor['checkpoint_sha256']
                or not common.hex_sha(descriptor.get('initial_core_sha256'))):
            raise ValueError('CPU cfg/core/CP byte 연결 변경')
    if (set(report['checkpoints']) != set(ENDPOINTS) or report.get('stdout_selection') != stdout_selection(values['probes'])
            or required(EVIDENCE / 'cpu_contract.json') != public_cpu(report)):
        raise ValueError('3CP/공개 CPU/사전표본 동결 변경')
    return report, values['probes'], values['cases']


def recount(events, cases, probes, tokenizer, endpoint, identity, input_sha):
    if len(cases) != EXPECTED or len({c['case_id'] for c in cases}) != EXPECTED:
        raise ValueError('546 고유case 계약 필요')
    if len(events) < EXPECTED:
        raise Pending('부분 원형: 관측%d/예상546; 누락을0으로 세지 않음' % len(events))
    if len(events) != EXPECTED:
        raise ValueError('예상 원형 분모 초과')
    lookup = {p['probe_id']: p for p in probes}; initials = {}; seen = set()
    for case, event in zip(cases, events):
        if event.get('case_id') != case['case_id'] or event['case_id'] in seen:
            raise ValueError('중복/순서/알 수 없는 원형case')
        seen.add(event['case_id']); probe = lookup.get(case['probe_id']); initial = initials.get(case['probe_id'])
        actual = materialize(case, probe, tokenizer, initial, identity, endpoint, input_sha)
        if actual['record_status'] == GENERATED:
            rebuilt = finish_event(actual, probe, endpoint, identity, input_sha,
                event.get('answer'), event.get('generation'), initial, event.get('decode_observation'), tokenizer)
        else:
            rebuilt = finish_event(actual, probe, endpoint, identity, input_sha)
        if sha(event) != sha(rebuilt):
            raise ValueError('원답/상태/동적목표/INITIAL참조/CP/receipt 재계수 불일치')
        if case['condition'] == 'INITIAL_DIRECT':
            initials[case['probe_id']] = event
    def aggregate(values):
        generated = [e for e in values if e['record_status'] == GENERATED]
        not_run = Counter(e['record_status'] for e in values if e['record_status'] != GENERATED)
        passed = sum(e['metrics']['condition_pass'] for e in generated)
        finish = Counter(e['generation']['finish_reason'] for e in generated)
        return dict(n_expected=len(values), n_generated=len(generated), n_not_run=sum(not_run.values()),
            not_run_reasons=dict(sorted(not_run.items())), condition_pass_sum=passed,
            not_run_input_detail_counts=dict(sorted(Counter(reason for e in values for reason in e['input_rejection_reasons']).items())),
            pass_rate_generated_only=passed / len(generated) if generated else None,
            pass_rate_full_when_complete=passed / len(values) if values and not not_run else None,
            empty_exact=sum(e['answer'] == '' for e in generated),
            whitespace_only=sum(bool(e['answer']) and not e['answer'].strip() for e in generated),
            empty_or_whitespace=sum(not e['answer'].strip() for e in generated), finish_reasons=dict(sorted(finish.items())),
            max_new=finish['MAX_NEW'], stop=finish['EOS'] + finish['STOP_SEQUENCE'],
            original_helper_vs_visible_body_differences=sum(e['answer'] != e['original_helper_answer'] for e in generated),
            terminal_body_relations=dict(sorted(Counter(e['decode_observation']['helper_to_visible_relation'] for e in generated).items())))
    result = dict(status='RAW_HISTORY_CASES_ACCOUNTED', expected_cases=EXPECTED,
        actual_generations=sum(e['record_status'] == GENERATED for e in events),
        explicit_not_run=sum(e['record_status'] != GENERATED for e in events),
        overall=aggregate(events),
        by_condition={name: aggregate([e for e in events if e['condition'] == name]) for name in (*CONDITIONS, 'MATH_COMPACT_INITIAL', 'MINIMAL_KO')},
        by_language={name: aggregate([e for e in events if e['language'] == name]) for name in LANGUAGES},
        by_cohort={name: aggregate([e for e in events if e['cohort'] == name]) for name in (*COHORTS, 'minimal_development')},
        by_family={name: aggregate([e for e in events if e['family'] == name]) for name in FAMILIES},
        by_truth_scope={name: aggregate([e for e in events if e['truth_scope'] == name]) for name in sorted({e['truth_scope'] for e in events})},
        overall_metric_scope='heterogeneous condition-contract pass, not pooled factual accuracy',
        aggregation_order='frozen source/case order; integer pass/coverage sums, explicit generated-only denominator',
        format_success_is_not_fact_recovery=True, automatic_adoption=False)
    cells = defaultdict(list)
    for event in events:
        cells[(event['cohort'], event['family'], event['language'], event['answer_change_policy'], event['condition'])].append(event)
    result['cells'] = [dict(cohort=k[0], family=k[1], language=k[2], answer_change_policy=k[3], condition=k[4], **aggregate(v)) for k, v in sorted(cells.items())]
    actual = [e for e in events if e['condition'] == 'ACTUAL_HISTORY']
    chain, wrong_wrapped = 0, 0
    for event in actual:
        first = initials[event['probe_id']]['metrics']['first_fact_correct']
        if event['record_status'] == GENERATED:
            chain += int(first and event['metrics']['condition_pass'])
            wrong_wrapped += int(not first and event['family'] == 'format' and event['metrics']['strict_c3_format_preserved'])
    result['real_chain'] = dict(n_expected=128, n_generated_follow=sum(e['record_status'] == GENERATED for e in actual),
        n_follow_not_run=sum(e['record_status'] != GENERATED for e in actual),
        first_fact_correct_sum=sum(e['metrics']['first_fact_correct'] for e in initials.values()),
        chain_both_sum=chain, first_wrong_but_c3_format_preserved=wrong_wrapped,
        chain_rate_full_when_complete=chain / 128 if all(e['record_status'] == GENERATED for e in actual) else None,
        c3_chain_requires_first_correct_and_visible_body_preservation=True)
    c3 = [e for e in actual if e['family'] == 'format']
    result['c3_actual_canonical_reference_budget'] = dict(
        all_c3=aggregate(c3), groups={name: aggregate([e for e in c3 if e['encoding']['canonical_target_fits_budget'] == fits])
            for name, fits in (('CANONICAL_REFERENCE_FITS', True), ('CANONICAL_REFERENCE_EXCEEDS', False))},
        basis='standalone canonical reference+EOT, not minimum over equivalent JSON',
        universal_impossibility_proven=False, exceeding_cases_not_dropped=True)
    compact = [e for e in events if e['condition'] == 'MATH_COMPACT_INITIAL']
    result['compact_vs_initial'] = dict(n=32,
        initial_correct_sum=sum(initials[e['probe_id']]['metrics']['condition_pass'] for e in compact),
        compact_correct_sum=sum(e['metrics']['condition_pass'] for e in compact),
        same_raw_answer=sum(e['answer'] == initials[e['probe_id']]['answer'] for e in compact),
        input_state='INITIAL operands/operator; not updated state', independent_new_roots=0)
    strict_conditions = ('CURRENT_DIRECT', 'GOLD_HISTORY', 'ACTUAL_HISTORY')
    strict_by_condition = {}
    for condition in strict_conditions:
        rows = [e for e in events if e['family'] == 'format' and e['condition'] == condition]
        generated = [e for e in rows if e['record_status'] == GENERATED]
        evaluated = [e for e in generated if type(e['metrics'].get('strict_c3_format_preserved')) is bool]
        passed = sum(e['metrics']['strict_c3_format_preserved'] for e in evaluated)
        strict_by_condition[condition] = dict(n_expected=len(rows), n_generated=len(generated),
            n_not_run=len(rows) - len(generated), n_evaluated=len(evaluated),
            n_generated_without_strict_flag=len(generated) - len(evaluated), strict_pass_sum=passed,
            strict_pass_rate_evaluated_only=passed / len(evaluated) if evaluated else None,
            strict_pass_rate_full_when_complete=passed / len(rows) if rows and len(evaluated) == len(rows) else None,
            rate_denominator='n_evaluated; explicit NOT_RUN is not scored as wrong')
    result['c3_common_strict_diagnostics'] = dict(by_condition=strict_by_condition,
        predicate='existing metrics.strict_c3_format_preserved; exact one string key/value and no duplicate keys',
        aggregation_order='frozen event order; integer strict pass/evaluated sums per condition',
        existing_condition_pass_unchanged=True,
        scope='same strict predicate, not identical targets: CURRENT/GOLD use code literal; ACTUAL uses visible first body')
    result['boolean_label_diagnostics'] = {}
    for condition in CONDITIONS:
        rows = [e for e in events if e['family'] == 'boolean' and e['condition'] == condition]
        gold = Counter(e['target'] for e in rows)
        if set(gold) - {'true', 'false'}:
            raise ValueError('Boolean source 코드라벨 범위 변경')
        generated = [e for e in rows if e['record_status'] == GENERATED]
        labels = Counter(e['answer'].strip().casefold() if e['answer'].strip().casefold() in ('true', 'false')
                         else 'UNRECOGNIZED' for e in generated)
        result['boolean_label_diagnostics'][condition] = dict(n_expected=len(rows), n_generated=len(generated),
            n_not_run=len(rows) - len(generated), source_gold_counts=dict(sorted(gold.items())),
            actual_label_counts=dict(sorted(labels.items())),
            constant_true_correct_sum=gold['true'], constant_false_correct_sum=gold['false'],
            condition_correct_sum=sum(e['metrics']['condition_pass'] for e in generated),
            scope='fixed code-owned labels; constant baseline, not proof of Boolean generalization')
        generated_gold = Counter(e['target'] for e in generated)
        result['boolean_label_diagnostics'][condition].update(
            full_nominal_baseline=dict(denominator=len(rows), source_gold_counts=dict(sorted(gold.items())),
                constant_true_correct_sum=gold['true'], constant_false_correct_sum=gold['false'],
                constant_true_rate=gold['true'] / len(rows) if rows else None,
                constant_false_rate=gold['false'] / len(rows) if rows else None,
                scope='all nominal source labels, including ungenerated cases; not a model score'),
            generated_subset_baseline=dict(denominator=len(generated), source_gold_counts=dict(sorted(generated_gold.items())),
                constant_true_correct_sum=generated_gold['true'], constant_false_correct_sum=generated_gold['false'],
                constant_true_rate=generated_gold['true'] / len(generated) if generated else None,
                constant_false_rate=generated_gold['false'] / len(generated) if generated else None,
                condition_correct_sum=sum(e['metrics']['condition_pass'] for e in generated),
                condition_pass_rate=sum(e['metrics']['condition_pass'] for e in generated) / len(generated) if generated else None,
                scope='only actually generated cases; compare model and constant baseline on this same subset'))
    return result


def print_examples(events, probes, frozen_selection, endpoint):
    if frozen_selection != stdout_selection(probes):
        raise ValueError('사전 stdout 표본 변경')
    indexed = {(e['probe_id'], e['condition']): e for e in events}
    for probe in probes:
        if probe['probe_id'] not in frozen_selection['probe_ids']:
            continue
        answers = {}
        for condition in CONDITIONS:
            row = indexed[probe['probe_id'], condition]
            answers[condition] = dict(status=row['record_status'],
                answer=row.get('answer'), finish_reason=row.get('generation', {}).get('finish_reason'),
                original_helper_answer=row.get('original_helper_answer'),
                helper_body_relation=row.get('decode_observation', {}).get('helper_to_visible_relation'),
                canonical_target_tokens_with_eot=row['encoding']['canonical_target_tokens_with_eot'],
                canonical_target_fits_budget=row['encoding']['canonical_target_fits_budget'], case_id=row['case_id'])
        print('[HISTORY_ACTUAL_QUESTION_ANSWERS] ' + json.dumps(dict(endpoint=endpoint,
            cohort=probe['cohort'], language=probe['language'], family=probe['family'],
            first_question=probe['initial_question'], current_question=probe['current_question'],
            follow_question=probe['follow_question'], answers=answers,
            raw_directory=str((LOCAL / 'evaluate' / endpoint).relative_to(ROOT)),
            example_selection_sha256=frozen_selection['selection_sha256'], not_performance_sample=True), ensure_ascii=False), flush=True)
    for event in events:
        if event['condition'] == 'MINIMAL_KO':
            print('[HISTORY_MINIMAL_DEVELOPMENT] ' + json.dumps(dict(endpoint=endpoint,
                question=text(event['messages'][0]), answer=event['answer'], generation=event['generation'],
                original_helper_answer=event['original_helper_answer'],
                user_original_wording=False), ensure_ascii=False), flush=True)


def evaluate(endpoint, guard):
    if endpoint not in ENDPOINTS:
        raise ValueError('parent/fixed/views 명시 필요')
    report, probes, cases = read_prepared(); identity = report['checkpoints'][endpoint]
    target, directory = safe(EVIDENCE / (endpoint + '_report.json')), safe(LOCAL / 'evaluate' / endpoint)
    if target.exists() or directory.exists():
        raise FileExistsError('완료/부분 endpoint 원형 보존')
    from scripts.p106b_gate_runtime import idle_before_gpu
    guard(); idle_before_gpu(); guard()
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts import diag_p106b_cpt_unique32k_eval as inference
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    path = safe(ROOT / identity['checkpoint'])
    if digest(path) != identity['checkpoint_sha256']:
        raise ValueError('GPU 직전 CP byteSHA 변경')
    directory.mkdir(parents=True, exist_ok=False); begin = time.perf_counter(); model = None
    try:
        model, cfg, device = load_model(arch='dense', ckpt_path=str(path), device='cuda')
        model.eval()
        if sha(asdict(cfg)) != identity['effective_cfg_sha256'] or state_fingerprint(model) != identity['initial_core_sha256']:
            raise ValueError('CPU cfg/core와 strict GPU 본체 불일치')
        tok = Tokenizer.from_file(str(TOKENIZER)); observer = DecodeObserver(tok)
        base_emit = inference.emit_function(model, cfg, observer, max_new=MAX_NEW)
        input_sha = digest(CORPUS / 'report.json'); writer = ShardWriter(directory, 'answers', limit=19_999_999)
        eval_calls = 0
        def emit(messages):
            nonlocal eval_calls
            if model.training:
                raise ValueError('자유답 직전 eval mode가 아님')
            body, metadata, observation = observe_helper(base_emit, observer, messages)
            if model.training:
                raise ValueError('자유답 경로가 model.train 모드로 바뀜')
            eval_calls += 1
            return body, metadata, observation
        def append(event):
            writer.append(event)
            if event['condition'] == 'INITIAL_DIRECT' or event['record_status'] == 'TOOL_ERROR_DECODE_OBSERVATION':
                writer._file.flush(); os.fsync(writer._file.fileno())
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            events = collect(cases, probes, tok, endpoint, identity, input_sha, emit, append, guard)
        fingerprint_after = state_fingerprint(model)
        if fingerprint_after != identity['initial_core_sha256'] or digest(path) != identity['checkpoint_sha256']:
            raise ValueError('무학습 실행 후 CP/core 변경')
        counts = recount(events, cases, probes, tok, endpoint, identity, input_sha)
        if eval_calls != counts['actual_generations']:
            raise ValueError('실제 generation 호출수와 원형 계수 불일치')
        manifest = writer.close(lineage=dict(info(), endpoint=endpoint, input_report_sha256=input_sha,
            checkpoint_sha256=identity['checkpoint_sha256'], initial_core_sha256=identity['initial_core_sha256']))
        mode_before_cleanup = bool(model.training)
        model.clear_quant(); model.eval()
        if state_fingerprint(model) != fingerprint_after:
            raise ValueError('cleanup 뒤 persistent core 변경')
        result = dict(info(), status='ACTUAL_HISTORY_EVALUATION_ACCOUNTED', endpoint=endpoint,
            checkpoint=identity['checkpoint'], checkpoint_sha256=identity['checkpoint_sha256'],
            initial_core_sha256=identity['initial_core_sha256'], final_core_sha256=fingerprint_after,
            core_unchanged=True, effective_cfg_sha256=identity['effective_cfg_sha256'],
            input_report_sha256=input_sha, source=report['source'], directory=str(directory.relative_to(ROOT)),
            output=dict(manifest=manifest, counts=counts), manifest_sha256=digest(directory / 'answers_shards_manifest.json'),
            actual_generation_calls=eval_calls, model_training_before_cleanup=mode_before_cleanup,
            model_training_after_cleanup=bool(model.training), all_generation_calls_eval_mode=True,
            torch_no_grad_during_generation=True, optimizer_updates=0, checkpoints_written=0,
            whole_seconds=time.perf_counter() - begin, peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
            automatic_adoption=False)
        if read_source()[0] != report['source'] or info()['code_sha256'] != report['code_sha256']:
            raise ValueError('실행 도중 source/code 변경')
        guard(); write(target, result)
        print_examples(events, probes, report['stdout_selection'], endpoint)
        print('[HISTORY_EVALUATION_COUNTS] ' + json.dumps(dict(endpoint=endpoint,
            expected=EXPECTED, generated=counts['actual_generations'], explicit_not_run=counts['explicit_not_run'])), flush=True)
        return 0
    finally:
        if model is not None:
            model.eval(); del model
        gc.collect(); torch.cuda.empty_cache()


def read_endpoint(endpoint, report, probes, cases, tok):
    result = required(EVIDENCE / (endpoint + '_report.json')); identity = report['checkpoints'][endpoint]
    if result.get('status') != 'ACTUAL_HISTORY_EVALUATION_ACCOUNTED':
        raise Pending('해당 endpoint의 전량case 계수 완료가 선결')
    expected = dict(endpoint=endpoint, checkpoint=identity['checkpoint'], checkpoint_sha256=identity['checkpoint_sha256'],
        initial_core_sha256=identity['initial_core_sha256'], final_core_sha256=identity['initial_core_sha256'],
        effective_cfg_sha256=identity['effective_cfg_sha256'], core_unchanged=True,
        input_report_sha256=digest(CORPUS / 'report.json'), source=report['source'],
        directory=str((LOCAL / 'evaluate' / endpoint).relative_to(ROOT)),
        all_generation_calls_eval_mode=True, model_training_before_cleanup=False, model_training_after_cleanup=False,
        torch_no_grad_during_generation=True)
    if any(result.get(k) != v for k, v in expected.items()) or any(result.get(k) != v for k, v in info().items()):
        raise ValueError('endpoint/source/core/eval mode/receipt 변경')
    directory = LOCAL / 'evaluate' / endpoint; path = directory / 'answers_shards_manifest.json'
    if digest(path) != result.get('manifest_sha256'):
        raise ValueError('원형 manifest 지문 변경')
    manifest = required(path)
    lineage = dict(info(), endpoint=endpoint, input_report_sha256=digest(CORPUS / 'report.json'),
        checkpoint_sha256=identity['checkpoint_sha256'], initial_core_sha256=identity['initial_core_sha256'])
    if manifest != result['output']['manifest'] or manifest.get('lineage') != lineage:
        raise ValueError('원형 manifest 계보 변경')
    events = common.read_shards(directory, manifest, 'answers')
    counts = recount(events, cases, probes, tok, endpoint, identity, digest(CORPUS / 'report.json'))
    if counts != result['output'].get('counts') or counts['actual_generations'] != result.get('actual_generation_calls'):
        raise ValueError('546원형/동적C3목표/계수 불일치')
    if digest(ROOT / identity['checkpoint']) != identity['checkpoint_sha256']:
        raise ValueError('판독 시 CP byteSHA 변경')
    return result, events


def readback(guard):
    report, probes, cases = read_prepared(); target = safe(EVIDENCE / 'readback.json')
    if target.exists():
        raise FileExistsError('기존 판독 보존')
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(TOKENIZER)); summaries, reports = {}, {}
    for endpoint in ENDPOINTS:
        guard(); result, events = read_endpoint(endpoint, report, probes, cases, tok)
        summaries[endpoint] = result['output']['counts']
        reports[endpoint] = digest(EVIDENCE / (endpoint + '_report.json'))
        print_examples(events, probes, report['stdout_selection'], endpoint)
    result = dict(info(), status='RAW_HISTORY_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION', errors=0,
        source=report['source'], input_report_sha256=digest(CORPUS / 'report.json'),
        endpoint_report_sha256=reports, summaries=summaries,
        expected_case_records=3 * EXPECTED,
        actual_generation_calls=sum(v['actual_generations'] for v in summaries.values()),
        explicit_not_run=sum(v['explicit_not_run'] for v in summaries.values()),
        old_gold_history_precision_not_a_reproduction_gate=True, automatic_adoption=False,
        new_training=False, general_intelligence='NOT_ESTABLISHED')
    guard(); write(target, result)
    print('[HISTORY_READBACK] 전량case/실제생성/명시미실행을 구분; 형식준수와 사실정답 분리', flush=True)
    return 0


def activity_key(mode, endpoint=None):
    key = 'evaluate_' + str(endpoint) if mode == 'evaluate' else mode
    if key not in SLOTS:
        raise ValueError('등록된 active worker 필요')
    return key


def stage_output(key):
    if key == 'prepare':
        return CORPUS / 'report.json'
    if key == 'readback':
        return EVIDENCE / 'readback.json'
    if key in ('evaluate_' + e for e in ENDPOINTS):
        return EVIDENCE / (key[len('evaluate_'):] + '_report.json')
    raise ValueError('미등록 단계')


def activities():
    result = {}
    for key in SLOTS:
        path = safe(EVIDENCE / ('activity_' + key + '.json'))
        if path.exists():
            value = required(path)
            if (value.get('schema') != VERSION or value.get('tag') != TAG or value.get('stage') != key
                    or value.get('status') not in ('COMPLETE', 'HOLD', 'TOOL_ERROR', 'INTERRUPTED')
                    or value.get('returncode') != dict(COMPLETE=0, HOLD=8, TOOL_ERROR=9, INTERRUPTED=130).get(value.get('status'))
                    or type(value.get('returncode')) is not int
                    or type(value.get('active_seconds')) not in (int, float) or not math.isfinite(value['active_seconds'])
                    or value['active_seconds'] < 0 or value.get('own_code_sha256') != {p: digest(ROOT / p) for p in OWN_CODE}):
                raise ValueError('active 시간/코드 영수증 변경')
            if value['status'] == 'COMPLETE' and value.get('output_report_sha256') != digest(stage_output(key)):
                raise ValueError('active 완료와 산출물 연결 불일치')
            result[key] = value
    return result


def admission(mode, endpoint, requested, previous, elapsed=0., now=None):
    key = activity_key(mode, endpoint)
    if (type(requested) is not int or not 60 <= requested <= 1200
            or type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0):
        raise ValueError('명시 bounded wall/active 경과 필요')
    if key in previous:
        raise Pending('완료/부분 active worker 덮어쓰기 금지')
    if set(previous) - set(SLOTS):
        raise ValueError('알 수 없는 active 단계')
    if any(type(v.get('active_seconds')) not in (int, float)
           or not math.isfinite(v['active_seconds']) or v['active_seconds'] < 0 for v in previous.values()):
        raise ValueError('유한한 실제 active 경과 영수증 필요')
    needed = [] if mode == 'prepare' else ['prepare']
    if mode == 'readback':
        needed += ['evaluate_' + e for e in ENDPOINTS]
    if any(previous.get(p, {}).get('status') != 'COMPLETE' for p in needed) or any(v.get('status') != 'COMPLETE' for v in previous.values()):
        raise Pending('완료된 앞 worker의 영수증 필요')
    spent = sum(v['active_seconds'] for v in previous.values()); cap = min(requested, SLOTS[key])
    future = sum(v for k, v in SLOTS.items() if k not in previous and k != key)
    if elapsed >= cap:
        raise TimeoutError('현재 active worker 상한 초과; 부분 원형 보존')
    total = spent + cap + future + RECORD_RESERVE
    if total > ACTIVE_LIMIT:
        raise Pending('worker 합/미실행 예약/기록600이5400초 초과')
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('시간대 있는 현재시각 필요')
    remaining = (END - now).total_seconds()
    if remaining < cap - elapsed + future + RECORD_RESERVE:
        raise Pending('20일17시 절대권한/미실행/기록 예비 부족')
    return dict(stage=key, slot_seconds=cap, previous_active_seconds=spent,
        future_reserved_seconds=future, record_reserve_seconds=RECORD_RESERVE,
        total_study_reserved_active_seconds=total, calendar_remaining_seconds=remaining,
        prepare_time_is_not_calendar_expiry=True, wrapper_regression_preflight_excluded=True)


def run_worker(mode, endpoint=None, max_wall_sec=1200):
    if mode == 'preflight':
        if (END - datetime.now(timezone.utc)).total_seconds() < RECORD_RESERVE:
            raise Pending('절대마감/기록600 예비 부족')
        read_prepared(); print('[HISTORY_PREFLIGHT] 동결 source/CP byte/정적입력 검산; tensor역직렬화/모델0', flush=True)
        return 0
    prior = activities(); budget = admission(mode, endpoint, max_wall_sec, prior)
    key = budget['stage']; began = time.perf_counter(); started = datetime.now(timezone.utc).isoformat()
    status, code = 'TOOL_ERROR', 9
    def guard():
        return admission(mode, endpoint, max_wall_sec, prior, elapsed=time.perf_counter() - began)
    try:
        from scripts.p106b_gate_runtime import wall_limit
        with wall_limit(budget['slot_seconds']):
            guard()
            if mode == 'prepare':
                code = prepare(guard)
            elif mode == 'evaluate':
                code = evaluate(endpoint, guard)
            elif mode == 'readback':
                code = readback(guard)
            else:
                raise ValueError('미등록 worker mode')
            guard()
        status = 'COMPLETE' if code == 0 else 'HOLD' if code == 8 else 'TOOL_ERROR'
        return code
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        status, code = common.failure_status(exc)
        print('[HISTORY_WORKER] %s%d: %s' % (status, code, str(exc)), flush=True)
        return code
    finally:
        write(EVIDENCE / ('activity_' + key + '.json'), dict(schema=VERSION, tag=TAG, stage=key,
            status=status, returncode=code, active_seconds=time.perf_counter() - began,
            started_utc=started, ended_utc=datetime.now(timezone.utc).isoformat(), admission=budget,
            own_code_sha256={p: digest(ROOT / p) for p in OWN_CODE},
            output_report_sha256=digest(stage_output(key)) if status == 'COMPLETE' else None,
            wrapper_regression_preflight_excluded=True, own_receipt_write_within_record_reserve=True))


def phase_commands(mode, endpoint=None, max_wall_sec=1200):
    if mode not in MODES or ((mode == 'evaluate') != (endpoint in ENDPOINTS)) or (mode != 'evaluate' and endpoint is not None):
        raise ValueError('evaluate만 정확한 parent/fixed/views endpoint 필요')
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 1200:
        raise ValueError('60..1200초 bounded wall 필요')
    py = [sys.executable, '-B', '-X', 'utf8']; driver = py + ['scripts/diag_p106d_history_scope.py']
    command = driver + ['--mode', mode, '--max-wall-sec', str(max_wall_sec), '--worker']
    if endpoint is not None:
        command += ['--endpoint', endpoint]
    preflight = (driver + ['--mode', 'prepare', '--check-only', '--worker'] if mode == 'prepare'
                 else driver + ['--mode', 'preflight', '--execute', '--worker', '--max-wall-sec', '600'])
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106d_history_scope', '-v']),
            ('PREFLIGHT', preflight), ('EXECUTE', command + ['--execute'])]


def run_pipeline(mode, endpoint=None, max_wall_sec=1200):
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        env = dict(os.environ)
        for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            env[name] = '2'
        try:
            cap = max_wall_sec if '--mode' in command and command[command.index('--mode') + 1] == 'evaluate' else 600
            return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, timeout=cap + 30, env=env).returncode
        except (OSError, subprocess.TimeoutExpired):
            return 9
        except KeyboardInterrupt:
            return 130
    return pipeline(phase_commands(mode, endpoint, max_wall_sec), launch,
        lambda line: print(line, flush=True), experiment='P106D_HISTORY_' + mode + '_' + str(endpoint or 'all'))['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--endpoint', choices=ENDPOINTS)
    parser.add_argument('--max-wall-sec', type=int, default=1200)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        phases = phase_commands(args.mode, args.endpoint, args.max_wall_sec)
    except ValueError as exc:
        parser.error(str(exc))
    if args.check_only:
        print('[HISTORY_CHECK_ONLY] ' + json.dumps(dict(syntax_info(), phases=phases,
            source_read=False, tokenizer_loaded=False, checkpoint_tensors_loaded=False,
            model_created=False, gpu_initialized=False), ensure_ascii=False))
        return 0
    try:
        return run_worker(args.mode, args.endpoint, args.max_wall_sec) if args.worker else run_pipeline(args.mode, args.endpoint, args.max_wall_sec)
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        status, code = common.failure_status(exc)
        print('[HISTORY_FINAL] %s%d: %s' % (status, code, str(exc)), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
