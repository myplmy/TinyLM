"""Project-authored conditional QA plus replay contracts; no model/data on import."""
from __future__ import annotations

import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate
from scripts.p106b_context_quality import make, sha, text

VERSION = 'P106B_CONTEXT_REPLAY_V1'
NAMES = {
    'ko': {
        'train': ['민수','지수','진우','예린','태호','소희','하준','은서','도윤','유진','서준','수빈'],
        'dev': ['지후','서연','현우','채원','정우','하린','시우','예나','수호','윤아','건우','소율'],
        'test': ['예준','도하','유나','세아','재윤','이안','아린','나윤','수아','지안','태민','다온']},
    'en': {
        'train': ['Alice','Brian','Claire','Daniel','Eva','Frank','Grace','Henry','Iris','Jack','Kate','Leon'],
        'dev': ['Lina','Theo','Rose','Owen','Ruby','Paul','Jade','Kyle','Tina','Ivan','Hugo','Emma'],
        'test': ['Oscar','Piper','Quinn','Reed','Sara','Troy','Uma','Vera','Wade','Xena','Yuri','Zane']}}
WEIGHTS = {'sft_only': 0., 'replay025': .25, 'replay100': 1.}


def binding_rows(split, per_family=None):
    if split not in ('train', 'dev', 'test'):
        raise ValueError('explicit split required')
    take = per_family if per_family is not None else (256 if split == 'train' else 32)
    result = []
    for language in ('ko', 'en'):
        names = NAMES[language][split]
        for family in ('color', 'department'):
            values = ({'ko': ['빨강','파랑','노랑','초록','보라','주황'],
                       'en': ['red','blue','yellow','green','purple','orange']} if family == 'color' else
                      {'ko': ['산수과','문법과','물리학과','역사학과','음악과','미술과'],
                       'en': ['Physics','History','Music','Art','Math','Grammar']})[language]
            combinations = [(a,b,x,y) for a in names for b in names if a < b
                            for x in values for y in values if x != y]
            random.Random(str((20261015, split, language, family))).shuffle(combinations)
            if take > len(combinations):
                raise ValueError('unique mapping supply exhausted')
            for a,b,x,y in combinations[:take]:
                mapping = {a:x, b:y}
                root = sha(dict(task='binding', language=language, family=family, mapping=mapping))
                for order in ((a,b), (b,a)):
                    for asked in (a,b):
                        if language == 'ko':
                            facts = [f'{n}의 색상은 {mapping[n]}입니다.' if family == 'color' else
                                     f'{n} 건물에는 {mapping[n]}가 있습니다.' for n in order]
                            question = (f'{asked}의 색상' if family == 'color' else f'{asked} 건물의 학과')
                            endings = [f'{question}만 답하세요.', f'{question}는 무엇인가요? 이름만 쓰세요.',
                                       f'위 기록에서 {question}에 해당하는 값만 쓰세요.',
                                       f'질문: {question}는? 다른 설명 없이 답하세요.']
                        else:
                            facts = [f'{n} is {mapping[n]}.' if family == 'color' else
                                     f'The {n} building houses {mapping[n]}.' for n in order]
                            question = f'the color of {asked}' if family == 'color' else f'the department in the {asked} building'
                            endings = [f'Give only {question}.', f'What is {question}? Name only.',
                                       f'According to the record, state only {question}.',
                                       f'Question: what is {question}? Answer without explanation.']
                        variant = int(sha([root, list(order), asked])[:8], 16) % 4
                        user = (' '.join(facts) if variant % 2 else '\n'.join(facts)) + '\n' + endings[variant]
                        result.append(validate(normalize(dict(messages=[dict(role='user', content=user),
                            dict(role='assistant', content=mapping[asked])], meta=dict(
                            source='PROJECT_AUTHORED_CODE', source_license='project_authored_fictional',
                            language=language, kind='binding_'+family, rubric='EXACT_SCALAR',
                            semantic_root_id=root, source_split=split, truth='PRODUCER_CODE_FACT_CONTRACT',
                            requested_entity=asked, mapping=mapping, ordered_entities=list(order),
                            target_is_first=asked == order[0], first_value=mapping[order[0]],
                            course_version=VERSION)))))
    return result


