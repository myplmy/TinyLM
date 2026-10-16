"""Row-occurrence identity and lossless replay for preserved retention answers.

No corpus/checkpoint is read and no model/GPU operation is started here.
The caller supplies frozen original rows and either an emitter or saved events.
Semantic roots remain grouping labels, never per-event unique identifiers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_eval as old
from tinylm.chat.serialize import serialize

VERSION = 'P106B_NIGHT_RETENTION_ROW_IDENTITY_V2'
IDENTITY_FIELDS = ('case_source_sha256', 'frozen_row_index', 'lane', 'case_id')
HISTORIES = ('ACTUAL_MODEL', 'GOLD_REFERENCE')
STOP_REASONS = frozenset(('EOS', 'EOT', 'STOP_SEQUENCE', 'TURN_END'))


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def _lane(lane):
    if not isinstance(lane, str) or not lane.strip():
        raise ValueError('explicit nonempty frozen retention lane required')
    return lane


def _identity(row, lane, row_index):
    _lane(lane)
    if type(row_index) is not int or row_index < 0:
        raise ValueError('nonnegative frozen row index required')
    if not isinstance(row, dict) or not isinstance(row.get('meta'), dict):
        raise ValueError('complete original canonical row and metadata required')
    messages, meta = row.get('messages'), row['meta']
    if (not isinstance(messages, list) or not messages or len(messages) % 2
            or [m.get('role') for m in messages] != ['user', 'assistant'] * (len(messages) // 2)):
        raise ValueError('nonempty complete alternating original turns required')
    if (meta.get('language') not in ('ko', 'en')
            or not isinstance(meta.get('semantic_root_id'), str) or not meta['semantic_root_id']
            or not isinstance(meta.get('kind'), str) or not meta['kind']):
        raise ValueError('declared original language/root/kind required')
    return dict(case_source_sha256=_sha(row), frozen_row_index=row_index,
                lane=lane, case_id=_sha([lane, row_index, row]))


def _attach(event, identity):
    if any(field in event for field in IDENTITY_FIELDS):
        raise ValueError('legacy event already contains row-identity fields')
    return dict(copy.deepcopy(event), **identity)


def _proof(event):
    if not isinstance(event.get('answer'), str) or not isinstance(event.get('gold'), str):
        raise ValueError('actual answer and source gold strings required, including empty answers')
    generation = event.get('generation')
    if (not isinstance(generation, dict)
            or not isinstance(generation.get('finish_reason'), str)
            or not generation['finish_reason']):
        raise ValueError('actual generation finish reason required')
    if not isinstance(event.get('messages'), list) or not event['messages']:
        raise ValueError('actual complete retained prompt required')
    if 'actual_prompt_sha256' in generation:
        prompt = serialize(dict(messages=event['messages']), 'chatml', add_generation_prompt=True)
        if generation['actual_prompt_sha256'] != _sha(prompt):
            raise ValueError('retention generation prompt SHA differs from raw messages')
    if ('raw_answer_sha256' in generation
            and generation['raw_answer_sha256'] != _sha(event['answer'])):
        raise ValueError('retention generation answer SHA differs from raw answer')
    literal = int(event['answer'].strip() == event['gold'].strip())
    if type(event.get('literal')) is not int or event['literal'] != literal:
        raise ValueError('retention raw literal recount differs')
    return literal


def collect(row, emit, *, lane, row_index):
    """Run only the supplied emitter through the unchanged dialogue producer."""
    identity = _identity(row, lane, row_index)
    result = [_attach(event, identity) for event in old.dialogue(row, emit)]
    summarize(result)
    return result


def _event_index(events):
    indexed, cases, occurrences = {}, {}, {}
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('retention event dict required')
        _proof(event)
        for field in ('case_source_sha256', 'case_id'):
            value = event.get(field)
            if (not isinstance(value, str) or len(value) != 64
                    or any(ch not in '0123456789ABCDEF' for ch in value)):
                raise ValueError('canonical uppercase row identity SHA required: ' + field)
        _lane(event.get('lane'))
        if type(event.get('frozen_row_index')) is not int or event['frozen_row_index'] < 0:
            raise ValueError('frozen row index required on every event')
        if (event.get('language') not in ('ko', 'en') or type(event.get('turn')) is not int
                or event['turn'] < 1 or event.get('history') not in HISTORIES
                or (event['history'] == 'GOLD_REFERENCE' and event['turn'] == 1)):
            raise ValueError('declared retention language/turn/history required')
        key = (event['case_id'], event['language'], event['turn'], event['history'])
        if key in indexed:
            raise ValueError('duplicate retention case/language/turn/history event')
        indexed[key] = event
        signature = tuple(event.get(field) for field in
            (*IDENTITY_FIELDS, 'language', 'root', 'neutral_root', 'kind', 'condition', 'family',
             'first_response_intent', 'query_sufficient', 'view', 'question_style'))
        case = cases.setdefault(event['case_id'], dict(signature=signature, positions=set()))
        if case['signature'] != signature:
            raise ValueError('one frozen case identity has inconsistent source or metadata')
        case['positions'].add((event['turn'], event['history']))
        occurrence = (event['lane'], event['frozen_row_index'])
        if occurrence in occurrences and occurrences[occurrence] != event['case_id']:
            raise ValueError('one lane/row occurrence has multiple case IDs')
        occurrences[occurrence] = event['case_id']
    if not indexed:
        raise ValueError('nonempty retention events required')
    for case in cases.values():
        last = max(turn for turn, history in case['positions'])
        expected = {(turn, 'ACTUAL_MODEL') for turn in range(1, last + 1)}
        expected.update((turn, 'GOLD_REFERENCE') for turn in range(2, last + 1))
        if case['positions'] != expected:
            raise ValueError('complete actual-history and separate gold-history turns required')
    return indexed


def summarize(events):
    """Old-style metric lane mapping with a row-occurrence event key.

    n/literal/empty retain their old meanings. blank additionally counts an
    answer containing only whitespace; zero scores/empty outputs are not dropped.
    Complete frozen-row coverage/order is the stronger verify() contract.
    """
    indexed = _event_index(events)
    totals = defaultdict(Counter)
    for event in indexed.values():
        history, language, turn = event['history'], event['language'], event['turn']
        condition = event.get('condition')
        slices = [history + '/all', history + '/' + language,
                  history + '/turn' + str(turn), history + '/' + language + '/turn' + str(turn)]
        if condition is not None:
            cell = '/condition' + str(condition)
            slices.extend((history + cell, history + '/' + language + cell,
                           history + '/turn' + str(turn) + cell))
        reason = event['generation']['finish_reason']
        counts = dict(n=1, literal=event['literal'], empty=int(not event['answer']),
                      blank=int(not event['answer'].strip()), stop=int(reason in STOP_REASONS),
                      max_new=int(reason.startswith('MAX_NEW')),
                      context_exhausted=int(reason == 'CONTEXT_BUDGET_EXHAUSTED'))
        for key in slices:
            totals[key].update(counts)
    return {key: dict(value) for key, value in sorted(totals.items())}


def _reconstruct(events, originals, lane, augmented):
    """Rebuild exact old producer order without a new model or generated answer."""
    _lane(lane)
    events, originals = list(events), list(originals)
    if not originals:
        raise ValueError('nonempty frozen original rows required')
    identities = [_identity(row, lane, index) for index, row in enumerate(originals)]
    count = sum(len(row['messages']) - 1 for row in originals)
    if len(events) != count:
        raise ValueError('missing or extra retention events for complete frozen original rows')
    cursor = 0
    rebuilt = []
    def replay(prefix):
        nonlocal cursor
        if cursor >= len(events):
            raise ValueError('missing retention actual/gold-history event')
        observed = events[cursor]
        cursor += 1
        if not isinstance(observed, dict) or prefix != observed.get('messages'):
            raise ValueError('retention original/actual/gold-history prefix or stored order changed')
        _proof(observed)
        return observed['answer'], copy.deepcopy(observed['generation'])
    for row, identity in zip(originals, identities):
        for event in old.dialogue(row, replay):
            expected = _attach(event, identity)
            observed = events[len(rebuilt)]
            if augmented:
                if observed != expected:
                    raise ValueError('retention source/gold/identity/metadata/order differs from frozen reconstruction')
            elif observed != event:
                raise ValueError('legacy retention source/gold/metadata/order differs from frozen reconstruction')
            rebuilt.append(expected)
    if cursor != len(events) or len(rebuilt) != len(events):
        raise ValueError('complete retention event set/order required')
    return rebuilt


def augment_legacy(events, originals, lane):
    """Verify preserved V1 raw and return augmented copies; never edit the input."""
    result = _reconstruct(events, originals, lane, augmented=False)
    summarize(result)
    return result


def verify(events, originals, lane):
    """Verify full V2 identity, source, gold, both histories and global order."""
    rebuilt = _reconstruct(events, originals, lane, augmented=True)
    return summarize(rebuilt)
