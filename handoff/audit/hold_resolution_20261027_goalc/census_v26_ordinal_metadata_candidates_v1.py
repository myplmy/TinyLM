"""Count every new proof on v25 diagnostics, without claiming source admission."""
from collections import Counter
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_metadata_v2 as metadata

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = BASE / 'ordinal_metadata_candidate_census_v26_v1'
inv.require(not OUT.exists(), 'new ordinal census namespace required')
draft_path = BASE / 'draft_proposals_v25/complete.json'
proof_path = AUDIT / 'DRAFT_V25_EXECUTION_RECEIPT_V2.json'
draft, verified = inv.cache.read(draft_path), inv.cache.read(proof_path)
inv.require(verified['completed_artifact']['sha256'] == inv.file_sha(draft_path)
            and verified['original_process_exit_code'] == 0, 'actual verified full25 required')
production_pins = dict(draft['lineage']['source_code_sha256'])
for name in ['scripts/p106b_hold_resolution_metadata_v2.py', 'scripts/p106b_hold_resolution_policy_v26.py']:
    production_pins[name] = inv.file_sha(ROOT / name)
for name, expected in production_pins.items():
    inv.require(inv.file_sha(ROOT / name) == expected, 'ordinal proof production source changed')
inv.verify(draft_path.parent / 'unique', draft['unique_manifest'])
writer = inv.ShardWriter(OUT / 'matches', 'matches', limit=19_999_999)
counts, reasons, category_values, languages = (Counter() for _ in range(4))
started = time.monotonic()
for row in inv.cache.rows(draft_path.parent / 'unique', draft['unique_manifest']):
    if row['decision'] != 'PENDING':
        continue
    counts.update(unique_pending=1, occurrences=row['occurrences'])
    if any('PRIOR_INDIVIDUAL_OR_SPAN' in reason for reason in row['reasons']):
        counts.update(individual_metadata_only=1)
        continue
    if 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' not in row['reasons']:
        counts.update(other_risk_metadata_only=1)
        continue
    body = row.get('diagnostic_candidate')
    if not isinstance(body, str) or not body.strip():
        counts.update(no_diagnostic_metadata_only=1)
        continue
    counts.update(appendix_diagnostic_candidates_checked=1)
    value = metadata.prove(body)
    if value is None:
        continue
    counts.update(proof_matches=1, matched_occurrences=row['occurrences'])
    reasons.update(row['reasons'])
    languages.update([row['language_bucket']])
    category_values.update(value['proof']['dotted_category_values'])
    other = sorted(set(row['reasons']) - {'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT'})
    if not other:
        counts.update(diagnostic_only_boundary_risk_matches=1,
                      diagnostic_only_boundary_risk_occurrences=row['occurrences'])
    record = {k: row[k] for k in ['id', 'original_text_sha256', 'source', 'split', 'source_ids',
               'source_ids_sha256', 'input_ids', 'language_bucket', 'occurrences']}
    writer.append(dict(record, prior_reasons=row['reasons'], diagnostic_sha256=inv.sha(body),
        proof=value['proof'], proposed_footer_changes=value['changes'], other_original_risks=other,
        raw_original_not_redecoded=True, diagnostic_proof_is_not_cache_admission=True))
inv.require(counts['unique_pending'] == 77665 and counts['occurrences'] == 122585, 'whole pending conservation differs')
inv.require(sum(counts[k] for k in ['individual_metadata_only', 'other_risk_metadata_only',
            'no_diagnostic_metadata_only', 'appendix_diagnostic_candidates_checked']) == 77665,
            'unexplained ordinal census omission')
inv.require(counts['proof_matches'] >= 2, 'two observed ordinal counter sources were not reproduced')
for name, expected in production_pins.items():
    inv.require(inv.file_sha(ROOT / name) == expected, 'proof code changed during census')
result = dict(status='ALL_V25_PENDING_TYPED_ORDINAL_PROOFS_CENSUSED_NOT_ADMISSION', counts=dict(counts),
    matched_source_reasons=dict(reasons), language_character_presence_buckets=dict(languages),
    actual_dotted_category_values=dict(category_values), matches_manifest=writer.close(lineage=production_pins),
    production_source_pins=production_pins,
    input_pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in [draft_path, proof_path, Path(__file__)]},
    original_streams_opened=False, current_cache_changed=False, root_adopted=0,
    seconds=time.monotonic() - started, goal_complete=False, training_authorized=False)
inv.write_json(OUT / 'complete.json', result)
print(json.dumps({k: result[k] for k in ['status', 'counts', 'actual_dotted_category_values', 'seconds']}, ensure_ascii=False))
