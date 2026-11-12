"""Independently decode every native shard and check source-class proof joins."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
frozen=AUDIT/'verify_sharded_counter_selection_v1.py'
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='B929CAE1A25DCA1831DBB8F8197A76CBF8CB88DA5970DB2362CE7879C3922F9F'
prefix=raw.decode().split('parser = argparse.ArgumentParser')[0]
scope=dict(__name__='independent_closed_rule_native_reader',__file__=str(Path(__file__)))
exec(compile(prefix,str(frozen),'exec'),scope)
read,native,pins=scope['read'],scope['native'],scope['pins']


def metadata(pin):
    return json.loads(read(ROOT/pin['path'],pin['sha256']))


def run(config_path,expected_sha):
    config=json.loads(read(config_path))
    path=AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(config['next_selection'])+'.json')
    selection,storage=native(path,expected_sha)
    assert selection['prior_selection']==config['prior_selection']
    prior,_=native(ROOT/config['prior_selection']['path'],config['prior_selection']['sha256'])
    assert selection['rows'][:len(prior['rows'])]==prior['rows']
    added=selection['rows'][len(prior['rows']):]
    closure=metadata(selection['closure'])
    assert closure['root_approved'] is True
    assert closure['automatic_guard_waivers']==closure['protected_payload_open_attempts']==closure['root_manual_training_TXT_authored']==0
    assert closure['full_individual_human_read_claimed_for_rule_batch'] is False
    guard_pin='handoff/audit/hold_resolution_20261027_goalc/GUARDED_SOURCE_METADATA_CONTRACT_V6.json'
    guard=json.loads(read(ROOT/guard_pin,closure['active_guard_sha256']))
    assert closure['active_guard_sha256']=='5AAFF02F7B2709C06843221FBE39C700909685809FA845253B6A749553721C0E'
    candidates={};literal={};context={};labels={}
    for batch in config['batches']:
        census=metadata(batch['census'])
        digest=hashlib.sha256();count=0
        for shard in census['metadata_manifest']['shards']:
            payload=read(ROOT/census['metadata_directory']/shard['path'],shard['sha256'])
            assert len(payload)==shard['bytes']
            digest.update(payload)
            group=[json.loads(line) for line in payload.splitlines()]
            assert len(group)==shard['rows']
            count+=len(group)
            for row in group:
                if row['eligible_rule_candidate']:
                    key=(batch['label'],row['id'])
                    assert key not in candidates
                    candidates[key]=row
        assert count==census['metadata_manifest']['rows']
        assert digest.hexdigest().upper()==census['metadata_manifest']['concat_sha256']
        for row in metadata(batch['literal'])['rows']:
            literal[(batch['label'],row['id'])]=row
        for row in metadata(batch['context_closure'])['rows']:
            context[(batch['label'],row['id'])]=row
        labels[batch['label']]=batch
    checks={row['id']:row for row in closure['checks']}
    assert len(added)==len(checks)==closure['new_unique']==selection['new_approved_sources']
    assert {row['id'] for row in added}==set(checks)
    deferred={(row['batch'],row['id']) for row in closure['deferred']}
    chosen={(row['batch'],row['id']) for row in closure['checks']}
    assert not deferred&chosen and deferred|chosen==set(candidates)
    prior_ids={row['id'] for row in prior['rows']}
    prior_hashes={row['original_text_sha256'] for row in prior['rows']}
    for row in added:
        check=checks[row['id']];key=(check['batch'],row['id'])
        original=candidates[key];proof=literal[key];content=context[key];choice=row['selected']
        assert row['id'] not in prior_ids and row['original_text_sha256'] not in prior_hashes
        assert row['original_text_sha256']==original['original_text_sha256']==proof['original']['sha256']
        assert row['root_approved'] is True and row['cache_admitted'] is False
        assert choice['decision']==original['proposed_decision'] in {'KEEP','EDIT'}
        assert choice['root_approved'] is True
        assert choice['approval_mode']=='SOURCE_CLASS_RULE_WITH_ALL_ROW_LITERAL_PROOFS'
        assert choice['individual_human_full_text_read_claimed'] is False
        assert choice['original']==original['original']==proof['original']==content['original']==check['original']
        assert choice['clean_text_sha256']==original['proposed_body_sha256']==proof['proposed_body_sha256']==content['proposed_body_sha256']==check['body']['sha256']
        assert choice['body']==check['body']['path']
        assert content['eligible'] is True and not content['remaining_content_headings']
        assert proof['eligible_narrow_literal_delta'] is True and all(proof['guards'].values())
        assert check['guards']==proof['guards'] and all(check['guards'].values())
        assert proof['source_populated_stream_sha256']==proof['candidate_populated_stream_sha256']==check['independent_populated_stream_sha256']
        assert check['occurrences']==original['occurrences']
        assert choice['review']==config['context_audit']
        assert row['id'] not in guard['restricted_ids']
        assert row['original_text_sha256'] not in guard['restricted_hashes']
        assert choice['clean_text_sha256'] not in guard['restricted_hashes']
        if choice['decision']=='KEEP':
            assert choice['body']==choice['original']['path']
            assert choice['clean_text_sha256']==choice['original']['sha256']
    positions=sum(row['occurrences'] for row in closure['checks'])
    assert positions==closure['new_positions']==selection['new_approved_positions']
    assert selection['expected_roster_HOLD_unique']==prior['expected_roster_HOLD_unique']-len(added)
    assert selection['expected_roster_HOLD_positions']==prior['expected_roster_HOLD_positions']-positions
    assert Counter(row['selected']['decision'] for row in selection['rows'])==selection['counts']
    for name,sha in closure['input_pins'].items():
        target=ROOT/name
        assert not target.is_symlink() and target.suffix!='.txt'
        if target.is_relative_to(ROOT/'scripts'):
            assert target.name.startswith(('p106b_hold_resolution_','test_p106b_hold_resolution_'))
            assert hashlib.sha256(target.read_bytes()).hexdigest().upper()==sha
            pins[name]=sha
        else:
            read(target,sha)
    pins[str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
    report=dict(status='CLOSED_LITERAL_BATCH_NATIVE_SELECTION_INDEPENDENTLY_RECONSTRUCTED',
        selection=dict(path=str(path.relative_to(ROOT)),sha256=expected_sha),
        preserved_prior_rows=len(prior['rows']),new_sources=len(added),new_positions=positions,
        expected_HOLD_unique=selection['expected_roster_HOLD_unique'],expected_HOLD_positions=selection['expected_roster_HOLD_positions'],
        storage=storage,protected_payload_open_attempts=0,original_or_candidate_TXT_opens=0,
        independent_source_literal_and_context_proofs_joined=True,input_pins=pins,
        cache_admitted=False,goal_complete=False,training_authorized=False)
    output=AUDIT/('ROOT'+str(config['next_selection'])+'_CLOSED_LITERAL_SELECTION_INDEPENDENT_VERIFIED_V1.json')
    assert not output.exists()
    with output.open('xb') as stream:
        stream.write((json.dumps(report,ensure_ascii=False,indent=2)+chr(10)).encode())
    print(json.dumps({k:v for k,v in report.items() if k not in {'input_pins','storage'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--expected-sha',required=True)
    args=parser.parse_args()
    config_path=Path(args.config).resolve()
    assert config_path.parent==AUDIT and not config_path.is_symlink()
    run(config_path,args.expected_sha)
