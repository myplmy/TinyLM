"""Apply ROOT-reviewed empty-alias deltas; write only fully verified results."""
from pathlib import Path
import json
import re
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from check_authored_workset_literal_v1 import read_metadata, workset_profiles, read_pair
from authored_round_closure_preservation_v1 import preservation
from authored_literal_readiness_v1 import deferrals
from structural_delimiter_deferrals_v2 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings
from verify_category_metadata_delta_v1 import context_deferrals
from scripts import p106b_hold_resolution_policy_v32 as policy


def normalize_empty_label(source, ident):
    value = source
    if ident == 'expanded_train:408569':
        value = value.replace('(, 복수형: )', '')
    if ident == 'expanded_train:303708':
        value = value.replace('(게임, 린트어: )', '(게임)')
    if ident == 'expanded_train:462395':
        value = value.replace('《》', '')
    return value


def repair(body, ident):
    value = normalize_empty_label(body, ident)
    if ident == 'expanded_train:451763':
        for before, after in [
            ('의식의 작용(意識의 作用, ,\ncaitasika,\n,\n)', '의식의 작용(意識의 作用, caitasika)'),
            ('의식작용(意識作用, (,\ncaitasika,\n,\n)', '의식작용(意識作用, caitasika)')]:
            assert value.count(before) == 1
            value = value.replace(before, after, 1)
    value = re.sub(r'\(\s*\)', '', value)
    value = re.sub(r'\(\s*[,，;]\s*', '(', value)
    value = re.sub(r'[,，]\s*\)', ')', value)
    return value


