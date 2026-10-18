"""Code-certified closed-world relation bundles; no model or source IO on import.

This deliberately does not certify natural QA cross-answers as negatives.
Facts are fictional. Agreement with the generated relation table is the label
contract, not a certificate of knowledge about real people or the world.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCHEMA = 'P106B_RELATION_BIND_DATA_V1'
TAG = 'p106b_relation_bind_v1_s1337'
FAMILIES = ('kinship', 'work', 'project', 'event')
SPLITS = ('train', 'dev', 'test')
COUNTS = dict(train=2048, dev=128, test=128)
NAMES = {
    'ko': ('민수', '영희', '지훈', '수진', '성호', '지영', '준호', '은지',
           '현우', '서연', '도윤', '지우', '유진', '하준', '예린', '정우',
           '소연', '태훈', '지민', '혜진', '동현', '수현', '승우', '민지'),
    'en': ('Alice', 'Brian', 'Clara', 'David', 'Emma', 'Frank', 'Grace', 'Henry',
           'Irene', 'James', 'Kate', 'Leo', 'Maria', 'Noah', 'Olivia', 'Peter',
           'Quinn', 'Rosa', 'Sam', 'Tina', 'Ursula', 'Victor', 'Wendy', 'Zoe'),
}
# Each family has exactly two relations. All answers are PERSON, not a coarse
# mixture of years/places/titles that can be solved by answer type alone.
RELATIONS = {
    'kinship': {'ko': ('아버지', '스승'), 'en': ('father', 'mentor')},
    'work': {'ko': ('상사', '보조 담당자'), 'en': ('manager', 'assistant')},
    'project': {'ko': ('설계 담당자', '검토 담당자'), 'en': ('designer', 'reviewer')},
    'event': {'ko': ('안내 담당자', '진행 담당자'), 'en': ('guide', 'coordinator')},
}


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def exact_answer(value):
    """Conservative metric: preserve punctuation, numbers, negation and case."""
    if not isinstance(value, str): raise ValueError('text answer required')
    return unicodedata.normalize('NFKC', value).strip()


def split_of(group_id):
    bucket = int(sha([SCHEMA, 'SPLIT', group_id])[:12], 16) % 100
    return 'train' if bucket < 80 else 'dev' if bucket < 90 else 'test'


def _spec(family, slots):
    if (family not in FAMILIES or not isinstance(slots, (list, tuple)) or len(slots) != 6
            or any(type(v) is not int or not 0 <= v < len(NAMES['ko']) for v in slots)
            or len(set(slots)) != 6):
        raise ValueError('six distinct entity slots and a declared family required')
    # Two queried roles for the same subject, plus another subject as distractor.
    s, other, a, b, c, d = slots
    facts = [(s, 0, a), (s, 1, b), (other, 0, c), (other, 1, d)]
    group_id = sha([SCHEMA, family, sorted(facts)])
    return group_id, facts


def _sentence(family, fact, language):
    s, relation, answer = fact
    names, roles = NAMES[language], RELATIONS[family][language]
    if language == 'ko':
        return f'{names[s]}의 {roles[relation]}: {names[answer]}.'
    return f'{names[s]} -- {roles[relation]}: {names[answer]}.'


def _question(family, subject, relation, language, alternate):
    name, role = NAMES[language][subject], RELATIONS[family][language][relation]
    if language == 'ko':
        final = ord(role[-1]) - 0xAC00
        topic = '은' if 0 <= final < 11172 and final % 28 else '는'
        return (f'기록에서 {name}의 {role}에 해당하는 사람은 누구인가요?' if alternate
                else f'{name}의 {role}{topic} 누구입니까?')
    return (f'According to the record, which person is the {role} of {name}?' if alternate
            else f'Who is the {role} of {name}?')


def build_bundle(family, slots, language):
    if language not in NAMES: raise ValueError('ko or en required')
    group_id, facts = _spec(family, slots)
    rng = random.Random(int(group_id[:16], 16))
    order = list(range(4)); rng.shuffle(order)
    questions = [0, 1]; rng.shuffle(questions)
    table = {(s, r): a for s, r, a in facts}
    subject = slots[0]
    result = dict(schema=SCHEMA, group_id=group_id, bundle_id=sha([group_id, language]),
        split=split_of(group_id), family=family, language=language, slots=list(slots),
        facts=[list(f) for f in facts], fact_order=order, query_order=questions,
        subject=subject, answers=[NAMES[language][table[subject, r]] for r in questions],
        negative_checks=[dict(question_index=qi, subject_id=subject, relation_id=r,
            correct_entity_id=table[subject, r], rejected_entity_id=table[subject, 1 - r],
            status='INVALID_FOR_THIS_QUERY', reason='different unique value of the other declared role')
            for qi, r in enumerate(questions)],
        label_status='CODE_GENERATED_CLOSED_WORLD', answer_type='PERSON',
        negative_policy='only the other verified role answer in this same bundle',
        context_scope='fictional record only; no world-truth claim', teacher_calls=0)
    result['bundle_sha256'] = sha(result)
    return result


def validate_bundle(bundle):
    if not isinstance(bundle, dict): raise ValueError('relation bundle required')
    expected = build_bundle(bundle.get('family'), bundle.get('slots'), bundle.get('language'))
    if bundle != expected: raise ValueError('code-certified facts/answers/split/identity changed')
    if len({exact_answer(x) for x in bundle['answers']}) != 2:
        raise ValueError('two genuinely different role values required')
    return True


def render(bundle, qi, ai=None, view=0):
    """View0 trains; 1 reverses fact order; 2 changes question wording only.

    Crossed answers are scoring candidates, not supervised positive examples.
    Counterfactual fact edits are a separate future study, not silently mixed.
    """
    from tinylm.chat.canonical import normalize, validate
    validate_bundle(bundle)
    if qi not in (0, 1) or ai not in (None, 0, 1) or view not in (0, 1, 2):
        raise ValueError('declared query/candidate and view required')
    if bundle['split'] == 'train' and view != 0:
        raise ValueError('evaluation-only views must not become TRAIN')
    ai = qi if ai is None else ai
    order = bundle['fact_order'][::-1] if view == 1 else bundle['fact_order']
    language, family = bundle['language'], bundle['family']
    context = '\n'.join(_sentence(family, bundle['facts'][i], language) for i in order)
    relation = bundle['query_order'][qi]
    question = _question(family, bundle['subject'], relation, language, view == 2)
    if language == 'ko':
        prompt = f'다음 가상 기록만 참고하세요.\n기록:\n{context}\n질문: {question}\n사람 이름만 답하고 끝내세요.'
    else:
        prompt = f'Use only this fictional record.\nRecord:\n{context}\nQuestion: {question}\nAnswer only with the person\'s name, then stop.'
    return validate(normalize(dict(messages=[dict(role='user', content=prompt),
        dict(role='assistant', content=bundle['answers'][ai])], meta=dict(
            source='code_closed_world_relation_v1', source_group_id=bundle['group_id'],
            semantic_root_id=sha([bundle['bundle_id'], qi]), parent_concept_id=bundle['group_id'],
            bundle_id=bundle['bundle_id'], split=bundle['split'], family=family,
            language=language, question_index=qi, candidate_index=ai, view=view,
            positive_example=qi == ai, label_status=bundle['label_status'],
            source_sha256=bundle['bundle_sha256'], supervised_assistant_turns=[1]))))


def complete_record(row, tokenizer):
    """Require complete answer coverage and the exact answer-free prefix.

    A tokenizer that merges a header boundary with the first name piece must
    fail instead of silently supervising only the remaining name pieces.
    """
    from tinylm.train.mtp_sft import encode_record
    from tinylm.chat.serialize import serialize, loss_spans
    from scripts.p106b_night_qa_data import text as message_text
    record = encode_record(row, tokenizer, context=1024)
    text = serialize(row, 'chatml')
    encoded = tokenizer.encode(text)
    spans = loss_spans(row, 'chatml')
    if len(spans) != 1 or len(encoded.ids) != len(encoded.offsets):
        raise ValueError('one complete assistant span and actual token offsets required')
    start, finish = spans[0]; body_end = finish - len('<|im_end|>')
    answer = message_text(row['messages'][-1])
    if text[start:body_end] != answer or text[body_end:finish] != '<|im_end|>':
        raise ValueError('complete assistant body and explicit end marker required')
    positions = []; coverage = []; ends = []
    eot = tokenizer.token_to_id('<|im_end|>')
    if type(eot) is not int: raise ValueError('actual ChatML EOT required')
    for i, (a, b) in enumerate(encoded.offsets):
        if not 0 <= a <= b <= len(text): raise ValueError('actual unicode token offsets required')
        if start <= a < b <= body_end:
            positions.append(i); coverage.append((a, b))
        if (a, b) == (body_end, finish) and encoded.ids[i] == eot: ends.append(i)
    cursor = start
    for a, b in sorted(coverage):
        if a > cursor: raise ValueError('answer character coverage has a token-boundary hole')
        cursor = max(cursor, b)
    prompt = serialize(dict(messages=row['messages'][:1]), 'chatml', add_generation_prompt=True)
    prefix = tokenizer.encode(prompt).ids
    if (cursor != body_end or not positions or positions[0] < 1 or len(ends) != 1
            or encoded.ids[:positions[0]] != prefix or len(prefix) != positions[0]
            or len(prefix) + 128 > 1024 or record.x != list(encoded.ids[:-1])
            or [i for i, y in enumerate(record.y) if y != -100] != [i - 1 for i in positions + ends]
            or any(record.y[i - 1] != encoded.ids[i] for i in positions + ends)):
        raise ValueError('complete shifted content/EOT and exact answer-free predictor prefix required')
    labels = [v for v in record.y if v != -100]
    unknown = tokenizer.token_to_id('<unk>')
    if (not 1 < len(labels) <= 128 or labels[-1] != eot or eot in labels[:-1]
            or (unknown is not None and unknown in labels[:-1])):
        raise ValueError('complete non-UNK content and one terminal EOT required')
    return record


def encode_bundle(bundle, tokenizer):
    positive = [complete_record(render(bundle, q), tokenizer) for q in (0, 1)]
    crossed = [complete_record(render(bundle, q, 1 - q), tokenizer) for q in (0, 1)]
    # Same candidate, two questions: exact target vector, not just equal length.
    if ([v for v in positive[0].y if v != -100] != [v for v in crossed[1].y if v != -100]
            or [v for v in positive[1].y if v != -100] != [v for v in crossed[0].y if v != -100]):
        raise ValueError('candidate tokenization changed with question')
    if ([v for v in positive[0].y if v != -100] == [v for v in positive[1].y if v != -100]):
        raise ValueError('distinct answers collapsed to the same token sequence')
    return positive, crossed


def generate(counts=None, *, seed=20261017, eligible=None):
    """Select graphs before any model output; translations share one split."""
    counts = dict(COUNTS if counts is None else counts)
    if (set(counts) != set(SPLITS) or any(type(v) is not int or v < 8 or v % 8 for v in counts.values())
            or (eligible is not None and not callable(eligible))):
        raise ValueError('whole ko/en by four-family strata required')
    result = {s: [] for s in SPLITS}; seen = set()
    for family in FAMILIES:
        rng = random.Random(int(sha([SCHEMA, seed, family])[:16], 16))
        remaining = {s: counts[s] // 8 for s in SPLITS}
        for _ in range(100000):
            if not any(remaining.values()): break
            slots = rng.sample(range(len(NAMES['ko'])), 6)
            group_id, _ = _spec(family, slots)
            split = split_of(group_id)
            if group_id in seen or not remaining[split]: continue
            translated = [build_bundle(family, slots, language) for language in ('ko', 'en')]
            if eligible is not None and not all(eligible(b) for b in translated): continue
            seen.add(group_id); remaining[split] -= 1
            result[split].extend(translated)
        if any(remaining.values()): raise ValueError('distinct relation graph supply exhausted')
    for split, rows in result.items():
        rows.sort(key=lambda b: sha([seed, 'ORDER', b['bundle_id']]))
        if len(rows) != counts[split]: raise ValueError('balanced graph quota differs')
    validate_splits(result)
    return result


def validate_splits(splits):
    if set(splits) != set(SPLITS): raise ValueError('three explicit partitions required')
    group_owner = {}; bundle_ids = set()
    for split, bundles in splits.items():
        balance = Counter()
        for b in bundles:
            validate_bundle(b)
            if b['split'] != split or b['bundle_id'] in bundle_ids:
                raise ValueError('duplicate bundle or split mismatch')
            bundle_ids.add(b['bundle_id'])
            if b['group_id'] in group_owner and group_owner[b['group_id']] != split:
                raise ValueError('same fact graph leaked across languages/splits')
            group_owner[b['group_id']] = split
            balance[b['language'], b['family']] += 1
        if len(balance) != 8 or len(set(balance.values())) != 1:
            raise ValueError('language/family quota must be balanced')
    return True


def shortcut_counts(bundles):
    """Code-side baseline opportunities, not model performance or truth scores."""
    counts = Counter(); cells = Counter()
    for b in bundles:
        validate_bundle(b)
        positions = {fact[2]: i for i, fact in enumerate([b['facts'][j] for j in b['fact_order']])}
        values = {r: a for s, r, a in b['facts'] if s == b['subject']}
        candidate_first = min(values.values(), key=positions.get)
        alphabetical = min(b['answers'])
        for qi, relation in enumerate(b['query_order']):
            correct = b['answers'][qi]
            counts.update(questions=1, type_only_tie=1,
                first_of_two_role_candidates=int(values[relation] == candidate_first),
                alphabetically_first_candidate=int(correct == alphabetical),
                repeat_answer0=int(qi == 0))
            cells[b['language'], b['family'], qi, relation] += 1
    return dict(counts=dict(counts), query_position_role_cells={
        '|'.join(map(str, key)): value for key, value in sorted(cells.items())},
        caveat='Both answers share PERSON type; 50% shortcuts do not establish language or reasoning ability.')
