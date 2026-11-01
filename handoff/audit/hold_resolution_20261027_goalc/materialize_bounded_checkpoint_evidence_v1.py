"""Freeze exact follow-up edits and the remaining limitations for local save."""
from pathlib import Path
from collections import Counter
import datetime
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()
def pin(path):
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=sha(path))
def load(name):
    return json.loads((AUDIT / name).read_text(encoding='utf-8'))
snapshot = load('supplemental_candidates_snapshot_v46.json')
plan = load('reviewed_selection_plan_v23.json')
audit = load('fresh_author_body_literals_v2.json')
checks = load('BOUNDED_CHECKPOINT_CHECKS_V1.json')
groups = {'root_selected_lexical_counter_v1':579, 'ordinal_metadata_counter_v26_v1':27,
          'profile_strata_source_counter_v25_v1':237}
for group, count in groups.items():
    assert snapshot['coverage'][group]['saved'] == count
    assert snapshot['coverage'][group]['awaiting_review'] == 0
assert not [r for r in snapshot['errors'] if r.get('group') in groups]
assert audit['counts']['bodies'] == 843 and not audit['errors']
assert checks['all_exit_zero'] and len(checks['tests']) == 7
test_count = sum(int(number) for row in checks['tests'] for number in
    re.findall(r'(?m)^Ran ([0-9]+) tests?', (ROOT / row['log']).read_text(encoding='utf-8')))
assert test_count == 495
authors = BASE / 'agents'
records = []
for ident, role, previous_version, hold_name, review_name in [
    ('47062', 'context_controls', 'v3', 'expanded_train_47062_v4_hold.md', 'review_009_v3.md'),
    ('119838', 'context_hangul', 'v2', 'expanded_train_119838_v4_hold.md', 'review_006_v3.md')
]:
    directory = authors / role / 'root_selected_lexical_counter_v1'
    previous = directory / ('expanded_train_' + ident + '_' + previous_version + '.txt')
    final = directory / ('expanded_train_' + ident + '_v4.txt')
    hold, review = directory / hold_name, directory / review_name
    row = [r for r in snapshot['records'] if r['cohort'] == 'root_selected_lexical_counter_v1'
           and r['id'] == 'expanded_train:' + ident]
    assert len(row) == 1
    row = row[0]
    original = ROOT / row['original']['path']
    assert sha(original) == row['original']['sha256']
    assert sha(final) == row['clean_text_sha256'] == row['author_output']['sha256']
    assert sha(review) == row['review']['sha256']
    before, after = previous.read_text(encoding='utf-8'), final.read_text(encoding='utf-8')
    if ident == '47062':
        old = '세상을 떠났다. 전국투어 개최하였다.'
        new = '세상을 떠남으로써 잠정적으로 밴드 활동 상황이 불투명해졌다. 전국투어를 개최하였다.'
        assert before.count(old) == 1
        assert before.replace(old, new) + chr(10) == after
        assert '세상을 떠남으로써 잠정적으로 밴드 활동 상황이 불투명해졌다가,' in original.read_text(encoding='utf-8')
        proof = dict(exact_local_clause_restored=True, particle_only_repaired=True,
                     final_LF_added=True, scheduled_release_not_actual_release=True)
    else:
        removals = {' 2008년 3월 26일 : ', ' 2001년 10월', ' 2006년 : China', '해외 음반 '}
        removed = [line for line in before.splitlines(keepends=True) if line.rstrip(chr(10)) in removals]
        assert len(removed) == 5
        assert after == ''.join(line for line in before.splitlines(keepends=True)
                                if line.rstrip(chr(10)) not in removals)
        assert '2008년 3월 26일 :  (2DVD)' in after
        proof = dict(exact_unbound_record_lines_removed=4, newly_empty_parent_heading_removed=1,
            separate_DVD_date_and_type_kept=True, duplicates_not_merged=True,
            original_records_preserved_in_pinned_hold=True)
    diff = chr(10).join(difflib.unified_diff(before.splitlines(), after.splitlines()))
    records.append(dict(id='expanded_train:' + ident, original=pin(original), previous=pin(previous),
        body=pin(final), hold=pin(hold), review=pin(review), proof=proof,
        complete_diff_sha256=hashlib.sha256(diff.encode()).hexdigest().upper(),
        current_edit_scope_reviewed=True, entire_body_semantic_approval=False, cache_admitted=False))
input_paths = [AUDIT / name for name in ['supplemental_candidates_snapshot_v46.json',
    'reviewed_selection_plan_v23.json', 'fresh_author_body_literals_v2.json',
    'BOUNDED_CHECKPOINT_CHECKS_V1.json', 'BOUNDED_CHECKPOINT_PROCESS_EXITS_V1.json',
    'LOCAL_SOURCE_DISCOVERY_REPORT_V1.md', 'V26_PENDING_REASON_GROUP_CENSUS_V1.json']]
flags = [{k:r.get(k) for k in ['id','cohort','body','clean_text_sha256','review','code_guard',
    'unicode_guard','semantic_style_guard','source_function_parentheses_losses']} for r in audit['records']
    if not r.get('unicode_guard') or not (r.get('code_guard') or r.get('exact_reviewed_literal_exception'))
    or not r.get('semantic_style_guard') or r.get('source_function_parentheses_losses')]
result = dict(status='TWO_FOLLOWUPS_AND_CURRENT_REVIEW_BATCH_SAVED_NOT_GOAL_COMPLETION',
    observed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
    user_direction='진행중이던 보조작업 2개 및 작업중이던 내용까지만 수행하고, 현재까지 수행한 작업 적절한 한국어 로컬 커밋메시지와 함께 저장.',
    rows=records, coverage={k:snapshot['coverage'][k] for k in groups},
    current_cohort_errors=0, historical_errors_preserved=len(snapshot['errors']),
    selection_plan_source_ids=plan['source_ids'], selection_plan_proposals=plan['proposal_records'],
    body_audit_counts=audit['counts'], body_audit_errors=0, remaining_guard_diagnostics=flags,
    tests_passed=test_count, test_processes=7, production_pins_unchanged=66,
    earlier_syntax_files_checked=len(checks['syntax_files']), input_pins=[pin(p) for p in input_paths],
    goal_status='paused', goal_resumed=False, goal_complete=False,
    final_cache_created=False, cache_admitted=0, training_authorized=False)
target = AUDIT / 'BOUNDED_CHECKPOINT_EVIDENCE_V1.json'
assert not target.exists()
payload = json.dumps(result, ensure_ascii=False, indent=2) + chr(10)
assert len(payload.encode()) < 20_000_000
with target.open('x', encoding='utf-8') as stream:
    stream.write(payload)
print(json.dumps(dict(followups=len(records), saved_bodies=843, current_cohort_errors=0,
    source_ids=plan['source_ids'], tests_passed=test_count, guard_diagnostic_cases=len(flags)),ensure_ascii=False))
