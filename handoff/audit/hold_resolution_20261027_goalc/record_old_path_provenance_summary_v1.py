"""Summarise exact links and their limits; never treat links as quality passes."""
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
path = AUDIT / 'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V2.json'
data = json.loads(path.read_bytes())
assert data['additional_exact_saved_review_links'] == 92
assert data['flags_without_a_link_in_these_audited_scopes'] == 200
runtime = {r['id']:r for r in json.loads((BASE / 'runtime_guard_counter_v1/manifest.json').read_bytes())['rows']}
limitations = []
for row in data['rows']:
    if row['status'] == 'EXISTING_BINDING_REQUIRES_FURTHER_AUDIT':
        source = runtime[row['id']]
        previous = source['review']
        assert '/runtime_guard_counter_v1/decision_notes/' in previous['path']
        limitations.append(dict(id=row['id'], declared_previous_role=source['previous_role'],
            previous_review_pointer=previous,
            reason='Previous-review pointer identifies a root decision note, not the previous author review path. '
                   'This audit does not prove that older author chain and leaves the link unresolved.'))
assert len(limitations) == 5
linked = [r for r in data['rows'] if r['status'].startswith('EXACT_CURRENT_BODY')]
result = dict(status='SAVED_OLD_REVIEW_LINKS_WITH_EXPLICIT_LIMITS_NOT_SEMANTIC_APPROVAL',
    audited_metadata=dict(ordered_flags=585, prior_three_scope_links=293,
                          remaining_path_records_examined=292, additional_exact_links=92,
                          union_of_audited_record_scopes=385, no_link_in_these_scopes=200),
    new_links_by_cohort=dict(Counter(r['selected_cohort'] for r in linked)),
    independent_input_equals_current_flagged_body=sum(r['input_equals_current_body'] for r in linked),
    independent_result_changed_from_input=sum(not r['input_equals_current_body'] for r in linked),
    unresolved_categories=dict(distinct_ownership_not_proven=165, no_canonical_cohort_manifest_here=29,
                               root_note_not_previous_author_review=5, restricted_metadata_only=1),
    unresolved_runtime_note_pointers=limitations,
    restricted_source_ids=[r['id'] for r in data['rows'] if r['status']=='RESTRICTED_METADATA_ONLY_NOT_OPENED'],
    tests=dict(tool_chunk='ebb140',passed=5,failed=0,actual_exit_code=0,
               command='python -I -B handoff/audit/hold_resolution_20261027_goalc/test_exact_manifest_review_row_binding_v1.py -v'),
    full_audit=dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),bytes=path.stat().st_size),
    root11_directly_pinned_current_manifest_for_new_links=0,
    old_manifest_ownership_chains_independently_proven=False,
    historical_input_delivery_proven=False, new_original_text_semantic_reads=0,
    additional_semantic_or_quality_passes=0, automatic_flag_waivers=0,
    source_body_rewrites=0, protected_body_reads=0, cache_admitted=0, goal_complete=False,
    meaning='92 exact source/body/review/role-assignment links were recovered. '
            'Current manifest metadata is pinned by this audit, not falsely claimed as a root11 direct pin. '
            'Remaining records may have other valid evidence; duplicate full readings are not automatically scheduled.')
target=AUDIT/'ORDERED_FLAG_EXISTING_REVIEW_REUSE_SUMMARY_V1.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(dict(links=92,union=385,not_linked_in_these_scopes=200,semantic_passes=0),ensure_ascii=False))
