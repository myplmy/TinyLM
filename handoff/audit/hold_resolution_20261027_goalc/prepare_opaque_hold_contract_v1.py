"""Join a fixed roster's HOLD sources to text-free parent positions only."""
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--expected-config-sha', required=True)
    args = parser.parse_args()
    path = args.config.resolve()
    assert path.is_relative_to(AUDIT) and not path.is_symlink()
    assert inv.file_sha(path) == args.expected_config_sha
    config = inv.cache.read(path)
    output = AUDIT/config['output']
    metadata_directory = (ROOT/config['metadata_directory']).resolve()
    assert metadata_directory.is_relative_to(inv.BASE) and not metadata_directory.exists()
    assert not output.exists()
    pins = config['input_pins']
    for name, expected in pins.items():
        assert inv.file_sha(ROOT/name) == expected, 'fixed metadata input changed'
    proof = inv.cache.read(ROOT/config['roster_proof'])
    for name, expected in proof['input_pins'].items():
        assert inv.file_sha(ROOT/name) == expected
    roster_path = ROOT/config['roster']
    roster = inv.cache.read(roster_path)
    directory = roster_path.parent/roster['records_directory']
    inv.verify(directory, roster['manifest'])
    hold_hashes = set()
    print(json.dumps(dict(phase='ROSTER_METADATA_PROJECTION_STARTED')), flush=True)
    with patch.object(metadata, 'FIELDS', metadata.FIELDS | {'decision'}):
        for shard in roster['manifest']['shards']:
            with (directory/shard['path']).open('rb') as stream:
                for line in stream:
                    row = metadata.project_metadata(line)
                    if row['decision'] == 'HOLD':
                        assert row['original_text_sha256'] not in hold_hashes
                        hold_hashes.add(row['original_text_sha256'])
    print(json.dumps(dict(phase='ROSTER_METADATA_PROJECTED', unique_HOLD=len(hold_hashes))), flush=True)
    parent_path = inv.PARENT/'built.json'
    parent = inv.cache.read(parent_path)
    ledger = inv.PARENT/'ledger'
    inv.verify(ledger, parent['manifests']['ledger'])
    trusted, counts = {}, Counter()
    with patch.object(metadata, 'FIELDS', metadata.FIELDS | {'decision'}):
        for shard in parent['manifests']['ledger']['shards']:
            with (ledger/shard['path']).open('rb') as stream:
                for line in stream:
                    matches = metadata.SOURCE_SHA.findall(line)
                    assert len(matches) <= 1
                    if not matches or matches[0].decode('ascii').upper() not in hold_hashes:
                        continue
                    row = metadata.project_metadata(line)
                    assert row['decision'] == 'HOLD', 'HOLD hash also has a non-HOLD parent'
                    ident = row['id']; assert ident not in trusted
                    trusted[ident] = {key: row[key] for key in metadata.IDENTITY_FIELDS}
                    trusted[ident]['parent_decision'] = 'HOLD'
                    counts.update(positions=1, input_ids=row['input_ids'])
    assert len(hold_hashes) == config['expected_HOLD_unique']
    assert counts['positions'] == config['expected_HOLD_positions'] == roster['remaining_hold']
    assert counts['input_ids'] == config['expected_HOLD_input_ids']
    for name, expected in pins.items():
        assert inv.file_sha(ROOT/name) == expected
    writer = inv.cache.ShardWriter(metadata_directory, 'hold_positions', limit=19_999_999)
    for ident in sorted(trusted):
        writer.append(trusted[ident])
    manifest = writer.close(lineage=dict(configuration_sha256=inv.file_sha(path),
        roster_sha256=pins[config['roster']], parent_built_sha256=inv.file_sha(parent_path)))
    assert all(shard['bytes'] < 20_000_000 for shard in manifest['shards'])
    value = dict(schema='OPAQUE_UNADOPTED_HOLD_METADATA_V1',
        status='CURRENT_ROSTER_HOLD_PARENT_POSITIONS_JOINED_WITHOUT_BODY_DECODE',
        utc=datetime.now(timezone.utc).isoformat(),
        selection=config['selection'], roster=config['roster'],
        selection_sha256=pins[config['selection']], roster_sha256=pins[config['roster']],
        hold_hashes=sorted(hold_hashes),
        hold_metadata_directory=str(metadata_directory.relative_to(ROOT)),
        hold_metadata_manifest=manifest,
        counts=dict(counts), unique_sources=len(hold_hashes),
        input_pins=dict(pins, **{str(path.relative_to(ROOT)): inv.file_sha(path),
            str(Path(__file__).relative_to(ROOT)): inv.file_sha(Path(__file__))}),
        parent_ledger_shard_pins={str((ledger/shard['path']).relative_to(ROOT)): shard['sha256']
            for shard in parent['manifests']['ledger']['shards']},
        ordinary_HOLD_is_not_reclassified_as_sensitive=True,
        original_or_candidate_payload_files_opened=0, body_fields_decoded=0,
        goal_complete=False, training_authorized=False)
    inv.write_json(output, value)
    print(json.dumps(dict(status=value['status'], unique_sources=len(hold_hashes),
        counts=dict(counts), sha256=inv.file_sha(output), body_fields_decoded=0)), flush=True)


if __name__ == '__main__': main()
