"""고정된 TEST 64개의 view1/3 순서 차이만 검산하는 순수 진단.

원본 TRAIN 전용 producer를 TEST에 우회 적용하지 않는다. 토크나이저,
실물 파일, 모형, 토큰 확률은 호출자가 소유하며 여기서는 읽거나 계산하지 않는다.
"""
from __future__ import annotations

from collections import Counter
import copy
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_qa_data as original
from scripts.p106b_night_learning import norm_text, qa_scores
from tinylm.chat.serialize import serialize

VERSION = 'P106B_NIGHT_ORDER_PROBE_V1'
VIEWS = (1, 3)
ROOTS = 64
PER_LANGUAGE = 32
MAX_NEW = 128
CONTEXT = 1024
SOURCE_FIELDS = ('root', 'language', 'split', 'article_id', 'article_title',
                 'context_id', 'qa_id', 'source_path', 'source_sha256',
                 'context', 'question', 'answers', 'aliases')
STOP_REASONS = frozenset(('EOS', 'STOP_SEQUENCE'))
CAP_REASONS = frozenset(('MAX_NEW', 'MAX_NEW_EOS_DISABLED', 'EOS_UNAVAILABLE'))
FORBIDDEN_SOURCE_FIELDS = frozenset(('answer', 'model_answer', 'scores', 'correct', 'generation'))


def _pair(pair):
    if not isinstance(pair, dict) or FORBIDDEN_SOURCE_FIELDS & set(pair):
        raise ValueError('모형 답이나 점수가 없는 동결 원형 dict가 필요하다')
    if pair.get('language') not in ('ko', 'en') or pair.get('split') != 'test':
        raise ValueError('원래 TEST split의 한영 원형만 허용한다')
    for name in SOURCE_FIELDS[:-2]:
        if not isinstance(pair.get(name), str) or not pair[name]:
            raise ValueError('비어 있지 않은 원형 필드가 필요하다: ' + name)
    identity = pair['source_sha256']
    if len(identity) != 64 or any(c not in '0123456789abcdefABCDEF' for c in identity):
        raise ValueError('원천 파일의 SHA256이 필요하다')
    answers = pair.get('answers'); aliases = pair.get('aliases')
    if not isinstance(answers, list) or not answers:
        raise ValueError('원래 문자 위치 정답 목록이 필요하다')
    for answer in answers:
        if (not isinstance(answer, dict) or not isinstance(answer.get('text'), str)
                or not answer['text'] or type(answer.get('answer_start')) is not int
                or answer['answer_start'] < 0
                or pair['context'][answer['answer_start']:answer['answer_start'] + len(answer['text'])] != answer['text']):
            raise ValueError('원래 정답의 유니코드 문자 위치가 다르다')
    if aliases != list(dict.fromkeys(answer['text'] for answer in answers)):
        raise ValueError('고정된 원래 alias의 내용과 순서가 필요하다')
    views = pair.get('views')
    if not isinstance(views, dict) or not isinstance(views.get('1'), dict):
        raise ValueError('실제 원형의 view1 전체 dict가 필요하다')
    if views['1'] != original.render_view(pair, 1):
        raise ValueError('view1의 지시·메타·원문·정답이 원형과 다르다')
    return pair


