"""제공된 Falcon 원답과 동결 원형의 독립 재검산만 수행한다.

원천·토크나이저·모델 파일을 열거나 로짓·원답을 새로 계산하지 않는다.
문항 선택, 자산·목록 해시, 모델 불변과 모델 간 교집합은 호출자 소유다.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_authorized_benchmark as public

VERSION = 'P106B_NIGHT_FALCON_RAW_RECOUNT_V1'
MC_TASKS = frozenset(('piqa', 'hellaswag', 'arc_easy'))
GEN_TASKS = frozenset(('gsm8k_plain', 'gsm8k_chatml'))
EOS = 11
MAX_NEW = 128
CONTEXT = 1024
VOCAB = 32768


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def _ids(values, label):
    if (not isinstance(values, (list, tuple))
            or any(type(value) is not int or not 0 <= value < VOCAB for value in values)):
        raise ValueError('0부터 32767 범위의 정수 토큰 식별자 목록 필요: ' + label)
    return list(values)


def _encode(tok, text):
    if not isinstance(text, str):
        raise ValueError('원래 토큰화 입력 문자열 필요')
    encoded = tok.encode(text)
    ids = _ids(encoded.ids, 'encode.ids')
    backend = getattr(tok, 'tokenizer', None)
    if backend is not None:
        without_bos = _ids(backend.encode(text, add_special_tokens=False), 'no_BOS')
        if ids != without_bos:
            raise ValueError('adapter 토큰화가 명시적 no-BOS 토큰화와 다름')
    return ids


def _decode(tok, ids):
    decoded = tok.decode(ids)
    if not isinstance(decoded, str):
        raise ValueError('원래 토큰 목록의 decode 문자열 필요')
    backend = getattr(tok, 'tokenizer', None)
    if backend is not None:
        exact = backend.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if decoded != exact:
            raise ValueError('adapter decode가 특수 토큰·공백 보존 계약과 다름')
    return decoded


def _finite(value, label, nonnegative=False):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or (nonnegative and value < 0)):
        raise ValueError('유한한 원래 수치 필요: ' + label)
    return float(value)


def _index(value, count, label):
    if type(value) is not int or not 0 <= value < count:
        raise ValueError('선택지 범위 안의 정수 식별자 필요: ' + label)
    return value


def _close(actual, expected, label):
    if abs(actual - expected) > 1e-3 + 1e-5 * abs(expected):
        raise ValueError('원래 수치의 재계산과 허용오차 밖에서 다름: ' + label)


def _originals(originals):
    indexed = {}
    for row in originals:
        if (not isinstance(row, dict) or not isinstance(row.get('task'), str)
                or row['task'] not in MC_TASKS | GEN_TASKS
                or type(row.get('index')) is not int or row['index'] < 0
                or row.get('kind') != ('mc' if row['task'] in MC_TASKS else 'gen')
                or 'expected_skip' not in row):
            raise ValueError('동결된 원래 과제·문항 번호·종류·제외 조건 필요')
        skip = row['expected_skip']
        if skip is not None and (not isinstance(skip, str) or not skip):
            raise ValueError('동결된 expected_skip은 None 또는 비어 있지 않은 사유여야 함')
        original = dict(row)
        case = original.pop('case_id', None)
        if not isinstance(case, str) or case != _sha([row['task'], row['index'], original]):
            raise ValueError('동결 원형 case_id가 전체 원형 내용과 다름')
        if case in indexed:
            raise ValueError('동결 원형 case_id 중복')
        indexed[case] = row
    if not indexed:
        raise ValueError('비어 있지 않은 동결 원형 목록 필요')
    return indexed


def _pairs(item):
    if not isinstance(item, dict):
        raise ValueError('원래 MC source_item 필요')
    if item.get('pairs'):
        pairs = item['pairs']
    else:
        choices = item.get('choices')
        if not isinstance(choices, list) or not choices or not isinstance(item.get('ctx'), str):
            raise ValueError('원래 MC 문맥과 선택지 목록 필요')
        pairs = [(item['ctx'], value) for value in choices]
    if (not isinstance(pairs, (list, tuple)) or not pairs
            or any(not isinstance(pair, (list, tuple)) or len(pair) != 2
                   or any(not isinstance(value, str) for value in pair) for pair in pairs)):
        raise ValueError('선택지별 원래 문맥·후속 문자열 쌍 필요')
    return pairs


def _mc(event, original, tok):
    if event.get('kind') != 'mc' or event.get('source_item') != original.get('item'):
        raise ValueError('MC source_item이 동결 원형과 다름')
    item = original['item']
    pairs = _pairs(item)
    count = len(pairs)
    gold = _index(item.get('gold'), count, 'source_item.gold')
    scores = event.get('scores')
    if not isinstance(scores, dict) or scores.get('id') != item.get('_iid'):
        raise ValueError('MC 원답 점수의 원래 문항 식별자가 다름')
    if _index(scores.get('gold'), count, 'scores.gold') != gold:
        raise ValueError('MC 원답 gold가 원래 정답과 다름')
    names = ('sum_nll', 'mean_nll', 'score', 'n_tokens', 'n_chars')
    if any(not isinstance(scores.get(name), list) or len(scores[name]) != count for name in names):
        raise ValueError('MC 선택지 수와 원답 수치 목록 길이가 다름')
    sums, means, internal, chars = [], [], [], []
    for index, (prompt, continuation) in enumerate(pairs):
        token_ids = _encode(tok, continuation)
        if not token_ids:
            raise ValueError('채점된 MC 후속 문자열에 실제 토큰이 없음')
        prompt_ids = _encode(tok, prompt) if prompt else _encode(tok, '\n')[:1]
        if not prompt_ids or len(prompt_ids) + len(token_ids) > CONTEXT:
            raise ValueError('채점된 MC 원형은 전체 길이 예산을 만족해야 함')
        ntokens = scores['n_tokens'][index]
        nchars = scores['n_chars'][index]
        if type(ntokens) is not int or ntokens != len(token_ids):
            raise ValueError('MC n_tokens가 실제 후속 토큰 수와 다름')
        if type(nchars) is not int or nchars != max(1, len(continuation)):
            raise ValueError('MC n_chars가 실제 유니코드 문자 수와 다름')
        summed = _finite(scores['sum_nll'][index], 'sum_nll', True)
        mean = _finite(scores['mean_nll'][index], 'mean_nll', True)
        score = _finite(scores['score'][index], 'score', True)
        if abs(mean * ntokens - summed) > 1e-3 + 1e-5 * summed:
            raise ValueError('MC 평균 NLL과 토큰 수의 곱이 합 NLL과 다름')
        if score != mean:
            raise ValueError('동결된 no-PMI 경로의 score가 mean_nll과 다름')
        sums.append(summed)
        means.append(mean)
        internal.append(score)
        chars.append(nchars)
    pred = min(range(count), key=lambda index: sums[index])
    char_pred = min(range(count), key=lambda index: sums[index] / chars[index])
    internal_pred = min(range(count), key=lambda index: internal[index])
    token_pred = min(range(count), key=lambda index: sums[index] / scores['n_tokens'][index])
    for name, expected in (('pred_harness', pred), ('pred_harness_norm', char_pred),
                           ('pred_internal', internal_pred), ('pred_internal_norm', token_pred)):
        if _index(scores.get(name), count, name) != expected:
            raise ValueError('MC 저장된 선택이 원래 NLL 재계산과 다름: ' + name)
    wrong = [value for index, value in enumerate(internal) if index != gold]
    margin_mean = statistics.fmean(wrong) - internal[gold] if wrong else 0.
    margin_decision = min(wrong) - internal[gold] if wrong else 0.
    for name, expected in (('margin_mean', margin_mean), ('margin_decision', margin_decision)):
        _close(_finite(scores.get(name), name), expected, name)
    return dict(case_id=original['case_id'], task=original['task'], index=original['index'],
                id=item.get('_iid'), gold=gold, pred=pred, correct=int(pred == gold),
                char_norm_pred=char_pred, char_norm_correct=int(char_pred == gold))


def _gen(event, original, tok):
    if event.get('kind') != 'gen':
        raise ValueError('GEN 원답 종류가 다름')
    for field in ('id', 'prompt', 'question', 'golds'):
        if field not in original or event.get(field) != original[field]:
            raise ValueError('GEN 동결 원형과 원답이 다름: ' + field)
    if (not isinstance(original['prompt'], str) or not original['prompt']
            or not isinstance(original['question'], str)
            or not isinstance(original['golds'], list) or not original['golds']
            or any(not isinstance(gold, str) for gold in original['golds'])):
        raise ValueError('GEN 원래 질문·프롬프트·정답 목록 필요')
    input_ids = _encode(tok, original['prompt'])
    if _ids(event.get('input_ids'), 'input_ids') != input_ids:
        raise ValueError('GEN input_ids가 전체 no-BOS 원형 프롬프트와 다름')
    if (not input_ids or len(input_ids) + MAX_NEW > CONTEXT
            or type(original.get('prompt_tokens')) is not int
            or original['prompt_tokens'] != len(input_ids)):
        raise ValueError('GEN 원래 전체 프롬프트 길이·128 생성 예산이 다름')
    new_ids = _ids(event.get('new_ids'), 'new_ids')
    if len(new_ids) > MAX_NEW:
        raise ValueError('GEN 추가 토큰 수가 128을 초과함')
    if EOS in new_ids and new_ids.index(EOS) != len(new_ids) - 1:
        raise ValueError('GEN 첫 EOS11은 마지막 추가 토큰이어야 함')
    terminal = bool(new_ids and new_ids[-1] == EOS)
    if not terminal and len(new_ids) != MAX_NEW:
        raise ValueError('EOS가 없으면 정확히 128개 추가 토큰이 있어야 함')
    content = new_ids[:-1] if terminal else new_ids
    raw = _decode(tok, new_ids)
    answer = _decode(tok, content).strip()
    if event.get('raw_answer') != raw or event.get('answer') != answer:
        raise ValueError('GEN 원시 decode 또는 EOS 제외·strip 답변이 다름')
    finish = 'eos' if terminal else 'max_new_tokens'
    if event.get('finish_reason') != finish:
        raise ValueError('GEN 종료 사유가 추가 토큰에서 재계산한 값과 다름')
    expected_generation = dict(temperature=0., max_new=128, do_sample=False, use_cache=True, bos_added=False)
    generation = event.get('generation')
    if (not isinstance(generation, dict)
            or any(generation.get(key) != value or type(generation.get(key)) is not type(value)
                   for key, value in expected_generation.items())):
        raise ValueError('GEN 원래 greedy·cache·128·no-BOS 생성 계약이 다름')
    numeric = public.numerical(answer)
    correct = int(numeric is not None and numeric == public.numerical(original['golds'][0]))
    if type(event.get('numeric_exact')) is not int or event['numeric_exact'] != correct:
        raise ValueError('GEN 숫자 정답 일치가 원답 재계산과 다름')
    return correct


def recount_reference(events, originals, tok):
    """제공한 원형 전체를 정확히 한 번씩 재검산하고 집계와 MC 문항 결과를 반환한다."""
    original_index = _originals(originals)
    indexed = {}
    for event in events:
        if (not isinstance(event, dict) or not isinstance(event.get('case_id'), str)
                or event['case_id'] not in original_index):
            raise ValueError('원형에 없는 원답 case_id')
        case = event['case_id']
        if case in indexed:
            raise ValueError('원답 case_id 중복')
        indexed[case] = event
    if set(indexed) != set(original_index):
        raise ValueError('제공된 원형 전체의 원답이 정확히 한 번씩 있어야 함')
    summary, outcomes = {}, []
    for case, original in original_index.items():
        event = indexed[case]
        if (event.get('task') != original['task'] or type(event.get('index')) is not int
                or event['index'] != original['index'] or type(event.get('skipped')) is not bool):
            raise ValueError('원답 과제·문항 번호·제외 표시가 동결 원형과 다름')
        if 'expected_skip' in event and event['expected_skip'] != original['expected_skip']:
            raise ValueError('원답 expected_skip이 동결 원형과 다름')
        mc = original['kind'] == 'mc'
        counts = summary.setdefault(original['task'], dict(n=0, correct=0,
            char_norm_correct=0 if mc else None, skip=0, skipped=0))
        if original['expected_skip'] is not None:
            if not event['skipped'] or event.get('reason') != original['expected_skip']:
                raise ValueError('원답 제외 사유가 동결 expected_skip과 다름')
            counts['skip'] += 1
            counts['skipped'] += 1
            continue
        if event['skipped']:
            raise ValueError('동결된 적격 원형을 원답에서 제외함')
        counts['n'] += 1
        if mc:
            outcome = _mc(event, original, tok)
            outcomes.append(outcome)
            counts['correct'] += outcome['correct']
            counts['char_norm_correct'] += outcome['char_norm_correct']
        else:
            counts['correct'] += _gen(event, original, tok)
    return dict(schema=VERSION, cases=len(original_index), summary=summary, mc_outcomes=outcomes,
                source_row_set_complete=True, model_logits_computed=False, model_loaded=False,
                source_files_read=False, outcomes_order='제공된 동결 원형의 MC 순서',
                scope='제공한 원형·원답의 내부 일치 검산이며 모델·자산·선택집합 증명은 호출자 소유')
