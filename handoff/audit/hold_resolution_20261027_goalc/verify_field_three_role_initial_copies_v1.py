"""Independently compare all 11,240 assigned candidate/copy byte identities."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
assert inv.file_sha(contract_path) == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
contract = inv.cache.read(contract_path)
complete_path = AUDIT / 'FIELD_THREE_ROLE_INITIAL_COPIES_COMPLETE_V1.json'
complete = inv.cache.read(complete_path)
assert complete['total_sources'] == 11240 and complete['role_page_groups'] == 108
assert complete['root_authored_cleaned_bodies'] == complete['new_reviews'] == complete['cache_admitted'] == 0
index_path = inv.BASE / 'remaining_field_title_readers_v1/complete.json'
index = inv.cache.read(index_path)
page_pins = {row['page']: row for row in index['pages']}
assert len(page_pins) == 36
manifests = {}
for number, page in page_pins.items():
    path = ROOT / page['path']
    assert inv.file_sha(path) == page['sha256']
    value = inv.cache.read(path)
    manifests[number] = {row['id']: row for row in value['rows']}
expected_counts = {'context_hangul': 3724, 'historical_review': 3757, 'legacy_review': 3759}
roles = []
total_bytes = 0
max_file_bytes = 0
all_sources = set()
for role_record in complete['roles']:
    role = role_record['role']
    assert role in expected_counts
    role_path = ROOT / role_record['receipt']['path']
    assert inv.file_sha(role_path) == role_record['receipt']['sha256']
    value = inv.cache.read(role_path)
    assert value['sources'] == expected_counts[role] and len(value['pages']) == 36
    count = 0
    for page_record in value['pages']:
        number = page_record['page']
        page = page_pins[number]
        path = ROOT / page_record['receipt']['path']
        assert inv.file_sha(path) == page_record['receipt']['sha256']
        receipt = inv.cache.read(path)
        source_rows = manifests[number]
        expected_ids = {ident for ident, row in source_rows.items() if row['role'] == role}
        rows = receipt['rows']
        assert len(rows) == len(expected_ids) == receipt['sources'] == page_record['sources']
        assert {row['id'] for row in rows} == expected_ids
        directory = inv.BASE / 'agents' / role / page['group']
        guide_path = ROOT / receipt['guide']['path']
        assert guide_path == directory / 'ROOT_UNCHANGED_INITIAL_COPIES_V1.md'
        assert inv.file_sha(guide_path) == receipt['guide']['sha256']
        guide = guide_path.read_text(encoding='utf-8')
        guide_entries = dict(re.findall(r'^- ((?:expanded_train|validation):[0-9]+): (.+)$', guide, re.M))
        assert set(guide_entries) == expected_ids
        for row in rows:
            ident = row['id']
            source = source_rows[ident]
            assert source['role'] == role
            assert ident not in contract['restricted_ids']
            assert source['original']['sha256'] not in contract['restricted_hashes']
            assert row['source'] == source['candidate']
            original_candidate = ROOT / source['candidate']['path']
            target = ROOT / row['initial_copy']['path']
            assert original_candidate.parent == inv.BASE / 'remaining_field_title_native_proofs_v1/pages' / f'page_{number:03}' / 'inputs'
            assert target == directory / (ident.replace(':', '_') + '_initial_candidate_v1.txt')
            assert not original_candidate.is_symlink() and not target.is_symlink()
            assert guide_entries[ident] == str(target)
            before, after = original_candidate.read_bytes(), target.read_bytes()
            assert before == after and 0 < len(after) < 20_000_000
            assert inv.file_sha(original_candidate) == inv.file_sha(target) == source['candidate']['sha256'] == row['initial_copy']['sha256']
            assert row['unchanged'] and not row['luna_revision'] and not row['root_admitted']
            assert ident not in all_sources
            all_sources.add(ident)
            total_bytes += len(after)
            max_file_bytes = max(max_file_bytes, len(after))
            count += 1
    assert count == expected_counts[role]
    roles.append(dict(role=role, sources=count, pages=36))
assert len(roles) == 3 and len(all_sources) == 11240
paths = [contract_path, complete_path, index_path, Path(__file__).resolve(),
         ROOT / 'scripts/p106b_hold_resolution_inventory.py']
result = dict(status='ALL_THREE_ROLE_CANDIDATE_COPY_BYTES_ASSIGNMENTS_GUIDES_AND_BOUNDS_INDEPENDENTLY_VERIFIED',
              roles=roles, sources=11240, role_page_groups=108,
              actual_copy_bytes=total_bytes, largest_copy_bytes=max_file_bytes,
              cross_role_source_overlap=0, protected_body_reads=0,
              original_source_code_executed=False, original_or_candidate_changed=False,
              new_cleaned_bodies=0, new_reviews=0, root_adopted=0, cache_admitted=0,
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'FIELD_THREE_ROLE_INITIAL_COPIES_INDEPENDENT_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], sources=11240, roles=roles,
                     bytes=total_bytes, largest_file_bytes=max_file_bytes,
                     new_cleaned_bodies=0, admitted=0), ensure_ascii=False))
