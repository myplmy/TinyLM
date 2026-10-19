"""Pure code-owned first-question transfer data; no asset or model access.

Language children, question wording, field placement and repeated passes are
not new knowledge. Actual source/replay exclusions and tokenizer verification
belong to the caller. This module never imports a consumer or opens a file.
"""
from __future__ import annotations

from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collections import Counter, defaultdict
import copy
import hashlib
import itertools
import json
import math
import random
import re

TAG = 'p106b_question_transfer_v1_s1337'
SCHEMA = 'P106B_QUESTION_TRANSFER_DATA_V1'
SEED = 20261019
ARMS = ('fixed_last', 'varied_last', 'fixed_balanced', 'varied_balanced')
FAMILIES = ('arithmetic', 'lookup', 'boolean', 'format')
LANGUAGES = ('ko', 'en')
SPLITS = ('train', 'dev', 'test')
QUOTAS = {'train': dict(arithmetic=1024, lookup=512, boolean=256, format=256),
          'dev': dict(arithmetic=64, lookup=32, boolean=64, format=32),
          'test': dict(arithmetic=64, lookup=32, boolean=64, format=32)}
LETTERS = tuple('ABCDEFGHIJKL')
KEYS = ('answer', 'result')
ATTRIBUTES = ('colour', 'object')
COLOURS = {'ko': ('빨강', '파랑', '노랑', '초록', '보라', '주황'),
           'en': ('red', 'blue', 'yellow', 'green', 'purple', 'orange')}
OBJECTS = {'ko': ('책', '가방', '열쇠', '상자', '우산', '노트', '지도', '공'),
           'en': ('book', 'bag', 'key', 'box', 'umbrella', 'notebook', 'map', 'ball')}
BOOL_ALLOCATION = {'train': {'AND': 20, 'OR': 20, 'XOR': 24},
                   'dev': {'AND': 5, 'OR': 5, 'XOR': 6},
                   'test': {'AND': 5, 'OR': 5, 'XOR': 6}}
PAIR_QUOTAS = dict(train=24, dev=6, test=6)
BUILD_SPLITS = ('test', 'dev', 'train')
PROBLEM_KEYS = frozenset(('schema', 'tag', 'split', 'family', 'query_id',
    'parent_group_id', 'state', 'query', 'target_by_language', 'rotation',
    'state_sha256', 'query_sha256', 'problem_sha256'))


class SupplyError(ValueError):
    """A declared pool cannot fill the unchanged quotas without repetition."""


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def _integer(value, label, low=0, high=50):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('bounded integer required: ' + label)
    return value


def arithmetic_key(op, a, b):
    """Exclusion identity; + and * operand exchanges are the same calculation.

    Historical exclusions outside this course's domain are retained, not used
    to enlarge the 0..50 +/- candidate pool.
    """
    if op not in ('+', '-', '*'):
        raise ValueError('known arithmetic exclusion operation required')
    _integer(a, 'a', -1_000_000, 1_000_000)
    _integer(b, 'b', -1_000_000, 1_000_000)
    if op in ('+', '*'):
        a, b = sorted((a, b))
    return op, a, b


