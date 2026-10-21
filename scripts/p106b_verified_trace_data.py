"""Code-owned, independently checkable short traces. Pure stdlib, no file IO.

The production course is fixed at 4096 roots/one row each/four passes. This is
a supervision-package comparison, not matched target-token efficiency or hidden
reasoning. Questions never contain a gold trace. Tokenizer admission is external.
"""
from __future__ import annotations

import copy
from collections import Counter
import hashlib
import json
import math
import re

VERSION = 'P106B_VERIFIED_SHORT_TRACE_DATA_V1'
FAMILIES = ('addition', 'lookup', 'update')
POLICIES = ('direct', 'trace')
COUNTS = {'train': {'addition': 2048, 'lookup': 1024, 'update': 1024},
          'dev': {'addition': 64, 'lookup': 32, 'update': 32},
          'test': {'addition': 64, 'lookup': 32, 'update': 32}}
RESERVATION_OWNER = 'scripts/diag_p106b_question_transfer.py::evaluation_cases'
USER6 = ('1+1은?', '2+2는?', 'A는 사과고 B는 당근이다 B는?',
    '문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 질문: 영희의 사과는 몇 개입니까? 답만 쓰세요.',
    '사과에 대해 알려줘', '농구란?')
CANARY_PAIRS = tuple((i + 2, (i * 7 + 3) % 17 + 1) for i in range(12))
SPECIAL = ('<|', '<eos>', '<bos>', '<pad>')