def _question_first(pair):
    # 실제 본문에서 질문이나 구분자의 첫 위치를 검색하지 않는다.
    context_mark, question_mark = '\x00P106B_PROBE_CONTEXT\x00', '\x00P106B_PROBE_QUESTION\x00'
    while any(mark in pair['context'] or mark in pair['question'] for mark in (context_mark, question_mark)):
        context_mark += '_'; question_mark += '_'
    template = original._user(context_mark, question_mark, pair['language'], 1)
    if template.count(context_mark) != 1 or template.count(question_mark) != 1:
        raise ValueError('단일 문맥·질문 슬롯의 원래 view1 구조가 필요하다')
    prefix, rest = template.split(context_mark)
    middle, suffix = rest.split(question_mark)
    context_header = '\n지문:\n' if pair['language'] == 'ko' else '\nPassage:\n'
    question_header = '\n질문:\n' if pair['language'] == 'ko' else '\nQuestion:\n'
    if not prefix.endswith(context_header) or middle != question_header or suffix:
        raise ValueError('지시와 두 필드만 있는 원래 view1 구조가 필요하다')
    instruction = prefix[:-len(context_header)]
    before = prefix + pair['context'] + middle + pair['question'] + suffix
    after = instruction + middle + pair['question'] + context_header + pair['context'] + suffix
    if (before != original.text(pair['views']['1']['messages'][0])
            or Counter(before) != Counter(after)):
        raise ValueError('필드 순서 외의 문자 변경은 허용하지 않는다')
    return after


def messages(pair, view=3):
    """원형을 수정하지 않고 view1 또는 순서만 바꾼 view3의 user 목록을 반환한다."""
    _pair(pair)
    if type(view) is not int or view not in VIEWS:
        raise ValueError('이번 진단은 view1과 view3만 허용한다')
    result = copy.deepcopy(pair['views']['1']['messages'][:1])
    if view == 3:
        # 원본 canonical 텍스트 블록의 구조와 역할은 유지한다.
        result[0]['content'][0]['text'] = _question_first(pair)
    return result


def _case_id(pair, row_index):
    if type(row_index) is not int or not 0 <= row_index < ROOTS:
        raise ValueError('동결 64개 목록 안의 정수 index가 필요하다')
    return original.sha([VERSION, row_index, pair])


def _panel(originals):
    if not isinstance(originals, (list, tuple)) or len(originals) != ROOTS:
        raise ValueError('이미 고정된 정확히 64개의 전체 원형이 필요하다')
    roots = set(); languages = Counter()
    for pair in originals:
        _pair(pair)
        if pair['root'] in roots: raise ValueError('동결 원형 root가 중복되었다')
        roots.add(pair['root']); languages[pair['language']] += 1
    if languages != dict(ko=PER_LANGUAGE, en=PER_LANGUAGE):
        raise ValueError('원래 한영 각32개의 균형을 유지해야 한다')


def source_proof(originals):
    """선정은 하지 않고 주어진 고정64의 순서·전체 원형·두 프롬프트를 묶는다."""
    _panel(originals)
    return dict(schema=VERSION, roots=ROOTS, per_language=PER_LANGUAGE, views=list(VIEWS),
        source_panel_sha256=original.sha(originals),
        ordered_roots_sha256=original.sha([p['root'] for p in originals]),
        cases=[dict(row_index=i, case_id=_case_id(pair, i), root=pair['root'], language=pair['language'],
            case_source_sha256=original.sha(pair),
            prompt_sha256={str(view): original.sha(serialize(dict(messages=messages(pair, view)),
                'chatml', add_generation_prompt=True)) for view in VIEWS}) for i, pair in enumerate(originals)],
        source_selection_performed=False, model_answers_used=False, source_mutated=False,
        source_split='test', instruction_source_view=1, field_order_only=True,
        tokenizer_checked_by_helper=False, legacy_order640_gate_credited=False)