def normalize_blocked(blocked=None):
    """Normalize supplied declarations only; do not inspect any old sources."""
    allowed = {'arithmetic', 'boolean_name_pairs', 'format_literals', 'lookup_parent_signatures'}
    if blocked is None:
        blocked = {}
    if not isinstance(blocked, dict) or set(blocked) - allowed:
        raise ValueError('only declared exclusion fields are supported')
    result = {key: [] for key in sorted(allowed)}
    for key, values in blocked.items():
        if not isinstance(values, (list, tuple)):
            raise ValueError('exclusion fields must be lists')
        normalized = []
        for value in values:
            if key == 'arithmetic':
                if not isinstance(value, (list, tuple)) or len(value) != 3:
                    raise ValueError('arithmetic exclusion is [op,a,b]')
                item = arithmetic_key(*value)
            elif key == 'boolean_name_pairs':
                if (not isinstance(value, (list, tuple)) or len(value) != 2
                        or any(not isinstance(v, str) or not v for v in value)
                        or value[0] == value[1]):
                    raise ValueError('two distinct Boolean exclusion names required')
                item = tuple(sorted(value))
            elif key == 'format_literals':
                if not isinstance(value, str):
                    raise ValueError('literal exclusions must remain exact strings')
                item = value
            else:
                if not isinstance(value, str) or re.fullmatch(r'[0-9A-Fa-f]{64}', value) is None:
                    raise ValueError('canonical lookup SHA256 required')
                item = value.upper()
            normalized.append(item)
        unique = sorted(set(normalized))
        result[key] = [list(v) if isinstance(v, tuple) else v for v in unique]
    return result


def _canonical(family, state, query):
    """Validate the producer grammar and return order-independent identities."""
    if not isinstance(state, dict) or not isinstance(query, dict):
        raise ValueError('explicit state and query dictionaries required')
    if family == 'arithmetic':
        if set(state) != {'op', 'a', 'b'} or query != {'kind': 'result'} or state['op'] not in ('+', '-'):
            raise ValueError('closed +/- calculation state/query required')
        a, b = _integer(state['a'], 'a'), _integer(state['b'], 'b')
        op, a, b = arithmetic_key(state['op'], a, b)
        return dict(op=op, a=a, b=b), dict(kind='result')
    if family == 'lookup':
        if set(state) != {'subjects', 'facts'} or set(query) != {'subject', 'attribute'}:
            raise ValueError('exact two-subject/two-attribute lookup schema required')
        subjects, facts = state['subjects'], state['facts']
        if (not isinstance(subjects, list) or len(subjects) != 2
                or any(not isinstance(s, str) or s not in LETTERS for s in subjects)
                or len(set(subjects)) != 2 or not isinstance(facts, list) or len(facts) != 4):
            raise ValueError('two known subjects and four facts required')
        table = {}
        for fact in facts:
            if not isinstance(fact, list) or len(fact) != 3:
                raise ValueError('lookup fact is [subject,attribute,value_index]')
            subject, attribute, index = fact
            if subject not in subjects or attribute not in ATTRIBUTES:
                raise ValueError('unknown lookup fact')
            _integer(index, 'lookup value', 0, len(COLOURS['ko']) - 1 if attribute == 'colour' else len(OBJECTS['ko']) - 1)
            if (subject, attribute) in table:
                raise ValueError('duplicate lookup fact')
            table[subject, attribute] = index
        if set(table) != set(itertools.product(subjects, ATTRIBUTES)):
            raise ValueError('all four facts are required')
        if any(len({table[s, attr] for s in subjects}) != 2 for attr in ATTRIBUTES):
            raise ValueError('each attribute needs two distinct answers')
        if query['subject'] not in subjects or query['attribute'] not in ATTRIBUTES:
            raise ValueError('lookup query must reference one unique fact')
        for language in LANGUAGES:
            words = [_lookup_word(attr, index, language) for (s, attr), index in table.items()]
            if len(set(words)) != 4:
                raise ValueError('four distinct rendered answers required')
        return dict(subjects=sorted(subjects), facts=[list(v) for v in sorted(tuple(v) for v in facts)]), dict(query)
    if family == 'boolean':
        if set(state) != {'bindings'} or set(query) != {'operator', 'operands'}:
            raise ValueError('closed Boolean binding/query schema required')
        bindings = state['bindings']
        if (not isinstance(bindings, list) or len(bindings) != 2
                or any(not isinstance(v, list) or len(v) != 2 for v in bindings)):
            raise ValueError('two explicit Boolean bindings required')
        if (any(name not in LETTERS or type(value) is not bool for name, value in bindings)
                or len({v[0] for v in bindings}) != 2):
            raise ValueError('distinct known names with real bool values required')
        names = sorted(v[0] for v in bindings)
        if (query['operator'] not in BOOL_ALLOCATION['train'] or not isinstance(query['operands'], list)
                or any(not isinstance(n, str) for n in query['operands'])
                or sorted(query['operands']) != names):
            raise ValueError('one AND/OR/XOR query over exactly those two bindings required')
        return dict(bindings=sorted(copy.deepcopy(bindings))), dict(operator=query['operator'], operands=names)
    if family == 'format':
        if set(state) != {'literal'} or set(query) != {'key'} or query['key'] not in KEYS:
            raise ValueError('one literal and one requested JSON key required')
        literal = state['literal']
        if (not isinstance(literal, str) or re.fullmatch(r'[1-9][0-9]{2,3}', literal) is None
                or not 100 <= int(literal) <= 9999):
            raise ValueError('literal candidate must be an exact numeric string100..9999')
        return dict(literal=literal), dict(key=query['key'])
    raise ValueError('unknown task family')


