"""Bind new Luna outputs to frozen prior sources, then replay all literal gates.

The previous body belongs to the workset. The new body belongs to its explicit
repair assignment. These are separate identities, not a workset match claim.
"""
from pathlib import Path
import argparse
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from check_authored_workset_literal_v1 import read_metadata, workset_profiles, read_pair
from authored_empty_section_literal_v2 import preservation
from authored_literal_readiness_v1 import deferrals
from structural_delimiter_deferrals_v2 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from selection_metadata_store_v1 import SelectionStore
from scripts import p106b_hold_resolution_policy_v32 as policy

PROSE = 'POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT'
APPROVALS = {'APPROVE_EXISTING_BODY', 'APPROVE_REPAIRED_BODY', 'BODY_REPAIRED'}


def author_row(text, case):
    matches = []
    for line in text.splitlines():
        cells = line.split('|', 5)
        if len(cells) != 6 or cells[1].strip().strip('`') != case['id']:
            continue
        value = cells[2].strip().strip('`')
        expected = case['body']['path'] if case['review_schema'] == 'OUTPUT_COMPLETE' else case['body']['sha256']
        assert value == expected, 'author output identity differs'
        decision, views = cells[3].strip().strip('`'), cells[4].strip().strip('`')
        reason = cells[5].rsplit('|', 1)[0].strip()
        assert views and reason and 'PENDING' not in (decision, views, reason)
        matches.append(dict(decision=decision, actual_views=views, reason=reason))
    assert len(matches) == 1, 'one exact author output row required'
    if case['review_schema'] == 'OUTPUT_COMPLETE':
        assert 'Status: COMPLETE' in text
    assert 'EOF' in matches[0]['actual_views'], 'actual final-body EOF evidence required'
    return matches[0]


