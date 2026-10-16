"""부모 소형 진단의 원형 선정과 공개 선택형 원답만 순수 함수로 검산한다.

실물 원천·토크나이저·가중치 파일을 열지 않으며 모형이나 로짓을 만들지 않는다.
모형 답·정오를 원형 선정의 입력이나 순위에 사용하지 않는다.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import hashlib
import json
import math

VERSION = 'P106B_NIGHT_PARENT_PANEL_V1'
CONTEXT = 1024


def _sha(value):
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    for block in encoder.iterencode(value):
        digest.update(block.encode())
    return digest.hexdigest().upper()


def select_pairs(full_natural, seed=20261017, per_language=32):
    """언어별 root 해시 순으로 선정한 뒤 원래 전체 목록의 순서를 보존한다."""
    if (not isinstance(full_natural, (list, tuple)) or not full_natural
            or type(seed) is not int or type(per_language) is not int or per_language < 1):
        raise ValueError('비어 있지 않은 원형 목록·정수 seed·언어별 개수 필요')
    lanes = defaultdict(list)
    roots = set()
    forbidden = {'answer', 'model_answer', 'scores', 'correct', 'numeric_exact', 'generation'}
    for index, pair in enumerate(full_natural):
        if (not isinstance(pair, dict) or pair.get('language') not in ('ko', 'en')
                or not isinstance(pair.get('root'), str) or not pair['root']):
            raise ValueError('원래 질문 묶음의 언어와 root 필요')
        if forbidden & set(pair):
            raise ValueError('모형 원답·정오가 붙은 행은 선정 입력으로 허용하지 않음')
        if pair['root'] in roots:
            raise ValueError('전체 원형의 root 중복')
        roots.add(pair['root'])
        lanes[pair['language']].append(index)
    selected = set()
    ranking = {}
    for language in ('ko', 'en'):
        indices = lanes[language]
        if len(indices) < per_language:
            raise ValueError('언어별 고유 원형 공급 부족: ' + language)
        ranked = sorted(indices, key=lambda index: _sha([seed, language, full_natural[index]['root']]))
        chosen = ranked[:per_language]
        selected.update(chosen)
        ranking[language] = [full_natural[index]['root'] for index in chosen]
    indices = sorted(selected)
    rows = [full_natural[index] for index in indices]
    if (len(rows) != 2 * per_language or len({pair['root'] for pair in rows}) != len(rows)
            or Counter(pair['language'] for pair in rows) != dict(ko=per_language, en=per_language)):
        raise ValueError('정확한 균형·고유 부분집합 선정 실패')
    proof = dict(schema=VERSION, seed=seed, per_language=per_language,
        source_rows=len(full_natural), selected_rows=len(rows), source_indices=indices,
        source_sha256=_sha(full_natural), source_roots_sha256=_sha(sorted(roots)),
        source_ordered_roots_sha256=_sha([pair['root'] for pair in full_natural]),
        selected_sha256=_sha(rows), selected_roots_sha256=_sha(sorted(pair['root'] for pair in rows)),
        selected_ordered_roots_sha256=_sha([pair['root'] for pair in rows]),
        ranked_roots_by_language=ranking, source_order_preserved=True,
        complete_pair_dicts_unchanged=True, selection_fields=['seed', 'language', 'root'],
        model_outputs_used=False,
        selection_rule='언어별 SHA([seed, language, root]) 순으로 선택하고 전체 원형 index 순으로 반환',
        scope='부모 64질문 진단은 학생 512질문 전량과 다른 분모이며 같은 ID 교집합으로만 직접 비교')
    return copy.deepcopy(rows), proof


def _finite(value, label, nonnegative=False):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or (nonnegative and value < 0)):
        raise ValueError('유한한 원래 수치 필요: ' + label)
    return float(value)


def _prediction(value, size, label):
    if type(value) is not int or not 0 <= value < size:
        raise ValueError('선택지 범위의 정수 예측 필요: ' + label)
    return value


def _encode(tok, text):
    if not isinstance(text, str):
        raise ValueError('원래 토큰화 문자열 필요')
    result = tok.encode(text)
    ids = getattr(result, 'ids', None)
    if not isinstance(ids, (list, tuple)) or any(type(value) is not int or value < 0 for value in ids):
        raise ValueError('주어진 토크나이저의 정수 ids 목록 필요')
    return list(ids)


def _pairs(item):
    if not isinstance(item, dict):
        raise ValueError('동결된 원래 선택형 item 필요')
    if item.get('pairs'):
        pairs = item['pairs']
    else:
        if not isinstance(item.get('ctx'), str) or not isinstance(item.get('choices'), list):
            raise ValueError('동결된 문맥·선택지 목록 필요')
        pairs = [(item['ctx'], choice) for choice in item['choices']]
    if (not isinstance(pairs, (list, tuple)) or not pairs
            or any(not isinstance(pair, (list, tuple)) or len(pair) != 2
                   or any(not isinstance(text, str) for text in pair) for pair in pairs)):
        raise ValueError('완전한 선택지별 문맥·후속 문자열 목록 필요')
    return pairs


def _original_index(rows):
    expected = {}
    for row in rows:
        if (not isinstance(row, dict) or row.get('kind') != 'mc'
                or not isinstance(row.get('task'), str) or not row['task']
                or 'expected_skip' not in row or not isinstance(row.get('item'), dict)):
            raise ValueError('동결된 선택형 원형과 적격성 선언 필요')
        item = row['item']
        if not isinstance(item.get('_iid'), str) or not item['_iid']:
            raise ValueError('원래 선택형 문항 식별자 필요')
        skip = row['expected_skip']
        if skip is not None and (not isinstance(skip, str) or not skip):
            raise ValueError('제외 선언은 None 또는 비어 있지 않은 사유여야 함')
        key = (row['task'], item['_iid'])
        if key in expected:
            raise ValueError('동결된 선택형 원형 식별자 중복')
        expected[key] = row
    if not expected:
        raise ValueError('비어 있지 않은 선택형 원형 목록 필요')
    return expected


def public_mc_recount(events, original_mc_rows, tok):
    """평탄한 run_mc 원답과 source_item을 검산하고 합 NLL 선택만 집계한다."""
    expected = _original_index(original_mc_rows)
    indexed = {}
    for event in events:
        if (not isinstance(event, dict) or not isinstance(event.get('task'), str)
                or not isinstance(event.get('id'), str)):
            raise ValueError('원답 과제·문항 식별자 필요')
        key = (event['task'], event['id'])
        if key not in expected or key in indexed:
            raise ValueError('원형에 없는 원답 또는 중복 선택형 원답')
        indexed[key] = event
    if set(indexed) != set(expected):
        raise ValueError('제공된 선택형 원형 전체가 정확히 한 번씩 필요')
    totals, outcomes = {}, []
    for key, original in expected.items():
        event = indexed[key]
        item = original['item']
        if (event.get('kind') != 'mc' or type(event.get('skipped')) is not bool
                or event.get('source_item') != item):
            raise ValueError('평탄한 선택형 원답의 종류·제외 표시·source_item이 원형과 다름')
        if 'index' in event and (type(event['index']) is not int or event['index'] != original.get('index')):
            raise ValueError('원답의 원래 문항 index가 다름')
        summary = totals.setdefault(key[0], dict(n=0, correct=0, char_norm_correct=0,
            skip=0, skipped=0, prediction_counts=Counter(), char_norm_prediction_counts=Counter()))
        if original['expected_skip'] is not None:
            if not event['skipped'] or event.get('reason') != original['expected_skip']:
                raise ValueError('선택형 제외 사유가 동결 선언과 다름')
            summary['skip'] += 1
            summary['skipped'] += 1
            outcomes.append(dict(task=key[0], id=key[1], skipped=True,
                reason=original['expected_skip'], gold=item.get('gold'), pred=None,
                char_norm_pred=None, correct=None, char_norm_correct=None))
            continue
        if event['skipped']:
            raise ValueError('적격 원형의 선택형 원답을 제외함')
        pairs = _pairs(item)
        size = len(pairs)
        gold = _prediction(item.get('gold'), size, 'item.gold')
        if _prediction(event.get('gold'), size, 'gold') != gold:
            raise ValueError('원답 gold가 동결 정답과 다름')
        for name in ('sum_nll', 'mean_nll', 'n_tokens', 'n_chars', 'score'):
            if not isinstance(event.get(name), list) or len(event[name]) != size:
                raise ValueError('원답 선택지 수와 수치 목록 길이가 다름: ' + name)
        sums, chars = [], []
        for index, (prompt, continuation) in enumerate(pairs):
            cont_ids = _encode(tok, continuation)
            prompt_ids = _encode(tok, prompt) if prompt else _encode(tok, '\n')[:1]
            if not cont_ids or not prompt_ids or len(cont_ids) + len(prompt_ids) > CONTEXT:
                raise ValueError('채점한 원래 문항의 전체 토큰 예산이 깨짐')
            ntokens, nchars = event['n_tokens'][index], event['n_chars'][index]
            if type(ntokens) is not int or ntokens != len(cont_ids):
                raise ValueError('실제 후속 토큰 수와 n_tokens가 다름')
            if type(nchars) is not int or nchars != max(1, len(continuation)):
                raise ValueError('실제 유니코드 문자 수와 n_chars가 다름')
            summed = _finite(event['sum_nll'][index], 'sum_nll', True)
            mean = _finite(event['mean_nll'][index], 'mean_nll', True)
            if abs(mean * ntokens - summed) > 1e-3 + 1e-5 * summed:
                raise ValueError('평균 NLL과 토큰 수의 곱이 합 NLL과 다름')
            _finite(event['score'][index], 'score')
            sums.append(summed)
            chars.append(nchars)
        for name in ('pred_internal', 'pred_internal_norm'):
            _prediction(event.get(name), size, name)
        for name in ('margin_mean', 'margin_decision'):
            _finite(event.get(name), name)
        pred = min(range(size), key=lambda index: sums[index])
        char_pred = min(range(size), key=lambda index: sums[index] / chars[index])
        if (_prediction(event.get('pred_harness'), size, 'pred_harness') != pred
                or _prediction(event.get('pred_harness_norm'), size, 'pred_harness_norm') != char_pred):
            raise ValueError('저장된 합 NLL·문자 정규화 예측이 재계산과 다름')
        correct, char_correct = int(pred == gold), int(char_pred == gold)
        summary['n'] += 1
        summary['correct'] += correct
        summary['char_norm_correct'] += char_correct
        summary['prediction_counts'][str(pred)] += 1
        summary['char_norm_prediction_counts'][str(char_pred)] += 1
        outcomes.append(dict(task=key[0], id=key[1], skipped=False, gold=gold,
            pred=pred, char_norm_pred=char_pred, correct=correct, char_norm_correct=char_correct))
    for summary in totals.values():
        for name in ('prediction_counts', 'char_norm_prediction_counts'):
            summary[name] = dict(sorted(summary[name].items()))
    return dict(schema=VERSION, cases=len(expected), summary=totals, outcomes=outcomes,
        source_row_set_complete=True, internal_pmi_used_for_ranking=False,
        source_files_read=False, model_loaded=False, model_logits_computed=False,
        scope='제공된 원형의 집계이며 전체 완료·모델 불변·공통 적격집합 검산은 호출자 소유')
