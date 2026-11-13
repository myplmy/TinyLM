"""Independently retain first nonnumeric tags in one typed terminal block."""
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from verify_rule27_literal_delta_v1 import evaluate as literal_evaluate, literal_stream, empty_eof_appendix
from verify_event_metadata_literal_delta_v1 import last_paragraph
from verify_category_metadata_delta_v1 import category_markers, context_deferrals
from structural_delimiter_deferrals_v1 import deferrals as delimiter_deferrals
from close_remaining_heading_context_v1 import remaining_headings


def evaluate(original, candidate, decision):
    before, suffix = last_paragraph(original)
    after, target_suffix = last_paragraph(candidate)
    source_values = [line.strip() for line in suffix.splitlines() if line.strip()]
    target_values = [line.strip() for line in target_suffix.splitlines() if line.strip()]
    counts = Counter(source_values)
    repeated = {value for value, count in counts.items() if count > 1}
    prefix_values = {line.strip() for line in before.splitlines() if line.strip()}
    nonnumeric = bool(repeated) and not any(re.search(r'\d', value) for value in repeated)
    confined = not bool(repeated & prefix_values)
    kept, seen, removed = [], set(), []
    for line in suffix.splitlines(keepends=True):
        value = line.strip()
        if value in repeated and value in seen:
            removed.append(dict(value_sha256=guard.inv.sha(value), retained_occurrence=1))
        else:
            kept.append(line)
        seen.add(value)
    expected_suffix = ''.join(kept).rstrip(chr(13) + chr(10))
    source_prefix, source_headers = empty_eof_appendix(before)
    target_prefix, target_headers = empty_eof_appendix(after)
    a = literal_stream(source_prefix + chr(10) * 2 + expected_suffix)
    b = literal_stream(target_prefix + chr(10) * 2 + target_suffix)
    base = literal_evaluate(original, candidate)
    guards = dict(base['guards'])
    guards.update(
        all_populated_characters_in_source_order=a == b,
        independent_typed_category_block=bool(category_markers(suffix)),
        repeated_tags_nonnumeric_and_confined=nonnumeric and confined,
        exact_first_unique_values_and_order=bool(repeated) and target_values == list(dict.fromkeys(source_values)),
        actual_terminal_body_contract=decision == 'EDIT' and original != candidate,
        question_answer_source_not_admitted_by_this_rule=not bool(re.search(r'(?im)^answers\s*:', original)),
        remaining_body_context=not context_deferrals(candidate) and not delimiter_deferrals(candidate),
        remaining_content_headings_absent=not remaining_headings(candidate),
    )
    return dict(guards=guards, eligible_narrow_literal_delta=all(guards.values()),
        comparison_basis='FIRST_IDENTICAL_NONNUMERIC_TAGS_IN_ONE_INDEPENDENT_TYPED_TERMINAL_BLOCK',
        source_populated_stream_sha256=guard.inv.sha(a), candidate_populated_stream_sha256=guard.inv.sha(b),
        source_empty_eof_appendix_headings=source_headers, candidate_empty_eof_appendix_headings=target_headers,
        removed_identical_tag_occurrences=removed, original_metadata_sha256=guard.inv.sha(suffix),
        candidate_metadata_sha256=guard.inv.sha(target_suffix),
        production_metadata_or_repeat_prove_called=False)


def run(census_path, output_path, context_path):
    guard.activate()
    census = json.loads(census_path.read_bytes())
    for name, digest in census['input_pins'].items():
        assert guard.inv.file_sha(ROOT / name) == digest, name
    from scripts import p106b_hold_resolution_policy_v32 as policy
    directory = ROOT / census['metadata_directory']
    guard.inv.verify(directory, census['metadata_manifest'])
    rows, contexts = [], []
    for row in guard.inv.cache.rows(directory, census['metadata_manifest']):
        if not row['eligible_rule_candidate']:
            continue
        guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['prior_candidate']))
        path = ROOT / row['original']['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(guard.inv.BASE)
        raw = path.read_bytes()
        original = raw.decode('utf-8')
        assert guard.inv.sha(original) == row['original']['sha256']
        proposed = policy.propose(dict(id=row['id'], text=original, complete_eos=True, valid_utf8=True))
        candidate = proposed.get('candidate', proposed['text'])
        assert proposed['decision'] == row['proposed_decision']
        assert guard.inv.sha(candidate) == row['proposed_body_sha256']
        proof = evaluate(original, candidate, proposed['decision'])
        rows.append(dict(id=row['id'], original=row['original'], occurrences=row['occurrences'],
            proposed_body_sha256=row['proposed_body_sha256'], proposed_decision=proposed['decision'], **proof))
        contexts.append(dict(id=row['id'], original=row['original'], proposed_body_sha256=row['proposed_body_sha256'],
            eligible=proof['eligible_narrow_literal_delta'],
            remaining_content_headings=remaining_headings(candidate),
            deferrals=[name for name, ok in proof['guards'].items() if not ok],
            individual_human_full_text_read_claimed=False))
    assert len(rows) == census['counts']['new_terminal_candidates']
    pins = {str(p.relative_to(ROOT)): guard.inv.file_sha(p) for p in [
        census_path, Path(__file__), guard.CONTRACT, AUDIT / 'verify_rule27_literal_delta_v1.py',
        AUDIT / 'verify_event_metadata_literal_delta_v1.py', AUDIT / 'verify_category_metadata_delta_v1.py',
        AUDIT / 'structural_delimiter_deferrals_v1.py']}
    good = [row for row in rows if row['eligible_narrow_literal_delta']]
    report = dict(status='ALL_TERMINAL_RULE32_CANDIDATES_INDEPENDENT_LITERAL_PROOF_NOT_ADMISSION',
        candidates=len(rows), verified=len(good), verified_positions=sum(row['occurrences'] for row in good),
        rows=rows, input_pins=pins, source_payload_copies=0, protected_payload_open_attempts=0,
        additional_human_full_read_credit=0, root_approved=False, cache_admitted=False,
        question_answer_candidate_deferred=True, goal_complete=False, training_authorized=False)
    context = dict(status='INDEPENDENT_TYPED_REPEAT_CONTEXT_CLOSURE_NOT_ADMISSION', rows=contexts,
        input_pins=dict(pins), root_approved=False, cache_admitted=False, goal_complete=False, training_authorized=False)
    guard.assert_no_protected_opens()
    for path, value in [(output_path, report), (context_path, context)]:
        assert not path.exists()
        guard.inv.write_json(path, value)
    print(json.dumps({k: v for k, v in report.items() if k not in {'rows', 'input_pins'}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--census', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--context', required=True)
    args = parser.parse_args()
    paths = [Path(value).resolve() for value in [args.census, args.output, args.context]]
    assert all(path.parent == AUDIT and not path.is_symlink() for path in paths)
    assert not paths[1].exists() and not paths[2].exists()
    run(*paths)
