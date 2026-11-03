"""Add exact reviewed HOLD accounting through the frozen guarded cache engines."""
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import guarded_reviewed_cache_v2 as previous
from reviewed_hold_partition_v1 import SCHEMA as HOLD_SCHEMA, classify_hold, partition_occurrences

ROOT, inv = previous.ROOT, previous.inv
first = previous.previous
reviewed = first.reviewed
partial, final = reviewed.partial, reviewed.final
BASE_RUNTIME = previous.runtime
BASE_INPUTS = previous.GuardedInputs
BASE_ENGINE = previous.GuardedResolutionEngine
BASE_FIRST_VERIFY = first.verify
HOLD_AUTHORITY = AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD37_V1.json'
WITHDRAWAL = AUDIT / 'ROOT_PRIOR_BODY_WITHDRAWAL_1255247_V1.json'
PHONETIC = AUDIT / 'EXACT_PHONETIC_STRESS_CODE_EXCEPTION_1291499_V1.json'


def hold_cases():
    document = inv.cache.read(HOLD_AUTHORITY)
    inv.require(document['unique_sources'] == len(document['rows']) == 37,
        'all individually reviewed non-admissions required')
    cases = {}
    for row in document['rows']:
        inv.require(row['decision'] == 'HOLD' and row['reviewed'] is True
            and row['root_approved'] is True, 'unapproved reviewed HOLD')
        key = row['original']['sha256']
        inv.require(key not in cases, 'reviewed source SHA repeated')
        cases[key] = dict(row, authority_pin=dict(path=str(HOLD_AUTHORITY.relative_to(ROOT)),
            sha256=inv.file_sha(HOLD_AUTHORITY), source_id=row['id']))
    row = inv.cache.read(WITHDRAWAL)
    inv.require(row['id'] == 'expanded_train:1255247' and row['decision'] == 'HOLD'
        and row['reviewed'] is True and row['root_approved'] is True
        and row['requires_prior_selected_body_withdrawal'] is True,
        'the exact erroneous prior admission must be withdrawn')
    key = row['original_text_sha256']
    inv.require(key not in cases, 'withdrawal overlaps a new reviewed source')
    cases[key] = dict(row, authority_pin=dict(path=str(WITHDRAWAL.relative_to(ROOT)),
        sha256=inv.file_sha(WITHDRAWAL), source_id=row['id']))
    return cases


def phonetic_case():
    row = inv.cache.read(PHONETIC)
    inv.require(row['id'] == 'expanded_train:1291499' and row['root_approved'] is True
        and row['applies_only_to_original_and_body_sha256'] is True
        and row['unchanged_real_fenced_code_blocks'] == 0
        and row['unchanged_other_inline_matches'] == 73, 'exact phonetic stress case required')
    for key in ['original', 'body', 'review', 'full_held_source_line']:
        pin = row[key]
        inv.require(inv.file_sha(ROOT / pin['path']) == pin['sha256'], 'phonetic evidence changed')
    return row


def load_roster(path, index):
    document = inv.cache.read(path)
    inv.require(document.get('schema') == partial.SCHEMA
        and document.get('status') == 'ROOT_REVIEWED_PARTIAL_RESIDUAL_CACHE_ROSTER'
        and document.get('hold_partition_schema') == HOLD_SCHEMA,
        'explicit reviewed HOLD partition roster required')
    inv.require(document.get('goal_complete') is False and document.get('training_authorized') is False,
        'partial cache cannot assert completion or training authorization')
    inv.require(document['parent_built_sha256'] == inv.file_sha(index.old / 'built.json'),
        'reviewed partial parent differs')
    directory = path.parent / document['records_directory']
    inv.require(directory.resolve().is_relative_to(path.parent.resolve()), 'roster records escape version')
    inv.cache.verify(directory, document['manifest'])
    cases, result, evidence_pins = hold_cases(), {}, {}
    for row in inv.cache.rows(directory, document['manifest']):
        key, decision = row['original_text_sha256'], row['decision']
        inv.require(key not in result and decision in {'KEEP', 'EDIT', 'EXCLUDE', 'HOLD'},
            'duplicate or unknown outcome')
        inv.require(row.get('reason') and isinstance(row.get('evidence'), dict), 'proposal lacks reason/evidence')
        evidence = row['evidence']
        evidence_path = ROOT / evidence['path']
        allowed = [index.base / 'agents', AUDIT]
        inv.require(any(evidence_path.resolve().is_relative_to(p.resolve()) for p in allowed),
            'proposal evidence escapes approved review paths')
        if evidence['path'] not in evidence_pins:
            evidence_pins[evidence['path']] = inv.file_sha(evidence_path)
        inv.require(evidence_pins[evidence['path']] == evidence['sha256'], 'proposal evidence changed')
        if decision == 'HOLD':
            classify_hold(row, cases)
        else:
            inv.require(row.get('root_approved') is True, 'body/exclusion disposition is not approved')
            if decision == 'KEEP':
                inv.require(row['clean_text_sha256'] == key, 'KEEP changes original text')
            elif decision == 'EDIT':
                inv.require(isinstance(row.get('text'), str) and row['text'].strip()
                    and inv.sha(row['text']) == row['clean_text_sha256']
                    and not inv.corpus.MEMOS.search(row['text']), 'edited body differs or contains memo')
        result[key] = row
    inv.cache.verify(index.old / 'hold', index.report['manifests']['hold'])
    keys = set()

    def positions():
        for source in inv.cache.rows(index.old / 'hold', index.report['manifests']['hold']):
            key = source['original_text_sha256']
            inv.require(key in result, 'roster omits a source position')
            keys.add(key)
            yield source

    counts = partition_occurrences(positions(), result, cases)
    inv.require(keys == set(result) and {k:counts[k] for k in ['documents', 'input_ids']} == document['counts']
        and counts['documents'] == index.counts['HOLD'], 'whole residual source coverage differs')
    for name in ['remaining_hold', 'reviewed_hold', 'unprocessed']:
        inv.require(document.get(name) == counts[name], 'reviewed HOLD partition count differs: ' + name)
    return document, result


