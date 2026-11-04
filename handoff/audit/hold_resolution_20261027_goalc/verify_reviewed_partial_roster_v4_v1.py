"""Verify every canonical row, unchanged predecessors and exact new outcomes."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

old_path=inv.BASE/'roster_reviewed_partial_v3/complete.json'
new_path=inv.BASE/'roster_reviewed_partial_v4/complete.json'
selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'
old,new,selection=map(inv.cache.read,[old_path,new_path,selection_path])
assert inv.file_sha(selection_path)=='C93C6A8B29D5FB3EF9769346C1B37383FEE8F45557139324757793F42DD0759A'
prior=inv.cache.read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json')
assert selection['rows'][:len(prior['rows'])]==prior['rows']
added={row['original_text_sha256']:row for row in selection['rows'][len(prior['rows']):]}
assert len(added)==123


def stable_row_digest(row):
    value={key:val for key,val in row.items() if key!='evidence'}
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()


before={};old_counts=Counter()
inv.verify(old_path.parent/old['records_directory'],old['manifest'])
for row in inv.cache.rows(old_path.parent/old['records_directory'],old['manifest']):
    key=row['original_text_sha256'];assert key not in before
    before[key]=(stable_row_digest(row),row['decision'],row['id']);old_counts[row['decision']]+=1
assert len(before)==297539 and dict(old_counts)==old['unique_counts']
inv.verify(new_path.parent/new['records_directory'],new['manifest'])
after=set();changes=[];counts=Counter();unchanged=0
for row in inv.cache.rows(new_path.parent/new['records_directory'],new['manifest']):
    key=row['original_text_sha256'];assert key in before and key not in after;after.add(key)
    counts[row['decision']]+=1
    if key not in added:
        assert stable_row_digest(row)==before[key][0],('unapproved predecessor change',row['id'])
        unchanged+=1
    else:
        expected=added[key]['selected']
        assert before[key][1]=='HOLD' and row['decision']==expected['decision']
        assert row['clean_text_sha256']==expected['clean_text_sha256'] and row['root_approved'] is True
        if row['decision']=='EDIT':assert inv.sha(row['text'])==row['clean_text_sha256']
        changes.append(dict(id=row['id'],original_text_sha256=key,before='HOLD',after=row['decision']))
    if key=='B148A48D8DC8EFA1D252E08E3F5240893938C381A9E1420E27123CC1C8961E5C':
        assert row['decision']=='HOLD' and 'text' not in row and row['root_approved'] is False
assert after==set(before) and len(changes)==123 and unchanged==297416
assert dict(counts)==new['unique_counts'] and counts['HOLD']==70107
assert new['remaining_hold']==109931 and new['reviewed_hold']==38 and new['unprocessed']==109893
assert new['counts']==old['counts']=={'documents':460695,'input_ids':462874291}
approval=inv.cache.read(ROOT/new['approval']['path'])
assert inv.file_sha(ROOT/new['approval']['path'])==new['approval']['sha256']
assert len(approval['changed_unique_dispositions'])==123
assert {row['original_text_sha256'] for row in changes}==set(added)
report=dict(status='ALL_ROSTER4_CANONICAL_ROWS_AND_EXACT_ROOT12_DELTA_VERIFIED_NOT_CACHE_BUILD',
    canonical_sources=297539,unchanged_predecessor_rows=unchanged,changed_sources=len(changes),
    changes=changes,unique_counts=dict(counts),positions=460695,original_input_ids=462874291,
    expected_cache_HOLD_positions=109931,reviewed_HOLD_positions=38,unprocessed_positions=109893,
    actual_new_cache_built=False,protected_original_or_candidate_TXT_opens=0,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [old_path,new_path,selection_path,Path(__file__)]},
    goal_complete=False,training_authorized=False)
out=AUDIT/'ROOT12_ROSTER_V4_INDEPENDENT_VERIFIED_V1.json'
assert not out.exists();inv.write_json(out,report)
print(json.dumps(dict(status=report['status'],canonical_sources=297539,changed_sources=123,
    unchanged_predecessor_rows=unchanged,remaining_hold=109931,sha256=inv.file_sha(out))))