def _lookup_word(attribute, index, language):
    return (COLOURS if attribute == 'colour' else OBJECTS)[language][index]


def lookup_parent_signature(state):
    """Canonical full-table SHA; fact order and language do not create tables."""
    if not isinstance(state, dict) or not isinstance(state.get('subjects'), list) or not state['subjects']:
        raise ValueError('explicit lookup state required')
    canonical, _ = _canonical('lookup', state, dict(subject=state['subjects'][0], attribute='colour'))
    return sha(['lookup', canonical])


def _parent(family, state):
    if family == 'arithmetic':
        return sha(['arithmetic', state['op'], state['a'], state['b']])
    if family == 'lookup':
        return sha(['lookup', state])
    if family == 'boolean':
        return sha(['boolean_name_pair', sorted(v[0] for v in state['bindings'])])
    return sha(['format_literal', state['literal']])


def _target(family, state, query, language):
    if family == 'arithmetic':
        return str(state['a'] + state['b'] if state['op'] == '+' else state['a'] - state['b'])
    if family == 'lookup':
        index = next(v for s, a, v in state['facts'] if (s, a) == (query['subject'], query['attribute']))
        return _lookup_word(query['attribute'], index, language)
    if family == 'boolean':
        values = dict(state['bindings']); a, b = (values[n] for n in query['operands'])
        value = a and b if query['operator'] == 'AND' else a or b if query['operator'] == 'OR' else a != b
        return str(value).lower()
    return json.dumps({query['key']: state['literal']}, ensure_ascii=False, separators=(',', ':'))


def _problem(family, state, query, split, rotation=0):
    if split not in SPLITS or type(rotation) is not int or rotation not in range(4):
        raise ValueError('known split and integer rotation0..3 required')
    canonical, canonical_query = _canonical(family, state, query)
    result = dict(schema=SCHEMA, tag=TAG, split=split, family=family,
        query_id=sha(['query', family, canonical, canonical_query]),
        parent_group_id=_parent(family, canonical), state=copy.deepcopy(state), query=copy.deepcopy(query),
        target_by_language={l: _target(family, canonical, canonical_query, l) for l in LANGUAGES},
        rotation=rotation, state_sha256=sha(canonical), query_sha256=sha(canonical_query))
    result['problem_sha256'] = sha(result)
    return result


def validate_problem(problem):
    if not isinstance(problem, dict) or set(problem) != PROBLEM_KEYS:
        raise ValueError('exact closed problem schema required')
    expected = _problem(problem['family'], problem['state'], problem['query'], problem['split'], problem['rotation'])
    if problem != expected:
        raise ValueError('problem state/query/truth/identity/rotation fingerprint changed')
    return True


