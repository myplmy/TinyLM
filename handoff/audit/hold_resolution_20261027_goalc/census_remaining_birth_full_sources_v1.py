"""Queue every unresolved birth-conflict source, preserving current ownership."""
from collections import Counter
from pathlib import Path
import json
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata

BASE=inv.BASE
OUT=BASE/'remaining_birth_full_sources_v1'
inv.require(not OUT.exists(),'new complete birth-type namespace required')
join_path=BASE/'resolution_join_plan_v4/complete.json'
current_path=BASE/'repeat_named_roles_counter_v2/manifest.json'
contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
join,current,contract=map(inv.cache.read,[join_path,current_path,contract_path])
inv.require(join['full_restricted_original_bodies_opened'] is False,'metadata-safe joined source required')
assigned={row['original_text_sha256']:row for row in current['rows']}
blocked_ids=set(contract['restricted_ids'])
blocked_shas=set(contract['restricted_hashes'])
directory=join_path.parent/join['records_directory']
inv.verify(directory,join['manifest'])
writer=inv.ShardWriter(OUT/'rows','pending_birth_sources',limit=19_999_999)
counts,overlap=Counter(),[]
fields=metadata.FIELDS|{'decision','reason','occurrences','language_bucket','review_status'}
for shard in join['manifest']['shards']:
    with (directory/shard['path']).open('rb') as stream:
        for line in stream:
            with patch.object(metadata,'FIELDS',fields):
                row=metadata.project_metadata(line)
            if row['decision']!='HOLD':continue
            reasons=row['reason'].split(',')
            if 'INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED' not in reasons:continue
            counts.update(whole_type_unique=1,whole_type_positions=row['occurrences'])
            key=row['original_text_sha256']
            inv.require(row['id'] not in blocked_ids and key not in blocked_shas,
                        'restricted source must remain metadata-only and unassigned')
            if key in assigned:
                overlap.append(dict(id=row['id'],role=assigned[key]['role'],original_text_sha256=key))
                counts.update(current732_owned_unique=1,current732_owned_positions=row['occurrences'])
                continue
            record={key:row[key] for key in ['id','source','split','source_ids','source_ids_sha256',
                'original_text_sha256','input_ids','language_bucket','occurrences']}
            record.update(previous_reasons=reasons,named_review_strata=['ENTIRE_REMAINING_BIRTH_YEAR_CONFLICT_TYPE'],
                root_approved=False,cache_admitted=False)
            writer.append(record)
            counts.update(queued_unique=1,queued_positions=row['occurrences'])
inv.require(counts['whole_type_unique']==join['pending_reasons_unique']['INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED']==2743,
            'every unresolved birth-type source must be conserved')
inv.require(counts['queued_unique']+counts['current732_owned_unique']==2743,'queued/current ownership must partition scope')
pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [join_path,current_path,contract_path,
    AUDIT/'REMAINING_BIRTH_FULL_SOURCE_SCOPE_V1.md',AUDIT/'guarded_scan_metadata_v1.py',Path(__file__)]}
manifest=writer.close(lineage=dict(input_pins=pins))
result=dict(status='ENTIRE_REMAINING_BIRTH_TYPE_METADATA_CENSUS_NOT_REVIEW_OR_ADMISSION',
    counts=dict(counts),rows=manifest,current732_owned=overlap,input_pins=pins,
    original_bodies_decoded=False,body_changed=0,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(OUT/'complete.json',result)
print(json.dumps(dict(status=result['status'],counts=dict(counts),goal_complete=False),ensure_ascii=False))
