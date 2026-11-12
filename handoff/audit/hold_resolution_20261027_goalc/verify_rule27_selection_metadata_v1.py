"""Reconstruct the mixed selection independently of its writer and loader."""
from pathlib import Path
import hashlib
import json

AUDIT=Path(__file__).resolve().parent; ROOT=AUDIT.parents[2]
frozen=AUDIT/'verify_sharded_counter_selection_v1.py'; raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='B929CAE1A25DCA1831DBB8F8197A76CBF8CB88DA5970DB2362CE7879C3922F9F'
prefix=raw.decode('utf-8').split('parser = argparse.ArgumentParser')[0]
scope=dict(__name__='independent_native_selection_reconstruction',__file__=str(Path(__file__)))
exec(compile(prefix,str(frozen),'exec'),scope)
read=scope['read']; native=scope['native']; pins=scope['pins']


def metadata(path,expected=None):
    return json.loads(read(path,expected))


path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V34.json'
selection_sha=hashlib.sha256(path.read_bytes()).hexdigest().upper()
selection,storage=native(path,selection_sha)
prior_pin=selection['prior_selection']; assert Path(prior_pin['path']).name=='ROOT_AUTHORED_SELECTIONS_V33.json'
assert prior_pin['sha256']=='9F99AA65B6D42EE78DE4D1C09A13C57BF7E15B3EECAE724BC948B69A33A05DE0'
previous,_=native(ROOT/prior_pin['path'],prior_pin['sha256'])
assert selection['rows'][:len(previous['rows'])]==previous['rows']
new=selection['rows'][len(previous['rows']):]
closure_pin=selection['closure']; closure=metadata(ROOT/closure_pin['path'],closure_pin['sha256'])
assert closure['root_approved'] is True
assert closure['automatic_guard_waivers']==closure['protected_payload_open_attempts']==0
assert closure['full_individual_human_read_claimed_for_rule_batch'] is False
assert closure['root_manual_training_TXT_authored']==0
assert closure['active_guard_sha256']=='01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338'
census=metadata(AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json',
    '0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6')
manifest=census['metadata_manifest']; directory=ROOT/census['metadata_directory']; candidates={}
stream_sha=hashlib.sha256(); total=0
for shard in manifest['shards']:
    payload=read(directory/shard['path'],shard['sha256']); assert len(payload)==shard['bytes']
    stream_sha.update(payload); group=[json.loads(line) for line in payload.splitlines()]
    assert len(group)==shard['rows']; total+=len(group)
    for row in group:
        if row['eligible_rule_candidate']:candidates[row['id']]=row
assert total==manifest['rows'] and stream_sha.hexdigest().upper()==manifest['concat_sha256']
assert len(candidates)==478
literal=metadata(AUDIT/'RULE27_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json',
    '67CBD366AEE45E82A32495173507F43512259367B381154E0DC659490635F2A6')
literal_rows={r['id']:r for r in literal['rows']}
checks={r['id']:r for r in closure['checks']}; new_ids={r['id'] for r in new}
assert len(checks)==len(closure['checks'])==len(new)==len(new_ids)
assert new_ids==set(checks)
deferred={r['id'] for r in closure['deferred']}
assert not deferred&new_ids and deferred|new_ids==set(candidates)
prior_ids={r['id'] for r in previous['rows']}
for row in new:
    key=row['id']; source=candidates[key]; check=checks[key]; proof=literal_rows[key]; choice=row['selected']
    assert key not in prior_ids and row['original_text_sha256']==source['original_text_sha256']
    assert row['root_approved'] is True and row['cache_admitted'] is False
    assert choice['decision']=='EDIT' and choice['root_approved'] is True
    assert choice['approval_mode']=='SOURCE_CLASS_RULE_WITH_ALL_ROW_LITERAL_PROOFS'
    assert choice['individual_human_full_text_read_claimed'] is False
    assert choice['original']==source['original']==check['original']==proof['original']
    assert choice['clean_text_sha256']==source['proposed_body_sha256']==check['body']['sha256']==proof['proposed_body_sha256']
    assert choice['body']==check['body']['path']
    assert choice['review']['path'].endswith('/RULE27_BATCH_ADMISSION_F3_F4_V1.md')
    read(ROOT/choice['review']['path'],choice['review']['sha256'])
    assert proof['eligible_narrow_literal_delta'] is True and all(proof['guards'].values())
    assert check['guards']==proof['guards']
    assert check['source_populated_stream_sha256']==check['candidate_populated_stream_sha256']==proof['source_populated_stream_sha256']
    assert check['occurrences']==source['occurrences']
    assert check['census_source_proofs_sha256']==source['source_proofs_sha256']
new_positions=sum(candidates[key]['occurrences'] for key in new_ids)
assert len(new)==closure['root_approved_new_sources']==selection['new_approved_sources']
assert new_positions==closure['root_approved_new_positions']==selection['new_approved_positions']
assert selection['expected_roster_HOLD_unique']==previous['expected_roster_HOLD_unique']-len(new)
assert selection['expected_roster_HOLD_positions']==previous['expected_roster_HOLD_positions']-new_positions
assert scope['Counter'](r['selected']['decision'] for r in selection['rows'])==selection['counts']
guard=metadata(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json',closure['active_guard_sha256'])
assert not new_ids&set(guard['restricted_ids'])
for row in new:
    assert row['original_text_sha256'] not in guard['restricted_hashes']
    assert row['selected']['clean_text_sha256'] not in guard['restricted_hashes']
allowed_code={ROOT/'scripts/p106b_hold_resolution_disambiguation_v1.py',ROOT/'scripts/p106b_hold_resolution_policy_v27.py'}
for name,expected in closure['input_pins'].items():
    target=ROOT/name
    if target in allowed_code:
        assert not target.is_symlink() and hashlib.sha256(target.read_bytes()).hexdigest().upper()==expected
        pins[name]=expected
    else:read(target,expected)
pins[str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
receipt=dict(status='RULE27_SHARDED_SELECTION_INDEPENDENTLY_RECONSTRUCTED_AND_RECOUNTED',
    selection=dict(path=str(path.relative_to(ROOT)),sha256=selection_sha),
    preserved_prior_rows=len(previous['rows']),new_sources=len(new),new_positions=new_positions,
    expected_HOLD_unique=selection['expected_roster_HOLD_unique'],expected_HOLD_positions=selection['expected_roster_HOLD_positions'],
    individual_human_full_read_claimed_for_rule_batch=False,all_source_literal_proofs_closed=True,
    storage=storage,original_or_candidate_TXT_opens=0,input_pins=pins,
    cache_admitted=False,goal_complete=False,training_authorized=False)
out=AUDIT/'ROOT34_RULE27_SELECTION_INDEPENDENT_VERIFIED_V1.json'
with out.open('xb') as stream:stream.write((json.dumps(receipt,ensure_ascii=False,indent=2)+chr(10)).encode())
print(json.dumps({k:receipt[k] for k in ['status','preserved_prior_rows','new_sources','new_positions','expected_HOLD_positions']},ensure_ascii=False))