def _allocate(values, counts, label):
    if len(values) < sum(counts.values()):
        raise SupplyError('%s: need%d distinct groups, found%d' % (label, sum(counts.values()), len(values)))
    start, result = 0, {}
    for split in BUILD_SPLITS:
        n = counts[split]; result[split] = values[start:start + n]; start += n
    return result


def _arithmetic(blocked, seed):
    denied = {tuple(v) for v in blocked['arithmetic']}; rows = {s: [] for s in SPLITS}
    for op in ('+', '-'):
        values = [(op, a, b) for a in range(51) for b in range(51)
                  if (op != '+' or a <= b) and (op, a, b) not in denied]
        values.sort(key=lambda v: sha([seed, 'arithmetic_selection', v]))
        chosen = _allocate(values, {s: QUOTAS[s]['arithmetic'] // 2 for s in SPLITS}, 'arithmetic/' + op)
        for split, selected in chosen.items():
            rows[split] += [_problem('arithmetic', dict(op=op, a=a, b=b), dict(kind='result'), split) for op, a, b in selected]
    return rows


def _lookup_candidates(seed):
    """Hash-seeded exhaustive permutation, without a large table materialization."""
    pairs = list(itertools.combinations(LETTERS, 2))
    colours = list(itertools.permutations(range(len(COLOURS['ko'])), 2))
    objects = list(itertools.permutations(range(len(OBJECTS['ko'])), 2))
    total = len(pairs) * len(colours) * len(objects)
    rng = random.Random(sha([seed, 'lookup_candidate_permutation']))
    start, step = rng.randrange(total), rng.randrange(1, total)
    while math.gcd(step, total) != 1:
        step = rng.randrange(1, total)
    for rank in range(total):
        i = (start + rank * step) % total
        subject_i, remainder = divmod(i, len(colours) * len(objects))
        colour_i, object_i = divmod(remainder, len(objects))
        a, b = pairs[subject_i]; x, y = colours[colour_i]; v, w = objects[object_i]
        facts = [[a, 'colour', x], [a, 'object', v], [b, 'colour', y], [b, 'object', w]]
        rng_order = random.Random(sha([seed, 'lookup_fact_order', facts])); rng_order.shuffle(facts)
        yield dict(subjects=[a, b], facts=facts)


def _lookups(blocked, seed):
    denied = set(blocked['lookup_parent_signatures']); counts = {s: QUOTAS[s]['lookup'] // 4 for s in SPLITS}
    states, seen = [], set()
    for state in _lookup_candidates(seed):
        signature = lookup_parent_signature(state)
        if signature in denied or signature in seen:
            continue
        states.append(state); seen.add(signature)
        if len(states) == sum(counts.values()):
            break
    selected = _allocate(states, counts, 'lookup tables'); rows = {s: [] for s in SPLITS}
    for split, values in selected.items():
        for state in values:
            for subject, attribute in itertools.product(sorted(state['subjects']), ATTRIBUTES):
                rows[split].append(_problem('lookup', state, dict(subject=subject, attribute=attribute), split))
    return rows


def _booleans(blocked, seed):
    denied = {tuple(v) for v in blocked['boolean_name_pairs']}
    pairs = [p for p in itertools.combinations(LETTERS, 2) if p not in denied]
    pairs.sort(key=lambda p: sha([seed, 'boolean_pair_selection', p]))
    chosen = _allocate(pairs, PAIR_QUOTAS, 'Boolean name pairs'); rows = {s: [] for s in SPLITS}
    for split, pair_bank in chosen.items():
        for a, b in itertools.product((False, True), repeat=2):
            for op, count in BOOL_ALLOCATION[split].items():
                ordered = sorted(pair_bank, key=lambda pair: sha([seed, 'boolean_operator_subset', pair, op, a, b]))
                for names in ordered[:count]:
                    state = dict(bindings=[[names[0], a], [names[1], b]])
                    rows[split].append(_problem('boolean', state, dict(operator=op, operands=list(names)), split))
    return rows


def _formats(blocked, seed):
    denied = set(blocked['format_literals'])
    values = [str(i) for i in range(100, 10000) if str(i) not in denied]
    values.sort(key=lambda literal: sha([seed, 'literal_selection', literal]))
    chosen = _allocate(values, {s: QUOTAS[s]['format'] // 2 for s in SPLITS}, 'format literals')
    return {s: [_problem('format', dict(literal=literal), dict(key=key), s)
                for literal in literals for key in KEYS] for s, literals in chosen.items()}


def _rotations(problems, seed):
    """Balance each family and language, arithmetic op, and Boolean target.

    Language children share a rotation. Lookup and format parent groups remain
    together. No claim of every Boolean-pattern x rotation cell being equal
    is made: some DEV/TEST operator/valuation counts are not divisible by4.
    """
    lanes = defaultdict(list)
    for p in problems:
        family = p['family']
        lane = (family, p['state']['op']) if family == 'arithmetic' else (family, p['target_by_language']['en']) if family == 'boolean' else (family,)
        lanes[lane].append(p)
    for lane, values in lanes.items():
        units = defaultdict(list)
        for p in values:
            units[p['parent_group_id'] if p['family'] in ('lookup', 'format') else p['query_id']].append(p)
        ordered = sorted(units, key=lambda unit: sha([seed, 'rotation', lane, unit]))
        for i, unit in enumerate(ordered):
            for p in units[unit]:
                p['rotation'] = i % 4
                p['problem_sha256'] = sha({k: v for k, v in p.items() if k != 'problem_sha256'})


def _summary(rows):
    result = {}
    for split in SPLITS:
        values = rows[split]; groups = defaultdict(list)
        for p in values:
            groups[p['family']].append(p)
        by_family = {}
        for family in FAMILIES:
            selected = groups[family]
            by_family[family] = dict(neutral_queries=len(selected), bilingual_records=2 * len(selected),
                parent_groups=len({p['parent_group_id'] for p in selected}),
                rotation_counts={str(i): sum(p['rotation'] == i for p in selected) for i in range(4)})
        bools = groups['boolean']; patterns = Counter()
        for p in bools:
            bindings = dict(p['state']['bindings']); a, b = (bindings[n] for n in sorted(bindings))
            patterns['%s/%s/%s' % (p['query']['operator'], str(a).lower(), str(b).lower())] += 1
        lookup = groups['lookup']; controls = dict(first_fact=0, subject_only=0, attribute_only=0)
        for p in lookup:
            state, query = p['state'], p['query']; wanted = p['target_by_language']['en']
            first = state['facts'][0]
            controls['first_fact'] += _lookup_word(first[1], first[2], 'en') == wanted
            table = {(s, a): v for s, a, v in state['facts']}
            controls['subject_only'] += _lookup_word('colour', table[query['subject'], 'colour'], 'en') == wanted
            controls['attribute_only'] += _lookup_word(query['attribute'], table[min(state['subjects']), query['attribute']], 'en') == wanted
        result[split] = dict(neutral_problems=len(values), bilingual_records=2 * len(values), by_family=by_family,
            ordered_query_ids_sha256=sha([p['query_id'] for p in values]),
            boolean=dict(named_instances=len(bools), name_pair_groups=len({p['parent_group_id'] for p in bools}),
                truth_functions=3, ordered_truth_table_patterns=len(patterns), pattern_counts=dict(sorted(patterns.items())),
                true_targets=sum(p['target_by_language']['en'] == 'true' for p in bools),
                false_targets=sum(p['target_by_language']['en'] == 'false' for p in bools),
                constant_false_correct=sum(p['target_by_language']['en'] == 'false' for p in bools),
                constant_true_correct=sum(p['target_by_language']['en'] == 'true' for p in bools),
                unseen_logical_functions_claim=False),
            lookup_controls=dict(neutral_queries=len(lookup), correct_counts=controls,
                scope='specified deterministic policies only; not unrestricted model bounds'))
    return result


def _construct(blocked, seed):
    if type(seed) is not int or seed < 0:
        raise ValueError('nonnegative integer course seed required')
    blocked = normalize_blocked(blocked)
    rows = {s: [] for s in SPLITS}
    for factory in (_arithmetic, _lookups, _booleans, _formats):
        produced = factory(blocked, seed)
        for split in SPLITS:
            rows[split].extend(produced[split])
    for split in SPLITS:
        _rotations(rows[split], seed)
        rows[split].sort(key=lambda p: (FAMILIES.index(p['family']), sha([seed, 'problem_order', p['query_id']])))
    metadata = dict(quota_basis='neutral query instances; each has two language children',
        quotas=copy.deepcopy(QUOTAS), split_assignment_order=list(BUILD_SPLITS),
        blocked_sha256=sha(blocked), actual_source_exclusions_verified=False,
        exclusion_scope='caller declarations only; no source/replay/file inspection',
        natural_qa_or_replay_included=False, tokenizer_verified=False, models_loaded=0,
        teacher_calls=0, world_knowledge_claim=False, unique_logical_knowledge_claim=False,
        train_wordings=[0, 1], heldout_wordings=[2, 3], epochs=4,
        render_generation_prefix_contains_assistant_target=False,
        summary=_summary(rows))
    return dict(schema=SCHEMA, tag=TAG, seed=seed, blocked=blocked, metadata=metadata, **rows)


def build_course(blocked=None, seed=SEED):
    """Build new in-memory code problems, never a frozen real-source artifact."""
    return _construct(blocked, seed)


def validate_course(course):
    if (not isinstance(course, dict) or set(course) != {'schema', 'tag', 'seed', 'blocked', 'metadata', *SPLITS}
            or course['schema'] != SCHEMA or course['tag'] != TAG):
        raise ValueError('exact independent course schema required')
    parent_sets, seen = {}, set()
    for split in SPLITS:
        values = course[split]
        if (not isinstance(values, list)
                or any(not isinstance(p, dict) or p.get('family') not in FAMILIES for p in values)
                or Counter(p['family'] for p in values) != QUOTAS[split]):
            raise ValueError('unchanged complete per-family quotas required: ' + split)
        parent_sets[split] = set(); grouped = defaultdict(list)
        for p in values:
            validate_problem(p)
            if p['split'] != split or p['query_id'] in seen:
                raise ValueError('query split/identity duplicated or changed')
            seen.add(p['query_id']); parent_sets[split].add(p['parent_group_id']); grouped[p['parent_group_id']].append(p)
        for group in grouped.values():
            if group[0]['family'] == 'lookup':
                expected = set(itertools.product(group[0]['state']['subjects'], ATTRIBUTES))
                if len(group) != 4 or {(p['query']['subject'], p['query']['attribute']) for p in group} != expected:
                    raise ValueError('whole lookup table needs all four queries')
            if group[0]['family'] == 'format' and (len(group) != 2 or {p['query']['key'] for p in group} != set(KEYS)):
                raise ValueError('whole literal needs both JSON keys')
    if any(parent_sets[a] & parent_sets[b] for a, b in itertools.combinations(SPLITS, 2)):
        raise ValueError('parent group crosses train/dev/test')
    expected = _construct(course['blocked'], course['seed'])
    if course != expected:
        raise ValueError('deterministic source/blocked/schedule/metadata course changed')
    return True


def schedule_view(problem, arm, epoch):
    validate_problem(problem)
    if arm not in ARMS or type(epoch) is not int or epoch not in range(4) or problem['split'] != 'train':
        raise ValueError('training problem, known arm and epoch0..3 required')
    phase = (epoch + problem['rotation']) % 4
    return dict(wording=phase // 2 if arm.startswith('varied_') else 0,
                position='QC' if arm.endswith('_balanced') and phase % 2 else 'CQ')


def _context(problem, language):
    state = problem['state']; family = problem['family']; ko = language == 'ko'
    if family == 'arithmetic':
        return ('계산식: ' if ko else 'Expression: ') + '%d %s %d' % (state['a'], state['op'], state['b'])
    if family == 'lookup':
        labels = {'colour': '색', 'object': '물건'}
        return '\n'.join((s + '의 ' + labels[a] + ': ' if ko else s + "'s " + a + ': ')
                         + _lookup_word(a, v, language) for s, a, v in state['facts'])
    if family == 'boolean':
        return '\n'.join(name + '=' + str(value).lower() for name, value in state['bindings'])
    return ('원문 문자열(JSON 표기): ' if ko else 'Original string (JSON notation): ') + json.dumps(state['literal'], ensure_ascii=False)


def _question(problem, language, wording):
    family, query, ko = problem['family'], problem['query'], language == 'ko'
    if family == 'arithmetic':
        return (('계산 결과를 정수 하나로 답하세요.', '식의 값은 얼마인가요? 정수만 쓰세요.',
                 '주어진 계산에서 얻는 수를 정수 하나로 적으세요.', '계산해서 나온 값만 알려 주세요. 정수 하나로 답하세요.') if ko else
                ('Give only the integer result of the calculation.', 'What is the value of the expression? Write one integer.',
                 'Evaluate the given calculation and return one integer only.', 'Which integer does the calculation produce? Answer with that integer only.'))[wording]
    if family == 'lookup':
        subject = query['subject']; label = {'colour': '색', 'object': '물건'}[query['attribute']] if ko else query['attribute']
        return ((f'{subject}의 {label}만 답하세요.', f'{subject}의 {label}은 무엇인가요? 값만 쓰세요.',
                 f'자료에서 {subject}에 연결된 {label} 값을 적으세요.', f'{subject}에 대해 요청한 항목은 {label}입니다. 해당 값만 쓰세요.') if ko else
                (f'Give only the {label} of {subject}.', f'What is the {label} of {subject}? Return only its value.',
                 f'Extract the value of {subject}\'s {label} from the data.', f'The requested attribute of {subject} is {label}. State its value only.'))[wording]
    if family == 'boolean':
        expression = (' ' + query['operator'] + ' ').join(query['operands'])
        return ((f'{expression}의 논리값을 true 또는 false로만 답하세요.', f'{expression}을 적용하면 어떤 논리값인가요? true 또는 false만 쓰세요.',
                 f'주어진 변수로 {expression}을 평가한 값만 true 또는 false로 적으세요.', f'요청한 논리식은 {expression}입니다. 그 결과만 true 또는 false로 알려 주세요.') if ko else
                (f'Give only true or false for {expression}.', f'What Boolean value results from {expression}? Write only true or false.',
                 f'Evaluate {expression} using the supplied variables. Return only true or false.', f'The requested logical expression is {expression}. State only its true or false result.'))[wording]
    key = query['key']
    return ((f'{key} 키 하나에 원문 문자열을 값으로 넣은 JSON 객체만 출력하세요.',
             f'원문 문자열을 값으로 하고 키가 {key} 하나뿐인 JSON 객체를 쓰세요.',
             f'{key} 항목 하나에 주어진 문자열 전체를 담아 JSON으로 답하세요.',
             f'요청한 출력은 단일 {key} 문자열 항목의 JSON 객체입니다. 원문 문자열을 바꾸지 마세요.') if ko else
            (f'Return only a JSON object with one {key} key whose string value is the original string.',
             f'Write one JSON object using exactly the key {key} and the unchanged original string as its value.',
             f'Put the entire supplied string in the single {key} field of a JSON object.',
             f'The requested output is a JSON object with one string field named {key}. Preserve the original string exactly.'))[wording]


def render(problem, language, wording, position):
    """Plain canonical-compatible SFT row; generation must use user only."""
    validate_problem(problem)
    if language not in LANGUAGES or type(wording) is not int or wording not in range(4) or position not in ('CQ', 'QC'):
        raise ValueError('known language, wording0..3 and CQ/QC required')
    context, question = _context(problem, language), _question(problem, language, wording)
    ko = language == 'ko'
    instruction = '자료에 주어진 값만 사용해 요청한 답만 쓰세요.' if ko else 'Use only the given data and return only the requested answer.'
    blocks = {'C': ('자료:\n' if ko else 'Data:\n') + context,
              'Q': ('질문:\n' if ko else 'Question:\n') + question}
    user = instruction + '\n' + '\n'.join(blocks[c] for c in position)
    contract = dict(arithmetic='EXACT_INTEGER', lookup='EXACT_VALUE', boolean='EXACT_BOOLEAN', format='STRICT_ONE_KEY_STRING_JSON')[problem['family']]
    return dict(messages=[dict(role='user', content=user), dict(role='assistant', content=problem['target_by_language'][language])],
        meta=dict(source='p106b_question_transfer_code', source_license='project_authored_synthetic',
            language=language, source_split=problem['split'], family=problem['family'], query_id=problem['query_id'],
            semantic_root_id=problem['query_id'], parent_concept_id=problem['parent_group_id'],
            parent_group_id=problem['parent_group_id'], problem_sha256=problem['problem_sha256'],
            state_sha256=problem['state_sha256'], question_sha256=sha(question), context_sha256=sha(context),
            wording=wording, position=position, supervised_assistant_turns=[1], target_contract=contract,
            input_contract='FORMAT_LITERAL_INPUT' if problem['family'] == 'format' else 'CODE_OWNED_STATE_QUERY',
            label_status='CODE_COMPUTED_CLOSED_WORLD', world_knowledge_claim=False, teacher_calls=0))


def evaluation_problems(course):
    """Pre-outcome hash selection; keep complete lookup and literal parents."""
    validate_course(course); result = {}
    for split, quota in (('test', 32), ('train', 16)):
        selected = []
        for family in FAMILIES:
            values = [p for p in course[split] if p['family'] == family]
            if family in ('lookup', 'format'):
                groups = defaultdict(list)
                for p in values:
                    groups[p['parent_group_id']].append(p)
                width = 4 if family == 'lookup' else 2
                keys = sorted(groups, key=lambda key: sha([TAG, 'evaluation_parent', split, family, key]))[:quota // width]
                values = [p for key in keys for p in sorted(groups[key], key=lambda p: p['query_id'])]
            else:
                values = sorted(values, key=lambda p: sha([TAG, 'evaluation_query', split, family, p['query_id']]))[:quota]
            if len(values) != quota:
                raise SupplyError('evaluation quota unavailable: ' + split + '/' + family)
            selected.extend(copy.deepcopy(values))
        result[split] = selected
    return result


def classify(problem, language, rawanswer):
    """Grade a whole raw answer; never wrap, repair, or mutate learner text."""
    validate_problem(problem)
    if language not in LANGUAGES:
        raise ValueError('known grading language required')
    if not isinstance(rawanswer, str):
        return False
    target = problem['target_by_language'][language]; family = problem['family']
    if family == 'arithmetic':
        value = rawanswer.strip()
        if re.fullmatch(r'[+-]?[0-9]+', value) is None:
            return False
        try:
            return int(value) == int(target)
        except ValueError:
            return False
    if family == 'boolean':
        return rawanswer.strip().casefold() == target
    if family == 'lookup':
        return rawanswer.strip() == target
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON is not an answer')
    try:
        value = json.loads(rawanswer, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError, RecursionError):
        return False
    key = problem['query']['key']
    return (type(value) is dict and set(value) == {key} and type(value[key]) is str
            and value[key] == problem['state']['literal'])
