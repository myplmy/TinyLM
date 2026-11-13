"""Fresh code-owned P108 diagnostic questions, not training or benchmark data."""
from collections import Counter
import json
import random

from scripts.p108_balanced_practice import NAMES, WORDS, ROLES, strict_score
from scripts.diag_p108_weight_space import OPEN

FAMILIES = ('arithmetic', 'lookup', 'role', 'boolean', 'update', 'copy', 'repeat', 'json')
FRESH_OPEN = (
    '물과 얼음은 어떻게 다른가요? 두 문장으로 설명해 주세요.',
    '도서관에서 책을 빌린 뒤에는 무엇을 해야 하나요?',
    '비가 오는 날 우산을 쓰는 이유를 알려 주세요.',
    '영희가 민수에게 연필을 주었습니다. 누가 연필을 받았나요?',
    '아침 인사를 한 문장으로 해 주세요.',
    '시간이 없는데 언제 어디로 가야 하는지 말하지 않았어요. 필요한 정보를 물어봐 주세요.',
    '사과 두 개에서 한 개를 먹었습니다. 몇 개 남았나요?',
    '고양이를 처음 키울 때 물과 먹이는 어떻게 준비하나요?',
    'Why does a person need sleep? Use two short sentences.',
    'Please explain the difference between a question and an answer.',
    'What should I do before crossing a busy road?',
    'Emma gives Frank a pencil. Who receives the pencil?',
    'Say good morning in one sentence.',
    'I want to travel, but have not said where or when. Ask for the missing details.',
    'Two birds sit on a branch and one leaves. How many remain?',
    'How can I keep a glass of drinking water clean?',
)


