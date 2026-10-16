"""같은 본문의 두 질문과 두 답에 대한 view0 조건부 로그확률 진단.

원형 메타와 후보 답을 분리하며 학습·파일 IO·모형 생성·가중치 로딩은 하지 않는다.
양의 gap도 품질 통과나 의미상 음성의 판정이 아니다.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
import torch.nn.functional as F
from tinylm.chat.serialize import serialize, loss_spans
from tinylm.train.mtp_sft import encode_record
from scripts import p106b_night_qa_data as data
from scripts import p106b_night_question_bundles as source
from scripts.p106b_night_learning import qa_scores

VERSION = 'P106B_NIGHT_QUESTION_SCORES_V1'
METRICS = ('content_sum', 'content_mean', 'first_content', 'eot', 'eot_included_sum', 'eot_included_mean')
IDENTITY = ('bundle_id', 'cell_id', 'record_sha256', 'language', 'question_index', 'candidate_index',
            'question_root', 'candidate_root', 'content_token_count', 'eot_token_id')


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _record_sha(cell):
    return data.sha({key: cell[key] for key in ('x', 'y', 'segments', 'content_positions',
        'content_target_ids', 'eot_position', 'eot_token_id')})


def _cell_id(cell):
    return data.sha([VERSION, cell['bundle_id'], cell['question_index'], cell['candidate_index'],
        cell['question_root'], cell['candidate_root'], cell['record_sha256'],
        cell['row'], cell['scoring_candidate']])


def _cell(cell):
    if not isinstance(cell, dict): raise ValueError('동결된 채점 cell dict가 필요하다')
    for key in ('x', 'y', 'segments', 'content_positions', 'content_target_ids'):
        if not isinstance(cell.get(key), list) or any(type(v) is not int for v in cell[key]):
            raise ValueError('실제 정수 목록이 필요하다: ' + key)
    x, y, seg = cell['x'], cell['y'], cell['segments']
    positions, targets = cell['content_positions'], cell['content_target_ids']
    eot, end = cell.get('eot_token_id'), cell.get('eot_position')
    if (not 1 <= len(x) <= 1024 or len(x) != len(y) or len(x) != len(seg)
            or any(v < 0 for v in x) or not positions or len(positions) != len(targets)
            or type(eot) is not int or eot < 0 or type(end) is not int
            or cell.get('content_token_count') != len(targets)
            or type(cell.get('content_token_count')) is not int
            or positions != list(range(positions[0], end)) or not 0 <= positions[0] < end < len(x)
            or any(v < 0 or v == eot for v in targets)
            or [i for i, v in enumerate(y) if v != -100] != positions + [end]
            or [y[i] for i in positions] != targets or y[end] != eot
            or any(seg[i] != (1 if y[i] != -100 else 0) for i in range(len(y)))
            or any(y[i] != x[i + 1] for i in positions + [end] if i + 1 < len(x))
            or cell.get('record_sha256') != _record_sha(cell)
            or cell.get('cell_id') != _cell_id(cell)):
        raise ValueError('완전한 내용 토큰·별도 EOT·실제 shifted predictor 계약이 다르다')
    return positions + [end], targets + [eot]


def _encode(case, candidate, tok, bundle_id, qi, ai):
    for field in ('split', 'article_title', 'qa_id'):
        if not isinstance(case.get(field), str) or not case[field]:
            raise ValueError('render_view에 필요한 원래 메타가 필요하다: ' + field)
    original = data.render_view(case, 0)
    if 'views' in case and case.get('views', {}).get('0') != original:
        raise ValueError('저장된 원래 view0 메타·원문·정답이 다르다')
    row = copy.deepcopy(original)
    answer = candidate['aliases'][0]
    row['messages'][1]['content'] = [dict(type='text', text=answer)]
    if row['meta'] != original['meta']: raise ValueError('source 질문 메타를 바꾸면 안 된다')
    record = encode_record(row, tok, context=1024)
    ids, labels, text = data.encode_view(row, tok)
    encoded = tok.encode(text); offsets = list(encoded.offsets)
    spans = loss_spans(row, 'chatml')
    eot = tok.token_to_id('<|im_end|>'); pad = tok.token_to_id('<pad>')
    if (type(eot) is not int or eot < 0 or list(encoded.ids) != ids or len(offsets) != len(ids)
            or len(spans) != 1 or record.x != ids[:-1] or record.y != labels[1:]
            or len(record.x) > 1024):
        raise ValueError('실제 encoder와 완전한 단일턴 shift가 같아야 한다')
    start, finish = spans[0]; body_end = finish - len('<|im_end|>')
    if text[start:body_end] != answer or text[body_end:finish] != '<|im_end|>':
        raise ValueError('정확한 assistant 내용과 EOT 문자 구간이 필요하다')
    content_full = []; end_full = []; coverage = []
    for i, offset in enumerate(offsets):
        if (not isinstance(offset, (list, tuple)) or len(offset) != 2
                or any(type(v) is not int for v in offset) or not 0 <= offset[0] <= offset[1] <= len(text)):
            raise ValueError('실제 유니코드 문자 offsets가 필요하다')
        a, b = offset
        if start <= a < b <= body_end:
            content_full.append(i); coverage.append((a, b))
        if (a, b) == (body_end, finish) and ids[i] == eot: end_full.append(i)
    cursor = start
    for a, b in sorted(coverage):
        if a > cursor: raise ValueError('BPE 경계 때문에 내용 문자가 감독에서 빠졌다')
        cursor = max(cursor, b)
    if (cursor != body_end or not content_full or min(content_full) < 1 or len(end_full) != 1
            or any(ids[i] == eot or (pad is not None and ids[i] == pad) for i in content_full)):
        raise ValueError('내용 전체를 수용하고 EOT 하나를 별도로 구별해야 한다')
    cell = dict(bundle_id=bundle_id, language=case['language'], question_index=qi, candidate_index=ai,
        question_root=case['root'], candidate_root=candidate['root'], row=row,
        scoring_candidate=dict(root=candidate['root'], text=answer, alias_index=0,
            source_aliases=copy.deepcopy(candidate['aliases']), diagnostic_only=True),
        x=list(record.x), y=list(record.y), segments=list(record.segments),
        content_positions=[i - 1 for i in content_full], content_target_ids=[ids[i] for i in content_full],
        content_token_count=len(content_full), eot_position=end_full[0] - 1, eot_token_id=eot,
        proof=dict(assistant_content_char_range=[start, body_end], eot_char_range=[body_end, finish],
            serialized_sha256=data.sha(text), full_ids_sha256=data.sha(ids),
            source_meta_sha256=data.sha(original['meta']), complete_content_coverage=True,
            shifted_encoder_exact=True, model_forward=False, training_example=False))
    cell['record_sha256'] = _record_sha(cell); cell['cell_id'] = _cell_id(cell); _cell(cell)
    return cell


def build_records(cases, tok):
    """주어진 두 원형을 root 순으로 고정하고 네 개의 JSON-safe 채점 cell을 반환한다."""
    census = source.census(cases)
    if len(cases) != 2 or census['counts']['exact_two_groups'] != 1:
        raise ValueError('같은 언어·기사·본문·원천의 두 source 질문이 필요하다')
    originals = sorted(copy.deepcopy(cases), key=lambda case: case['root'])
    identity = data.sha([VERSION, originals])
    cells = [_encode(originals[qi], originals[ai], tok, identity, qi, ai) for qi in range(2) for ai in range(2)]
    for ai in range(2):
        left, right = cells[ai], cells[2 + ai]
        if left['content_target_ids'] != right['content_target_ids'] or left['eot_token_id'] != right['eot_token_id']:
            raise ValueError('같은 후보 답의 두 질문 target ID가 달라 BPE 길이 대조가 무효다')
    result = dict(schema=VERSION, bundle_id=identity, language=originals[0]['language'], roots=[c['root'] for c in originals],
        source_cases=originals, source_bundle_definition_sha256=data.sha(census['bundles'][0]), cells=cells,
        view=0, first_alias_only=True, source_meta_preserved=True, training_examples_generated=False,
        whole_source_group_cardinality_owned_by_controller=True)
    return result


def _metrics(logprobs):
    if (not isinstance(logprobs, list) or len(logprobs) < 2
            or any(not _finite(v) or v > 0 for v in logprobs)):
        raise ValueError('비어 있지 않은 내용과 별도 EOT의 유한한 로그확률이 필요하다')
    content = logprobs[:-1]; total = sum(content)
    result = dict(content_sum=total, content_mean=total / len(content), first_content=content[0],
        eot=logprobs[-1], eot_included_sum=total + logprobs[-1],
        eot_included_mean=(total + logprobs[-1]) / len(logprobs))
    if any(not _finite(v) for v in result.values()): raise ValueError('집계 로그확률이 유한하지 않다')
    return result


def _event(cell, logprobs):
    _cell(cell)
    if len(logprobs) != cell['content_token_count'] + 1: raise ValueError('내용 길이와 EOT 하나의 수가 다르다')
    return dict({field: copy.deepcopy(cell[field]) for field in IDENTITY}, schema=VERSION,
        content_target_ids=copy.deepcopy(cell['content_target_ids']), token_logprobs=logprobs,
        metrics=_metrics(logprobs), softmax_precision='FP32', training_performed=False)


def _selected(logits, targets):
    if (not isinstance(logits, torch.Tensor) or logits.ndim != 2 or not logits.is_floating_point()
            or logits.shape[0] != len(targets) or logits.shape[1] < 2
            or any(not 0 <= t < logits.shape[1] for t in targets)
            or not bool(torch.isfinite(logits.float()).all())):
        raise ValueError('전체 어휘의 유한한 실제 predictor logits와 범위 안 target이 필요하다')
    target = torch.tensor(targets, dtype=torch.long, device=logits.device)
    values = F.log_softmax(logits.float(), dim=-1).gather(1, target[:, None]).squeeze(1)
    return values.detach().cpu().tolist()


def score_logits(cell, logits):
    """실제 x 길이의 [T,V]에서 shifted 내용/EOT predictor만 채점한다."""
    positions, targets = _cell(cell)
    if (not isinstance(logits, torch.Tensor) or logits.ndim != 2 or logits.shape[0] != len(cell['x'])
            or not logits.is_floating_point() or not bool(torch.isfinite(logits).all())):
        raise ValueError('padding 없이 실제 x 길이와 같은 유한한 [T,V] logits가 필요하다')
    with torch.no_grad(): return _event(cell, _selected(logits[positions], targets))


def score_hidden(cell, hidden, head, chunk=128):
    """[T,H]의 실제 predictor만 모아 head([1,N,H])→[1,N,V]로 작은 청크를 채점한다."""
    positions, targets = _cell(cell)
    if (not isinstance(hidden, torch.Tensor) or hidden.ndim != 2 or hidden.shape[0] != len(cell['x'])
            or hidden.shape[1] < 1 or not hidden.is_floating_point() or not bool(torch.isfinite(hidden).all())
            or not callable(head) or type(chunk) is not int or chunk < 1):
        raise ValueError('padding 없는 실제 [T,H]와 head callable 및 양의 정수 chunk가 필요하다')
    values = []
    with torch.no_grad():
        for start in range(0, len(positions), chunk):
            pos = positions[start:start + chunk]; output = head(hidden[pos].unsqueeze(0))
            if not isinstance(output, torch.Tensor) or output.ndim != 3 or output.shape[:2] != (1, len(pos)):
                raise ValueError('head는 실제 청크와 같은 [1,N,V]를 반환해야 한다')
            values.extend(_selected(output[0], targets[start:start + chunk]))
    return _event(cell, values)


def _bundles(bundles):
    if not isinstance(bundles, (list, tuple)) or not bundles: raise ValueError('동결된 채점 bundle 전체 목록이 필요하다')
    indexed = {}; roots = {}
    for bundle in bundles:
        if not isinstance(bundle, dict) or bundle.get('schema') != VERSION: raise ValueError('원래 채점 bundle이 필요하다')
        cases = bundle['source_cases']; census = source.census(cases)
        if (len(cases) != 2 or census['counts']['exact_two_groups'] != 1
                or [c['root'] for c in cases] != sorted(c['root'] for c in cases)
                or bundle['bundle_id'] != data.sha([VERSION, cases])
                or bundle.get('language') != cases[0]['language'] or bundle.get('roots') != [c['root'] for c in cases]
                or type(bundle.get('view')) is not int or bundle['view'] != 0
                or bundle.get('source_bundle_definition_sha256') != data.sha(census['bundles'][0])
                or bundle.get('first_alias_only') is not True or bundle.get('source_meta_preserved') is not True
                or bundle.get('training_examples_generated') is not False or len(bundle.get('cells', [])) != 4):
            raise ValueError('원래 source 두 질문과 고정 view0 2×2가 필요하다')
        if bundle['bundle_id'] in indexed: raise ValueError('bundle이 중복되었다')
        seen = {}
        for cell in bundle['cells']:
            _cell(cell); qi, ai = cell.get('question_index'), cell.get('candidate_index')
            if type(qi) is not int or type(ai) is not int or qi not in (0, 1) or ai not in (0, 1) or (qi, ai) in seen:
                raise ValueError('중복 없는 두 질문×두 후보가 필요하다')
            expected = data.render_view(cases[qi], 0); expected['messages'][1]['content'] = [dict(type='text', text=cases[ai]['aliases'][0])]
            if (cell['row'] != expected or cell['bundle_id'] != bundle['bundle_id']
                    or cell['language'] != bundle['language'] or cell['question_root'] != cases[qi]['root']
                    or cell['candidate_root'] != cases[ai]['root']
                    or cell['scoring_candidate'] != dict(root=cases[ai]['root'], text=cases[ai]['aliases'][0], alias_index=0,
                        source_aliases=cases[ai]['aliases'], diagnostic_only=True)):
                raise ValueError('원래 질문 메타와 별도 scoring 후보가 다르다')
            seen[qi, ai] = cell
        for ai in range(2):
            if (seen[0, ai]['content_target_ids'] != seen[1, ai]['content_target_ids']
                    or seen[0, ai]['eot_token_id'] != seen[1, ai]['eot_token_id']):
                raise ValueError('같은 답의 두 질문 target ID가 다르다')
        for case in cases:
            if case['root'] in roots: raise ValueError('서로 다른 bundle에서 source root가 중복되었다')
            roots[case['root']] = case
        indexed[bundle['bundle_id']] = bundle, seen
    return indexed, roots


def _free(events, cases):
    if events is None: return None
    if not isinstance(events, (list, tuple)) or len(events) != len(cases): raise ValueError('같은 source의 view0 자유답 전체가 필요하다')
    indexed = {}
    for event in events:
        root = event.get('root') if isinstance(event, dict) else None
        if root not in cases or root in indexed or type(event.get('view')) is not int or event['view'] != 0:
            raise ValueError('중복 없는 같은 source root의 view0 자유답만 필요하다')
        case = cases[root]
        if any(event.get(k) != case[k] for k in ('language', 'question', 'context', 'aliases')) or not isinstance(event.get('answer'), str):
            raise ValueError('자유답의 원래 질문·본문·언어·alias가 다르다')
        expected = qa_scores(event['answer'], case['aliases'], case['language']); observed = event.get('scores')
        if (not isinstance(observed, dict) or set(observed) != set(expected)
                or any(not _finite(observed[k]) or observed[k] != expected[k] for k in expected)):
            raise ValueError('자유답의 저장 점수와 원답 재계산이 다르다')
        indexed[root] = event
    return indexed


def _gap_stats(values):
    if any(not _finite(v) for v in values): raise ValueError('유한한 질문 조건부 gap이 필요하다')
    mean = sum(values) / len(values) if values else None
    if mean is not None and not _finite(mean): raise ValueError('질문 조건부 gap 평균이 유한하지 않다')
    return dict(n=len(values), positive=sum(v > 0 for v in values), zero=sum(v == 0 for v in values),
        negative=sum(v < 0 for v in values), mean=mean)


def summarize(events, bundles, free_events=None):
    """같은 후보의 right-question−other-question을 두 방향으로 계산한다."""
    expected, cases = _bundles(bundles); free = _free(free_events, cases)
    if not isinstance(events, (list, tuple)) or len(events) != len(expected) * 4: raise ValueError('각 고정 bundle의 네 채점 원답이 필요하다')
    indexed = {}
    for event in events:
        if not isinstance(event, dict) or event.get('bundle_id') not in expected: raise ValueError('등록된 bundle 채점 원답이 필요하다')
        qi, ai = event.get('question_index'), event.get('candidate_index')
        if type(qi) is not int or type(ai) is not int or qi not in (0, 1) or ai not in (0, 1): raise ValueError('실제 질문·후보 index가 필요하다')
        key = event['bundle_id'], qi, ai
        if key in indexed: raise ValueError('채점 cell 원답이 중복되었다')
        cell = expected[event['bundle_id']][1][qi, ai]
        metrics = _metrics(event.get('token_logprobs'))
        stored = event.get('metrics')
        if (event.get('schema') != VERSION or event.get('softmax_precision') != 'FP32'
                or event.get('training_performed') is not False
                or any(event.get(k) != cell[k] for k in IDENTITY)
                or event.get('content_target_ids') != cell['content_target_ids']
                or len(event.get('token_logprobs', [])) != cell['content_token_count'] + 1
                or not isinstance(stored, dict) or set(stored) != set(metrics)
                or any(not _finite(stored[k]) or stored[k] != metrics[k] for k in metrics)):
            raise ValueError('동결 레코드·내용 길이·EOT·실제 토큰 점수가 다르다')
        indexed[key] = event
    outcomes = []
    for identity, (bundle, cells) in expected.items():
        matrix = {metric: [[indexed[identity, qi, ai]['metrics'][metric] for ai in range(2)] for qi in range(2)] for metric in METRICS}
        gaps = {metric: [matrix[metric][ai][ai] - matrix[metric][1 - ai][ai] for ai in range(2)] for metric in METRICS}
        both = None if free is None else all(free[root]['scores']['em'] == 1. for root in bundle['roots'])
        outcomes.append(dict(bundle_id=identity, language=bundle['language'], roots=bundle['roots'],
            score_matrix=matrix, gaps=gaps, free_view0_both_correct=both))
    def aggregate(rows):
        return dict(bundles=len(rows), gaps={metric: _gap_stats([v for row in rows for v in row['gaps'][metric]]) for metric in METRICS},
            by_free_view0=None if free is None else {label: {metric: _gap_stats([v for row in rows
                if row['free_view0_both_correct'] is condition for v in row['gaps'][metric]]) for metric in METRICS}
                for label, condition in (('both_correct', True), ('not_both_correct', False))})
    return dict(schema=VERSION, status='QUESTION_SCORE_RAW_RECOUNTED', cells=len(indexed), outcomes=outcomes,
        overall=aggregate(outcomes), by_language={language: aggregate([r for r in outcomes if r['language'] == language]) for language in ('ko', 'en')},
        metrics=list(METRICS), gap_definition='각 후보 답을 고정한 right-question minus other-question; 두 방향을 각각 보존',
        view=0, first_alias_only=True, scoring_candidate_is_semantic_negative=False,
        quality_pass_declared=False, training_performed=False, model_loaded_by_helper=False,
        source_bundles_reselected=False, free_answers_used_for_selection=False)
