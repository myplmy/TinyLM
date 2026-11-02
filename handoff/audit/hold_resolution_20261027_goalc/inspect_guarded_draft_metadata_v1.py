"""Inspect only protected draft decision metadata, never candidate body values."""
from pathlib import Path
from unittest.mock import patch
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata

contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
protected=set(contract['restricted_hashes'])
directory=inv.BASE/'draft_proposals_v26_delta_v1'
draft=inv.cache.read(directory/'complete.json')
records=[]
for shard in draft['unique_manifest']['shards']:
    with (directory/'unique'/shard['path']).open('rb') as stream:
        for line in stream:
            if not any(key.encode('ascii') in line for key in protected):
                continue
            with patch.object(metadata,'FIELDS',metadata.FIELDS|{'decision','occurrences','reasons'}):
                row=metadata.project_metadata(line)
            if row.get('original_text_sha256') in protected:
                records.append({key:row.get(key) for key in ['id','original_text_sha256','decision','occurrences','reasons']})
result=dict(status='PROTECTED_DRAFT_TOP_LEVEL_METADATA_ONLY_NOT_BODY_OR_ADMISSION',records=records,
            source_or_diagnostic_bodies_decoded=False,training_authorized=False,goal_complete=False)
inv.write_json(AUDIT/'GUARDED_DRAFT_METADATA_V1.json',result)
print(json.dumps(result,ensure_ascii=False))
