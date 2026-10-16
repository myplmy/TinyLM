"""Pure-record evaluation for overnight natural QA and a fixed64 counterfactual cube.

No corpus/checkpoint is read, no model is created, and no GPU operation is used.
The parent driver owns generation, source manifests and frozen artifact hashes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate
from scripts.p106b_night_learning import norm_text, qa_scores

VERSION = 'P106B_NIGHT_RECORD_EVALUATION_V1'
CUBE_VERSION = 'P106B_NIGHT_AGE_CLASS_CUBE_V1'
STOP_REASONS = frozenset(('EOS', 'EOT', 'STOP_SEQUENCE', 'TURN_END'))
SOURCE_FIELDS = ('source_sha256', 'source_path', 'question', 'context',
                 'context_id', 'qa_id', 'prompt', 'messages')


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest().upper()


def _view(value, allowed=(0, 1, 2)):
    if type(value) is int and value in allowed:
        return value
    if isinstance(value, str) and value in tuple(str(v) for v in allowed):
        return int(value)
    raise ValueError('explicit registered view required')


def _generation(event):
    generation = event.get('generation')
    if (not isinstance(generation, dict)
            or not isinstance(generation.get('finish_reason'), str)
            or not generation['finish_reason']):
        raise ValueError('actual generation finish_reason required')
    answer = event.get('answer')
    if not isinstance(answer, str):
        raise ValueError('actual answer string, including empty, required')
    reason = generation['finish_reason']
    return dict(empty=int(not answer.strip()), stop=int(reason in STOP_REASONS),
                max_new=int(reason.startswith('MAX_NEW')),
                context_exhausted=int(reason == 'CONTEXT_BUDGET_EXHAUSTED'),
                finish_reason=reason)


def _source_identity(event):
    return {key: event[key] for key in SOURCE_FIELDS if key in event}


def _natural_index(events):
    indexed, roots = {}, defaultdict(dict)
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('natural event dict required')
        language = event.get('language')
        if language not in ('ko', 'en'):
            raise ValueError('declared ko/en natural event required')
        for field in ('root', 'article_id'):
            if not isinstance(event.get(field), str) or not event[field]:
                raise ValueError('nonempty natural ' + field + ' required')
        view = _view(event.get('view'))
        aliases = event.get('aliases')
        if (not isinstance(aliases, list) or not aliases
                or any(not isinstance(v, str) or not v.strip() for v in aliases)):
            raise ValueError('nonempty original alias strings required')
        _generation(event)
        expected = qa_scores(event['answer'], aliases, language)
        observed = event.get('scores')
        if (not isinstance(observed, dict) or set(observed) != set(expected)
                or any(type(observed[k]) not in (int, float)
                       or not math.isfinite(observed[k]) or observed[k] != expected[k]
                       for k in expected)):
            raise ValueError('stored natural scores differ from raw-answer recount')
        key = (language, event['root'], view)
        if key in indexed:
            raise ValueError('duplicate natural root/language/view')
        indexed[key] = event
        roots[language, event['root']][view] = event
    if not indexed:
        raise ValueError('nonempty natural events required')
    for views in roots.values():
        if set(views) != {0, 1, 2}:
            raise ValueError('complete natural root views0/1/2 required')
        first = views[0]
        for event in views.values():
            if (event['article_id'] != first['article_id']
                    or event['aliases'] != first['aliases']):
                raise ValueError('same root article/gold aliases required across views')
            # A wrapper prompt/messages may differ by view. Original question,
            # context and source-file identity must not change with the wrapper.
            for field in SOURCE_FIELDS[:6]:
                if ((field in event) != (field in first)
                        or (field in first and event[field] != first[field])):
                    raise ValueError('same root original source required across views: ' + field)
    return indexed, roots


def _natural_metrics(events):
    count = len(events)
    if not count:
        raise ValueError('nonempty natural metric slice required')
    observed = [_generation(event) for event in events]
    out = dict(n=count, roots=len({(e['language'], e['root']) for e in events}),
               articles=len({(e['language'], e['article_id']) for e in events}))
    for metric in ('em', 'f1', 'raw_exact'):
        total = sum(e['scores'][metric] for e in events)
        out[metric] = total / count
        out[metric + '_sum'] = total
    for metric in ('empty', 'stop', 'max_new', 'context_exhausted'):
        out[metric] = sum(row[metric] for row in observed)
    out['finish_reasons'] = dict(sorted(Counter(row['finish_reason'] for row in observed).items()))
    return out


def _train_pair_metrics(groups):
    if not groups:
        raise ValueError('nonempty paired natural roots required')
    both, same_wrong, same_wrong_including_empty, both_empty = 0, 0, 0, 0
    for views in groups:
        left, right = views[0], views[1]
        both += int(left['scores']['em'] == right['scores']['em'] == 1.)
        a = norm_text(left['answer'], left['language'])
        b = norm_text(right['answer'], right['language'])
        wrong = left['scores']['em'] == right['scores']['em'] == 0.
        same_wrong_including_empty += int(wrong and a == b)
        same_wrong += int(wrong and a == b and bool(a))
        both_empty += int(not left['answer'].strip() and not right['answer'].strip())
    n = len(groups)
    return dict(n=n, both_correct=both, both_correct_rate=both / n,
                same_wrong=same_wrong, same_wrong_rate=same_wrong / n,
                same_wrong_including_empty=same_wrong_including_empty,
                both_empty=both_empty,
                same_wrong_rule='both EM0 and equal nonempty scorer-normalized answers; empty collapse reported separately')


def summarize_natural(events):
    """Recount exact complete roots and separate trained-pair/held-out behavior."""
    indexed, roots = _natural_index(events)
    languages = {}
    for language in sorted({key[0] for key in indexed}):
        groups = [values for (lang, root), values in sorted(roots.items()) if lang == language]
        by_view = {str(view): _natural_metrics([values[view] for values in groups])
                   for view in (0, 1, 2)}
        languages[language] = dict(roots=len(groups), by_view=by_view,
                                  train_pair=_train_pair_metrics(groups),
                                  heldout_view2=by_view['2'])
    return dict(schema=VERSION, status='NATURAL_RAW_RECOUNTED', cases=len(indexed),
                roots=len(roots), by_language=languages, train_views=[0, 1], heldout_view=2,
                scoring='p106b_night_learning.qa_scores; KO whitespace-insensitive character F1 / EN word F1; local metric, not official scorer',
                same_wrong_is_not_correctness=True,
                semantic_truth='source aliases and scoped local metrics, not full semantic adjudication')


def paired_natural(left, right, draws=2000, seed=1337):
    """Within-language article-cluster paired bootstrap; all case/gold IDs fixed."""
    import numpy as np
    if type(draws) is not int or draws < 1 or type(seed) is not int:
        raise ValueError('positive bootstrap draws and integer seed required')
    a, aroots = _natural_index(left)
    b, broots = _natural_index(right)
    if set(a) != set(b):
        raise ValueError('identical natural case sets required')
    for key, event in a.items():
        other = b[key]
        if (event['article_id'] != other['article_id']
                or event['aliases'] != other['aliases']
                or _source_identity(event) != _source_identity(other)):
            raise ValueError('paired natural case/gold/original source differs')
    languages = {}
    for language in sorted({key[0] for key in a}):
        article_values = defaultdict(lambda: [0.] * 15)
        for key, views in sorted(aroots.items()):
            if key[0] != language:
                continue
            other = broots[key]
            values = article_values[views[0]['article_id']]
            for view in (0, 1, 2):
                for j, metric in enumerate(('em', 'f1')):
                    index = 2 * (2 * view + j)
                    values[index] += views[view]['scores'][metric]
                    values[index + 1] += other[view]['scores'][metric]
            values[12] += int(views[0]['scores']['em'] == views[1]['scores']['em'] == 1.)
            values[13] += int(other[0]['scores']['em'] == other[1]['scores']['em'] == 1.)
            values[14] += 1
        matrix = np.asarray([values for article, values in sorted(article_values.items())], dtype=float)
        n_articles = len(matrix)
        indices = np.random.default_rng(seed).integers(n_articles, size=(draws, n_articles))
        samples = matrix[indices].sum(axis=1)
        totals = matrix.sum(axis=0)
        def interval(index):
            differences = (samples[:, index + 1] - samples[:, index]) / samples[:, 14]
            return dict(left=float(totals[index] / totals[14]),
                        right=float(totals[index + 1] / totals[14]),
                        right_minus_left=float((totals[index + 1] - totals[index]) / totals[14]),
                        ci95=np.quantile(differences, [.025, .975]).tolist(),
                        n=int(totals[14]), articles=n_articles)
        by_view = {str(view): {metric: interval(2 * (2 * view + j))
                              for j, metric in enumerate(('em', 'f1'))}
                   for view in (0, 1, 2)}
        languages[language] = dict(articles=n_articles, roots=int(totals[14]), by_view=by_view,
                                  train_pair_both_correct=interval(12))
    return dict(schema=VERSION, status='NATURAL_PAIRED_ARTICLE_BOOTSTRAP',
                cases=len(a), by_language=languages, draws=draws, seed=seed,
                cluster_unit='article_id within language; paired roots/views stay together',
                aggregation='case-weighted ratios under article-cluster resampling',
                interval_scope='descriptive fixed-source paired intervals',
                training_seed_generalization=False, multiple_comparison_adjusted=False,
                semantic_truth='not a general intelligence or world-truth certificate')


def cube_rows():
    """Eight new code-owned starting records, each in eight controlled conditions."""
    names = dict(ko=('서온', '유담', '재린', '해솔'),
                 en=('Tarin', 'Belva', 'Neris', 'Odel'))
    rows = []
    for language in ('ko', 'en'):
        for index, person in enumerate(names[language]):
            age, grade = 9 + 2 * index, 2 + index
            new_age = age + 4 + index
            root = _sha([CUBE_VERSION, language, person, age, grade, new_age])
            for view in (0, 1):
                for field in ('age', 'class'):
                    for updated in (False, True):
                        if language == 'ko':
                            reference = (f'다음은 가상 학생 기록입니다. {person}의 나이는 {age}세이고 '
                                         f'학년은 {grade}입니다. ')
                            if updated:
                                reference += f'이후 기록의 나이를 {new_age}세로 바꿨습니다. 학년은 바꾸지 않았습니다.'
                            else:
                                reference += '이후 기록을 바꾸지 않았습니다.'
                            label = '나이' if field == 'age' else '학년'
                            question = f'현재 기록에서 {person}의 {label} 값은 무엇인가요? 숫자만 답하세요.'
                            user = (f'자료:\n{reference}\n질문:\n{question}' if view == 0 else
                                    f'아래 기록에 근거해 답하세요.\n기록:\n{reference}\n요청:\n{question}')
                        else:
                            reference = (f'This is a fictional student record. {person} is {age} years old '
                                         f'and is in school grade {grade}. ')
                            if updated:
                                reference += f'The recorded age was then changed to {new_age}. The school grade was not changed.'
                            else:
                                reference += 'The record was not changed afterwards.'
                            label = 'age' if field == 'age' else 'school grade'
                            question = f'What is the current recorded {label} of {person}? Give digits only.'
                            user = (f'Reference:\n{reference}\nQuestion:\n{question}' if view == 0 else
                                    f'Answer from the following record.\nRecord:\n{reference}\nRequest:\n{question}')
                        messages = validate(normalize(dict(messages=[dict(role='user', content=user)])))['messages']
                        gold = str(new_age if field == 'age' and updated else age if field == 'age' else grade)
                        rows.append(dict(root=root, language=language, lang=language, view=view,
                            field=field, updated=updated, messages=messages, gold=gold,
                            question=question, reference=reference, person=person,
                            initial_age=age, new_age=new_age, class_value=grade,
                            case_id=_sha([root, view, field, updated]), producer_version=CUBE_VERSION,
                            source_truth='CODE_FICTIONAL_STATED_FACTS_AND_EXPLICIT_AGE_REPLACEMENT_ONLY'))
    if len(rows) != 64 or len({row['case_id'] for row in rows}) != 64:
        raise ValueError('producer must supply exact64 distinct cube conditions')
    return rows


def _cube_metrics(events):
    n = len(events)
    if not n:
        raise ValueError('nonempty cube slice required')
    correct = sum(event['answer'].strip() == event['gold'] for event in events)
    out = dict(n=n, literal=correct, literal_rate=correct / n,
               raw_exact=sum(event['answer'] == event['gold'] for event in events))
    observed = [_generation(event) for event in events]
    for metric in ('empty', 'stop', 'max_new', 'context_exhausted'):
        out[metric] = sum(row[metric] for row in observed)
    out['finish_reasons'] = dict(sorted(Counter(row['finish_reason'] for row in observed).items()))
    return out


def _cube_transition_metrics(indexed):
    roots = sorted({(language, root, view) for language, root, view, field, updated in indexed})
    result = {}
    for field, name in (('age', 'age_change'), ('class', 'class_invariance')):
        both, same, same_wrong, both_empty = 0, 0, 0, 0
        for language, root, view in roots:
            before, after = (indexed[language, root, view, field, updated] for updated in (False, True))
            a, b = before['answer'].strip(), after['answer'].strip()
            correct_a, correct_b = a == before['gold'], b == after['gold']
            both += int(correct_a and correct_b)
            same += int(a == b)
            same_wrong += int(not correct_a and not correct_b and a == b and bool(a))
            both_empty += int(not a and not b)
        n = len(roots)
        result[name] = dict(n_pairs=n, both_correct=both, both_correct_rate=both / n,
                            output_unchanged=same, output_changed=n - same,
                            same_wrong=same_wrong, both_empty=both_empty)
    return result


def summarize_cube(events):
    """Require all64 exact producer rows; numbers retain signs and decimals."""
    expected = cube_rows()
    producer = {(r['language'], r['root'], r['view'], r['field'], r['updated']): r for r in expected}
    indexed = {}
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('cube event dict required')
        if type(event.get('updated')) is not bool:
            raise ValueError('explicit cube updated boolean required')
        key = (event.get('language'), event.get('root'), _view(event.get('view'), (0, 1)),
               event.get('field'), event['updated'])
        if key in indexed:
            raise ValueError('duplicate cube condition')
        if key not in producer or any(event.get(field) != value for field, value in producer[key].items()):
            raise ValueError('cube source/messages/gold differ from the exact code producer')
        _generation(event)
        indexed[key] = event
    if len(indexed) != 64 or set(indexed) != set(producer):
        raise ValueError('complete exact64 cube events required')
    values = list(indexed.values())
    slices = {}
    for field in ('language', 'view', 'field', 'updated'):
        groups = defaultdict(list)
        for event in values:
            key = str(event[field]).lower() if field == 'updated' else str(event[field])
            groups[key].append(event)
        slices['by_' + field] = {key: _cube_metrics(rows) for key, rows in sorted(groups.items())}
    transitions = _cube_transition_metrics(indexed)
    by_language_transitions = {language: _cube_transition_metrics({k: v for k, v in indexed.items() if k[0] == language})
                               for language in ('ko', 'en')}
    return dict(schema=VERSION, status='CODE_CUBE_EXACT64_RECOUNTED', summary=_cube_metrics(values),
                cases=64, independent_starting_roots=8, slices=slices,
                transitions=transitions, transitions_by_language=by_language_transitions,
                literal_rule='outer whitespace stripped only; signs, decimal points and internal text retained',
                correct_output_change_is_separate_from_output_change=True,
                scope='eight fictional starting records and64 fixed interventions; not world knowledge or population accuracy')
