"""Append two exact quarantines by metadata projection; never open their text."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv


def read(path, digest):
    assert not path.is_symlink() and inv.file_sha(path) == digest, str(path)
    return inv.cache.read(path)


old_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json'
old = read(old_path, '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D')
manifest_path = inv.BASE/'root12_independent_admission_counter_v1/manifest.json'
manifest = read(manifest_path, 'A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D')
targets = {
    'expanded_train:32895': ('3CBF35E6BC45649806BE5F4D93C1021725B9C4CE52E49DF608119135852F20FD',
        '2050B0AC1E4E6497B34227F47624EAC4BFE851020162FCDBD4CF9FA8477731DD',
        'Nuclear material processing procedure concern; no additional payload read.'),
    'expanded_train:74587': ('4A27CDEDFB2EAE5214BB90C466B8B0456B630D82629729FA0C2BD50E33F085F6',
        '1A295B6ED32906AE68E99177B1FB467B34DC5DCE0A9ECE89023271C09CF8AE1D',
        'Specific component manipulation and aiming/use directions mixed into general history; no additional payload read.')}
sources = {r['id']: r for r in manifest['rows'] if r['id'] in targets}
assert set(sources) == set(targets)
selection_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V30.json'
selection = read(selection_path, '36222437913A563A7D8402AAF67B6E47070B1AEA3D17CD9A70863D82B2054FA6')
assert not set(targets) & {r['id'] for r in selection['rows']}
projector_path = AUDIT/'guarded_scan_metadata_v1.py'
assert inv.file_sha(projector_path) == old['input_pins'][str(projector_path.relative_to(ROOT))]
spec = importlib.util.spec_from_file_location('frozen_metadata_guard5', projector_path)
projector = importlib.util.module_from_spec(spec); spec.loader.exec_module(projector)
projector.FIELDS = set(projector.FIELDS) | {'decision'}
parent_path = inv.PARENT/'built.json'
parent = read(parent_path, '47F117C11261581E82A1594DC4E2F4706400CF868FBB2F39521B47C917EDA7DE')
directory = inv.PARENT/'ledger'; inv.verify(directory, parent['manifests']['ledger'])
fields = ['id','source','split','source_ids','source_ids_sha256','original_text_sha256','input_ids']
by_hash = {r['original']['sha256']: key for key,r in sources.items()}
needles = [value.encode('ascii') for value in by_hash]
aliases = {key: {} for key in targets}
for shard in parent['manifests']['ledger']['shards']:
    with (directory/shard['path']).open('rb') as stream:
        for line in stream:
            if not any(needle in line for needle in needles): continue
            row = projector.project_metadata(line)
            key = by_hash.get(row.get('original_text_sha256'))
            if key is None: continue
            assert row['decision'] == 'HOLD' and row['id'] not in aliases[key]
            aliases[key][row['id']] = {name: row[name] for name in fields}
            aliases[key][row['id']]['parent_decision'] = row['decision']
trusted = dict(old['trusted_metadata']); entries = []
for key,source in sources.items():
    original_sha,candidate_sha,reason = targets[key]
    assert source['role'] == 'context_controls'
    assert source['original']['sha256'] == original_sha and source['candidate']['sha256'] == candidate_sha
    assert key not in old['restricted_ids'] and len(aliases[key]) == source['occurrences'] == 2
    assert set(fields)-set(source) == {'source','split'}
    assert all(aliases[key][key][name] == source[name] for name in fields if name in source)
    assert aliases[key][key]['source'] == key.split(':')[0]
    assert aliases[key][key]['split'] == 'train'
    for alias,value in aliases[key].items():
        assert alias not in trusted
        trusted[alias] = value
    entries.append(dict(id=key,original=source['original'],derived_candidate=source['candidate'],
        occurrences=source['occurrences'],parent_alias_ids=sorted(aliases[key]),
        role=source['role'],cohort='root12_independent_admission_counter_v1',
        disposition='METADATA_ONLY_HOLD_NOT_ADMITTED',reason=reason,
        root_additional_payload_reads=0,body_admission_approved=False))
ids = old['restricted_ids'] + sorted(targets)
hashes = old['restricted_hashes'] + [value for key in sorted(targets) for value in targets[key][:2]]
assert len(ids) == len(set(ids)) == 11 and len(hashes) == len(set(hashes)) == 14 and len(trusted) == 19
result = dict(old,status='CUMULATIVE_GUARD_V5_TWO_EXACT_METADATA_QUARANTINES',
    restricted_ids=ids,restricted_hashes=hashes,active_restricted_ids=ids,active_restricted_hashes=hashes,
    trusted_metadata=trusted,counts=dict(Counter(r['parent_decision'] for r in trusted.values())),
    previous_contract=dict(path=str(old_path.relative_to(ROOT)),sha256=inv.file_sha(old_path)),
    newly_quarantined_entries=entries,root_additional_payload_reads=0,
    additional_payload_hashing=0,technical_detail_quoted_in_new_artifacts=False,
    all_new_payload_reads_require_V5_first=True,all_new_global_cache_and_consumer_reads_require_V5=True,
    V4_frozen_disjoint_scope_requires_active_V5_or_exact_metadata_disjointness=True,
    old_V4_fields_are_frozen_provenance_not_current_authorization=True,
    goal_complete=False,training_authorized=False)
result['exact_source_parent_decisions'] = {key:value['parent_decision'] for key,value in trusted.items()}
result['input_pins'] = dict(old['input_pins'],**{str(p.relative_to(ROOT)):inv.file_sha(p)
    for p in [old_path,manifest_path,selection_path,parent_path,projector_path,Path(__file__)]})
out = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json'; assert not out.exists()
inv.write_json(out,result)
print(json.dumps(dict(status=result['status'],sha256=inv.file_sha(out),ids=len(ids),hashes=len(hashes),
    aliases=len(trusted),new_aliases={key:sorted(value) for key,value in aliases.items()},payload_reads=0)))
