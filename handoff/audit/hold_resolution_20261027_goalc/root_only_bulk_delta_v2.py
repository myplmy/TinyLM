"""Repair only affected saved bodies; reuse source values and cheap rejection."""
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
from root_empty_section_contract_v3 import mask, possible, preservation, typed_footer
from root_only_alias_delta_v1 import repair as alias_repair, normalize_empty_label
from authored_literal_readiness_v1 import deferrals
from structural_delimiter_deferrals_v2 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from verify_event_metadata_literal_delta_v1 import last_paragraph
from verify_category_metadata_delta_v1 import context_deferrals
from verify_rule27_literal_delta_v1 import empty_eof_appendix
from selection_metadata_store_v1 import SelectionStore
from numeric_atom_integrity_v1 import numeric_atom_changes
from scripts import p106b_hold_resolution_policy_v32 as policy

CLOSURE_IDS = {'expanded_train:' + number for number in ['303708', '309061', '451763', '410435']}
METADATA_REPAIR_IDS = {'expanded_train:' + number for number in [
    '114975', '117380', '125554', '127049', '246925', '247043', '241592',
    '125295', '125907', '198273', '304809']}


def source_basis(source, ident):
    source = normalize_empty_label(source, ident)
    if ident == 'expanded_train:198273':
        source = source.replace('(二層 - , )', '(二層)')
    source, removed = mask(source)
    if ident == 'expanded_train:198273':
        prefix, suffix = last_paragraph(source)
        assert suffix.strip() == '종류별 버스'
        prefix, headings = empty_eof_appendix(prefix)
        source = prefix + chr(10) * 2 + suffix + chr(10)
        removed += [dict(item, boundary='ROOT_CONFIRMED_SINGLE_BUS_TAXONOMIC_FOOTER') for item in headings]
    return source, removed


def trim_body(body, ident):
    body = mask(body)[0]
    if ident == 'expanded_train:198273':
        prefix, suffix = last_paragraph(body)
        if suffix.strip() == '종류별 버스':
            prefix = empty_eof_appendix(prefix)[0]
            body = prefix + chr(10) * 2 + suffix + chr(10)
    return body


def restore_footer(body, footer):
    """Replace an ordered partially retained tag tail, without duplicating it."""
    if last_paragraph(body)[1] == footer:
        return body
    expected = [value.strip() for value in footer.splitlines() if value.strip()]
    lines = body.splitlines(keepends=True)
    end = len(lines) - 1
    while end >= 0 and not lines[end].strip():
        end -= 1
    position, first, matched = len(expected) - 1, end + 1, 0
    for i in range(end, -1, -1):
        value = lines[i].strip()
        if not value:
            if matched:
                continue
            break
        found = next((j for j in range(position, -1, -1) if expected[j] == value), None)
        if found is None:
            break
        position, first, matched = found - 1, i, matched + 1
    prefix = ''.join(lines[:first]).rstrip(chr(13) + chr(10)) if matched else body.rstrip(chr(13) + chr(10))
    return prefix + chr(10) * 2 + footer + chr(10)


def close_exact_native(body, ident):
    value = alias_repair(body, ident)
    changes = {
        'expanded_train:303708': [('가면라이더 덴오(로', '가면라이더 덴오로')],
        'expanded_train:309061': [('붉은 해적단 (에', '붉은 해적단에'), ('Zagin, , Z=', 'Zagin, Z=')],
        'expanded_train:451763': [('의(疑,\n는', '의(疑)는')],
        'expanded_train:410435': [('각각 염색체 2세트씩 물려받음))', '각각 염색체 2세트씩 물려받음)')],
    }
    for before, after in changes[ident]:
        assert value.count(before) == 1, (ident, before)
        value = value.replace(before, after, 1)
    return value


