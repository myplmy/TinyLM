"""Join verified drafts and every actual partial-cache ledger position.

No decoding, text repair, cache admission or outcome promotion occurs here.
Exact raw-source matches to already admitted baseline bodies are diagnostics.
Diagnostic-candidate matches alone cannot justify deduplication.
"""
from collections import Counter, defaultdict
from itertools import zip_longest
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / 'verified_v21_v25_actual_cache_comparison_v1'
inv.require(not OUT.exists(), 'new comparison namespace required')
started = time.monotonic()
drafts = {}
pins = {}
for version, receipt_name in [(21, 'DRAFT_V21_EXECUTION_RECEIPT_V1.json'),
                               (25, 'DRAFT_V25_EXECUTION_RECEIPT_V2.json')]:
    path = BASE / ('draft_proposals_v' + str(version)) / 'complete.json'
    receipt_path = AUDIT / receipt_name
    report, proof = inv.cache.read(path), inv.cache.read(receipt_path)
    inv.require(proof['completed_artifact']['sha256'] == inv.file_sha(path)
                and proof['original_process_exit_code'] == 0, 'verified draft linkage differs')
    inv.verify(path.parent / 'unique', report['unique_manifest'])
    drafts[version] = path, report
    pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
    pins[str(receipt_path.relative_to(ROOT))] = inv.file_sha(receipt_path)
pins[str(Path(__file__).relative_to(ROOT))] = inv.file_sha(Path(__file__))
changes = inv.ShardWriter(OUT / 'draft_changes', 'changes', limit=19_999_999)
rechecks = inv.ShardWriter(OUT / 'actual_admission_rechecks', 'rechecks', limit=19_999_999)
matches = inv.ShardWriter(OUT / 'baseline_exact_matches', 'matches', limit=19_999_999)
transitions, weighted, counts = Counter(), Counter(), Counter()
current, pending_by_raw, pending_by_candidate = {}, {}, defaultdict(list)
source_fields = ['id', 'original_text_sha256', 'source', 'split', 'source_ids',
                 'source_ids_sha256', 'input_ids', 'language_bucket', 'occurrences']
sentinel = object()
streams = [inv.cache.rows(drafts[v][0].parent / 'unique', drafts[v][1]['unique_manifest']) for v in (21, 25)]
for old, new in zip_longest(*streams, fillvalue=sentinel):
    inv.require(old is not sentinel and new is not sentinel, 'draft rows lost or added')
    inv.require(all(old[k] == new[k] for k in source_fields), 'draft source identity changed')
    key = new['original_text_sha256']
    inv.require(key not in current, 'unique original repeats')
    metadata = {k: new[k] for k in source_fields}
    current[key] = dict(metadata, decision=new['decision'], reasons=new['reasons'],
                        clean_text_sha256=new.get('clean_text_sha256'))
    transition = old['decision'] + '->' + new['decision']
    transitions[transition] += 1
    weighted[transition] += new['occurrences']
    counts['unique_sources_checked'] += 1
    counts['original_positions_checked'] += new['occurrences']
    if old['decision'] != new['decision'] or old.get('clean_text_sha256') != new.get('clean_text_sha256'):
        changes.append(dict(metadata, before=dict(decision=old['decision'], reasons=old['reasons'],
            clean_text_sha256=old.get('clean_text_sha256')), after=current[key], cache_admitted=False))
        counts['changed_unique_decision_or_terminal_body'] += 1
    if new['decision'] == 'PENDING':
        pending_by_raw[key] = current[key]
        body = new.get('diagnostic_candidate')
        if isinstance(body, str) and body.strip() and not any('PRIOR_INDIVIDUAL_OR_SPAN' in r for r in new['reasons']):
            pending_by_candidate[inv.sha(body)].append(key)
inv.require(counts['unique_sources_checked'] == 297539 and counts['original_positions_checked'] == 460695,
            'full draft comparison scope differs')

built_path = BASE / 'cache_partial_v1/built.json'
partial_proof_path = BASE / 'cache_partial_v1/partial_resolution_verified.json'
old_rechecks_path = AUDIT / 'PARTIAL_V1_ACTUAL_ADMISSION_RECHECKS_V1.json'
built, partial_proof, old_rechecks = [inv.cache.read(p) for p in [built_path, partial_proof_path, old_rechecks_path]]
inv.require(partial_proof['status'] == 'CPU_PARTIAL_RECOVERY_CACHE_VERIFIED_GOAL_INCOMPLETE',
            'actual partial cache verification is absent')
inv.require(old_rechecks['input_pins'][str(built_path.relative_to(ROOT))] == inv.file_sha(built_path),
            'actual old admission verification refers to a different cache')
for path in [built_path, partial_proof_path, old_rechecks_path]:
    pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