def run():
    guard.activate()
    started, pins = time.monotonic(), {}
    config_path = AUDIT / 'B_ROOT_ONLY_BULK_READINESS_CONFIG_V1.json'
    config = json.loads(config_path.read_bytes())
    runtime = read_metadata(config['runtime_basis'], pins)
    for name, sha in runtime['input_pins'].items():
        assert guard.inv.file_sha(ROOT / name) == sha, name
        pins[name] = sha
    profiles = {row['id']: row for _, row in workset_profiles(config['workset'], pins)}
    scope_path = AUDIT / 'B_C_REMAINING_ALIAS_REPAIR_SCOPE_V1.json'
    scope = json.loads(scope_path.read_bytes())
    for case in scope['cases']:
        prior = profiles[case['id']]
        assert case['original'] == prior['original'] and case['body'] == prior['body']
        guard.require_payload_context(dict(source_id=case['id'], original=case['original'], candidate=case['body']))
    output = guard.inv.BASE / 'root_only_literal_repairs_v1'
    checks, deferred, written = [], [], []
    for case in scope['cases']:
        prior = profiles[case['id']]
        source, old_body = read_pair(prior, pins)
        body = repair(old_body, case['id'])
        assert body != old_body
        normalized = normalize_empty_label(source, case['id'])
        proof, raw_proof = preservation(normalized, body), preservation(source, body)
        failed = [key for key, value in proof['guards'].items() if not value]
        # The optional empty field labels contain no numeric/code/style value.
        # Those raw-source checks must pass independently of normalization.
        for key in ['numeric_atoms', 'code', 'unicode', 'style', 'ordered']:
            if not raw_proof['guards'].get(key, False):
                failed.append('RAW_SOURCE_' + key)
        flags = set(deferrals(body) + policy.literal_holes(body) + delimiter_deferrals(body))
        if ('POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT' in flags
                and not context_deferrals(body)):
            flags.remove('POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT')
        failed += sorted(flags)
        failed += ['REMAINING_CONTENT_HEADING:' + value for value in remaining_headings(body)]
        if proof.get('candidate_empty_eof_appendix_headings') or proof.get('candidate_independently_empty_section_lines'):
            failed.append('EMPTY_SECTION_REMAINS_IN_FINAL_BODY')
        if case['id'] == 'expanded_train:309061':
            failed.append('ROOT_OBSERVED_UNRESOLVED_CURRENCY_SYMBOL_Z_EQUALS')
        if body.rstrip().endswith((':', '：', '→', '/')):
            failed.append('FINAL_TAIL_REQUIRES_CONTEXT')
        if failed:
            deferred.append(dict(id=case['id'], old_body=case['body'], proposed_body_sha256=guard.inv.sha(body),
                                 reasons=sorted(set(failed)), payload_written=False))
            continue
        raw = body.encode('utf-8')
        assert 0 < len(raw) < 20_000_000
        sha = guard.inv.sha(body)
        target = output / sha[:2] / (sha + '.txt')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == raw
        else:
            with target.open('xb') as stream:
                stream.write(raw)
            written.append(dict(path=str(target.relative_to(ROOT)), sha256=sha, bytes=len(raw)))
        for pin in prior['all_reviews']:
            assert guard.inv.file_sha(ROOT / pin['path']) == pin['sha256']
        actual_proof = dict(proof, raw_source_observations=raw_proof,
            exact_empty_label_normalization=dict(used=normalized != source,
                source_sha256=prior['original']['sha256'], normalized_comparison_sha256=guard.inv.sha(normalized),
                target=case['id'], no_new_translation_or_value=True), author='/root',
            primary_full_source_and_unchanged_body_reused=True, additional_original_full_read_credit=0)
        checks.append(dict(id=case['id'], original=prior['original'], original_text_sha256=prior['original']['sha256'],
            body=dict(path=str(target.relative_to(ROOT)), sha256=sha, bytes=len(raw)), decision='EDIT',
            occurrences=prior['occurrences'], primary_review=prior['primary_review'], primary_source_cohort=prior['primary_cohort'],
            reason=prior['reason'] + ' / ROOT-only exact empty-alias repair after direct match-context inspection.',
            all_saved_reviews=prior['all_reviews'], full_source_read_by_primary_author_claimed=True,
            additional_human_full_text_read_claimed=False, fresh_preservation_proof=actual_proof,
            additional_readiness_guards=dict(prior_workset_source_and_body_match=True,
                raw_numeric_code_unicode_style_and_order_preserved=True,
                no_remaining_native_formal_or_structural_gap=True, exact_ROOT_repair_context=True)))
    for path in [config_path, scope_path, Path(__file__), guard.CONTRACT] + [AUDIT / name for name in [
        'authored_round_closure_preservation_v1.py', 'authored_empty_section_literal_v2.py',
        'authored_empty_section_literal_v1.py', 'authored_literal_metadata_readiness_v2.py',
        'authored_literal_readiness_v1.py', 'structural_delimiter_deferrals_v2.py',
        'verify_category_metadata_delta_v1.py', 'close_remaining_heading_context_v1.py']]:
        pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
    result = dict(status='ROOT_ONLY_REPAIRED_AND_LITERAL_VERIFIED_PENDING_SELECTION',
        verified=len(checks), verified_positions=sum(row['occurrences'] for row in checks), checks=checks,
        deferred_rows=deferred, deferred=len(deferred), input_pins=pins, written_payloads=written,
        original_payload_copies_written=0, cumulative_guard_sha256=guard.EXPECTED,
        protected_payload_open_attempts=0, corpus_payload_copies_written=0, additional_human_full_read_credit=0,
        newly_authored_body_files=len(written), newly_authored_body_bytes=sum(row['bytes'] for row in written),
        root_approved=False, cache_admitted=False, goal_complete=False, training_authorized=False,
        elapsed_seconds=time.monotonic() - started)
    path = AUDIT / 'B_ROOT_ONLY_ALIAS_REPAIR_READINESS_V1.json'
    assert not path.exists()
    guard.inv.write_json(path, result)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in result.items() if key not in {'checks', 'deferred_rows', 'input_pins', 'written_payloads'}}))


if __name__ == '__main__':
    run()