def _generation(answer, generation, prompt):
    if not isinstance(answer, str) or not isinstance(generation, dict):
        raise ValueError('빈 답도 보존하는 실제 문자열과 생성 메타가 필요하다')
    reason = generation.get('finish_reason')
    if (not isinstance(reason, str)
            or reason not in STOP_REASONS | CAP_REASONS | {'CONTEXT_BUDGET_EXHAUSTED'}
            or generation.get('actual_prompt_sha256') != original.sha(prompt)
            or generation.get('raw_answer_sha256') != original.sha(answer)
            or type(generation.get('requested_max_new')) is not int
            or generation['requested_max_new'] != MAX_NEW
            or type(generation.get('prompt_tokens')) is not int or generation['prompt_tokens'] <= 0):
        raise ValueError('실제 프롬프트·원답 SHA와 출력128 생성 계약이 다르다')
    count = generation.get('generated_tokens', 0)
    if type(count) is not int or not 0 <= count <= MAX_NEW:
        raise ValueError('실제 생성 토큰 수가 출력128 범위를 벗어났다')
    if 'max_new' in generation and (type(generation['max_new']) is not int or generation['max_new'] != MAX_NEW):
        raise ValueError('생성 메타의 출력상한이 고정128과 다르다')
    if reason == 'CONTEXT_BUDGET_EXHAUSTED':
        if answer or count or generation['prompt_tokens'] + MAX_NEW <= CONTEXT:
            raise ValueError('문맥 예산 초과는 원답 없이 별도로 보존해야 한다')
    elif (generation.get('max_new') != MAX_NEW or type(generation.get('max_new')) is not int
            or generation['prompt_tokens'] + MAX_NEW > CONTEXT or count < 1
            or (reason in CAP_REASONS and count != MAX_NEW)):
        raise ValueError('실제 전체 입력과 종료 및 출력상한 계약이 다르다')
    return dict(empty=int(not answer.strip()), stop=int(reason in STOP_REASONS),
        max_new=int(reason in CAP_REASONS), at_output_cap=int(count == MAX_NEW),
        context_exhausted=int(reason == 'CONTEXT_BUDGET_EXHAUSTED'), generated_tokens=count,
        finish_reason=reason)


def make_event(pair, row_index, view, answer, generation):
    """호출자가 생성한 원답에 원형 ID를 붙이며 실제 생성 SHA를 재검산한다."""
    prompt_messages = messages(pair, view)
    prompt = serialize(dict(messages=prompt_messages), 'chatml', add_generation_prompt=True)
    _generation(answer, generation, prompt)
    event = {key: copy.deepcopy(pair[key]) for key in SOURCE_FIELDS}
    event.update(schema=VERSION, frozen_row_index=row_index, case_id=_case_id(pair, row_index),
        case_source_sha256=original.sha(pair), view=view, messages=prompt_messages,
        answer=answer, generation=copy.deepcopy(generation), scores=qa_scores(answer, pair['aliases'], pair['language']))
    return event


def _verify_event(event, pair, row_index):
    view = event.get('view')
    expected_messages = messages(pair, view)
    if (event.get('schema') != VERSION or event.get('frozen_row_index') != row_index
            or event.get('case_id') != _case_id(pair, row_index)
            or event.get('case_source_sha256') != original.sha(pair)
            or any(event.get(key) != pair[key] for key in SOURCE_FIELDS)
            or event.get('messages') != expected_messages):
        raise ValueError('원답의 고정 index·ID·출처·alias·원문·순서가 다르다')
    prompt = serialize(dict(messages=expected_messages), 'chatml', add_generation_prompt=True)
    generation = _generation(event.get('answer'), event.get('generation'), prompt)
    scores = qa_scores(event['answer'], pair['aliases'], pair['language'])
    stored = event.get('scores')
    if (not isinstance(stored, dict) or set(stored) != set(scores)
            or any(type(stored[key]) not in (int, float) or not math.isfinite(stored[key])
                   or stored[key] != scores[key] for key in scores)):
        raise ValueError('저장된 점수가 실제 원답과 원래 alias의 재계산과 다르다')
    return generation


def _metrics(events, generations):
    n = len(events)
    result = dict(n=n, roots=n)
    for metric in ('em', 'f1', 'raw_exact'):
        result[metric + '_sum'] = sum(e['scores'][metric] for e in events)
        result[metric] = result[metric + '_sum'] / n
    for metric in ('empty', 'stop', 'max_new', 'at_output_cap', 'context_exhausted', 'generated_tokens'):
        result[metric] = sum(g[metric] for g in generations)
    result['finish_reasons'] = dict(sorted(Counter(g['finish_reason'] for g in generations).items()))
    return result