old_review_ids = {r['id'] for r in old_rechecks['rows']}
new_review_ids, raw_matched_keys, candidate_matched_keys = set(), set(), set()
ledger = built['manifests']['ledger']
concatenated = hashlib.sha256()
actual_outcomes, actual_residual_outcomes = Counter(), Counter()
for shard in ledger['shards']:
    path = built_path.parent / 'ledger' / shard['path']
    digest, size, rows = hashlib.sha256(), 0, 0
    with path.open('rb') as stream:
        for payload in stream:
            digest.update(payload)
            concatenated.update(payload)
            size += len(payload)
            rows += 1
            row = json.loads(payload)
            counts['actual_ledger_positions_checked'] += 1
            actual_outcomes[row['decision']] += 1
            if row['parent_decision'] != 'HOLD':
                if row['decision'] in {'KEEP', 'EDIT'}:
                    counts['baseline_admitted_positions_preserved'] += 1
                    body_sha = row['clean_text_sha256']
                    raw_match = pending_by_raw.get(body_sha)
                    candidate_keys = pending_by_candidate.get(body_sha, [])
                    if raw_match or candidate_keys:
                        matches.append(dict(baseline=dict(id=row['id'], decision=row['decision'], split=row['split'],
                            clean_text_sha256=body_sha),
                            exact_raw_source_match=raw_match,
                            diagnostic_candidate_only_source_keys=candidate_keys,
                            candidate_match_alone_does_not_justify_deduplication=True,
                            root_approved=False, cache_admitted=False))
                        if raw_match:
                            raw_matched_keys.add(body_sha)
                        candidate_matched_keys.update(candidate_keys)
                continue
            key = row['original_text_sha256']
            inv.require(key in current, 'actual original-HOLD source is outside the verified draft')
            actual_residual_outcomes[row['decision']] += 1
            if row['decision'] not in {'KEEP', 'EDIT'}:
                continue
            counts['actual_residual_admitted_positions_checked'] += 1
            later = current[key]
            status = ('LATER_CONSERVATIVE_PENDING_REQUIRES_REVIEW' if later['decision'] == 'PENDING'
                      else 'LATER_TERMINAL_BODY_DIFFERS_REQUIRES_REVIEW'
                      if later['decision'] in {'KEEP', 'EDIT'} and later['clean_text_sha256'] != row['clean_text_sha256']
                      else 'LATER_EXCLUSION_REQUIRES_REVIEW' if later['decision'] == 'EXCLUDE' else None)
            if status is None:
                counts['actual_residual_admitted_positions_same_verified_terminal_body'] += 1
                continue
            new_review_ids.add(row['id'])
            counts['actual_admitted_positions_requiring_fresh_review'] += 1
            counts[status] += 1
            counts['review_' + row['split']] += 1
            rechecks.append(dict(id=row['id'], original_text_sha256=key, split=row['split'], source_ids=row['source_ids'],
                actual_body_sha256=row['clean_text_sha256'], actual_decision=row['decision'], later=later,
                conservative_recheck_status=status, confirmed_defect=False, cache_changed=False))
    inv.require(size == shard['bytes'] and rows == shard['rows'] and digest.hexdigest().upper() == shard['sha256'],
                'actual partial ledger shard integrity differs')
inv.require(concatenated.hexdigest().upper() == ledger['concat_sha256'], 'actual ledger concat differs')
inv.require(counts['actual_ledger_positions_checked'] == 2154912
            and sum(actual_residual_outcomes.values()) == 460695,
            'actual cache scope differs')
inv.require(dict(actual_outcomes) == {k: built['counts'][k] for k in actual_outcomes}, 'actual ledger outcome counts differ')
inv.require(dict(actual_residual_outcomes) == partial_proof['outcomes'], 'actual residual outcome counts differ')
inv.require(counts['baseline_admitted_positions_preserved'] == 1145290
            and counts['actual_residual_admitted_positions_checked'] == 196115,
            'baseline/newly admitted scope differs')
counts['pending_exact_raw_source_matches_to_baseline'] = len(raw_matched_keys)
counts['pending_diagnostic_candidate_matches_to_baseline_not_dedup_proof'] = len(candidate_matched_keys)
counts['prior3421_positions_still_requiring_review'] = len(new_review_ids & old_review_ids)
counts['new_positions_requiring_review_beyond_prior3421'] = len(new_review_ids - old_review_ids)
counts['prior3421_positions_no_longer_flagged_by25_not_semantic_approval'] = len(old_review_ids - new_review_ids)
for path, digest in pins.items():
    inv.require(inv.file_sha(ROOT / path) == digest, 'comparison input changed')
result = dict(status='VERIFIED_DRAFT_AND_ACTUAL_LEDGER_COMPARISON_NOT_ADMISSION',
    counts=dict(counts), unique_transitions=dict(transitions), occurrence_transitions=dict(weighted),
    draft_change_manifest=changes.close(lineage=pins), actual_recheck_manifest=rechecks.close(lineage=pins),
    baseline_match_manifest=matches.close(lineage=pins),
    actual_residual_outcomes=dict(actual_residual_outcomes), actual_whole_outcomes=dict(actual_outcomes),
    input_pins=pins, original_streams_opened=False, existing_cache_changed=False,
    confirmed_defects_are_not_inferred_from_pending=True, root_adopted=0,
    seconds=time.monotonic() - started, goal_complete=False, training_authorized=False)
inv.write_json(OUT / 'complete.json', result)
print(json.dumps({k: result[k] for k in ['status', 'counts', 'unique_transitions', 'occurrence_transitions', 'seconds']}, ensure_ascii=False))
