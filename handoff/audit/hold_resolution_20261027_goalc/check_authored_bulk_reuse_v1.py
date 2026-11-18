"""One pass over all unselected saved bodies; no delegation or payload copies.

Reuse the existing literal, typed-metadata and closing-delimiter contracts.
Never reinterpret a missing source value as an empty formatting field.
"""
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
from check_authored_workset_literal_v1 import read_metadata, workset_profiles, read_pair, checked_row
from authored_round_closure_preservation_v1 import preservation
from authored_literal_readiness_v1 import deferrals
from structural_delimiter_deferrals_v2 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from verify_event_metadata_literal_delta_v1 import last_paragraph
from verify_category_metadata_delta_v1 import category_markers, context_deferrals
from selection_metadata_store_v1 import SelectionStore
from scripts import p106b_hold_resolution_policy_v32 as policy

PROSE = 'POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT'


def run(path):
    guard.activate()
    started, pins = time.monotonic(), {}
    config = json.loads(path.read_bytes())
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert not (ROOT / name).is_symlink() and guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    selected = {row['id'] for row in SelectionStore(AUDIT).read(
        ROOT / config['selection']['path'], config['selection']['sha256'])['rows']}
    pins[config['selection']['path']] = config['selection']['sha256']
    blocked = {}
    for value in config['root_context_deferrals']:
        prior = read_metadata(value, pins)
        for row in prior['deferred_rows']:
            actual = [v for v in row['reasons'] if v.startswith('ROOT_OBSERVED_')]
            if actual:
                blocked.setdefault(row['id'], []).extend(actual)
    for name in config['completed_secondary_files']:
        file = ROOT / name
        assert file.suffix == '.md' and not file.is_symlink()
        raw = file.read_bytes()
        pins[name] = guard.inv.file_sha(file)
        text = raw.decode('utf-8')
        # Status-marked in-progress drafts supply no completed evidence.
        if 'Status: DRAFT' in text:
            continue
        for line in text.splitlines():
            cells = line.split('|', 5)
            if len(cells) == 6 and cells[1].strip().startswith(('expanded_train:', 'validation:')):
                if cells[3].strip().strip('`') in {'BODY_NEEDS_REPAIR', 'NEEDS_ROOT_CONTEXT'}:
                    blocked.setdefault(cells[1].strip().strip('`'), []).append('SAVED_SPECIFIC_SECONDARY_CONTEXT_REQUIRES_CLOSURE')
    items = [(item, row) for item, row in workset_profiles(config['workset'], pins) if row['id'] not in selected]
    # Check the complete ID/hash scope before opening its first source.
    for _, row in items:
        guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['body']))
    checks, deferred = [], []
    reasons, partitions, groups = Counter(), Counter(), Counter()
    source_pairs = 0
    for item, row in items:
        groups[item['group']] += 1
        failed = sorted(set(blocked.get(row['id'], [])))
        if failed:
            partitions['PREEXISTING_SPECIFIC_CONTEXT_DEFERRAL'] += 1
        else:
            source, body = read_pair(row, pins)
            source_pairs += 1
            proof = preservation(source, body)
            failed = [name for name, passed in proof['guards'].items() if not passed]
            if failed:
                partitions['SOURCE_VALUE_OR_ORDER_GUARD_REQUIRES_CONTEXT'] += 1
            else:
                flags = set(deferrals(body) + policy.literal_holes(body) + delimiter_deferrals(body))
                typed_nominal = False
                if PROSE in flags:
                    source_suffix, body_suffix = last_paragraph(source)[1], last_paragraph(body)[1]
                    typed_nominal = (source_suffix == body_suffix and category_markers(source_suffix)
                                     and not context_deferrals(body))
                    if typed_nominal:
                        flags.remove(PROSE)
                failed += sorted(flags)
                failed += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(body)]
                empty = proof.get('candidate_empty_eof_appendix_headings', []) + proof.get('candidate_independently_empty_section_lines', [])
                if empty:
                    failed.append('INDEPENDENTLY_PROVEN_EMPTY_SECTION_REMAINS_IN_FINAL_BODY')
                if body.rstrip().endswith((':', '：', '→', '/')):
                    failed.append('FINAL_TAIL_REQUIRES_CONTEXT')
                if failed:
                    partitions['REMAINING_BODY_GAP_OR_STRUCTURE_REQUIRES_CONTEXT'] += 1
                else:
                    for value in row['all_reviews']:
                        assert guard.inv.file_sha(ROOT / value['path']) == value['sha256']
                    proof = dict(proof, independent_typed_nominal_context=dict(
                        used=typed_nominal, preserved_source_suffix_sha256=guard.inv.sha(source_suffix) if typed_nominal else None,
                        verifier='verify_category_metadata_delta_v1.context_deferrals',
                        no_unfinished_sentence_bearing_prefix=True, universal_scanner_relaxation=False))
                    checks.append(checked_row(row, [source, body], proof,
                        dict(no_independently_proven_empty_final_body_section=True,
                             no_unresolved_final_tail=True, no_saved_specific_context_deferral=True)))
                    partitions['ALL_SOURCE_VALUES_AND_REMAINING_BODY_CONTRACT_READY'] += 1
        if failed:
            failed = sorted(set(failed))
            reasons.update(failed)
            deferred.append(dict(id=row['id'], body_sha256=row['body']['sha256'],
                                 occurrences=row['occurrences'], reasons=failed))
    assert len(checks) + len(deferred) == len(items) == sum(partitions.values())
    for value in [path, Path(__file__), guard.CONTRACT] + [AUDIT / name for name in [
        'check_authored_workset_literal_v1.py', 'authored_round_closure_preservation_v1.py',
        'authored_empty_section_literal_v2.py', 'authored_empty_section_literal_v1.py',
        'authored_literal_metadata_readiness_v2.py', 'authored_literal_readiness_v1.py',
        'structural_delimiter_deferrals_v2.py', 'structural_delimiter_deferrals_v1.py',
        'close_remaining_heading_context_v1.py', 'verify_event_metadata_literal_delta_v1.py',
        'verify_category_metadata_delta_v1.py']]:
        pins[str(value.relative_to(ROOT))] = guard.inv.file_sha(value)
    result = dict(status='WHOLE_UNSELECTED_WORKSET_ONE_PASS_REUSE_PENDING_ROOT',
        examined_unique=len(items), examined_positions=sum(row['occurrences'] for _, row in items),
        verified=len(checks), verified_positions=sum(row['occurrences'] for row in checks),
        checks=checks, deferred_rows=deferred, deferred=len(deferred), deferral_reason_counts=dict(reasons),
        disjoint_partitions=dict(partitions), original_workset_groups=dict(groups),
        source_body_pairs_opened_once=source_pairs, input_pins=pins,
        cumulative_guard_sha256=guard.EXPECTED, protected_payload_open_attempts=0,
        corpus_payload_copies_written=0, additional_human_full_read_credit=0,
        root_approved=False, cache_admitted=False, goal_complete=False, training_authorized=False,
        elapsed_seconds=time.monotonic() - started)
    out = AUDIT / config['output']
    assert not out.exists()
    guard.inv.write_json(out, result)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in result.items()
        if key not in {'checks', 'deferred_rows', 'input_pins', 'original_workset_groups'}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    path = parser.parse_args().config.resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    run(path)
