"""Prove existing named-list roles without relaxing other source/body guards."""
from pathlib import Path
from collections import Counter
import argparse
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from selection_metadata_store_v1 import SelectionStore
from check_authored_workset_literal_v1 import read_metadata, workset_profiles, read_pair, checked_row
from authored_empty_section_literal_v2 import preservation
from authored_named_list_context_v1 import context_deferrals, PROSE
from structural_delimiter_deferrals_v1 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from scripts import p106b_hold_resolution_policy_v32 as policy


def run(config_path):
    guard.activate()
    start = time.monotonic()
    config = json.loads(config_path.read_bytes())
    pins = {}
    selection = SelectionStore(AUDIT).read(ROOT / config['selection']['path'], config['selection']['sha256'])
    selected = {row['id'] for row in selection['rows']}
    pins[config['selection']['path']] = config['selection']['sha256']
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    old = read_metadata(config['prior_context_deferrals'], pins)
    explicit = {row['id']: [reason for reason in row['reasons'] if reason.startswith('ROOT_OBSERVED_')]
                for row in old['deferred_rows']}
    checks, deferred = [], []
    reasons, types = Counter(), Counter()
    examined = discharged = 0
    for item, row in workset_profiles(config['workset'], pins):
        if row['id'] in selected or PROSE not in row['remaining_deferrals']:
            continue
        examined += 1
        values = read_pair(row, pins)
        remaining, context = context_deferrals(*values)
        failed = list(remaining) + policy.literal_holes(values[1]) + delimiter_deferrals(values[1])
        failed += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(values[1])]
        failed += explicit.get(row['id'], [])
        if not context['discharged']:
            assert PROSE in remaining
            failed.append(context.get('reason', 'UNPROVEN_LISTING_ROLE'))
        else:
            discharged += 1
        proof = None
        if not failed:
            proof = preservation(*values)
            failed += [name for name, ok in proof['guards'].items() if not ok]
        if failed:
            deferred.append(dict(id=row['id'], original_text_sha256=row['original']['sha256'],
                                 body=row['body'], occurrences=row['occurrences'], reasons=sorted(set(failed)),
                                 named_list_context=context))
            reasons.update(set(failed))
        else:
            assert proof is not None and proof['eligible_narrow_literal_delta']
            for review in row['all_reviews']:
                assert guard.inv.file_sha(ROOT / review['path']) == review['sha256']
            proof = dict(proof, named_list_context=context)
            result = checked_row(row, values, proof, dict(
                every_prose_flag_has_explicit_existing_listing_role=True,
                source_record_values_and_line_order_preserved=True,
                other_native_code_numeric_quote_and_heading_guards_preserved=True))
            checks.append(result)
            types.update(context['types'])
        if examined % 200 == 0:
            print(json.dumps(dict(progress_examined=examined, context_discharged=discharged,
                                  ready=len(checks), source_body_copies=0)), flush=True)
    for path in [config_path, Path(__file__), guard.CONTRACT, AUDIT / 'authored_named_list_context_v1.py',
                 AUDIT / 'test_authored_named_list_context_v1.py', AUDIT / 'check_authored_workset_literal_v1.py',
                 AUDIT / 'authored_empty_section_literal_v2.py', AUDIT / 'authored_literal_readiness_v1.py',
                 AUDIT / 'structural_delimiter_deferrals_v1.py']:
        pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
    report = dict(status='SOURCE_ANCHORED_NAMED_LIST_CONTEXT_AND_ALL_ROW_LITERAL_PROOFS_PENDING_ROOT',
                  candidates=examined, context_discharged=discharged, verified=len(checks),
                  verified_positions=sum(row['occurrences'] for row in checks), deferred=len(deferred),
                  deferral_reason_counts=dict(reasons), named_list_type_counts=dict(types),
                  checks=checks, deferred_rows=deferred, input_pins=pins,
                  cumulative_guard_sha256=guard.EXPECTED, protected_payload_open_attempts=0,
                  corpus_payload_copies_written=0, additional_human_full_read_credit=0,
                  root_approved=False, cache_admitted=False, elapsed_seconds=time.monotonic() - start,
                  goal_complete=False, training_authorized=False)
    assert len(checks) + len(deferred) == examined
    output = AUDIT / config['output']
    assert not output.exists()
    assert len((json.dumps(report, ensure_ascii=False, indent=2) + chr(10)).encode()) < 20_000_000
    guard.inv.write_json(output, report)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in report.items() if key not in {'checks', 'deferred_rows', 'input_pins'}}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    path = Path(args.config).resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    run(path)