def run(path):
    guard.activate()
    started, pins = time.monotonic(), {}
    config = json.loads(path.read_bytes())
    profiles = {row['id']: row for _, row in workset_profiles(config['workset'], pins)}
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert not (ROOT / name).is_symlink() and guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    selected = {row['id'] for row in SelectionStore(AUDIT).read(
        ROOT / config['selection']['path'], config['selection']['sha256'])['rows']}
    pins[config['selection']['path']] = config['selection']['sha256']
    assert len({case['id'] for case in config['cases']}) == len(config['cases'])
    prepared = []
    # Validate every role/path/author mapping before any source/body is opened.
    for case in config['cases']:
        prior = profiles[case['id']]
        assert case['id'] not in selected
        scope = read_metadata(case['assignment'], pins)
        assert scope['role'] == case['role']
        assigned = next(row for row in scope['cases'] if row['id'] == case['id'])
        assert assigned['original'] == prior['original']
        if 'new_output' in assigned:
            assert assigned['new_output'] == case['body']['path']
        else:
            assert case['review_schema'] == 'HASH_FINAL' and case['older_saved_inventory']
            inventory = read_metadata(case['older_saved_inventory'], pins)
            assert any(row['id'] == case['id'] and row['new_body'] == case['body'] for row in inventory['rows'])
        body_path = ROOT / case['body']['path']
        assert not body_path.is_symlink() and body_path.resolve().is_relative_to(guard.inv.BASE / 'agents')
        guard.require_payload_context(dict(source_id=case['id'], original=prior['original'], candidate=case['body']))
        review_path = ROOT / case['review']['path']
        assert not review_path.is_symlink() and guard.inv.file_sha(review_path) == case['review']['sha256']
        pins[case['review']['path']] = case['review']['sha256']
        review = author_row(review_path.read_text(encoding='utf-8'), case)
        prepared.append((case, prior, review))
    checks, deferred = [], []
    for case, prior, review in prepared:
        source, body = read_pair(dict(prior, body=case['body']), pins)
        proof = preservation(source, body)
        flags = set(deferrals(body) + policy.literal_holes(body) + delimiter_deferrals(body))
        # Actual new-output reviews may resolve nominal-list prose context;
        # code/native/formal holes and all other guards remain in force.
        allowed = {PROSE} if case['role'] in {'l_partial_deletions', 'g_partial_context', 'h_small_word_changes'} else set()
        failed = [name for name, passed in proof['guards'].items() if not passed]
        failed += sorted(flags - allowed)
        failed += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(body)]
        empty = proof.get('candidate_empty_eof_appendix_headings', []) + proof.get('candidate_independently_empty_section_lines', [])
        if empty:
            failed.append('INDEPENDENTLY_PROVEN_EMPTY_SECTION_REMAINS_IN_FINAL_BODY')
        if review['decision'] not in APPROVALS:
            failed.append('AUTHOR_REQUIRES_REPAIR_OR_ROOT_CONTEXT')
        if body.rstrip().endswith((':', '：', '→', '/')):
            failed.append('FINAL_TAIL_REQUIRES_CONTEXT')
        if failed:
            deferred.append(dict(id=case['id'], body=case['body'], reasons=sorted(set(failed)), author_review=case['review']))
            continue
        for pin in prior['all_reviews']:
            assert guard.inv.file_sha(ROOT / pin['path']) == pin['sha256']
        proof = dict(proof, exact_manual_output_review=dict(role=case['role'], review=case['review'],
            resolved_flags=sorted(flags & allowed), actual_views=review['actual_views'],
            source_specific_reason=review['reason'], universal_scanner_relaxation=False))
        checks.append(dict(id=case['id'], original=prior['original'], original_text_sha256=prior['original']['sha256'],
            body=dict(case['body'], bytes=len(body.encode('utf-8'))), decision='KEEP' if source == body else 'EDIT',
            occurrences=prior['occurrences'], primary_review=prior['primary_review'], primary_source_cohort=prior['primary_cohort'],
            reason=prior['reason'] + ' / Manual final repair: ' + review['reason'],
            all_saved_reviews=prior['all_reviews'] + [case['review']],
            full_source_read_by_primary_author_claimed=True, additional_human_full_text_read_claimed=False,
            manual_final_body_full_read_by_author_claimed=True, fresh_preservation_proof=proof,
            additional_readiness_guards=dict(prior_source_identity_matches_frozen_workset=True,
                new_body_identity_matches_explicit_author_assignment=True, exact_new_body_author_review=True,
                all_literal_numeric_code_unicode_style_and_order_guards=True, no_remaining_native_or_formal_gap=True,
                no_unfilled_content_heading=True, no_independently_proven_empty_final_body_section=True)))
    for value in [path, Path(__file__), guard.CONTRACT] + [AUDIT / name for name in [
        'check_authored_workset_literal_v1.py', 'authored_empty_section_literal_v2.py',
        'authored_empty_section_literal_v1.py', 'authored_literal_metadata_readiness_v2.py',
        'authored_literal_readiness_v1.py', 'structural_delimiter_deferrals_v2.py',
        'structural_delimiter_deferrals_v1.py', 'close_remaining_heading_context_v1.py']]:
        pins[str(value.relative_to(ROOT))] = guard.inv.file_sha(value)
    result = dict(status='EXACT_MANUAL_OUTPUT_ALL_LITERAL_GUARDS_PENDING_ROOT',
        verified=len(checks), verified_positions=sum(row['occurrences'] for row in checks), checks=checks,
        deferred_rows=deferred, deferred=len(deferred), input_pins=pins, cumulative_guard_sha256=guard.EXPECTED,
        protected_payload_open_attempts=0, corpus_payload_copies_written=0, additional_human_full_read_credit=0,
        root_approved=False, cache_admitted=False, goal_complete=False, training_authorized=False,
        elapsed_seconds=time.monotonic() - started)
    out = AUDIT / config['output']
    assert not out.exists()
    guard.inv.write_json(out, result)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in result.items() if key not in {'checks', 'deferred_rows', 'input_pins'}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    path = args.config.resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    run(path)
