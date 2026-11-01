"""Independently join every inherited row and freshly decode the27 delta sources."""
from collections import Counter
from contextlib import ExitStack
from itertools import zip_longest
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy

AUDIT, BASE = Path(__file__).resolve().parent, inv.BASE
OLD, NEW = BASE / 'draft_proposals_v25', BASE / 'draft_proposals_v26_delta_v1'
old, new = inv.cache.read(OLD / 'complete.json'), inv.cache.read(NEW / 'complete.json')
exit_path = AUDIT / 'DRAFT_V26_DELTA_PROCESS_EXIT_V1.json'
actual_exit = inv.cache.read(exit_path)
inv.require(actual_exit['process_exit_code'] == 0
            and actual_exit['observation_method'] == 'ACTUAL_EXIT_ZERO_FROM_WRITE_STDIN'
            and actual_exit['completed_artifact_sha256'] == inv.file_sha(NEW / 'complete.json'),
            'actual producer closure does not match this delta')
pins = dict(new['lineage']['source_code_sha256'])
inv.require(len(pins) == 66, 'source-code pin scope differs')
for path, expected in pins.items():
    inv.require(inv.file_sha(ROOT / path) == expected, 'production source changed')
for directory, report in [(OLD, old), (NEW, new)]:
    for label, key in [('unique', 'unique_manifest'), ('occurrences', 'occurrence_manifest')]:
        inv.verify(directory / label, report[key])
        inv.require(all(0 < shard['bytes'] < 20000000 for shard in report[key]['shards']), 'shard size violation')
pair_path = BASE / 'ordinal_metadata_counter_v26_v1/manifest.json'
pairs = {row['id']: row for row in inv.cache.read(pair_path)['rows']}
inv.require(len(pairs) == 27, 'exact source-pair coverage differs')
allowed = {'decision', 'reasons', 'changes', 'rules', 'clean_text_sha256',
           'diagnostic_candidate', 'text', 'delta_extension_proof'}
counts, phases, outcomes, expected_multiplicity = Counter(), Counter(), {}, {}
changed = set()
started = time.monotonic()
with ExitStack() as stack:
    reader = inv.OriginalReader(inv.cache.read(BASE / 'scope.json'), stack)
    for before, after in zip_longest(inv.cache.rows(OLD / 'unique', old['unique_manifest']),
                                   inv.cache.rows(NEW / 'unique', new['unique_manifest'])):
        inv.require(before is not None and after is not None, 'unique row count differs')
        key, ident = before['original_text_sha256'], before['id']
        inv.require(key not in outcomes and key == after['original_text_sha256'] and ident == after['id'], 'unique identity/order differs')
        if ident not in pairs:
            inv.require(before == after, 'a non-censused JSON row changed: ' + ident)
            phases.update(exactly_inherited_unique_json_rows=1)
        else:
            inv.require({k: v for k, v in before.items() if k not in allowed}
                        == {k: v for k, v in after.items() if k not in allowed}, 'delta changed source metadata')
            raw, eos, valid = reader.text(before)
            inv.require(eos and valid and inv.sha(raw) == key == pairs[ident]['original']['sha256'], 'independent native readback differs')
            value = policy.propose(dict(before, text=raw, complete_eos=eos, valid_utf8=valid))
            clean = value.get('candidate', value['text'])
            inv.require(after['decision'] == value['decision'] and after['reasons'] == value['reasons']
                        and after['changes'] == value['changes'] and after['rules'] == policy.RULES,
                        'fresh native26 decision/reasons/changes differ')
            inv.require(inv.sha(clean) == pairs[ident]['candidate']['sha256'], 'pair candidate differs')
            expected_sha = inv.sha(clean) if value['decision'] in {'KEEP', 'EDIT'} else None
            inv.require(after['clean_text_sha256'] == expected_sha, 'delta clean SHA differs')
            if value['decision'] == 'EDIT':
                inv.require(after['text'] == clean and 'diagnostic_candidate' not in after, 'edited body differs')
            elif value['decision'] == 'KEEP':
                inv.require(clean == raw and 'text' not in after and 'diagnostic_candidate' not in after, 'keep serialization differs')
            else:
                inv.require(after['diagnostic_candidate'] == clean and 'text' not in after, 'pending diagnostic differs')
            proof = after['delta_extension_proof']
            inv.require(proof['source_pair_manifest_sha256'] == inv.file_sha(pair_path)
                        and proof['old_diagnostic_sha256'] == inv.sha(before['diagnostic_candidate'])
                        and proof['native_source_freshly_redecoded'] is True
                        and proof['metadata_boundary'] == value.get('metadata_boundary_proof'), 'delta proof differs')
            changed.add(ident)
            phases.update(independently_redecoded_native_sources=1)
        outcomes[key] = after['decision'], after['reasons']
        expected_multiplicity[key] = before['occurrences']
        counts.update([after['decision']])
inv.require(changed == set(pairs) and len(outcomes) == 297539 and dict(counts) == new['unique_counts'], 'unique conservation differs')
positions, observed_multiplicity = Counter(), Counter()
for before, after in zip_longest(inv.cache.rows(OLD / 'occurrences', old['occurrence_manifest']),
                               inv.cache.rows(NEW / 'occurrences', new['occurrence_manifest'])):
    inv.require(before is not None and after is not None, 'occurrence count differs')
    inv.require({k: v for k, v in before.items() if k not in {'resolution', 'resolution_reasons'}}
                == {k: v for k, v in after.items() if k not in {'resolution', 'resolution_reasons'}},
                'occurrence source ID/split/interval/SHA metadata differs')
    key = after['original_text_sha256']
    inv.require((after['resolution'], after['resolution_reasons']) == outcomes[key], 'occurrence outcome differs from unique')
    positions.update(documents=1, input_ids=after['input_ids'], **{after['resolution']: 1})
    positions[after['resolution'] + '_input_ids'] += after['input_ids']
    observed_multiplicity[key] += 1
inv.require(dict(observed_multiplicity) == expected_multiplicity, 'source multiplicity differs')
inv.require(dict(positions) == new['occurrence_counts'] and positions['documents'] == 460695
            and positions['input_ids'] == 462874291 and positions['PENDING'] == 122534, 'full position/input-ID conservation differs')
inv.require(pins == {name: inv.file_sha(ROOT / name) for name in pins}, 'production source changed during verification')
result = dict(status='VERIFIED_V25_PLUS_NARROW_V26_DELTA_NOT_CACHE_ADMISSION',
    original_process_exit_code=0, full_native_v26_rerun=False, unique_sources_checked=len(outcomes),
    verification_phases=dict(phases), occurrence_counts=dict(positions), unique_counts=dict(counts),
    all_nonmatch_unique_json_exactly_preserved=True, all_occurrence_source_metadata_and_reasons_checked=True,
    all_source_multiplicities_checked=True, fresh_native_source_pairs=27, production_source_count=len(pins),
    completed_artifact=dict(path=str((NEW / 'complete.json').relative_to(ROOT)), sha256=inv.file_sha(NEW / 'complete.json')),
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [OLD / 'complete.json', exit_path, pair_path, Path(__file__)]},
    source_code_pins=pins, seconds=time.monotonic() - started, cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(AUDIT / 'DRAFT_V26_DELTA_EXECUTION_RECEIPT_V1.json', result)
print(json.dumps({key: result[key] for key in ['status', 'unique_sources_checked', 'verification_phases',
    'occurrence_counts', 'unique_counts', 'seconds']}, ensure_ascii=False), flush=True)
