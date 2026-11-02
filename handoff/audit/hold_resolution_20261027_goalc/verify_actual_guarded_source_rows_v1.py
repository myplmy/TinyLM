"""Validate all 11 real scan rows without decoding any restricted body."""
from pathlib import Path
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_reviewed_cache_v1 as adapter
import guarded_scan_metadata_v1 as metadata

selection=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW6.json'
inputs=adapter.GuardedInputs(selection)
source_base=adapter.reviewed.final.engine.recovery.PARENT
scope=inv.cache.read(source_base/'scope.json')
seen,units=set(),[]
started=time.monotonic()
for source in scope['inputs']:
    ordinals={int(ident.rsplit(':',1)[1]) for ident in inputs.metadata if ident.startswith(source['name']+':')}
    if not ordinals:
        continue
    for stamp in sorted((source_base/'scan'/source['name']).glob('unit_*/complete.json')):
        info=inv.cache.read(stamp)
        expected={number for number in ordinals if info['start_ordinal']<=number<info['end_ordinal']}
        if not expected:
            continue
        inv.verify(stamp.parent/'records',info['manifest'])
        units.append(dict(path=str(stamp.relative_to(ROOT)),sha256=inv.file_sha(stamp)))
        for shard in info['manifest']['shards']:
            with (stamp.parent/'records'/shard['path']).open('rb') as stream:
                for line in stream:
                    ids=metadata.IDENT.findall(line)
                    inv.require(len(ids)==1,'scan source must have one exact byte ID')
                    ident=ids[0].decode('ascii')
                    if ident not in inputs.metadata:
                        continue
                    projected=metadata.guarded_row(line,restricted_ids=inputs.restricted_ids,
                        restricted_hashes=inputs.restricted_hashes,trusted_metadata=inputs.metadata)
                    inv.require(projected['text']=='' and projected['restricted_parent_body_not_decoded'] is True,
                                'actual restricted body was not projected')
                    inv.require(ident not in seen,'actual restricted source repeats')
                    seen.add(ident)
inv.require(seen==set(inputs.metadata) and len(seen)==11,'all restricted source aliases must be validated')
inputs.check()
result=dict(status='ALL11_REAL_RESTRICTED_SCAN_METADATA_ROWS_VALIDATED_WITH_OPAQUE_BODIES',
    exact_restricted_ids=7,alias_positions=len(seen),source_units=units,
    original_parent_text_fields_decoded=False,approved_safe_views=3,
    input_pins=dict(inputs.pin_values,**{str(Path(__file__).relative_to(ROOT)):inv.file_sha(Path(__file__))}),
    seconds=time.monotonic()-started,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(AUDIT/'ACTUAL_GUARDED_SOURCE_ROWS_V1.json',result)
print(json.dumps(dict(status=result['status'],alias_positions=len(seen),source_units=len(units),seconds=result['seconds'])))
