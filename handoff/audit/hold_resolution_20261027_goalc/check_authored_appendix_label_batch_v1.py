"""Apply the narrow label contract to every remaining linked B body once."""
from pathlib import Path
from collections import Counter
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from check_authored_workset_literal_v1 import read_metadata, workset_profiles, read_pair
from authored_appendix_heading_literal_v1 import mask, possible, preservation
from root_empty_section_contract_v3 import typed_footer
from root_only_bulk_delta_v2 import restore_footer
from selection_metadata_store_v1 import SelectionStore
from numeric_atom_integrity_v1 import numeric_atom_changes
from authored_literal_readiness_v1 import deferrals
from structural_delimiter_deferrals_v2 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from verify_event_metadata_literal_delta_v1 import last_paragraph
from verify_category_metadata_delta_v1 import context_deferrals
from scripts import p106b_hold_resolution_policy_v32 as policy


def run():
    guard.activate()
    started, pins, times = time.monotonic(), {}, Counter()
    base = AUDIT / 'B_ROOT_ONLY_BULK_READINESS_CONFIG_V1.json'
    config = json.loads(base.read_bytes())
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    selection = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V52.json'
    selected = {row['id'] for row in SelectionStore(AUDIT).read(selection, guard.inv.file_sha(selection))['rows']}
    prior_path = AUDIT / 'B_ROOT_ONLY_BULK_DELTA_READINESS_V2.json'
    prior = json.loads(prior_path.read_bytes())
    specific = {row['id']: row['reasons'] for row in prior['deferred_rows']
        if any(value.startswith('ROOT_OBSERVED_') for value in row['reasons'])
        or row.get('heavy_checks') == 'NOT_RUN_REUSED_SPECIFIC_DEFERRAL'}
    items = [row for _, row in workset_profiles(config['workset'], pins) if row['id'] not in selected]
    times['metadata_seconds'] = time.monotonic() - started
    checks, deferred, written, counters = [], [], [], Counter()
    for row in items:
        ident = row['id']
        if ident in specific:
            deferred.append(dict(id=ident, occurrences=row['occurrences'], reasons=specific[ident]))
            counters['specific_context_retained'] += 1
            continue
        tick = time.monotonic()
        source, saved = read_pair(row, pins)
        body = mask(saved)[0]
        variants = [(body, 'REMOVE_ONLY_EXACT_APPENDIX_LABEL_LINES')]
        footer = last_paragraph(source)[1]
        if typed_footer(footer):
            restored = restore_footer(body, footer)
            if body != restored:
                variants.append((restored, 'RESTORE_EXACT_SOURCE_FOOTER_AND_REMOVE_APPENDIX_LABEL_LINES'))
        times['source_read_and_prepare_seconds'] += time.monotonic() - tick
        accepted, failed = None, ['POPULATED_SOURCE_VALUES_DIFFER']
        for body, operation in variants:
            tick = time.monotonic()
            feasible = possible(source, body)
            times['cheap_filter_seconds'] += time.monotonic() - tick
            if not feasible:
                counters['cheap_rejected_variants'] += 1
                continue
            tick = time.monotonic()
            proof = preservation(source, body)
            failed = [name for name, passed in proof['guards'].items() if not passed]
            failed += ['RAW_NUMERIC_ATOMS'] if numeric_atom_changes(source, body) else []
            failed += ['RAW_CODE'] if not policy.code_preserved(source, body) else []
            failed += ['RAW_UNICODE'] if not policy.unicode_examples_preserved(source, body) else []
            failed += ['RAW_STYLE'] if not policy.semantic_style_preserved(source, body) else []
            flags = set(deferrals(body) + delimiter_deferrals(body) + policy.literal_holes(body))
            nominal = bool(typed_footer(footer) and last_paragraph(body)[1] == footer and not context_deferrals(body))
            if nominal:
                flags.discard('POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT')
            failed += sorted(flags)
            failed += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(body)]
            if body.rstrip().endswith((':', '：', '/', '→')):
                failed.append('FINAL_TAIL_REQUIRES_CONTEXT')
            times['preservation_and_body_checks_seconds'] += time.monotonic() - tick
            counters['heavy_variants'] += 1
            if not failed:
                accepted = body, operation, proof, nominal
                break
        if accepted is None:
            deferred.append(dict(id=ident, occurrences=row['occurrences'], reasons=sorted(set(failed))))
            continue
        tick = time.monotonic()
        body, operation, proof, nominal = accepted
        sha = guard.inv.sha(body)
        if sha == row['body']['sha256']:
            body_pin = row['body']
            counters['existing_body_reused'] += 1
        else:
            raw = body.encode('utf-8')
            assert 0 < len(raw) < 20_000_000
            target = guard.inv.BASE / 'root_only_literal_repairs_v1' / sha[:2] / (sha + '.txt')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == raw
            else:
                with target.open('xb') as stream:
                    stream.write(raw)
                written.append(dict(path=str(target.relative_to(ROOT)), sha256=sha, bytes=len(raw)))
            body_pin = dict(path=str(target.relative_to(ROOT)), sha256=sha)
            counters['root_body_delta'] += 1
        for pin in row['all_reviews']:
            assert guard.inv.file_sha(ROOT / pin['path']) == pin['sha256']
        proof = dict(proof, original_source_sha256=row['original']['sha256'],
            operation=operation, typed_nominal_context=nominal,
            retained_populated_values_source_order_and_multiplicity=True)
        checks.append(dict(id=ident, original=row['original'], original_text_sha256=row['original']['sha256'],
            body=dict(body_pin, bytes=len(body.encode('utf-8'))), decision='KEEP' if source == body else 'EDIT',
            occurrences=row['occurrences'], primary_review=row['primary_review'], primary_source_cohort=row['primary_cohort'],
            reason=row['reason'] + ' / ROOT exact appendix label contract; populated values retained',
            all_saved_reviews=row['all_reviews'], full_source_read_by_primary_author_claimed=True,
            additional_human_full_text_read_claimed=False, fresh_preservation_proof=proof,
            additional_readiness_guards=dict(original_source_and_prior_body_match_frozen_workset=True,
                new_body_matches_ROOT_exact_label_delta=True, raw_numeric_code_unicode_style_preserved=True,
                no_remaining_native_formal_or_body_structure_gap=True, no_saved_specific_context_deferral=True)))
        times['accepted_payload_and_review_pins_seconds'] += time.monotonic() - tick
    for path in [base, prior_path, selection, Path(__file__), guard.CONTRACT,
        AUDIT / 'authored_appendix_heading_literal_v1.py', AUDIT / 'test_authored_appendix_heading_literal_v1.py',
        AUDIT / 'root_empty_section_contract_v3.py', AUDIT / 'root_only_bulk_delta_v2.py']:
        pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
    result = dict(status='EXACT_APPENDIX_LABEL_AND_POPULATED_VALUE_BATCH_PENDING_ADMISSION',
        examined_unique=len(items), examined_positions=sum(row['occurrences'] for row in items),
        verified=len(checks), verified_positions=sum(row['occurrences'] for row in checks),
        checks=checks, deferred_rows=deferred, deferred=len(deferred), counters=dict(counters), stage_seconds=dict(times),
        input_pins=pins, cumulative_guard_sha256=guard.EXPECTED, protected_payload_open_attempts=0,
        corpus_payload_copies_written=0, additional_human_full_read_credit=0, written_payloads=written,
        newly_authored_body_files=len(written), newly_authored_body_bytes=sum(row['bytes'] for row in written),
        root_approved=False, cache_admitted=False, goal_complete=False, training_authorized=False,
        elapsed_seconds=time.monotonic() - started)
    output = AUDIT / 'B_ROOT_ONLY_APPENDIX_LABEL_READINESS_V1.json'
    assert not output.exists()
    guard.inv.write_json(output, result)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in result.items()
        if key not in {'checks', 'deferred_rows', 'input_pins', 'written_payloads'}}))


if __name__ == '__main__':
    run()
