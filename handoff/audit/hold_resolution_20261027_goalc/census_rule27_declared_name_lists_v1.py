"""Audit the current remaining queues for a narrow, metadata-only v27 delta.

Original bytes are verified once; nonmatching source bodies are never copied.
No original/candidate TXT or accepted cache is written by this census.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from selection_metadata_store_v1 import SelectionStore
from numeric_atom_integrity_v1 import numeric_atom_changes
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v27 as policy

activate()
guard = checked_contract()
blocked_ids = set(guard['restricted_ids']) | set(guard['trusted_metadata'])
blocked_hashes = set(guard['restricted_hashes'])
pins = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def read_metadata(path, expected=None):
    raw = path.read_bytes()
    actual = sha(raw)
    assert expected is None or actual == expected, str(path)
    pins[str(path.relative_to(ROOT))] = actual
    return json.loads(raw)


started = time.monotonic()
opaque = read_metadata(AUDIT/'OPAQUE_UNADOPTED_HOLD_ROOT32_ROSTER23_V1.json',
    '87EB0550B9F11BC3EC4E6CBF6B75673A8785633B0522762F7E4277849292EFEF')
hold_hashes = set(opaque['hold_hashes'])
selection_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V32.json'
selection = SelectionStore(AUDIT).read(selection_path,
    '67A77EA21E4F98FE5FF5F27D906B0C8E08C0B702C2B852750A9C0825281DA5A8')
individual_hashes = {row['original_text_sha256'] for row in selection['rows']
                     if row['selected']['decision'] == 'HOLD'}
stage_path = AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V12.json'
stage = read_metadata(stage_path, '3E7EE29411E8B00791D040FAA48E90F466B0E2013BC0A347DF959403E3CA7516')
for item in stage['coverage'] + [dict(cohort='root12_independent_admission_counter_v1', version='v38')]:
    complete = read_metadata(inv.BASE/(item['cohort']+'_snapshots')/item['version']/'complete.json')
    assert not complete['errors']
    for pin in complete['shards']:
        for row in read_metadata(ROOT/pin['path'], pin['sha256']):
            if row.get('decision') == 'NEEDS_ROOT':
                # A pending individual content judgment is never released by
                # this general rule, even when it is not a final terminal HOLD.
                original = row.get('original')
                if original:
                    individual_hashes.add(original['sha256'])
                else:
                    blocked_ids.add(row['id'])

# Validate the inherited production chain without rerunning or copying it.
draft = read_metadata(inv.BASE/'draft_proposals_v26_delta_v1/complete.json',
    '64FE41A6E14D385177169C27426B5030B6FDCA4F5AEBB0412B1B00C02EC62764')
for name, expected in draft['lineage']['source_code_sha256'].items():
    assert inv.file_sha(ROOT/name) == expected, name
    pins[name] = expected
for path in [Path(__file__), ROOT/'scripts/p106b_hold_resolution_disambiguation_v1.py',
    ROOT/'scripts/p106b_hold_resolution_policy_v27.py', ROOT/'scripts/test_p106b_hold_resolution_policy_v27.py',
    AUDIT/'V27_SOURCE_DISAMBIGUATION_ALIAS_SCOPE_V1.md', AUDIT/'POLICY_V27_REGRESSION_RUN_V2.log',
    AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json']:
    pins[str(path.relative_to(ROOT))] = inv.file_sha(path)

out = inv.BASE/'rule27_declared_name_list_census_v1'
assert not out.exists()
writer = inv.cache.ShardWriter(out, 'candidate_metadata', limit=3_999_999)
seen, source_digests = set(), hashlib.sha256()
counts, transitions, guard_failures, weights = Counter(), Counter(), Counter(), Counter()
for kind, group in [('field','remaining_field_title_readers_v1'), ('other','remaining_other_types_readers_v1')]:
    index = read_metadata(inv.BASE/group/'complete.json')
    for page in index['pages']:
        manifest_path = ROOT/page['path']
        manifest = read_metadata(manifest_path, page['sha256'])
        for row in manifest['rows']:
            source_hash = row['original_text_sha256']
            if source_hash not in hold_hashes:
                continue
            assert source_hash not in seen
            seen.add(source_hash)
            if (row['id'] in blocked_ids or source_hash in individual_hashes
                    or any(row[label]['sha256'] in blocked_hashes for label in ['original','candidate'])):
                counts['protected_or_individual_source_not_opened'] += 1
                continue
            original_path = (ROOT/row['original']['path']).resolve()
            assert original_path.is_relative_to(inv.BASE) and not original_path.is_symlink()
            raw = original_path.read_bytes()
            assert sha(raw) == row['original']['sha256'] == source_hash
            counts['originals_verified'] += 1
            source_digests.update((row['id']+':'+source_hash+chr(10)).encode('ascii'))
            original = raw.decode('utf-8')
            declaration = policy.disambiguation.declared_name_list(original)
            if declaration is None:
                counts['nonmatching_header_unchanged'] += 1
                continue
            prepared, proof = policy.disambiguation.source_named_aliases(original)
            if not proof:
                counts['matching_header_without_new_edit_unchanged'] += 1
                continue
            assert row['complete_eos'] and row['valid_utf8']
            input_row = dict(row, text=original, previous_holds=[])
            before = policy.previous.propose(input_row)
            after = policy.propose(input_row)
            candidate = after.get('candidate', after['text'])
            numeric = numeric_atom_changes(original, candidate)
            guards = dict(numeric_atoms=not numeric, code=policy.code_preserved(original,candidate),
                unicode=policy.unicode_examples_preserved(original,candidate),
                style=policy.semantic_style_preserved(original,candidate),
                ordered=policy.ordered_deletion(original,candidate),
                no_memo=not bool(inv.corpus.MEMOS.search(candidate)))
            eligible = before['decision']=='PENDING' and after['decision'] in {'KEEP','EDIT'} and all(guards.values())
            transitions[before['decision']+'_TO_'+after['decision']] += 1
            if eligible:
                counts['new_terminal_rule_candidates'] += 1
                weights['new_terminal_rule_candidate_positions'] += row['occurrences']
            else:
                counts['still_requires_context_or_guard_closure'] += 1
            guard_failures.update(name for name,value in guards.items() if not value)
            proof_raw=(json.dumps(proof,ensure_ascii=False,sort_keys=True)+chr(10)).encode('utf-8')
            writer.append(dict(id=row['id'], original=row['original'], prior_candidate=row['candidate'],
                original_text_sha256=source_hash, occurrences=row['occurrences'], cohort=group,
                source_manifest=dict(path=str(manifest_path.relative_to(ROOT)),sha256=page['sha256']),
                source_list=declaration, before_decision=before['decision'], before_reasons=before['reasons'],
                proposed_decision=after['decision'], proposed_reasons=after['reasons'],
                proposed_body_sha256=inv.sha(candidate), proposed_characters=len(candidate),
                source_proof_count=len(proof), source_proofs_sha256=sha(proof_raw),
                guards=guards, numeric_flags=numeric, eligible_rule_candidate=eligible,
                candidate_body_stored=False, root_approved=False, cache_admitted=False))
        assert_no_protected_opens()
        if page['page'] % 12 == 0:
            print(json.dumps(dict(phase='RULE27_CENSUS',group=kind,through_page=page['page'],
                counts=dict(counts),weights=dict(weights))),flush=True)
manifest = writer.close(lineage=dict(input_pins=pins, accepted_cache_changed=False))
assert len(seen)==66411 and len(hold_hashes-seen)==914
assert counts['originals_verified']==counts['nonmatching_header_unchanged']+counts['matching_header_without_new_edit_unchanged']+manifest['rows']
result=dict(status='V27_WHOLE_REMAINING_QUEUE_CENSUS_AND_NARROW_DELTA_CANDIDATES_NOT_ADMISSION',
    basis='ROOT32_ROSTER23_EXPECTED_REMAINING_HOLD',covered_remaining_unique=len(seen),
    remaining_sources_outside_two_queues=len(hold_hashes-seen), counts=dict(counts),weights=dict(weights),
    transitions=dict(transitions),guard_failures=dict(guard_failures),
    metadata_directory=str(out.relative_to(ROOT)),metadata_manifest=manifest,input_pins=pins,
    verified_source_identity_stream_sha256=source_digests.hexdigest().upper(),
    elapsed_seconds=time.monotonic()-started, source_or_candidate_payload_modified=False,
    original_payload_bytes_copied=0,candidate_payload_bytes_stored=0,
    automatic_root_admissions=0,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json',result)
print(json.dumps({key:result[key] for key in ['status','covered_remaining_unique','counts','weights',
    'transitions','guard_failures','elapsed_seconds','automatic_root_admissions']},ensure_ascii=False),flush=True)