def _paired(groups):
    result = Counter(); n = len(groups)
    for left, right in groups:
        a, b = left['scores']['em'] == 1., right['scores']['em'] == 1.
        result['both_correct' if a and b else 'correct_to_wrong' if a else 'wrong_to_correct' if b else 'both_wrong'] += 1
        x, y = norm_text(left['answer'], left['language']), norm_text(right['answer'], right['language'])
        result['same_wrong'] += int(not a and not b and bool(x) and x == y)
        result['same_wrong_including_empty'] += int(not a and not b and x == y)
        result['raw_same_wrong'] += int(not a and not b and bool(left['answer']) and left['answer'] == right['answer'])
        result['both_empty'] += int(not left['answer'].strip() and not right['answer'].strip())
    out = {key: result[key] for key in ('both_correct', 'correct_to_wrong', 'wrong_to_correct', 'both_wrong',
        'same_wrong', 'same_wrong_including_empty', 'raw_same_wrong', 'both_empty')}
    out.update(n=n, direction='view1_to_view3',
        same_wrong_rule='양쪽 EM0이며 정규화된 비어 있지 않은 답이 같음; 빈 답과 원문 일치는 별도 집계')
    for metric in ('em', 'f1', 'raw_exact'):
        out[metric + '_delta_view3_minus_view1'] = sum(r['scores'][metric] - l['scores'][metric] for l, r in groups) / n
    return out


def summarize(events, originals):
    """같은64 root의 view1/3 각 한 번만 인정하고 원래 alias의 한정 점수를 집계한다."""
    proof = source_proof(originals)
    if not isinstance(events, (list, tuple)) or len(events) != ROOTS * len(VIEWS):
        raise ValueError('같은64 원형의 두 view 원답128개가 필요하다')
    indexed = {}; generations = {}
    for event in events:
        if not isinstance(event, dict): raise ValueError('실제 원답 dict가 필요하다')
        index, view = event.get('frozen_row_index'), event.get('view')
        if type(index) is not int or not 0 <= index < ROOTS or type(view) is not int or view not in VIEWS:
            raise ValueError('동결64의 정수 index와 view1/3이 필요하다')
        key = index, view
        if key in indexed: raise ValueError('같은 원형과 view의 원답이 중복되었다')
        generations[key] = _verify_event(event, originals[index], index); indexed[key] = event
    if set(indexed) != {(i, view) for i in range(ROOTS) for view in VIEWS}:
        raise ValueError('고정64 원형의 view1/3 전체가 필요하다')
    def group(indices):
        return dict(roots=len(indices), by_view={str(view): _metrics([indexed[i, view] for i in indices],
            [generations[i, view] for i in indices]) for view in VIEWS},
            paired=_paired([(indexed[i, 1], indexed[i, 3]) for i in indices]))
    return dict(schema=VERSION, status='ORDER_PROBE_RAW_RECOUNTED', roots=ROOTS, cases=len(indexed),
        views=list(VIEWS), source_panel_sha256=proof['source_panel_sha256'],
        ordered_roots_sha256=proof['ordered_roots_sha256'], overall=group(list(range(ROOTS))),
        by_language={language: group([i for i, p in enumerate(originals) if p['language'] == language])
            for language in ('ko', 'en')},
        scoring='p106b_night_learning.qa_scores를 사용한 원래 source alias 기준 한정 점수',
        field_order_only=True, instruction_source_view=1, held_view2_used=False,
        source_selection_performed=False, source_mutated=False, model_probabilities_computed=False,
        world_truth_certified=False, semantic_review_performed=False, training_performed=False,
        legacy_order640_gate_credited=False, tokenizer_checks_owned_by_controller=True)
