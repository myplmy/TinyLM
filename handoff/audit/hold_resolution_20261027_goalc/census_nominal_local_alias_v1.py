"""Try a narrow lead proof on every remaining field source, without admission."""
from collections import Counter, defaultdict
from pathlib import Path
import importlib.util
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy

helper_path = AUDIT / 'typed_nominal_local_alias_v1.py'
spec = importlib.util.spec_from_file_location('nominal_alias', helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
SOURCE = inv.BASE / 'draft_proposals_v26_delta_v1'
OUT = inv.BASE / 'nominal_local_alias_candidates_v1'
inv.require(not OUT.exists(), 'new immutable local-alias census required')
source_report = SOURCE / 'complete.json'
report = inv.cache.read(source_report)
inv.verify(SOURCE / 'unique', report['unique_manifest'])
for name, digest in report['lineage']['source_code_sha256'].items():
    inv.require(inv.file_sha(ROOT / name) == digest, 'frozen production code changed')
restricted = {'expanded_train:' + str(n) for n in [14760,756966,15695,1216576,1250821,20624,6030]}
counts, roles, reasons = Counter(), Counter(), Counter()
examples = defaultdict(list)
writer = inv.ShardWriter(OUT / 'rows', 'proofs', limit=19_999_999)
started = time.monotonic()
for row in inv.cache.rows(SOURCE / 'unique', report['unique_manifest']):
    if row['decision'] != 'PENDING' or 'UNRESOLVED_FIELD_OR_TITLE' not in row['reasons']:
        continue
    counts.update(field_sources=1, field_occurrences=row['occurrences'])
    if row['id'] in restricted:
        counts['restricted_metadata_only'] += 1
        continue
    candidate = row.get('diagnostic_candidate', '')
    proof = helper.prove(candidate)
    if proof is None:
        continue
    remaining = set(row['reasons']) - {'UNRESOLVED_FIELD_OR_TITLE'}
    remaining.update(policy.literal_holes(proof['candidate']))
    counts.update(proof_matches=1, matched_occurrences=row['occurrences'])
    if not remaining:
        counts.update(no_remaining_literal_reason=1, no_remaining_literal_reason_occurrences=row['occurrences'])
    roles.update([proof['role']])
    reasons.update(remaining)
    if len(examples[proof['role']]) < 4:
        examples[proof['role']].append(dict(id=row['id'], input_ids=row['input_ids'],
            source_characters=len(candidate), subject=proof['subject'],
            lead_preview=candidate.split('\n\n', 1)[0][:500], remaining_reasons=sorted(remaining)))
    writer.append(dict({key:row[key] for key in ['id','source','split','source_ids','source_ids_sha256',
        'original_text_sha256','input_ids','occurrences','language_bucket']},
        v26_candidate_sha256=inv.sha(candidate), previous_reasons=row['reasons'],
        proof=proof, remaining_reasons=sorted(remaining), root_approved=False, cache_admitted=False))
inv.require(counts['field_sources'] == 19123, 'all19123 field sources must be evaluated')
pins = {str(path.relative_to(ROOT)):inv.file_sha(path) for path in [source_report, helper_path,
    AUDIT/'TYPED_NOMINAL_LOCAL_ALIAS_SCOPE_V1.md', Path(__file__)]}
manifest = writer.close(lineage=pins)
result = dict(status='ALL19123_FIELD_SOURCES_TRIED_NARROW_ALIAS_PROOFS_NOT_ADMISSION',
    counts=dict(counts), roles=dict(roles), remaining_reasons=dict(reasons), examples=dict(examples),
    rows=manifest, input_pins=pins, source_code_pins=report['lineage']['source_code_sha256'],
    native_sources_freshly_decoded=False, cache_admitted=0, goal_complete=False, training_authorized=False,
    seconds=time.monotonic()-started)
inv.write_json(OUT/'complete.json', result)
print(json.dumps({key:result[key] for key in ['status','counts','roles','remaining_reasons','seconds']},ensure_ascii=False))