def make_data():
    rng = random.Random(20261105)
    numbers = [(a, b) for a in range(1, 31) for b in range(a, 31)]
    rng.shuffle(numbers)
    rows = []
    for block, (split, count, offset) in enumerate((('dev', 16, 700), ('test', 32, 900))):
        for family in FAMILIES:
            for within in range(count // 2):
                a, b = numbers.pop()
                target, reverse = within % 2, (within // 2) % 2
                distance = 1 if block == 0 else 2 + within // 8
                actor_indices = [within % 8, (within + distance) % 8]
                value_indices = [within % 8, (within + 3) % 8]
                serial = offset + within
                for lang in ('ko', 'en'):
                    ko = lang == 'ko'
                    actors = [NAMES[lang][i] for i in actor_indices]
                    values = [WORDS[lang][i] for i in value_indices]
                    if family == 'arithmetic':
                        rule = facts = dict(a=a, b=b)
                        q = (f'{a}에 {b}를 더한 결과를 숫자로만 답하세요.' if ko else
                             f'Calculate {a} plus {b}. Give only the number.')
                        expected = str(a + b)
                    elif family == 'lookup':
                        facts = dict(associations=sorted(zip(actor_indices, value_indices)))
                        rule = dict(facts, target=target, reverse=reverse)
                        clauses = [f'{actors[i]}의 표시는 {values[i]}입니다' if ko else
                                   f'The label for {actors[i]} is {values[i]}' for i in range(2)]
                        if reverse: clauses.reverse()
                        q = ('문장: ' + '. '.join(clauses) + f'. 질문: {actors[target]}의 표시는? 단어만 답하세요.' if ko else
                             'Statements: ' + '. '.join(clauses) + f'. Question: What is the label for {actors[target]}? Give only the label.')
                        expected = values[target]
                    elif family == 'role':
                        roles = [within % 4, (within + 1) % 4]
                        facts = dict(associations=sorted(zip(actor_indices, roles)))
                        rule = dict(facts, target=target, reverse=reverse)
                        clauses = [f'{actors[i]}는 {ROLES[lang][roles[i]][0]}' if ko else
                                   f'{actors[i]} {ROLES[lang][roles[i]][0]}' for i in range(2)]
                        if reverse: clauses.reverse()
                        q = ('문장: ' + '. '.join(clauses) + f'. 질문: 누가 {ROLES[lang][roles[target]][1]}? 이름만 답하세요.' if ko else
                             'Statements: ' + '. '.join(clauses) + f'. Question: Who {ROLES[lang][roles[target]][1]}? Give only the name.')
                        expected = actors[target]
                    elif family == 'boolean':
                        op = 'AND' if within % 2 == 0 else 'OR'
                        left, right = bool((within // 2) % 2), bool((within // 4) % 2)
                        render = lambda v: ('참' if v else '거짓') if ko else ('true' if v else 'false')
                        u, v = f'G{serial}', f'H{serial}'
                        facts = dict(variables=[u, v], values=[left, right])
                        rule = dict(facts, operator=op, reverse=reverse)
                        clauses = [f'{u}={render(left)}', f'{v}={render(right)}']
                        if reverse: clauses.reverse()
                        q = (', '.join(clauses) + f'. {u} {op} {v}의 결과만 참 또는 거짓으로 답하세요.' if ko else
                             ', '.join(clauses) + f'. Give only true or false for {u} {op} {v}.')
                        expected = render(left and right if op == 'AND' else left or right)
                    elif family == 'update':
                        changed = (within // 2) % 2
                        vals = [a, b]
                        replacement = (vals[changed] + 7) % 31
                        vals[changed] = replacement
                        facts = dict(a=a, b=b, changed=changed, replacement=replacement)
                        rule = dict(facts, target=target)
                        q = (f'A의 수는 {a}, B의 수는 {b}입니다. {("A", "B")[changed]}의 수를 {replacement}로 고칩니다. {("A", "B")[target]}의 새 수만 답하세요.' if ko else
                             f'The number for A is {a}, and the number for B is {b}. Set the number for {("A", "B")[changed]} to {replacement}. Give only the new number for {("A", "B")[target]}.')
                        expected = str(vals[target])
                    elif family == 'copy':
                        expected = f'note-{serial}-{a}'
                        rule = facts = dict(text=expected)
                        q = f'다른 말 없이 이 문자열만 복사하세요: {expected}' if ko else f'Return only an exact copy of this string: {expected}'
                    elif family == 'repeat':
                        times = 2 + within % 4
                        rule = facts = dict(token=str(serial), times=times)
                        expected = ' '.join([str(serial)] * times)
                        q = (f'{serial}을 공백으로 나누어 {times}번 쓰고 끝내세요.' if ko else
                             f'Write {serial} {times} times with spaces and then stop.')
                    else:
                        rule = facts = dict(a=a, b=b)
                        expected = json.dumps({'answer': str(a + b)}, separators=(',', ':'))
                        q = (f'{a}에 {b}를 더하세요. answer 키 하나와 문자열 값만 있는 JSON 객체로 답하세요.' if ko else
                             f'Add {a} and {b}. Return a JSON object with only the key answer and a string value.')
                    source = family + ':' + json.dumps(facts, sort_keys=True, separators=(',', ':'))
                    rows.append(dict(id=f'{split}_{family}_{within:02d}_{lang}', split=split,
                        family=family, language=lang, question=q, expected=expected,
                        source_group=source, rule=rule,
                        protected=family in ('copy', 'repeat')))
    for split, questions in (('open_seen', OPEN), ('open_fresh', FRESH_OPEN)):
        for i, q in enumerate(questions):
            rows.append(dict(id=f'{split}_{i:03d}', split=split, family=split,
                             language='ko' if i < 8 else 'en', question=q,
                             expected=None, protected=False))
    validate(rows)
    return rows


def validate(rows):
    for split, count in (('dev', 16), ('test', 32)):
        group = [r for r in rows if r['split'] == split]
        if Counter(r['family'] for r in group) != Counter({f: count for f in FAMILIES}):
            raise ValueError('fresh diagnostic family counts differ')
        boolean = [r['expected'] for r in group if r['family'] == 'boolean']
        if Counter(boolean) != Counter({'참': count // 4, '거짓': count // 4,
                                       'true': count // 4, 'false': count // 4}):
            raise ValueError('fresh Boolean balance differs')
    a = {r['source_group'] for r in rows if r['split'] == 'dev'}
    b = {r['source_group'] for r in rows if r['split'] == 'test'}
    prompts = [r['question'] for r in rows if r['expected'] is not None]
    if a & b or len(set(prompts)) != len(prompts):
        raise ValueError('fresh split/source prompt overlap')
    return dict(rows=len(rows), counts=dict(Counter(r['split'] for r in rows)),
                dev_test_source_overlap=0,
                scope='EXPLORATORY_CODE_RULES_NOT_OFFICIAL_BENCHMARK')
