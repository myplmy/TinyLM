"""Pure subject/role derivatives of validated frozen A fact bundles.

No source/tokenizer file IO, model, teacher, tensor construction or GPU action.
There are still only the original fictional facts/names/role families. Four
queries do not create four independent fact graphs or certify world knowledge.
Canonical rows contain only the supported messages/assistant supervision
contract; provenance and candidate labels stay in the derivative outside it.
Actual frozen-file membership belongs to the caller's source/manifest checks;
this module verifies the supplied parent factory contract and exact derivation.
"""
from __future__ import annotations

from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import copy
from scripts import p106b_relation_bind_data as original
from scripts.p106b_night_qa_data import text as message_text

TAG = 'p106b_subject_role_v1_s1337'
SCHEMA = 'P106B_SUBJECT_ROLE_DATA_V1'
POSITIVE_LAYOUT = tuple((i, i) for i in range(4))
CROSSED_LAYOUT = tuple((i, j) for i in range(4) for j in range(4) if j != i)
CORRECT = 'CORRECT'
SAME_SUBJECT_OTHER_ROLE = 'SAME_SUBJECT_OTHER_ROLE'
OTHER_SUBJECT_SAME_ROLE = 'OTHER_SUBJECT_SAME_ROLE'
OTHER_SUBJECT_OTHER_ROLE = 'OTHER_SUBJECT_OTHER_ROLE'


def _index(value, label, maximum=4):
    if type(value) is not int or not 0 <= value < maximum:
        raise ValueError('explicit ' + label + ' index required')
    return value


