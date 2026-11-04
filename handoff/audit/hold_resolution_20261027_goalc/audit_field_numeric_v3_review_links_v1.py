"""Join exact V3 numeric targets to existing source/body-bound review evidence."""
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
A = Path(__file__).resolve().parent
pins = {}

def read(path, expected=None):
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest().upper()
    assert expected is None or sha == expected, str(path)
    pins[str(path.relative_to(ROOT))] = sha
    return json.loads(raw)

guard = read(A / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json',
             'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF')
diagnostic = read(A / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V3.json',
                  '038D54BAE21991ED621120D267975C31870B680D345F1AF2868CDA4A8DB53C82')
proofs = read(A / 'FIELD_BOUND_NUMERIC_LOCAL_PROOFS_V1.json')
contexts = read(A / 'FIELD_NUMERIC_V1_CONTEXT_DISPOSITIONS_V1.json')
old_proofs = {row['id']: row for row in proofs['rows']}
old_contexts = {row['id']: row for row in contexts['records']}

def flag_key(flag):
    return json.dumps(flag, sort_keys=True, ensure_ascii=False)

extra = {}
for number in range(13, 17):
    name = f'FIELD_NUMERIC_CONTEXT_BATCH{number:03}_ADJUDICATIONS_V1.json'
    batch = read(A / name)
    for row in batch['records']:
        body = row.get('body', row.get('current_body', row.get('diagnostic_V3_body')))
        flags = row.get('numeric_flags', row.get('current_numeric_flags'))
        assert body and flags is not None, (name, row['id'])
        assert row['id'] not in guard['restricted_ids']
        assert row['original']['sha256'] not in guard['restricted_hashes']
        decision = row.get('decision', row.get('status'))
        # Only finished manual judgments are links. Pending removal is a disposition,
        # not evidence that an old body is suitable for admission.
        allowed = {'NUMERIC_CONTEXT_REVIEWED',
                   'THREE_FLAGGED_ZEROS_PARTIAL_HOLD_ONE_BIBLIOGRAPHY_ATOM_RETAINED'}
        if decision in allowed:
            for flag in flags:
                key = (row['id'], row['original']['sha256'], body['sha256'], flag_key(flag))
                extra.setdefault(key, []).append(dict(path=str((A / name).relative_to(ROOT)),
                                                       decision=decision))

rows = []
status_counts = Counter()
for shard in diagnostic['shards']:
    value = read(ROOT / shard['path'], shard['sha256'])
    records = value if isinstance(value, list) else value.get('rows', value.get('records'))
    for row in records:
        flags = row['numeric_atom_flags']
        if not flags:
            continue
        identity = row['id']
        assert identity not in guard['restricted_ids']
        assert row['original']['sha256'] not in guard['restricted_hashes']
        prior = old_proofs.get(identity)
        context = old_contexts.get(identity)
        exact_old_pair = bool(prior and context and
                              prior['original'] == row['original'] and
                              prior['body']['sha256'] == row['body']['sha256'] and
                              context['V1_body_sha256'] == row['body']['sha256'])
        targets = {flag_key(item['flag']): item for item in prior['proofs']} if exact_old_pair else {}
        decisions = []
        for flag in flags:
            key = flag_key(flag)
            proof = targets.get(key)
            status, evidence = 'UNLINKED_REQUIRES_EXACT_CONTEXT_OR_BODY_BRIDGE', []
            if proof and proof['status'] == 'EXACT_LOCAL_ATOM_AND_UNIT':
                status = 'EXACT_V1_LOCAL_ATOM_PROOF_REUSED_NOT_MANUAL_CONTEXT'
                evidence = ['handoff/audit/hold_resolution_20261027_goalc/FIELD_BOUND_NUMERIC_LOCAL_PROOFS_V1.json']
            elif proof and proof['status'] == 'MANUAL_CONTEXT_REQUIRED':
                dispositions = context['manual_dispositions']
                if set(dispositions) <= {'CONTEXT_RETAINED'} and sum(dispositions.values()) == context['manual_flags']:
                    status = 'EXACT_V1_BODY_AND_TARGET_MANUAL_CONTEXT_REUSED'
                    evidence = [context['context_receipt']]
            extra_key = (identity, row['original']['sha256'], row['body']['sha256'], key)
            if status.startswith('UNLINKED') and extra_key in extra:
                status = 'EXACT_ADDITIONAL_BATCH_BODY_AND_TARGET_LINKED'
                evidence = extra[extra_key]
            status_counts[status] += 1
            decisions.append(dict(flag=flag, status=status, evidence=evidence))
        rows.append(dict(id=identity, original=row['original'], body=row['body'],
                         review=row['review'], targets=decisions))
assert len(rows) == 87 and sum(len(row['targets']) for row in rows) == 441
assert sum(status_counts.values()) == 441
pending = [dict(id=row['id'], targets=sum(item['status'].startswith('UNLINKED') for item in row['targets']))
           for row in rows if any(item['status'].startswith('UNLINKED') for item in row['targets'])]
result = dict(status='V3_NUMERIC_REVIEW_LINK_AUDIT_NOT_ADMISSION', rows=rows,
              documents=87, targets=441, statuses=dict(status_counts), pending=pending,
              source_body_payload_reads=0, input_pins=pins, generic_guards_changed=False,
              exact_body_and_flag_identity_required=True, source_wide_semantic_or_fact_pass=False,
              V3_is_older_than_latest_selected_followup_bodies=True,
              new_root_or_cache_admissions=0, whole_goal_complete=False, training_authorized=False)
target = A / 'FIELD_NUMERIC_V3_REVIEW_LINKS_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(path=str(target.relative_to(ROOT)), documents=87, targets=441,
                     statuses=dict(status_counts), pending=pending,
                     bytes=target.stat().st_size), ensure_ascii=False))
