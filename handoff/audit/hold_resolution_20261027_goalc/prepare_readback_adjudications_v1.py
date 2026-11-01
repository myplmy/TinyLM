"""Pin root-selected readback bodies and three additional nonprogram pairs."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v13 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
snapshot = AUDIT / 'authored_body_integrity_v1.json'
source_rows = {row['id']: row for row in inv.cache.read(snapshot)['records']}
evidence = AUDIT / 'ROOT_READBACK_ADJUDICATIONS_V1.md'
assignments = AUDIT / 'integrity_counter_assignments_v1.json'
decisions = []
for number in [383689, 36061, 4003, 8455, 1709, 6175, 8121, 5416]:
    key = 'expanded_train:' + str(number)
    row = source_rows[key]
    original, body = ROOT / row['source'], ROOT / row['body']
    role = {383689: 'historical_review', 36061: 'historical_review', 4003: 'context_hangul',
            8455: 'context_controls', 1709: 'context_controls', 6175: 'context_hangul',
            8121: 'legacy_review', 5416: 'legacy_review'}[number]
    reviews = [BASE / 'agents' / role / 'integrity_counter_v1/review.md']
    if number == 383689:
        body = BASE / 'agents/historical_review/integrity_counter_v1/expanded_train_383689_v2.txt'
    elif number == 4003:
        body = BASE / 'agents/context_hangul/integrity_counter_v1/expanded_train_4003_v5.txt'
        reviews.append(BASE / 'agents/context_hangul/integrity_counter_v1/review_v3.md')
    elif number == 8455:
        body = BASE / 'agents/context_hangul/strict_failure_text_repair_v1/expanded_train_8455_v3.txt'
        reviews.append(BASE / 'agents/context_hangul/strict_failure_text_repair_v1/review_v2.md')
    inv.require(inv.file_sha(original) == row['original_text_sha256'], 'readback original differs')
    raw, clean = original.read_bytes().decode('utf-8'), body.read_bytes().decode('utf-8')
    inv.require(policy.unicode_examples_preserved(raw, clean), 'readback Unicode example differs')
    decision = 'KEEP' if raw == clean else 'EDIT'
    item = dict(id=key, decision=decision, source=str(original.relative_to(ROOT)),
                original_text_sha256=inv.file_sha(original), body=str(body.relative_to(ROOT)),
                clean_text_sha256=inv.file_sha(body), root_approved=True,
                evidence=dict(path=str(evidence.relative_to(ROOT)), sha256=inv.file_sha(evidence)),
                review_inputs=[dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)) for path in reviews],
                code_guard=policy.code_preserved(raw, clean),
                semantic_style_guard=policy.semantic_style_preserved(raw, clean))
    inv.require(item['semantic_style_guard'], 'readback body loses a source style value')
    if not item['code_guard']:
        inv.require(number in {36061, 8455, 8121}, 'unreviewed code guard failure')
        item['literal_guard_case_id'] = key
    decisions.append(item)
inv.write_json(AUDIT / 'ROOT_READBACK_BODY_SELECTIONS_V1.json', dict(status='ROOT_REVIEWED_EXACT_BODY_SELECTIONS_NOT_CACHE_BUILD',
               rows=decisions, source_receipt_sha256=inv.file_sha(snapshot),
               assignment_sha256=inv.file_sha(assignments), producer_sha256=inv.file_sha(Path(__file__)),
               goal_complete=False, training_authorized=False))
exceptions = []
for row in decisions:
    if row['code_guard']:
        continue
    exceptions.append(dict(row, kind='EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR', original=row['source'],
                           required_literal_segments=['~~~~ end chapter ~~~~~'] if row['id'].endswith(':36061') else []))
inv.require(len(exceptions) == 3, 'additional literal exception scope differs')
target = AUDIT / 'LITERAL_GUARD_ADDITIONAL_APPROVALS_V1.json'
inv.write_json(target, dict(schema='P106B_EXACT_LITERAL_GUARD_APPROVALS_V1',
               status='ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS', rows=exceptions,
               global_code_guard_waiver=False, goal_complete=False, training_authorized=False))
print(json.dumps(dict(selected=len(decisions), additional_nonprogram_pairs=len(exceptions),
                      additional_registry_sha256=inv.file_sha(target)), ensure_ascii=False))
