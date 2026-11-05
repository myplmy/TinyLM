"""Reuse byte-identical full-source metadata enumeration with fresh guard6 pins."""
from collections import Counter
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT)); sys.path.insert(0, str(ROOT))
from guarded_reviewed_cache_v6 import inv
from opaque_cache_census_support_v1 import current_pins
import guarded_scan_metadata_v1 as metadata

selection = AUDIT/'ROOT_AUTHORED_SELECTIONS_V28.json'
roster_path = inv.BASE/'roster_reviewed_partial_v20/complete.json'
opaque_path = AUDIT/'OPAQUE_HOLD_ROOT28_ROSTER20_CONTRACT_V1.json'
opaque_sha = '3F0E1828F8637C34F0303149D409813F0929F3A848541C5C68BD1646294A7EBA'
assert inv.file_sha(selection) == 'FA41807ABB0F98E28A50B03EBAAA02EF8672357A9EDE8904884BE4E079A1B1F8'
assert inv.file_sha(roster_path) == 'DF7C5300053394B380C18B7A46DF6139F81A2316306729E5530220C8147BD372'
roster = inv.cache.read(roster_path)
parent_path = inv.PARENT/'built.json'
assert inv.file_sha(parent_path) == '47F117C11261581E82A1594DC4E2F4706400CF868FBB2F39521B47C917EDA7DE'
parent = inv.cache.read(parent_path)
source = inv.PARENT/'hold'; manifest = parent['manifests']['hold']
inv.verify(source, manifest)
pins = current_pins(selection, opaque_path, opaque_sha)
out = inv.BASE/'guarded_partial_proposals_opaque_root28_roster20_v1'
assert not out.exists()
counts = Counter(); identities = set()
for shard in manifest['shards']:
    with (source/shard['path']).open('rb') as stream:
        for line in stream:
            row = metadata.project_metadata(line)
            assert row['id'] not in identities; identities.add(row['id'])
            counts.update(documents=1, input_ids=row['input_ids'])
assert dict(counts) == {'documents':460695, 'input_ids':462874291}
target = out/'ledger'; target.mkdir(parents=True, exist_ok=False)
for shard in manifest['shards']:
    assert shard['bytes'] < 20_000_000
    with (source/shard['path']).open('rb') as original, (target/shard['path']).open('xb') as copied:
        shutil.copyfileobj(original, copied, length=1_048_576)
inv.verify(target, manifest)
assert current_pins(selection, opaque_path, opaque_sha) == pins
value = dict(unprocessed=0, enumeration_unprocessed=0,
    meaning='FULL_SOURCE_ENUMERATION_ONLY_NOT_CONTENT_COMPLETION',
    content_unprocessed=roster['unprocessed'], reviewed_hold=roster['reviewed_hold'],
    remaining_hold=roster['remaining_hold'], counts=dict(counts), manifest=manifest,
    pin=dict(recovery_revision_source_sha256=pins,
        parent_built_sha256=inv.file_sha(parent_path),
        parent_verified_sha256=inv.file_sha(inv.PARENT/'verified.json'),
        scope_sha256=inv.file_sha(inv.BASE/'scope.json')),
    approval=roster['approval'],
    source_metadata_enumeration=dict(path=str(source.relative_to(ROOT)),
        every_position_identity_and_input_ids_recounted=True,
        all_shard_bytes_identical_to_frozen_parent=True,
        original_or_candidate_payload_files_opened=0, body_fields_decoded=0),
    generator_input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in
        [Path(__file__),AUDIT/'opaque_cache_census_support_v1.py',selection,roster_path,opaque_path]},
    goal_complete=False, training_authorized=False)
inv.write_json(out/'complete.json', value)
receipt = AUDIT/'OPAQUE_CACHE_CENSUS_ROOT28_ROSTER20_VERIFIED_V1.json'
assert not receipt.exists()
inv.write_json(receipt, dict(status='FRESH_GUARD6_PINS_AND_FULL_460695_SOURCE_ENUMERATION_RECOUNTED',
    complete=dict(path=str((out/'complete.json').relative_to(ROOT)),sha256=inv.file_sha(out/'complete.json')),
    counts=dict(counts), remaining_hold=roster['remaining_hold'],runtime_pin_files=len(pins),
    all_metadata_shards_under_20000000=True, original_or_candidate_payload_files_opened=0,
    body_fields_decoded=0,goal_complete=False,training_authorized=False))
print(json.dumps(dict(status='GUARD6_FULL_ENUMERATION_CENSUS_READY',counts=dict(counts),
    remaining_hold=roster['remaining_hold'],complete_sha256=inv.file_sha(out/'complete.json'),
    receipt_sha256=inv.file_sha(receipt))),flush=True)
