"""Partition every unprocessed source against exact current author ownership."""
from collections import Counter
from pathlib import Path
import json
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata

out=inv.BASE/'remaining_unassigned_all_sources_v1'
assert not out.exists()
roster_path=inv.BASE/'roster_reviewed_partial_v3/complete.json'
roster=inv.cache.read(roster_path)
contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract=inv.cache.read(contract_path)
owners={};ownership_paths=[]
for name in ['repeat_named_full_independent_v1','remaining_birth_full_counter_v1','remaining_literal_full_counter_v1']:
    path=inv.BASE/name/'manifest.json';ownership_paths.append(path)
    for row in inv.cache.read(path)['rows']:
        key=row['original_text_sha256'];assert key not in owners
        owners[key]=dict(id=row['id'],cohort=name,role=row['role'])
assert len(owners)==5268
blocked_ids=set(contract['restricted_ids']);blocked_shas=set(contract['restricted_hashes'])
directory=roster_path.parent/roster['records_directory']
inv.verify(directory,roster['manifest'])
fields=metadata.FIELDS|{'decision','reason','occurrences','language_bucket','review_status'}
writer=inv.ShardWriter(out/'rows','unassigned_sources',limit=19_999_999)
counts,reasons,owned,restricted=Counter(),Counter(),[],[]
seen=set()
with patch.object(metadata,'FIELDS',fields):
    for shard in roster['manifest']['shards']:
        with (directory/shard['path']).open('rb') as stream:
            for line in stream:
                if b'"HOLD"' not in line:continue
                row=metadata.project_metadata(line)
                if row['decision']!='HOLD' or row.get('review_status')!='UNRESOLVED_NOT_ADMITTED':continue
                key=row['original_text_sha256'];assert key not in seen;seen.add(key)
                counts.update(unprocessed_unique=1,unprocessed_positions=row['occurrences'])
                if row['id'] in blocked_ids or key in blocked_shas:
                    restricted.append(dict(id=row['id'],original_text_sha256=key,occurrences=row['occurrences']))
                    counts.update(restricted_unique=1,restricted_positions=row['occurrences']);continue
                if key in owners:
                    owned.append(dict(**owners[key],original_text_sha256=key,occurrences=row['occurrences']))
                    counts.update(current_owned_unique=1,current_owned_positions=row['occurrences']);continue
                record={k:row[k] for k in ['id','source','split','source_ids','source_ids_sha256',
                    'original_text_sha256','input_ids','language_bucket','occurrences']}
                record.update(previous_reasons=row['reason'].split(','),root_approved=False,cache_admitted=False)
                writer.append(record);counts.update(queued_unique=1,queued_positions=row['occurrences'])
                reasons.update(record['previous_reasons'])
assert counts['unprocessed_unique']==70192 and counts['unprocessed_positions']==110135
assert counts['current_owned_unique']==1792
for unit in ['unique','positions']:
    assert counts['unprocessed_'+unit]==sum(counts[x+'_'+unit] for x in ['queued','current_owned','restricted'])
paths=[roster_path,contract_path,*ownership_paths,AUDIT/'REMAINING_ALL_TYPES_COVERAGE_SCOPE_V1.md',
    AUDIT/'guarded_scan_metadata_v1.py',Path(__file__)]
pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in paths}
manifest=writer.close(lineage=dict(input_pins=pins))
result=dict(status='ALL_UNASSIGNED_TYPES_METADATA_CENSUS_NOT_CONTENT_REVIEW',counts=dict(counts),
    pending_reasons_unique=dict(reasons),rows=manifest,current_owned=owned,restricted_metadata_only=restricted,
    input_pins=pins,raw_original_bodies_opened=False,goal_complete=False,training_authorized=False)
inv.write_json(out/'complete.json',result)
print(json.dumps(dict(counts=dict(counts),pending_reasons_unique=dict(reasons)),ensure_ascii=False))