def verify_partial(base, roster, output_name):
    with partial.revision():
        result = partial.engine.verify(base, output_name)
    index = final.LatestIndex(base)
    document, proposals = load_roster(roster, index)
    report = inv.cache.read(base / output_name / 'built.json')
    inv.require(report['counts'].get('HOLD', 0) == document['remaining_hold'], 'actual HOLD count differs')
    checked, outcomes, observed = Counter(), Counter(), Counter()
    roster_sha, cases = inv.file_sha(roster), hold_cases()
    for row in inv.cache.rows(base / output_name / 'ledger', report['manifests']['ledger']):
        if index.state(row) != 3: continue
        expected = proposals[row['original_text_sha256']]
        if expected['decision'] == 'HOLD':
            inv.require(row['decision'] == 'HOLD', 'HOLD was promoted or discarded')
            kind = classify_hold(expected, cases)
            observed['reviewed_hold' if kind == 'REVIEWED_NOT_ADMITTED' else 'unprocessed'] += 1
        elif expected['decision'] == 'EXCLUDE':
            inv.require(row['decision'] == 'EXCLUDE', 'excluded source was admitted')
        elif row['decision'] in {'KEEP', 'EDIT'}:
            inv.require(row['clean_text_sha256'] == expected['clean_text_sha256'], 'admitted text differs')
        else:
            inv.require(row['decision'] == 'EXCLUDE' and (row.get('duplicate_of') or row.get('validation_overlap')),
                'approved body was lost without exact duplicate/split evidence')
        inv.require(row.get('resolution_roster_sha256') == roster_sha, 'ledger roster pin differs')
        checked.update(documents=1, input_ids=row['input_ids'])
        outcomes[row['decision']] += 1
    inv.require(dict(checked) == document['counts'], 'independent residual coverage differs')
    for name in ['reviewed_hold', 'unprocessed']:
        inv.require(observed[name] == document[name], 'consumer HOLD partition differs: ' + name)
    proof = dict(schema=partial.SCHEMA, hold_partition_schema=HOLD_SCHEMA,
        status='CPU_PARTIAL_RECOVERY_CACHE_VERIFIED_GOAL_INCOMPLETE', roster_sha256=roster_sha,
        checked=dict(checked), outcomes=dict(outcomes), remaining_hold=document['remaining_hold'],
        reviewed_hold=document['reviewed_hold'], unprocessed=document['unprocessed'],
        all_previous_adopted_text_preserved=True, goal_complete=False, training_authorized=False,
        core_recovery_verified_sha256=inv.file_sha(base / output_name / 'recovery_verified.json'))
    inv.write_json(base / output_name / 'partial_resolution_verified.json', proof)
    return dict(result, partial_resolution=proof)


class GuardedInputs(BASE_INPUTS):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hold_cases()
        self.phonetic_case = phonetic_case()
        paths = [Path(__file__), AUDIT / 'reviewed_hold_partition_v1.py', HOLD_AUTHORITY,
            WITHDRAWAL, PHONETIC, AUDIT / 'REVIEWED_HOLD_PARTITION_SCOPE_V1.md',
            AUDIT / 'REVIEWED_HOLD_PARTITION_TEST_RESULT_V1.json']
        paths += [ROOT / self.phonetic_case[key]['path'] for key in
            ['original', 'body', 'review', 'full_held_source_line']]
        paths = [str(p.relative_to(ROOT)) for p in paths]
        self.pins = list(dict.fromkeys(self.pins + paths))
        self.pin_values.update({name:inv.file_sha(ROOT / name) for name in paths})


class GuardedResolutionEngine(BASE_ENGINE):
    def code_guard(self, original, cleaned, manual=None):
        if super().code_guard(original, cleaned, manual): return True
        row, state = self.current
        if state != 3 or row.get('restricted_parent_body_not_decoded') is True: return False
        case = self.guard.phonetic_case
        return ((manual or {}).get('phonetic_stress_pair_id') == case['id']
            and inv.sha(original) == case['original']['sha256']
            and inv.sha(cleaned) == case['body']['sha256']
            and reviewed.final.engine.policy.unicode_examples_preserved(original, cleaned))


@contextmanager
def runtime(selection):
    with patch.object(previous, 'GuardedInputs', GuardedInputs), \
        patch.object(previous, 'GuardedResolutionEngine', GuardedResolutionEngine), \
        patch.object(partial, 'load_roster', load_roster), \
        patch.object(partial, 'verify', verify_partial), patch.object(final, 'load_roster', load_roster):
        with BASE_RUNTIME(selection) as inputs:
            yield inputs


def build(base, adoptions, roster, output_name, proposal_name, selection):
    with runtime(selection):
        return reviewed.build(base, adoptions, roster, output_name, proposal_name)


def verify(base, roster, output_name, selection):
    with patch.object(first, 'runtime', runtime):
        return BASE_FIRST_VERIFY(base, roster, output_name, selection)


def main():
    with patch.object(first, 'build', build), patch.object(first, 'verify', verify):
        return first.main()


if __name__ == '__main__': main()