def run():
    guard.activate()
    started, pins = time.monotonic(), {}
    base_config = AUDIT / 'B_ROOT_ONLY_BULK_READINESS_CONFIG_V1.json'
    config = json.loads(base_config.read_bytes())
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    selection_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V51.json'
    selection_sha = guard.inv.file_sha(selection_path)
    selected = {row['id'] for row in SelectionStore(AUDIT).read(selection_path, selection_sha)['rows']}
    pins[str(selection_path.relative_to(ROOT))] = selection_sha
    old_path = AUDIT / 'B_ROOT_ONLY_BULK_READINESS_V1.json'
    old = json.loads(old_path.read_bytes())
    deferred_basis = {row['id']: row for row in old['deferred_rows']}
    more = json.loads((AUDIT / 'B_ROOT_ONLY_COMBINED_READINESS_V1.json').read_bytes())
    for row in more['deferred_rows']:
        if any(reason.startswith('ROOT_OBSERVED_') for reason in row['reasons']):
            deferred_basis[row['id']] = row
    inventory_path = AUDIT / 'B_MANUAL_REPAIR_SAVED_INVENTORY_V1.json'
    inventory = json.loads(inventory_path.read_bytes())
    saved_outputs = {(row['id'], row['new_body']['sha256']): row['new_body'] for row in inventory['rows']}
    items = [(item, row) for item, row in workset_profiles(config['workset'], pins) if row['id'] not in selected]
    for _, row in items:
        guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['body']))
    checks, deferred, written = [], [], []
    counters = Counter()
    output = guard.inv.BASE / 'root_only_literal_repairs_v1'
    for index, (_, row) in enumerate(items, 1):
        ident = row['id']
        previous = deferred_basis.get(ident, {})
        previous_reasons = previous.get('reasons', [])
        roots = [reason for reason in previous_reasons if reason.startswith('ROOT_OBSERVED_')]
        if ident == 'expanded_train:309061':
            roots = [reason for reason in roots if reason != 'ROOT_OBSERVED_UNRESOLVED_CURRENCY_SYMBOL_Z_EQUALS']
        specific = 'SAVED_SPECIFIC_SECONDARY_CONTEXT_REQUIRES_CLOSURE' in previous_reasons
        if roots or (specific and ident not in CLOSURE_IDS | METADATA_REPAIR_IDS):
            counters['specific_context_preserved'] += 1
            deferred.append(dict(id=ident, occurrences=row['occurrences'], reasons=roots or previous_reasons,
                                 heavy_checks='NOT_RUN_REUSED_SPECIFIC_DEFERRAL'))
            continue
        source, before = read_pair(row, pins)
        canonical_source, normalized_heads = source_basis(source, ident)
        body = close_exact_native(before, ident) if ident in CLOSURE_IDS else before
        body = trim_body(body, ident)
        footer = last_paragraph(source)[1]
        variants = [(body, 'EXISTING_BODY_OR_PROVEN_EMPTY_HEADING_TRIM')]
        footer_type = typed_footer(footer)
        if footer_type:
            restored = restore_footer(body, footer)
            if restored != body:
                variants.append((restored, 'RESTORED_EXACT_FULL_OR_PARTIAL_TYPED_SOURCE_FOOTER'))
        accepted = None
        last_fail = ['NO_LITERAL_SOURCE_PRESERVING_VARIANT']
        for candidate, operation in variants:
            if not candidate.strip() or not possible(canonical_source, candidate):
                counters['cheap_literal_rejections'] += 1
                continue
            counters['heavy_preservation_runs'] += 1
            proof = preservation(canonical_source, candidate)
            failed = [name for name, passed in proof['guards'].items() if not passed]
            failed += ['RAW_NUMERIC_ATOMS'] if numeric_atom_changes(source, candidate) else []
            failed += ['RAW_CODE'] if not policy.code_preserved(source, candidate) else []
            failed += ['RAW_UNICODE'] if not policy.unicode_examples_preserved(source, candidate) else []
            failed += ['RAW_STYLE'] if not policy.semantic_style_preserved(source, candidate) else []
            flags = set(deferrals(candidate) + policy.literal_holes(candidate) + delimiter_deferrals(candidate))
            nominal = (footer_type and last_paragraph(candidate)[1] == footer and not context_deferrals(candidate))
            if nominal:
                flags.discard('POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT')
            failed += sorted(flags)
            failed += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(candidate)]
            if mask(candidate)[0] != candidate:
                failed.append('PROVEN_EMPTY_SECTION_REMAINS')
            if candidate.rstrip().endswith((':', '：', '→', '/')):
                failed.append('FINAL_TAIL_REQUIRES_CONTEXT')
            if failed:
                last_fail = sorted(set(failed))
                continue
            accepted = candidate, operation, proof, bool(nominal)
            break
        if accepted is None:
            counters['not_admitted'] += 1
            deferred.append(dict(id=ident, occurrences=row['occurrences'], reasons=last_fail,
                prior_body_sha256=row['body']['sha256'], heavy_checks='RUN_ONLY_WHERE_LITERAL_POSSIBLE'))
            continue
        body, operation, proof, nominal = accepted
        sha = guard.inv.sha(body)
        if sha == row['body']['sha256']:
            body_pin = row['body']
            counters['existing_body_reused'] += 1
        elif (ident, sha) in saved_outputs:
            body_pin = saved_outputs[ident, sha]
            assert guard.inv.file_sha(ROOT / body_pin['path']) == sha
            counters['matching_saved_manual_body_reused'] += 1
        else:
            raw = body.encode('utf-8')
            assert 0 < len(raw) < 20_000_000
            target = output / sha[:2] / (sha + '.txt')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == raw
            else:
                with target.open('xb') as stream:
                    stream.write(raw)
                written.append(dict(path=str(target.relative_to(ROOT)), sha256=sha, bytes=len(raw)))
            body_pin = dict(path=str(target.relative_to(ROOT)), sha256=sha)
            counters['root_reproduced_body'] += 1
        for value in row['all_reviews']:
            assert guard.inv.file_sha(ROOT / value['path']) == value['sha256']
        proof = dict(proof, original_source_sha256=row['original']['sha256'],
            canonical_source_sha256=guard.inv.sha(canonical_source), source_header_role_evidence=normalized_heads,
            source_specific_empty_alias_normalization=ident in CLOSURE_IDS or ident == 'expanded_train:198273',
            exact_source_footer_restore=operation, typed_nominal_context=nominal,
            author='/root', universal_scanner_relaxation=False)
        checks.append(dict(id=ident, original=row['original'], original_text_sha256=row['original']['sha256'],
            body=dict(body_pin, bytes=len(body.encode('utf-8'))), decision='KEEP' if source == body else 'EDIT',
            occurrences=row['occurrences'], primary_review=row['primary_review'], primary_source_cohort=row['primary_cohort'],
            reason=row['reason'] + ' / ROOT-only source-bound delta: ' + operation,
            all_saved_reviews=row['all_reviews'], full_source_read_by_primary_author_claimed=True,
            additional_human_full_text_read_claimed=False, fresh_preservation_proof=proof,
            additional_readiness_guards=dict(original_source_and_prior_body_match_frozen_workset=True,
                new_body_matches_reproduced_ROOT_delta=True, raw_numeric_code_unicode_style_preserved=True,
                no_unresolved_native_formal_or_body_structure_gap=True, no_unresolved_specific_ROOT_context=True)))
        counters['ready'] += 1
        if index % 1000 == 0:
            print(json.dumps(dict(processed=index, ready=len(checks), payload_bytes=sum(x['bytes'] for x in written))), flush=True)
    for path in [base_config, old_path, inventory_path, Path(__file__), guard.CONTRACT,
                 AUDIT / 'B_ROOT_ONLY_COMBINED_READINESS_V1.json'] + [AUDIT / name for name in [
        'root_empty_section_contract_v3.py', 'test_root_empty_section_contract_v3.py',
        'root_only_alias_delta_v1.py', 'quick_literal_feasibility_v1.py',
        'authored_round_closure_preservation_v1.py', 'check_authored_workset_literal_v1.py']]:
        pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
    result = dict(status='ROOT_ONLY_AFFECTED_EMPTY_SECTIONS_AND_SOURCE_FOOTER_DELTA_PENDING_REVIEW',
        examined_unique=len(items), examined_positions=sum(row['occurrences'] for _, row in items),
        verified=len(checks), verified_positions=sum(row['occurrences'] for row in checks), checks=checks,
        deferred_rows=deferred, deferred=len(deferred), counters=dict(counters), input_pins=pins,
        cumulative_guard_sha256=guard.EXPECTED, protected_payload_open_attempts=0, corpus_payload_copies_written=0,
        additional_human_full_read_credit=0, written_payloads=written,
        newly_authored_body_files=len(written), newly_authored_body_bytes=sum(row['bytes'] for row in written),
        root_approved=False, cache_admitted=False, goal_complete=False, training_authorized=False,
        elapsed_seconds=time.monotonic() - started)
    path = AUDIT / 'B_ROOT_ONLY_BULK_DELTA_READINESS_V2.json'
    assert not path.exists()
    guard.inv.write_json(path, result)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in result.items()
        if key not in {'checks', 'deferred_rows', 'input_pins', 'written_payloads'}}), flush=True)


if __name__ == '__main__':
    run()
