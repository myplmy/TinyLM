"""Reuse source-specific secondary reviews; retain every other literal guard."""
from pathlib import Path
from collections import Counter
import argparse
import json
import re
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from selection_metadata_store_v1 import SelectionStore
from check_authored_workset_literal_v1 import read_metadata, workset_profiles, read_pair, checked_row
from authored_empty_section_literal_v2 import preservation
from authored_literal_readiness_v1 import deferrals
from structural_delimiter_deferrals_v1 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from scripts import p106b_hold_resolution_policy_v32 as policy

PROSE = 'POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT'
ALLOWED = {'j_structured_lists': {PROSE}, 'c_local_calls': {
    'NATIVE_UNRESOLVED_FIELD_NOT_LOCALLY_PROVEN',
    'GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL'}}
DECISIONS = {'APPROVE_EXISTING_BODY', 'NEEDS_ROOT_CONTEXT', 'BODY_NEEDS_REPAIR'}


def review_rows(text):
    rows = {}
    for line in text.splitlines():
        cells = [value.strip().strip('`').strip() for value in line.split('|')]
        if len(cells) < 7 or not re.fullmatch(r'(?:(?:expanded_train|validation):)?[0-9]+', cells[1]):
            continue
        ident, sha, decision = cells[1:4]
        if ident.isdigit():
            ident = 'expanded_train:' + ident
        if sha in DECISIONS:
            sha, decision = decision, sha
        assert re.fullmatch('[A-F0-9]{64}', sha), ident
        assert decision in DECISIONS and ident not in rows, ident
        assert cells[4] and any(cells[5:-1]), ident
        rows[ident] = dict(body_sha256=sha, decision=decision,
                           actual_views=cells[4], reason=' | '.join(cells[5:-1]))
    assert rows, 'no structured review rows'
    return rows


def run(config_path):
    assert config_path.parent == AUDIT and not config_path.is_symlink()
    guard.activate()
    started = time.monotonic()
    config = json.loads(config_path.read_bytes())
    pins = {}
    current = SelectionStore(AUDIT).read(ROOT / config['selection']['path'], config['selection']['sha256'])
    pins[config['selection']['path']] = config['selection']['sha256']
    selected = {row['id'] for row in current['rows']}
    old = read_metadata(config['prior_context_deferrals'], pins)
    explicit = {row['id']: [reason for reason in row['reasons'] if reason.startswith('ROOT_OBSERVED_')]
                for row in old['deferred_rows']}
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert not (ROOT / name).is_symlink() and guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    workset = {row['id']: (item, row) for item, row in workset_profiles(config['workset'], pins)}
    checked, deferred, secondary = {}, [], []
    for pin in config.get('existing_ready_proofs', []):
        prior = read_metadata(pin, pins)
        assert prior['root_approved'] is prior['cache_admitted'] is False
        assert prior['cumulative_guard_sha256'] == guard.EXPECTED
        assert prior['protected_payload_open_attempts'] == prior['corpus_payload_copies_written'] == 0
        for name, sha in prior['input_pins'].items():
            assert guard.inv.file_sha(ROOT / name) == sha, name
            pins[name] = sha
        for row in prior['checks']:
            assert row['id'] in workset and row['id'] not in selected
            profile = workset[row['id']][1]
            assert row['body']['sha256'] == profile['body']['sha256']
            assert all(row['fresh_preservation_proof']['guards'].values())
            assert all(row['additional_readiness_guards'].values())
            checked[row['id']] = row
    for group in config['groups']:
        scope = read_metadata(group['scope'], pins)
        role = scope['role']
        assert role in ALLOWED
        allowed = ALLOWED[role]
        scope_rows = {row['id']: row for row in scope['cases']}
        reviews = {}
        for pin in group['reviews']:
            path = ROOT / pin['path']
            assert path.suffix == '.md' and not path.is_symlink()
            assert guard.inv.file_sha(path) == pin['sha256']
            pins[pin['path']] = pin['sha256']
            for ident, row in review_rows(path.read_text(encoding='utf-8')).items():
                assert ident not in reviews and ident in scope_rows, ident
                assert row['body_sha256'] == scope_rows[ident]['body']['sha256'], ident
                reviews[ident] = dict(row, review=pin)
        # All assignments are metadata checked before any source/body is opened.
        for ident, review in reviews.items():
            assert ident in workset and workset[ident][1]['body'] == scope_rows[ident]['body']
            guard.require_payload_context(dict(source_id=ident, original=scope_rows[ident]['original'], candidate=scope_rows[ident]['body']))
            secondary.append(dict(id=ident, decision=review['decision'], review=review['review']))
        for ident, review in reviews.items():
            if review['decision'] != 'APPROVE_EXISTING_BODY' or ident in selected:
                continue
            profile = workset[ident][1]
            values = read_pair(profile, pins)
            proof = preservation(*values)
            reasons = deferrals(values[1]) + policy.literal_holes(values[1]) + delimiter_deferrals(values[1])
            reasons += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(values[1])]
            reasons += explicit.get(ident, [])
            remaining = sorted(set(reasons) - allowed)
            remaining += [name for name, passed in proof['guards'].items() if not passed]
            if remaining:
                deferred.append(dict(id=ident, body=profile['body'], reasons=sorted(set(remaining))))
                continue
            for pin in profile['all_reviews']:
                assert guard.inv.file_sha(ROOT / pin['path']) == pin['sha256']
            proof = dict(proof, exact_secondary_context=dict(role=role, review=review['review'],
                body_sha256=profile['body']['sha256'], resolved_flags=sorted(set(reasons) & allowed),
                actual_views=review['actual_views'], source_specific_reason=review['reason'],
                universal_scanner_relaxation=False))
            row = checked_row(profile, values, proof, dict(exact_body_secondary_context_review=True,
                all_other_literal_numeric_code_quote_and_metadata_guards_preserved=True))
            row['all_saved_reviews'] = row['all_saved_reviews'] + [review['review']]
            if ident in checked:
                assert checked[ident]['body']['sha256'] == row['body']['sha256']
            checked[ident] = row
    for path in [Path(__file__), config_path, guard.CONTRACT] + [AUDIT / name for name in [
            'check_authored_workset_literal_v1.py', 'authored_empty_section_literal_v2.py',
            'authored_empty_section_literal_v1.py', 'authored_literal_metadata_readiness_v2.py',
            'authored_literal_readiness_v1.py', 'structural_delimiter_deferrals_v1.py',
            'close_remaining_heading_context_v1.py', 'active_guard_v6_preflight_v1.py',
            'selection_metadata_store_v1.py']]:
        pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
    checks = list(checked.values())
    output = AUDIT / config['output']
    assert not output.exists()
    report = dict(status='EXACT_EXISTING_BODY_SECONDARY_CONTEXT_AND_ALL_LITERAL_GUARDS_PENDING_ROOT',
        verified=len(checks), verified_positions=sum(row['occurrences'] for row in checks),
        checks=checks, deferred_rows=deferred, deferred=len(deferred), secondary_decisions=secondary,
        secondary_counts=dict(Counter(row['decision'] for row in secondary)), input_pins=pins,
        cumulative_guard_sha256=guard.EXPECTED, protected_payload_open_attempts=0,
        corpus_payload_copies_written=0, additional_human_full_read_credit=0,
        root_approved=False, cache_admitted=False, elapsed_seconds=time.monotonic()-started,
        goal_complete=False, training_authorized=False)
    guard.inv.write_json(output, report)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {'checks', 'deferred_rows', 'secondary_decisions', 'input_pins'}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    run(Path(parser.parse_args().config).resolve())
