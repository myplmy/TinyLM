"""Recount all parent positions and write only new census metadata and code pins."""
from collections import Counter
from pathlib import Path
import argparse
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from guarded_reviewed_cache_v7 import ROOT, inv, current_pins, checked_contract
from referenced_census_metadata_v1 import SCHEMA
import guarded_scan_metadata_v1 as metadata

checked_contract()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--expected-config-sha', required=True)
args = parser.parse_args()
p = args.config.resolve()
assert p.is_relative_to(AUDIT) and not p.is_symlink()
assert inv.file_sha(p) == args.expected_config_sha
c = inv.cache.read(p)
for name, digest in c['input_pins'].items():
    assert inv.file_sha(ROOT/name) == digest
selection, roster_path, opaque_path = [ROOT/c[k] for k in ['selection', 'roster', 'opaque_contract']]
roster = inv.cache.read(roster_path)
pins = current_pins(selection, opaque_path, c['input_pins'][c['opaque_contract']])
parent_path = inv.PARENT/'built.json'
parent = inv.cache.read(parent_path)
manifest = parent['manifests']['hold']
source = inv.PARENT/'hold'
inv.verify(source, manifest)
counts = Counter()
seen = set()
for shard in manifest['shards']:
    with (source/shard['path']).open('rb') as stream:
        for line in stream:
            row = metadata.project_metadata(line)
            assert row['id'] not in seen
            seen.add(row['id'])
            counts.update(documents=1, input_ids=row['input_ids'])
assert dict(counts) == {'documents':460695, 'input_ids':462874291}
assert current_pins(selection, opaque_path, c['input_pins'][c['opaque_contract']]) == pins
out = inv.BASE/c['proposal_name']
assert not out.exists()
out.mkdir()
value = dict(unprocessed=0, enumeration_unprocessed=0,
    meaning='FULL_SOURCE_ENUMERATION_ONLY_NOT_CONTENT_COMPLETION',
    content_unprocessed=roster['unprocessed'], reviewed_hold=roster['reviewed_hold'],
    remaining_hold=roster['remaining_hold'], counts=dict(counts), manifest=manifest,
    pin=dict(recovery_revision_source_sha256=pins,
        parent_built_sha256=inv.file_sha(parent_path),
        parent_verified_sha256=inv.file_sha(inv.PARENT/'verified.json'),
        scope_sha256=inv.file_sha(inv.BASE/'scope.json')),
    approval=roster['approval'], metadata_reference_schema=SCHEMA,
    metadata_reference=dict(path=str(source.relative_to(ROOT)), parent_built_sha256=inv.file_sha(parent_path)),
    source_metadata_enumeration=dict(path=str(source.relative_to(ROOT)),
        every_position_identity_and_input_ids_recounted=True),
    generator_input_pins=dict(c['input_pins'], **{str(p.relative_to(ROOT)):inv.file_sha(p),
        str(Path(__file__).relative_to(ROOT)):inv.file_sha(Path(__file__))}),
    metadata_payload_bytes_copied=0, original_or_candidate_payload_files_opened=0,
    body_fields_decoded=0, goal_complete=False, training_authorized=False)
inv.write_json(out/'complete.json', value)
print(__import__('json').dumps(dict(status='REFERENCE_CENSUS_READY',counts=dict(counts),
    remaining_hold=roster['remaining_hold'],runtime_pin_files=len(pins),metadata_payload_bytes_copied=0,
    complete_sha256=inv.file_sha(out/'complete.json'))),flush=True)