def _derive(parent):
    original.validate_bundle(parent)
    subjects = list(parent['slots'][:2]); roles = list(parent['query_order'])
    table = {(s, r): a for s, r, a in parent['facts']}
    if len(table) != 4 or len(subjects) != 2 or len(set(subjects)) != 2 or sorted(roles) != [0, 1]:
        raise ValueError('two distinct subjects with exactly two unique role lookups required')
    queries = []; entities = []; answers = []
    for qi in range(4):
        subject = subjects[qi // 2]; role = roles[qi % 2]
        values = [a for s, r, a in parent['facts'] if s == subject and r == role]
        if len(values) != 1 or values[0] != table[subject, role]:
            raise ValueError('every query needs one exact code-table answer')
        entity = values[0]; answer = original.NAMES[parent['language']][entity]
        entities.append(entity); answers.append(answer)
        queries.append(dict(question_index=qi, subject_id=subject, role_id=role,
            correct_entity_id=entity, origin='ORIGINAL_A' if qi < 2 else 'ADDITIONAL_SUBJECT',
            parent_question_index=qi % 2))
    if (len(set(entities)) != 4 or len({original.exact_answer(v) for v in answers}) != 4
            or answers[:2] != parent['answers'] or parent['subject'] != subjects[0]):
        raise ValueError('four unique PERSON answers and unchanged first two original answers required')
    result = dict(schema=SCHEMA, tag=TAG, parent_bundle=copy.deepcopy(parent),
        parent_bundle_sha256=parent['bundle_sha256'], parent_bundle_id=parent['bundle_id'],
        parent_group_id=parent['group_id'], group_id=parent['group_id'],
        bundle_id=original.sha([SCHEMA, parent['bundle_id'], parent['bundle_sha256']]),
        split=parent['split'], inherited_source_split=parent['split'],
        family=parent['family'], language=parent['language'], slots=list(parent['slots']),
        facts=copy.deepcopy(parent['facts']), fact_order=list(parent['fact_order']),
        query_order=roles, subjects=subjects, queries=queries, answer_entity_ids=entities,
        answers=answers, answer_type='PERSON', label_status='CODE_GENERATED_CLOSED_WORLD',
        negative_policy='only other verified unique values of this same two-subject two-role fact table',
        new_fact_graphs_created=0, world_knowledge_claim=False, training_policy_adopted=False,
        teacher_calls=0)
    result['bundle_sha256'] = original.sha(result)
    return result


def derive_bundle(parent):
    """Create a different schema; never mutate subject/slots to bypass A validation."""
    return _derive(parent)


def validate_bundle(bundle, parent=None):
    if not isinstance(bundle, dict) or not isinstance(bundle.get('parent_bundle'), dict):
        raise ValueError('honest derivative and embedded validated original parent required')
    source = bundle['parent_bundle'] if parent is None else parent
    if bundle['parent_bundle'] != source or bundle != _derive(source):
        raise ValueError('parent identity/facts/queries/golds/labels/derivative fingerprint changed')
    return True


def query_id(bundle, qi, view=0):
    validate_bundle(bundle); _index(qi, 'question'); _index(view, 'view', 3)
    if qi < 2:
        return original.sha(['RELATION', bundle['parent_bundle_id'], view, qi])
    return original.sha([SCHEMA, 'QUERY', bundle['parent_bundle_id'], view, qi])


def error_type(qi, ai):
    """The four query/candidate labels are mutually exclusive and exhaustive."""
    _index(qi, 'question'); _index(ai, 'candidate')
    if qi == ai: return CORRECT
    if qi // 2 == ai // 2: return SAME_SUBJECT_OTHER_ROLE
    if qi % 2 == ai % 2: return OTHER_SUBJECT_SAME_ROLE
    return OTHER_SUBJECT_OTHER_ROLE


def candidate_layout():
    """Graph-major, then q-major; off-diagonal answer index increases within q."""
    return dict(positive=POSITIVE_LAYOUT, crossed=CROSSED_LAYOUT,
        positive_rows_per_bundle=4, crossed_rows_per_bundle=12,
        errors=tuple(error_type(q, a) for q, a in CROSSED_LAYOUT))


def negative_masks():
    """Pure Python masks; role-only j=i^1, same-role other-subject j=i^2."""
    return dict(ROLE_ONLY4=[[j == (i ^ 1) for j in range(4)] for i in range(4)],
                ALL_AXES4=[[j != i for j in range(4)] for i in range(4)])


def negative_checks(bundle):
    validate_bundle(bundle)
    result = []
    for qi, ai in CROSSED_LAYOUT:
        q = bundle['queries'][qi]; a = bundle['queries'][ai]
        kind = error_type(qi, ai)
        if (q['correct_entity_id'] == a['correct_entity_id']
                or (kind == SAME_SUBJECT_OTHER_ROLE and not (q['subject_id'] == a['subject_id'] and q['role_id'] != a['role_id']))
                or (kind == OTHER_SUBJECT_SAME_ROLE and not (q['subject_id'] != a['subject_id'] and q['role_id'] == a['role_id']))
                or (kind == OTHER_SUBJECT_OTHER_ROLE and not (q['subject_id'] != a['subject_id'] and q['role_id'] != a['role_id']))):
            raise ValueError('exclusive code-table negative mapping differs')
        result.append(dict(question_index=qi, candidate_index=ai, error_type=kind,
            correct_entity_id=q['correct_entity_id'], rejected_entity_id=a['correct_entity_id'],
            status='INVALID_FOR_THIS_QUERY'))
    return result


def render(bundle, qi, ai=None, view=0):
    """Same original context/frame; additional queries replace only its subject."""
    from tinylm.chat.canonical import normalize, validate
    validate_bundle(bundle); _index(qi, 'question'); _index(view, 'view', 3)
    ai = qi if ai is None else _index(ai, 'candidate')
    parent = bundle['parent_bundle']; parent_qi = qi % 2
    source = original.render(parent, parent_qi, view=view)
    prompt = message_text(source['messages'][0])
    if qi >= 2:
        role = bundle['query_order'][parent_qi]
        old_question = original._question(bundle['family'], bundle['subjects'][0], role, bundle['language'], view == 2)
        new_question = original._question(bundle['family'], bundle['subjects'][1], role, bundle['language'], view == 2)
        marker = '질문: ' if bundle['language'] == 'ko' else 'Question: '
        before = prompt.split('\n'); after = list(before)
        indices = [i for i, line in enumerate(before) if line == marker + old_question]
        if len(indices) != 1 or old_question == new_question:
            raise ValueError('exact original query sentence required')
        index = indices[0]; after[index] = marker + new_question
        if [i for i, (a, b) in enumerate(zip(before, after)) if a != b] != [index]:
            raise ValueError('only question subject may change')
        prompt = '\n'.join(after)
    row = validate(normalize(dict(messages=[dict(role='user', content=prompt),
        dict(role='assistant', content=bundle['answers'][ai])], meta=dict(supervised_assistant_turns=[1]))))
    if qi < 2 and ai == qi:
        if (message_text(row['messages'][0]) != message_text(source['messages'][0])
                or message_text(row['messages'][1]) != message_text(source['messages'][1])):
            raise ValueError('original A user body/gold bytes changed')
    return row


def evaluation_case(bundle, qi, view=0):
    row = render(bundle, qi, view=view)
    return dict(id=query_id(bundle, qi, view), lane='subject_role', language=bundle['language'],
        family=bundle['family'], group_id=bundle['parent_group_id'], parent_bundle_id=bundle['parent_bundle_id'],
        bundle_id=bundle['bundle_id'], question_index=qi, view=view,
        origin=bundle['queries'][qi]['origin'], messages=row['messages'][:1], gold=bundle['answers'][qi],
        candidate_answers_supplied=False)


def encode_bundle(bundle, tokenizer, view=0):
    """positive4 + crossed12, with actual full labels/prefix/EOT validation.

Candidate lengths may differ between four names. Each one candidate must keep
identical target IDs across all four questions. No equal-length eligibility
filter is added, and no short answer is promoted to an independent fact.
"""
    validate_bundle(bundle)
    records = {(q, a): original.complete_record(render(bundle, q, a, view), tokenizer)
               for q in range(4) for a in range(4)}
    targets = {a: [v for v in records[a, a].y if v != -100] for a in range(4)}
    if len({tuple(v) for v in targets.values()}) != 4:
        raise ValueError('four PERSON names collapsed to duplicate token targets')
    for (q, a), record in records.items():
        if [v for v in record.y if v != -100] != targets[a]:
            raise ValueError('one candidate has question-dependent target IDs or length')
    return [records[k] for k in POSITIVE_LAYOUT], [records[k] for k in CROSSED_LAYOUT]


def encode_micro(bundles, tokenizer, view=0):
    if not isinstance(bundles, (list, tuple)) or len(bundles) != 2:
        raise ValueError('exactly two source fact bundles per physical positive micro8 required')
    if len({b['bundle_id'] for b in bundles}) != 2:
        raise ValueError('duplicate source bundle cannot fill a micro')
    encoded = [encode_bundle(b, tokenizer, view) for b in bundles]
    return [r for positive, _ in encoded for r in positive], [r for _, crossed in encoded for r in crossed]


def cross_micro_batches(records):
    if len(records) != 24:
        raise ValueError('exact crossed24 split into three physical micro8 batches required')
    return [records[i:i + 8] for i in range(0, 24, 8)]


def classify_answer(bundle, qi, answer):
    validate_bundle(bundle); _index(qi, 'question')
    value = original.exact_answer(answer)
    for ai, candidate in enumerate(bundle['answers']):
        if value == original.exact_answer(candidate): return error_type(qi, ai)
    if not value: return 'EMPTY'
    if any(value == original.NAMES[bundle['language']][s] for s in bundle['subjects']):
        return 'OTHER_CONTEXT_ENTITY'
    return 'OUT_OF_TABLE'


def shortcut_bounds(bundle, view=0):
    """Bounds for specified deterministic feature-restricted policies only.

Role-only predicts the same value for that role across subjects; subject-only
predicts the same value across its two roles. These restrictions are not a
theorem about unrestricted language models, stochastic answers, familiar-name
memorization or future free generation. First-fact means an unconditional copy
of its value, not a query-conditioned search for a matching fact sentence.
"""
    validate_bundle(bundle); _index(view, 'view', 3)
    answers = bundle['answers']
    first = bundle['fact_order'][-1 if view == 1 else 0]
    first_value = original.NAMES[bundle['language']][bundle['facts'][first][2]]
    predictions = dict(role_only=[answers[i % 2] for i in range(4)],
        subject_only=[answers[2 * (i // 2)] for i in range(4)],
        constant=[answers[0]] * 4, first_fact=[first_value] * 4)
    result = {}
    for name, values in predictions.items():
        hits = [values[i] == answers[i] for i in range(4)]
        result[name] = dict(correct=sum(hits), questions=4, all_four_correct=all(hits),
            deterministic_feature_restricted_upper_bound=2 if name in ('role_only', 'subject_only') else 1,
            original_two_correct=all(hits[:2]), additional_two_correct=all(hits[2:]), predictions=values)
    return result
