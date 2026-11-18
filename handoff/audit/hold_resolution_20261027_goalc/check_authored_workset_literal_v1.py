"""Run the existing literal-preservation gates on current workset references."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from authored_empty_section_literal_v2 import preservation
from authored_literal_readiness_v1 import deferrals
from structural_delimiter_deferrals_v1 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from scripts import p106b_hold_resolution_policy_v32 as policy
from selection_metadata_store_v1 import SelectionStore


def read_metadata(pin, pins):
    path = ROOT / pin['path']
    assert not path.is_symlink() and path.suffix == '.json'
    raw = path.read_bytes()
    assert 0 < len(raw) < 20_000_000
    assert hashlib.sha256(raw).hexdigest().upper() == pin['sha256']
    pins[pin['path']] = pin['sha256']
    return json.loads(raw)


def workset_profiles(summary_pin, pins):
    summary = read_metadata(summary_pin, pins)
    assert summary['source_body_opens'] == summary['source_body_copies'] == 0
    for name, sha in summary['input_pins'].items():
        path = ROOT / name
        assert path.suffix != '.txt' and not path.is_symlink()
        assert guard.inv.file_sha(path) == sha, name
        pins[name] = sha
    index = read_metadata(summary['index'], pins)
    assert len(index['rows']) == summary['unique_sources']
    assert sum(row['occurrences'] for row in index['rows']) == summary['positions']
    cache = {}
    for row in index['rows']:
        locator = row.get('profile_record')
        if not locator:
            continue
        name = locator['path']
        if name not in cache:
            path = ROOT / name
            assert path.suffix == '.jsonl' and not path.is_symlink()
            assert guard.inv.file_sha(path) == locator['sha256']
            pins[name] = locator['sha256']
            cache[name] = list(guard.inv.cache.rows(path.parent, dict(shards=[dict(path=path.name)])))
        profile = cache[name][locator['offset']]
        assert profile['id'] == row['id']
        assert profile['original']['sha256'] == row['original_sha256']
        assert profile['body']['sha256'] == row['body_sha256']
        yield row, profile


def read_pair(row, pins):
    guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['body']))
    values = []
    for name in ['original', 'body']:
        pin = row[name]
        path = ROOT / pin['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(guard.inv.BASE)
        raw = path.read_bytes()
        value = raw.decode('utf-8')
        assert guard.inv.sha(value) == pin['sha256']
        values.append(value)
    return values


def checked_row(row, values, proof, context_checks=None):
    return dict(id=row['id'], original=row['original'], original_text_sha256=row['original']['sha256'],
                body=dict(row['body'], bytes=len(values[1].encode('utf-8'))),
                decision='KEEP' if values[0] == values[1] else 'EDIT', occurrences=row['occurrences'],
                primary_review=row['primary_review'], primary_source_cohort=row['primary_cohort'],
                reason=row['reason'], all_saved_reviews=row['all_reviews'],
                full_source_read_by_primary_author_claimed=True, additional_human_full_text_read_claimed=False,
                fresh_preservation_proof=proof, additional_readiness_guards=dict(
                    no_native_or_formal_gap=True, no_unfinished_prose_flag=True, no_unfilled_content_heading=True,
                    no_explicit_ROOT_context_deferral=True, existing_saved_bodies_agree=True,
                    current_workset_identity_matches=True, **(context_checks or {})))


def run(config_path):
    guard.activate()
    started = time.monotonic()
    config = json.loads(config_path.read_bytes())
    pins = {}
    selection = SelectionStore(AUDIT).read(ROOT / config['selection']['path'], config['selection']['sha256'])
    selected = {row['id'] for row in selection['rows']}
    pins[config['selection']['path']] = config['selection']['sha256']
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert not (ROOT / name).is_symlink() and guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    explicit = read_metadata(config['prior_context_deferrals'], pins)
    root_deferrals = {row['id']: [reason for reason in row['reasons'] if reason.startswith('ROOT_OBSERVED_')]
                      for row in explicit['deferred_rows']}
    checks, deferred = [], []
    failures, bases = Counter(), Counter()
    allowed = {'EXISTING_LITERAL_EQUAL', 'SOURCE_WORD_DELETIONS_ONLY', 'WORD_ATOMS_IDENTICAL_ONLY_OTHER_CHARACTERS_DIFFER',
               'ADDED_OR_REPLACED_SOURCE_WORDS', 'DELETIONS_WITH_ONLY_PARTICLE_CHANGES'}
    for item, row in workset_profiles(config['workset'], pins):
        if row['id'] in selected or not item['group'].endswith(':NO_SCANNER_GAPS'):
            continue
        if row['delta']['kind'] not in allowed:
            continue
        values = read_pair(row, pins)
        proof = preservation(*values)
        reasons = [name for name, passed in proof['guards'].items() if not passed]
        reasons += deferrals(values[1]) + policy.literal_holes(values[1]) + delimiter_deferrals(values[1])
        reasons += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(values[1])]
        reasons += root_deferrals.get(row['id'], [])
        if reasons:
            deferred.append(dict(id=row['id'], original_text_sha256=row['original']['sha256'],
                                 body=row['body'], occurrences=row['occurrences'], reasons=sorted(set(reasons))))
            failures.update(set(reasons))
            continue
        assert proof['eligible_narrow_literal_delta'] and all(proof['guards'].values())
        for review in row['all_reviews']:
            assert guard.inv.file_sha(ROOT / review['path']) == review['sha256']
        checks.append(checked_row(row, values, proof))
        bases[proof['comparison_basis']] += 1
    for path in [Path(__file__), config_path, guard.CONTRACT, AUDIT / 'authored_empty_section_literal_v2.py',
                 AUDIT / 'authored_empty_section_literal_v1.py', AUDIT / 'authored_literal_metadata_readiness_v2.py',
                 AUDIT / 'authored_literal_readiness_v1.py', AUDIT / 'structural_delimiter_deferrals_v1.py',
                 AUDIT / 'close_remaining_heading_context_v1.py']:
        pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
    result = dict(status='CURRENT_WORKSET_EXISTING_LITERAL_GATES_VERIFIED_PENDING_ROOT_CONTEXT',
                  candidates=len(checks) + len(deferred), verified=len(checks),
                  verified_positions=sum(row['occurrences'] for row in checks), deferred=len(deferred),
                  deferral_reason_counts=dict(failures), proof_basis_counts=dict(bases), checks=checks, deferred_rows=deferred,
                  input_pins=pins, cumulative_guard_sha256=guard.EXPECTED, protected_payload_open_attempts=0,
                  corpus_payload_copies_written=0, additional_human_full_read_credit=0,
                  elapsed_seconds=time.monotonic() - started, root_approved=False, cache_admitted=False,
                  goal_complete=False, training_authorized=False)
    output = AUDIT / config['output']
    assert not output.exists()
    assert len((json.dumps(result, ensure_ascii=False, indent=2) + chr(10)).encode()) < 20_000_000
    guard.inv.write_json(output, result)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in result.items() if key not in {'input_pins', 'checks', 'deferred_rows'}}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    path = Path(args.config).resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    run(path)