class SupplyExhausted(ValueError):
    """Do not fill missing roots by duplication or silently reduce the course."""


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def integer(value, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('bounded integer required; bool/float are not integer facts')
    return value


def checked_task(task):
    if not isinstance(task, dict) or task.get('family') not in FAMILIES:
        raise ValueError('explicit closed task family required')
    family = task['family']
    expected = {'family', 'a', 'b'} if family == 'addition' else {'family', 'facts', 'asked'}
    if family == 'update': expected.add('update')
    if set(task) != expected:
        raise ValueError('exact closed task fields required')
    if family == 'addition':
        integer(task['a'], 99); integer(task['b'], 99)
    else:
        facts = task['facts']
        if (not isinstance(facts, dict) or len(facts) != 2
                or any(not isinstance(n, str) or not n.isidentifier() or len(n) > 16 for n in facts)
                or task['asked'] not in facts):
            raise ValueError('two explicit subjects and an existing asked subject required')
        values = [integer(v, 255) for v in facts.values()]
        if len(set(values)) != 2:
            raise ValueError('two distinct initial values required for target counterfactuals')
        if family == 'update':
            update = task['update']
            if (not isinstance(update, dict) or set(update) != {'subject', 'value'}
                    or update['subject'] not in facts):
                raise ValueError('one explicit existing-subject update required')
            integer(update['value'], 255)
            if update['value'] in values:
                raise ValueError('fresh update value required, distinct from both initial values')
    return task


def canonical_fact(task):
    checked_task(task)
    if task['family'] == 'addition':
        return {'family': 'addition', 'operands': sorted((task['a'], task['b']))}
    # Distinct values define name-independent entity ranks. Values themselves
    # are NOT renamed; all queried subjects of this fact graph share one root.
    names = sorted(task['facts'], key=task['facts'].__getitem__)
    result = {'family': task['family'], 'facts': [[i, task['facts'][n]] for i, n in enumerate(names)]}
    if task['family'] == 'update':
        result['update'] = [names.index(task['update']['subject']), task['update']['value']]
    return result


def canonical_root(task):
    return sha(['CANONICAL_CODE_FACT_ROOT_V1', canonical_fact(task)])


def split_for_root(root, seed=1337):
    bucket = int(sha(['SPLIT_BEFORE_RENDER', seed, root])[:16], 16) % 10
    return 'train' if bucket < 8 else 'dev' if bucket == 8 else 'test'


def is_reserved(task):
    checked_task(task)
    if task['family'] == 'addition':
        pair = tuple(sorted((task['a'], task['b'])))
        return pair in {tuple(sorted(p)) for p in ((1, 1), (2, 2), *CANARY_PAIRS)}
    # Preserve the user's apples 3/5 fact table under subject/order/ask changes,
    # including updates of that initial table. Food strings are out of domain.
    return sorted(task['facts'].values()) == [3, 5]


def truth(task):
    checked_task(task)
    if task['family'] == 'addition': return task['a'] + task['b']
    facts = dict(task['facts'])
    if task['family'] == 'update': facts[task['update']['subject']] = task['update']['value']
    return facts[task['asked']]


def build_steps(task):
    checked_task(task)
    if task['family'] == 'addition':
        steps = []; carry = 0
        for position in range(max(len(str(task['a'])), len(str(task['b'])))):
            a = task['a'] // 10**position % 10; b = task['b'] // 10**position % 10
            total = a + b + carry
            steps.append(dict(kind='digit', position=position, a=a, b=b, carry_in=carry,
                              total=total, digit=total % 10, carry_out=total // 10))
            carry = total // 10
        return steps
    steps = []
    if task['family'] == 'update':
        update = task['update']; name = update['subject']
        steps.append(dict(kind='update', subject=name, old=task['facts'][name], new=update['value']))
    steps.extend((dict(kind='query', subject=task['asked']),
                  dict(kind='select', subject=task['asked'], value=truth(task))))
    return steps


def validate_steps(task, steps):
    """Replay every claimed elementary operation against ORIGINAL input facts."""
    checked_task(task)
    if not isinstance(steps, list): raise ValueError('explicit step list required')
    if task['family'] == 'addition':
        width = max(len(str(task['a'])), len(str(task['b'])))
        if len(steps) != width: raise ValueError('exact digit-step count required')
        carry = 0; assembled = 0
        for position, step in enumerate(steps):
            keys = {'kind', 'position', 'a', 'b', 'carry_in', 'total', 'digit', 'carry_out'}
            if not isinstance(step, dict) or set(step) != keys or step['kind'] != 'digit':
                raise ValueError('exact digit-step fields required')
            if any(type(step[k]) is not int for k in keys - {'kind'}):
                raise ValueError('digit steps require integer fields')
            a, b = task['a'] // 10**position % 10, task['b'] // 10**position % 10
            total = a + b + carry
            if (step['position'], step['a'], step['b'], step['carry_in'], step['total'], step['digit'], step['carry_out']) != (
                    position, a, b, carry, total, total % 10, total // 10):
                raise ValueError('false operand/digit/sum/carry transition')
            assembled += step['digit'] * 10**position; carry = step['carry_out']
        assembled += carry * 10**width
        if assembled != task['a'] + task['b']: raise ValueError('digit assembly differs from independent addition')
        return assembled
    current = dict(task['facts']); offset = 0
    if any(not isinstance(s, dict) or any(type(s[k]) is not int for k in ('old', 'new', 'value') if k in s) for s in steps):
        raise ValueError('lookup/update numeric step fields must be integers, not bool/float')
    if task['family'] == 'update':
        if len(steps) != 3: raise ValueError('update/query/select steps required')
        step = steps[0]; update = task['update']; subject = update['subject']
        if step != dict(kind='update', subject=subject, old=current[subject], new=update['value']):
            raise ValueError('false updated subject/old value/new value')
        current[subject] = update['value']; offset = 1
    elif len(steps) != 2: raise ValueError('query/select steps required')
    if steps[offset] != dict(kind='query', subject=task['asked']):
        raise ValueError('trace queried a different subject')
    if steps[offset + 1] != dict(kind='select', subject=task['asked'], value=current[task['asked']]):
        raise ValueError('trace selected a stale/wrong subject value')
    return current[task['asked']]


def step_text(step):
    if step['kind'] == 'digit':
        return (f"D{step['position']}:{step['a']}+{step['b']}+{step['carry_in']}={step['total']},"
                f"d={step['digit']},c={step['carry_out']}")
    if step['kind'] == 'update': return f"U:{step['subject']}:{step['old']}->{step['new']}"
    if step['kind'] == 'query': return 'Q:' + step['subject']
    if step['kind'] == 'select': return f"S:{step['subject']}={step['value']}"
    raise ValueError('unknown step kind')


def parse_steps(lines):
    steps = []
    for line in lines:
        match = re.fullmatch(r'D(\d+):(\d+)\+(\d+)\+(\d+)=(\d+),d=(\d+),c=(\d+)', line, re.ASCII)
        if match:
            values = list(map(int, match.groups()))
            steps.append(dict(zip(('position', 'a', 'b', 'carry_in', 'total', 'digit', 'carry_out'), values), kind='digit'))
            continue
        match = re.fullmatch(r'U:([^\s:=;,]+):(\d+)->(\d+)', line, re.ASCII)
        if match:
            name, old, new = match.groups(); steps.append(dict(kind='update', subject=name, old=int(old), new=int(new))); continue
        match = re.fullmatch(r'Q:([^\s:=;,]+)', line)
        if match: steps.append(dict(kind='query', subject=match[1])); continue
        match = re.fullmatch(r'S:([^\s:=;,]+)=(\d+)', line, re.ASCII)
        if match:
            steps.append(dict(kind='select', subject=match[1], value=int(match[2]))); continue
        raise ValueError('unrecognized trace line')
    return steps


def parse_final_line(text, language=None):
    """One final marker only; never extract an arbitrary numeric substring."""
    bad = dict(ok=False, value=None, trace_lines=[], reason='final_line_contract')
    if language not in (None, 'ko', 'en') or not isinstance(text, str) or any(t in text for t in SPECIAL): return bad
    if any(ord(c) < 32 and c not in '\r\n\t' for c in text): return bad
    text = text.replace('\r\n', '\n')
    if '\r' in text or text.count('Answer:') + text.count('답:') != 1: return bad
    lines = text.split('\n')
    while lines and not lines[-1].strip(): lines.pop()
    if not lines: return bad
    marker = '답:' if language == 'ko' else 'Answer:' if language == 'en' else '(?:답:|Answer:)'
    match = re.fullmatch(marker + r'[ \t]*(0|[1-9][0-9]*)[ \t]*', lines[-1], re.ASCII)
    if match is None or len(match[1]) > 10: return bad
    return dict(ok=True, value=int(match[1]), trace_lines=lines[:-1], reason=None)


def score_response(task, text, language=None, policy=None):
    if policy not in (None, *POLICIES): raise ValueError('known policy required')
    parsed = parse_final_line(text, language); has_trace = bool(parsed['trace_lines'])
    valid = None; step_value = None; reason = parsed['reason']
    if has_trace:
        try: step_value = validate_steps(task, parse_steps(parsed['trace_lines'])); valid = True
        except (ValueError, TypeError, KeyError): valid = False; reason = 'invalid_trace'
    final = parsed['ok'] and parsed['value'] == truth(task)
    compliant = parsed['ok'] and (not has_trace if policy == 'direct' else valid is True if policy == 'trace' else True)
    return dict(final_contract=parsed['ok'], final_value=parsed['value'], final_correct=bool(final),
        trace_present=has_trace, trace_valid=valid, trace_value=step_value,
        trace_final_agree=None if valid is not True else step_value == parsed['value'],
        policy_compliant=bool(compliant), reason=reason)


def oriented_task(task, flip):
    """Presentation only: change raw name/value orientation, never root/split."""
    checked_task(task); result = copy.deepcopy(task)
    if type(flip) is not bool: raise ValueError('explicit presentation orientation required')
    if not flip: return result
    if task['family'] == 'addition': result['a'], result['b'] = result['b'], result['a']; return result
    a, b = sorted(task['facts']); rename = {a: b, b: a}
    result['facts'] = {rename[n]: v for n, v in task['facts'].items()}
    result['asked'] = rename[task['asked']]
    if task['family'] == 'update': result['update']['subject'] = rename[task['update']['subject']]
    return result


def render_row(task, language, policy, split, view=0):
    if language not in ('ko', 'en') or policy not in POLICIES or split not in COUNTS or view not in (0, 1, 2, 3):
        raise ValueError('registered language/policy/split/view required')
    checked_task(task); task = copy.deepcopy(task); ko = language == 'ko'
    if task['family'] == 'addition':
        if view % 2: task['a'], task['b'] = task['b'], task['a']
        a, b = task['a'], task['b']
        question = (f'{a}+{b}를 계산하세요.' if ko else f'Calculate {a}+{b}.') if view // 2 == 0 else (
            f'질문: 두 수의 합은 얼마입니까?\n수: {a}, {b}' if ko else f'Question: what is the sum?\nNumbers: {a}, {b}')
    else:
        names = sorted(task['facts'])
        task['asked'] = names[view % 2]
        if view // 2: names.reverse()
        table = '; '.join(f"{n}={task['facts'][n]}" for n in names)
        record = ('기록: ' if ko else 'Records: ') + table
        update = ''
        if task['family'] == 'update':
            u = task['update']; update = ('변경: ' if ko else 'Update: ') + f"{u['subject']}={u['value']}"
        query = f"질문: {task['asked']}의 현재 값은?" if ko else f"Question: what is the current value of {task['asked']}?"
        # Wording/context placement is independently hash-owned; it is not the
        # queried subject or first-row bit. Four views are order x asked target.
        wording = int(sha(['WORDING_ONLY', canonical_root(task)])[:4], 16) % 2
        question = '\n'.join(p for p in ((query, record, update) if wording else (record, update, query)) if p)
    question += ("\n마지막 줄은 '답: 정수' 형식으로 정확히 한 번 쓰세요." if ko else
                 "\nWrite exactly one final line in the form 'Answer: integer'.")
    final = ('답: ' if ko else 'Answer: ') + str(truth(task))
    steps = build_steps(task); validate_steps(task, steps)
    answer = '\n'.join([*(step_text(s) for s in steps), final]) if policy == 'trace' else final
    root = canonical_root(task)
    presentation = dict(wording=view // 2, operand_order=view % 2,
        raw_a_lt_b=task['a'] < task['b'], equal_operands=task['a'] == task['b']) if task['family'] == 'addition' else dict(
        asked=task['asked'], first_subject=names[0], wording=wording,
        raw_A_lt_B=task['facts'][sorted(task['facts'])[0]] < task['facts'][sorted(task['facts'])[1]])
    if task['family'] == 'update':
        presentation.update(target_updated=task['asked'] == task['update']['subject'],
                            answer_changed=truth(task) != task['facts'][task['asked']])
    presentation['view'] = view
    return dict(messages=[dict(role='user', content=question), dict(role='assistant', content=answer)],
        meta=dict(schema=VERSION, root=root, family=task['family'], split=split, language=language,
                  policy=policy, view=view, task=task, gold_value=truth(task), question_sha256=sha(question),
                  row_id=sha([root, split, language, view, policy]), source='CODE_OWNED_PROCEDURAL',
                  presentation=presentation, gold_trace_in_prompt=False, unique_knowledge_claim=False))


def presentation_summary(rows):
    groups = {}
    for row in rows:
        m = row['meta']; key = m['family'] + ':' + m['language']
        counts = groups.setdefault(key, Counter()); counts['rows'] += 1
        for field, value in m['presentation'].items(): counts[field + '=' + str(value)] += 1
        p = m['presentation']
        if m['family'] != 'addition':
            counts[f"joint:orientation={p['raw_A_lt_B']}:asked={p['asked']}:first={p['first_subject']}"] += 1
    return {key: dict(value) for key, value in groups.items()}


def shortcut_baselines(rows):
    """Named deterministic shortcuts, not a model or a correct-answer grader."""
    groups = {}
    for row in rows:
        m = row['meta']; task = m['task']; family = task['family']; gold = truth(task)
        if family == 'addition': predictions = dict(first_operand=task['a'], maximum_operand=max(task['a'], task['b']))
        else:
            p = m['presentation']; initial = task['facts']; current = dict(initial)
            if family == 'update': current[task['update']['subject']] = task['update']['value']
            predictions = dict(first_initial_value=initial[p['first_subject']],
                               first_current_value=current[p['first_subject']], maximum_current_value=max(current.values()))
            if family == 'update':
                predictions.update(stale_asked_value=initial[task['asked']], last_update_value=task['update']['value'])
        for name, predicted in predictions.items():
            item = groups.setdefault(family, {}).setdefault(name, dict(correct=0, total=0))
            item['correct'] += int(predicted == gold); item['total'] += 1
    return groups


def batch_groups(indices, micro_bs=8, accum=16):
    indices = list(indices)
    if (micro_bs != 8 or accum != 16 or len(indices) != 128 or len(set(indices)) != 128
            or any(type(i) is not int or i < 0 for i in indices)):
        raise ValueError('exact128 distinct rows/sixteen full eight-row micros required')
    return [indices[i:i + 8] for i in range(0, 128, 8)]


def training_schedule(row_count=4096, seed=1337):
    if type(row_count) is not int or row_count < 128 or row_count % 128:
        raise ValueError('whole128-row updates required; no partial gradient accumulation')
    result = []
    for epoch in range(4):
        order = sorted(range(row_count), key=lambda i: sha([VERSION, seed, epoch, i]))
        for start in range(0, row_count, 128):
            result.append(dict(update=len(result) + 1, epoch=epoch + 1,
                               micros=batch_groups(order[start:start + 128])))
    return result


def _pair(index, maximum, equal):
    for low in range(maximum + 1):
        width = maximum - low + int(equal)
        if index < width: return low, low + int(not equal) + index
        index -= width
    raise ValueError('pair index out of range')


def _candidates(family, seed, limit):
    pairs = 5050 if family == 'addition' else 32640
    capacity = pairs * (2 * 254 if family == 'update' else 1)
    start = int(sha([VERSION, seed, family, 'START'])[:16], 16) % capacity
    step = 1 + int(sha([VERSION, seed, family, 'STEP'])[:16], 16) % (capacity - 1)
    while math.gcd(step, capacity) != 1: step = step % (capacity - 1) + 1
    for count in range(min(limit, capacity)):
        index = (start + count * step) % capacity
        if family == 'addition':
            a, b = _pair(index, 99, True); yield dict(family=family, a=a, b=b); continue
        pair_index, change = divmod(index, 508) if family == 'update' else (index, 0)
        low, high = _pair(pair_index, 255, False)
        task = dict(family=family, facts={'A': low, 'B': high}, asked='A')
        if family == 'update':
            subject, value = divmod(change, 254)
            if value >= low: value += 1
            if value >= high: value += 1
            task['update'] = dict(subject=('A', 'B')[subject], value=value)
        yield task


def _build_course(counts, seed, candidate_limit):
    if type(seed) is not int or type(candidate_limit) is not int or candidate_limit < 1:
        raise ValueError('integer seed and positive bounded candidate budget required')
    if (set(counts) != set(COUNTS) or any(set(counts[s]) != set(FAMILIES) for s in counts)
            or any(type(n) is not int or n < 1 for v in counts.values() for n in v.values())
            or any(counts['train'][f] % 2 for f in FAMILIES)
            or any(counts[s]['update'] % 2 for s in counts)):
        raise ValueError('positive family counts and even bilingual TRAIN counts required')
    roots = {s: [] for s in counts}; rejected = {}; consumed = {}
    for family in FAMILIES:
        picked = {s: [] for s in counts}
        picked_strata = {s: Counter() for s in counts}
        seen = set(); used = 0; blocked = 0
        for task in _candidates(family, seed, candidate_limit):
            used += 1; root = canonical_root(task)
            if root in seen: raise ValueError('candidate generator repeated a semantic root')
            seen.add(root)
            if is_reserved(task): blocked += 1; continue
            split = split_for_root(root, seed)
            stratum = canonical_fact(task)['update'][0] if family == 'update' else None
            stratum_full = family == 'update' and picked_strata[split][stratum] >= counts[split][family] // 2
            if len(picked[split]) < counts[split][family] and not stratum_full:
                picked[split].append(task); picked_strata[split][stratum] += 1
            if all(len(picked[s]) == counts[s][family] for s in counts): break
        else:
            raise SupplyExhausted(f'{family}: required={dict((s, counts[s][family]) for s in counts)} '
                                  f'found={dict((s, len(v)) for s, v in picked.items())}; do not duplicate/shrink')
        for split, tasks in picked.items(): roots[split].extend(tasks)
        rejected[family] = blocked; consumed[family] = used
    result = {s: {p: [] for p in POLICIES} for s in counts}
    for split in counts:
        family_indices = Counter()
        ordered = sorted(roots[split], key=lambda t: sha([seed, 'ROW', canonical_root(t)]))
        for task in ordered:
            family = task['family']; stratum = canonical_fact(task)['update'][0] if family == 'update' else None
            lane = (family, stratum); index = family_indices[lane]; family_indices[lane] += 1
            # Root hash order is independent from numeric order. Crossed rank
            # bits balance language, raw orientation, asked/order within each
            # family (and each canonical update-target stratum).
            flip = bool((index // 2) % 2) if split == 'train' else bool(index % 2)
            task = oriented_task(task, flip)
            fixed_view = (index // 4) % 2 + 2 * ((index // 8) % 2)
            views = [(('ko', 'en')[index % 2], fixed_view)] if split == 'train' else [
                (language, view) for language in ('ko', 'en') for view in range(4)]
            for language, view in views:
                for policy in POLICIES:
                    result[split][policy].append(render_row(task, language, policy, split, view))
    root_ids = {s: sorted(canonical_root(t) for t in roots[s]) for s in roots}
    if any(set(root_ids[a]) & set(root_ids[b]) for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test'))):
        raise ValueError('semantic root split leakage')
    for split in counts:
        for direct, trace in zip(result[split]['direct'], result[split]['trace']):
            if direct['messages'][0] != trace['messages'][0] or direct['meta']['root'] != trace['meta']['root']:
                raise ValueError('same question/root pair required')
            for row in (direct, trace):
                m = row['meta']; task = m['task']
                score = score_response(task, row['messages'][-1]['content'], m['language'], m['policy'])
                if (is_reserved(task) or m['root'] != canonical_root(task) or split_for_root(m['root'], seed) != split
                        or row['messages'][0]['content'] in USER6 or not score['final_correct'] or not score['policy_compliant']):
                    raise ValueError('row source/split/reservation/answer/step contract differs')
    train = result['train']['direct']; n = len(train)
    zero_one = sorted({operand for row in train if row['meta']['family'] == 'addition'
                       for operand in (row['meta']['task']['a'], row['meta']['task']['b']) if operand in (0, 1)})
    production = counts == COUNTS
    if production and (n != 4096 or zero_one != [0, 1]):
        raise SupplyExhausted('production4096 and both0/1 TRAIN exposure required; no condition reduction')
    language_counts = {lang: sum(r['meta']['language'] == lang for r in train) for lang in ('ko', 'en')}
    if language_counts['ko'] != n // 2 or language_counts['en'] != n // 2:
        raise ValueError('same fixed bilingual half rows required')
    presentations = {s: presentation_summary(result[s]['direct']) for s in counts}
    if production:
        for split, summary in presentations.items():
            for family in ('lookup', 'update'):
                for language in ('ko', 'en'):
                    c = summary[family + ':' + language]; total = c['rows']
                    expected = {'raw_A_lt_B=True': total // 2, 'raw_A_lt_B=False': total // 2,
                        'asked=A': total // 2, 'asked=B': total // 2,
                        'first_subject=A': total // 2, 'first_subject=B': total // 2}
                    expected.update({'view=' + str(v): total // 4 for v in range(4)})
                    expected.update({f'joint:orientation={o}:asked={a}:first={f}': total // 8
                                     for o in (True, False) for a in ('A', 'B') for f in ('A', 'B')})
                    if family == 'update':
                        expected.update({'target_updated=True': total // 2, 'target_updated=False': total // 2,
                                         'answer_changed=True': total // 2, 'answer_changed=False': total // 2})
                    if any(c.get(k, 0) != v for k, v in expected.items()):
                        raise ValueError('independent family/language presentation balance failed: ' + split + '/' + family + '/' + language)
    result['roots'] = roots
    result['report'] = dict(schema=VERSION, seed=seed, production_geometry=production,
        counts=copy.deepcopy(counts), root_ids=root_ids, root_ids_sha256=sha(root_ids),
        train_rows=n, train_languages=language_counts, zero_one_train_operands=zero_one,
        rows_per_policy={s: len(result[s]['direct']) for s in counts},
        ordered_train_roots_sha256=sha([r['meta']['root'] for r in train]),
        four_pass_updates=128 if production else None, four_pass_positive_rows=n * 4,
        padded_sft_slots_ceiling=n * 4 * 1024, token_counts='NOT_MEASURED_NO_TOKENIZER_OPENED',
        reservation_owner=RESERVATION_OWNER, user_questions_sha256=sha(USER6),
        reserved_addition_roots=sorted(canonical_root(dict(family='addition', a=a, b=b)) for a, b in ((1, 1), (2, 2), *CANARY_PAIRS)),
        user_food_fact_outside_integer_domain=True, reserved_numeric_initial_values=[3, 5],
        rejected_reserved=rejected, candidates_consumed=consumed, source='CODE_OWNED_ONLY',
        presentation_counts=presentations,
        shortcut_baselines={s: shortcut_baselines(result[s]['direct']) for s in counts},
        label_efficiency_is_not_token_efficiency=True, gold_trace_in_prompt=False,
        model_loading='NOT_RUN', tokenizer_loading='NOT_RUN', formal_train_ready=False)
    return result


def build_course(*, seed=1337, candidate_limit=50_000):
    """Fixed production4096/128/128 ROOTS, one fixed language row/TRAIN root."""
    return _build_course(copy.deepcopy(COUNTS), seed, candidate_limit)
