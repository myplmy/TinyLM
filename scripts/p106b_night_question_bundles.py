"""인자로 받은 원형 QA의 두 질문 묶음과 실제 답을 순수 함수로 검산한다.

문자상 분리 후보는 의미상 음성이나 학습예제가 아니다. 파일·토크나이저·
가중치·모형을 열지 않으며 실제 답으로 source 묶음을 다시 고르지 않는다.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_night_learning import qa_scores

VERSION = 'P106B_NIGHT_QUESTION_BUNDLES_V1'
VIEWS = (0, 1, 2)
SOURCE_FIELDS = ('root', 'language', 'article_id', 'context_id', 'context', 'question',
                 'answers', 'aliases', 'source_path', 'source_sha256')
GROUP_FIELDS = ('language', 'article_id', 'context_id', 'source_path', 'source_sha256',
                'context_exact_sha256')
CATEGORIES = ('same_alias', 'alias_containment', 'span_overlap', 'same_question',
              'character_distinct_candidate')
FORBIDDEN_SOURCE = frozenset(('answer', 'model_answer', 'scores', 'correct', 'generation'))
NORMALIZATION = 'NFKC → 공백 구간을 한 칸으로 정리 → casefold; 숫자·부정·부호·소수점·문장부호 제거 없음'


def _sha(value):
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = hashlib.sha256()
    for part in encoder.iterencode(value): digest.update(part.encode('utf-8'))
    return digest.hexdigest().upper()


def normalized(text):
    """문자 비교만을 위한 제한된 정규화이며 정오 채점기를 대체하지 않는다."""
    if not isinstance(text, str): raise ValueError('비교할 원래 문자열이 필요하다')
    return ' '.join(unicodedata.normalize('NFKC', text).split()).casefold()


def _source_case(case):
    if not isinstance(case, dict) or FORBIDDEN_SOURCE & set(case):
        raise ValueError('모형 원답이나 점수가 붙지 않은 source 원형 dict가 필요하다')
    for field in SOURCE_FIELDS:
        if field in ('answers', 'aliases'): continue
        if not isinstance(case.get(field), str) or not case[field].strip():
            raise ValueError('비어 있지 않은 source 문자열이 필요하다: ' + field)
    if case['language'] not in ('ko', 'en'): raise ValueError('한영 source 언어가 필요하다')
    identity = case['source_sha256']
    if len(identity) != 64 or any(c not in '0123456789abcdefABCDEF' for c in identity):
        raise ValueError('원천 파일의 SHA256 문자열이 필요하다')
    answers, aliases = case.get('answers'), case.get('aliases')
    if not isinstance(answers, list) or not answers:
        raise ValueError('원래 정답과 문자 위치의 비어 있지 않은 목록이 필요하다')
    for answer in answers:
        if (not isinstance(answer, dict) or not isinstance(answer.get('text'), str)
                or not normalized(answer['text']) or type(answer.get('answer_start')) is not int
                or answer['answer_start'] < 0
                or case['context'][answer['answer_start']:answer['answer_start'] + len(answer['text'])] != answer['text']):
            raise ValueError('정답의 원래 유니코드 문자 구간이 본문과 다르다')
    expected_aliases = list(dict.fromkeys(answer['text'] for answer in answers))
    if not isinstance(aliases, list) or aliases != expected_aliases:
        raise ValueError('alias는 원래 정답 문자열의 중복 제거 순서와 정확히 같아야 한다')
    return {field: copy.deepcopy(case[field]) for field in SOURCE_FIELDS}


def _relation(left, right):
    a, b = [list(dict.fromkeys(normalized(alias) for alias in case['aliases'])) for case in (left, right)]
    same_alias = bool(set(a) & set(b))
    alias_containment = any(x != y and (x in y or y in x) for x in a for y in b)
    left_spans = [(v['answer_start'], v['answer_start'] + len(v['text'])) for v in left['answers']]
    right_spans = [(v['answer_start'], v['answer_start'] + len(v['text'])) for v in right['answers']]
    span_overlap = any(max(x[0], y[0]) < min(x[1], y[1]) for x in left_spans for y in right_spans)
    same_question = normalized(left['question']) == normalized(right['question'])
    flags = dict(same_alias=same_alias, alias_containment=alias_containment,
        span_overlap=span_overlap, same_question=same_question)
    category = next((key for key in CATEGORIES[:-1] if flags[key]), CATEGORIES[-1])
    return category, flags, [a, b], [left_spans, right_spans]


def _bundle(key, members):
    ordered = sorted(members, key=lambda case: case['root'])
    category, flags, aliases, spans = _relation(*ordered)
    case_shas = [_sha(case) for case in ordered]
    return dict(bundle_id=_sha([VERSION, list(key), case_shas]),
        source={field: value for field, value in zip(GROUP_FIELDS, key)},
        language=key[0], roots=[case['root'] for case in ordered], case_sha256=case_shas,
        question_sha256=[_sha(case['question']) for case in ordered],
        aliases=[copy.deepcopy(case['aliases']) for case in ordered], normalized_aliases=aliases,
        answer_char_ranges=[[list(span) for span in case_spans] for case_spans in spans],
        category=category, relation_flags=flags,
        character_distinct_candidate=category == 'character_distinct_candidate',
        semantic_negative=False, training_example=False)


def _counts(groups, bundles, cases):
    return dict(cases=len(cases), source_groups=len(groups),
        group_size_histogram={str(size): n for size, n in sorted(Counter(len(m) for m in groups.values()).items())},
        exact_two_groups=len(bundles), bundled_cases=2 * len(bundles),
        unbundled_cases=len(cases) - 2 * len(bundles),
        categories={category: sum(b['category'] == category for b in bundles) for category in CATEGORIES},
        relation_flags={flag: sum(b['relation_flags'][flag] for b in bundles) for flag in CATEGORIES[:-1]})


def _build(cases):
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError('비어 있지 않은 전체 source 원형 목록이 필요하다')
    index, groups, contexts, sources = {}, defaultdict(list), {}, {}
    ordered = []
    for original in cases:
        case = _source_case(original); root = case['root']
        if root in index: raise ValueError('전체 source 원형의 root가 중복되었다')
        canonical_context = normalized(case['context'])
        if case['context_id'] in contexts and contexts[case['context_id']] != canonical_context:
            raise ValueError('같은 context_id의 정규화 본문이 서로 다르다')
        if case['source_path'] in sources and sources[case['source_path']] != case['source_sha256']:
            raise ValueError('같은 source_path의 원천 SHA가 서로 다르다')
        contexts[case['context_id']] = canonical_context; sources[case['source_path']] = case['source_sha256']
        index[root] = case; ordered.append(case)
        # The collector IDs normalized text. Distinct raw paragraphs must remain
        # distinct model inputs, even when their normalized context_id agrees.
        key = tuple(case[field] for field in GROUP_FIELDS[:-1]) + (_sha(case['context']),)
        groups[key].append(case)
    bundles = sorted((_bundle(key, members) for key, members in groups.items() if len(members) == 2),
        key=lambda bundle: bundle['bundle_id'])
    by_language = {}
    for language in ('ko', 'en'):
        lang_cases = [case for case in ordered if case['language'] == language]
        lang_groups = {key: members for key, members in groups.items() if key[0] == language}
        lang_bundles = [bundle for bundle in bundles if bundle['language'] == language]
        by_language[language] = _counts(lang_groups, lang_bundles, lang_cases)
    report = dict(schema=VERSION, status='SOURCE_ONLY_BUNDLE_CENSUS',
        counts=_counts(groups, bundles, ordered), by_language=by_language,
        source_ordered_sha256=_sha(ordered), source_set_sha256=_sha([index[root] for root in sorted(index)]),
        bundle_set_sha256=_sha(bundles), bundles=bundles,
        source_identity_fields=list(SOURCE_FIELDS), source_group_fields=list(GROUP_FIELDS),
        grouping='정규화 context_id와 별도로 정확한 원문 SHA를 사용; source 전체에서 정확히 두 root인 그룹만 포함; 세 개 이상에서 두 개를 고르지 않음',
        category_precedence=list(CATEGORIES), normalization=NORMALIZATION,
        label_contract='원래 answers의 유니코드 문자 구간 일치와 alias 목록 일치만 검산; 의미상 정답성 인증 아님',
        candidates_are_semantic_negatives=False, training_examples_generated=False,
        model_answers_used_for_selection=False, source_files_read=False)
    return index, bundles, report


def census(cases):
    """원형만으로 묶음·분류·해시·언어별 전수 계수를 반환한다."""
    return _build(cases)[2]


def _events(events, cases):
    if not isinstance(events, (list, tuple)) or len(events) != len(cases) * len(VIEWS):
        raise ValueError('전체 source의 view0/1/2 원답이 빠짐없이 필요하다')
    indexed = {}
    for event in events:
        if not isinstance(event, dict): raise ValueError('실제 원답 dict가 필요하다')
        root, view = event.get('root'), event.get('view')
        if not isinstance(root, str) or root not in cases or type(view) is not int or view not in VIEWS:
            raise ValueError('전체 원형에 있는 root와 정수 view0/1/2가 필요하다')
        case = cases[root]
        language = event.get('language') if 'language' in event else event.get('lang')
        if language != case['language'] or ('lang' in event and event['lang'] != language):
            raise ValueError('실제 원답의 원형 언어가 다르다')
        for field in ('question', 'context', 'aliases'):
            if event.get(field) != case[field]: raise ValueError('실제 원답의 원형 필드가 다르다: ' + field)
        for field in SOURCE_FIELDS:
            if field in event and event[field] != case[field]:
                raise ValueError('원답에 붙은 source 필드가 원형과 다르다: ' + field)
        if not isinstance(event.get('answer'), str): raise ValueError('빈 답도 보존하는 실제 원답 문자열이 필요하다')
        expected = qa_scores(event['answer'], case['aliases'], case['language']); scores = event.get('scores')
        if (not isinstance(scores, dict) or set(scores) != set(expected)
                or any(type(scores[key]) not in (int, float) or not math.isfinite(scores[key])
                       or scores[key] != expected[key] for key in expected)):
            raise ValueError('저장 점수가 원답과 원래 alias로 재계산한 점수와 다르다')
        key = root, view
        if key in indexed: raise ValueError('같은 root와 view의 원답이 중복되었다')
        indexed[key] = event
    if set(indexed) != {(root, view) for root in cases for view in VIEWS}:
        raise ValueError('묶음 밖 질문도 포함한 전체 source 원답 집합이 필요하다')
    return indexed


def _metrics(bundles, events, view):
    result = dict(n=len(bundles), roots=2 * len(bundles), both_correct=0, one_correct=0, both_wrong=0,
        same_output=0, changed_output=0, same_wrong=0, same_wrong_including_empty=0,
        raw_same_output=0, both_empty=0, em_sum=0., f1_sum=0., raw_exact_sum=0.)
    for bundle in bundles:
        left, right = [events[root, view] for root in bundle['roots']]
        a, b = left['scores']['em'] == 1., right['scores']['em'] == 1.
        result['both_correct' if a and b else 'one_correct' if a or b else 'both_wrong'] += 1
        x, y = normalized(left['answer']), normalized(right['answer'])
        same = x == y
        result['same_output'] += int(same); result['changed_output'] += int(not same)
        result['same_wrong'] += int(not a and not b and same and bool(x))
        result['same_wrong_including_empty'] += int(not a and not b and same)
        result['raw_same_output'] += int(left['answer'] == right['answer'])
        result['both_empty'] += int(not left['answer'].strip() and not right['answer'].strip())
        for metric in ('em', 'f1', 'raw_exact'):
            result[metric + '_sum'] += left['scores'][metric] + right['scores'][metric]
    for metric in ('em', 'f1', 'raw_exact'):
        result[metric] = result[metric + '_sum'] / result['roots'] if result['roots'] else None
    return result


def _summary(bundles, events):
    return dict(bundles=len(bundles), by_view={str(view): _metrics(bundles, events, view) for view in VIEWS},
        by_category={category: {str(view): _metrics([b for b in bundles if b['category'] == category], events, view)
            for view in VIEWS} for category in CATEGORIES})


def summarize(events, cases):
    """source에서 먼저 정한 묶음을 유지하고 전체 원형의 실제 점수를 재검산한다."""
    index, bundles, source = _build(cases); indexed = _events(events, index)
    return dict(schema=VERSION, status='QUESTION_BUNDLE_RAW_RECOUNTED',
        source_census=source, source_census_sha256=_sha(source), cases=len(index), events=len(indexed), views=list(VIEWS),
        overall=_summary(bundles, indexed),
        by_language={language: _summary([b for b in bundles if b['language'] == language], indexed)
            for language in ('ko', 'en')}, normalization=NORMALIZATION,
        scoring='scripts.p106b_night_learning.qa_scores를 원답과 고정 alias로 재계산; EM1을 개별 정답으로 사용',
        same_output_rule='NFKC·공백정리·casefold 후 같음; 빈 답과 원문 일치는 별도 계수',
        same_wrong_rule='양쪽 EM0이며 정규화 후 같은 비어 있지 않은 답; 빈 답 포함 값은 별도 계수',
        source_bundles_reselected=False, same_output_promoted_to_correct=False,
        candidates_are_semantic_negatives=False, training_examples_generated=False,
        world_truth_certified=False, source_files_read=False, model_loaded=False)