def code_rows():
    output = {}; used = set(); bodies = set()
    for split, count in (('train',1024), ('dev',128), ('test',128)):
        rows = []; attempt = 0
        while len(rows) < count:
            language = ('ko','en')[len(rows) % 2]
            kind = ('arithmetic','boolean','json','update')[(len(rows)//2) % 4]
            seed = {'train': 7100000, 'dev': 8100000, 'test': 9100000}[split] + attempt
            attempt += 1
            if attempt > count*100:
                raise ValueError('unique code supply exhausted')
            row = make(kind, language, seed, novel=split != 'train')
            root = row['meta']['semantic_root_id']; signature = sha(row['messages'])
            if root in used or signature in bodies:
                continue
            used.add(root); bodies.add(signature)
            row['meta'].update(source_split=split, course_version=VERSION,
                               truth='PRODUCER_CODE_FACT_CONTRACT')
            rows.append(row)
        output[split] = binding_rows(split) + rows
    return output


def add_public(output, original):
    """Old source QA is pseudo evidence, not code truth or a fresh world test."""
    for old_split, new_split in (('train','train'), ('val','dev')):
        for row in original[old_split]:
            if row['meta']['kind'] != 'source_qa':
                continue
            item = copy.deepcopy(row)
            item['meta'].update(kind='public_qa', rubric='UNSCORED_PUBLIC_QA',
                truth='PSEUDO_UNVERIFIED', source_split=new_split, course_version=VERSION,
                eval_scope='PRIOR_PUBLIC_DEVELOPMENT_NOT_INDEPENDENT_WORLD_TEST')
            output[new_split].append(item)
    return output


def validate_splits(rows):
    roots = {}; bodies = {}
    for split, values in rows.items():
        roots[split] = {r['meta']['semantic_root_id'] for r in values}
        bodies[split] = {sha(r['messages']) for r in values}
        if len(bodies[split]) != len(values):
            raise ValueError('duplicate conversation within split')
    for a,b in (('train','dev'), ('train','test'), ('dev','test')):
        if roots[a] & roots[b] or bodies[a] & bodies[b]:
            raise ValueError('source root/conversation leakage')
    for language, splits in NAMES.items():
        if any(set(splits[a]) & set(splits[b]) for a,b in
               (('train','dev'), ('train','test'), ('dev','test'))):
            raise ValueError('binding entity names leak')
    return {split: dict(Counter(r['meta']['kind'] for r in values)) for split,values in rows.items()}


def native_offsets(token_count, count, width=1024):
    if token_count < (width+1)*count or count < 1:
        raise ValueError('not enough disjoint native train windows')
    blocks = random.Random(20261015).sample(range(token_count//(width+1)), count)
    return [i*(width+1) for i in blocks]


def exact(answer, gold, rubric):
    if rubric == 'UNSCORED_PUBLIC_QA':
        return None
    answer = answer.strip()
    if rubric == 'EXACT_JSON_OBJECT':
        try:
            return json.loads(answer) == json.loads(gold)
        except (ValueError, TypeError):
            return False
    if rubric == 'EXACT_INTEGER':
        import re
        return bool(re.fullmatch(r'[+-]?\d+', answer)) and int(answer) == int(gold)
    if rubric not in ('EXACT_SCALAR', 'EXACT_BOOLEAN'):
        raise ValueError('unknown output contract')
    return answer.casefold() == gold.casefold()


def combined_loss(sft_sum, sft_denominator, native_sum, native_denominator, weight):
    if min(sft_denominator, native_denominator) <= 0 or weight not in WEIGHTS.values():
        raise ValueError('positive whole-update denominators and registered weight required')
    return sft_sum/sft_denominator + weight*native_sum/native_denominator
