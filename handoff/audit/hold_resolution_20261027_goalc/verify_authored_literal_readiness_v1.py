"""Fresh all-row preservation proofs and conservative context deferrals; no copies."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from authored_literal_readiness_v1 import deferrals
from verify_rule27_literal_delta_v1 import evaluate

guard.activate()
pins = {}
candidate_path = AUDIT/'AUTHORED_LITERAL_PRESERVATION_CANDIDATES_V1.json'
raw = candidate_path.read_bytes()
pins[str(candidate_path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest().upper()
candidates = json.loads(raw)
explicit_context_deferrals = {
    'expanded_train:7386': 'ROOT_OBSERVED_UNFINISHED_PROSE',
    'expanded_train:1395057': 'ROOT_OBSERVED_QUOTE_BOUNDARY',
    'expanded_train:137822': 'ROOT_OBSERVED_UNCLEAR_AFFILIATION',
    'expanded_train:17463': 'ROOT_OBSERVED_UNBOUND_INLINE_CITATION_MARKERS',
}
started = time.monotonic()
checks, deferred = [], []
counts = Counter()
for row in candidates['rows']:
    guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['body']))
    values = []
    for name in ['original', 'body']:
        path = ROOT/row[name]['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc')
        value = path.read_bytes()
        assert hashlib.sha256(value).hexdigest().upper() == row[name]['sha256']
        values.append(value.decode('utf-8'))
    proof = evaluate(*values)
    assert proof['eligible_narrow_literal_delta'] and all(proof['guards'].values())
    reasons = deferrals(values[1])
    if row['id'] in explicit_context_deferrals:
        reasons.append(explicit_context_deferrals[row['id']])
    for review in row['all_saved_reviews']:
        path = ROOT/review['path']
        assert not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest().upper() == review['sha256']
    if reasons:
        deferred.append(dict(id=row['id'], original_text_sha256=row['original_text_sha256'],
            body=row['body'], occurrences=row['occurrences'], reasons=reasons))
        counts.update(set(reasons))
        continue
    assert row['full_source_read_by_primary_author_claimed'] is True
    checks.append(dict(row, fresh_preservation_proof=proof,
        additional_readiness_guards=dict(no_native_gap=True, no_unfinished_prose_flag=True,
            balanced_curly_double_quotes=True, no_retail_fields=True,
            no_ambiguous_affiliation_flag=True, no_ROOT_explicit_context_deferral=True)))
guard.assert_no_protected_opens()
for path in [Path(__file__), AUDIT/'authored_literal_readiness_v1.py',
        AUDIT/'AUTHORED_LITERAL_ROOT_CONTEXT_AUDIT_V1.md',
        AUDIT/'AUTHORED_LITERAL_READINESS_TESTS_V2.log',
        AUDIT/'active_guard_v6_preflight_v1.py', guard.CONTRACT,
        AUDIT/'verify_rule27_literal_delta_v1.py']:
    pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
result = dict(status='AUTHORED_ALL_ROW_LITERAL_AND_READINESS_VERIFIED_PENDING_ROOT_SELECTION',
    candidates=len(candidates['rows']), verified=len(checks), verified_positions=sum(r['occurrences'] for r in checks),
    deferred=len(deferred), deferral_reason_counts=dict(counts), checks=checks, deferred_rows=deferred,
    input_pins=pins, cumulative_guard_sha256=guard.EXPECTED,
    elapsed_seconds=time.monotonic()-started, protected_payload_open_attempts=0,
    corpus_payload_copies_written=0, root_approved=False, cache_admitted=False,
    goal_complete=False, training_authorized=False)
out = AUDIT/'AUTHORED_LITERAL_READINESS_INDEPENDENT_VERIFIED_V1.json'
payload = (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
assert len(payload) < 20_000_000 and not out.exists()
with out.open('xb') as stream:
    stream.write(payload)
print(json.dumps({k:result[k] for k in ['status','candidates','verified','verified_positions',
    'deferred','deferral_reason_counts','elapsed_seconds','corpus_payload_copies_written']},ensure_ascii=False))
