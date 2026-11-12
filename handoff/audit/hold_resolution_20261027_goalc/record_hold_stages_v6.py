"""Keep human full reads separate from approved source-class rule processing."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent; ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens
from selection_metadata_store_v1 import SelectionStore


def reconcile(human,rule,root_ids,official_hold,expected_hold,initial=110173,prior_hold=38,initial_unique=70192):
    assert all(isinstance(v,int) and v>0 for values in [human,rule] for v in values.values())
    assert all(human[key]==rule[key] for key in set(human)&set(rule))
    processed=dict(human);processed.update(rule)
    assert root_ids<=set(processed)
    human_positions=sum(human.values());processed_positions=sum(processed.values())
    root_positions=sum(processed[key] for key in root_ids)
    assert initial-root_positions==expected_hold
    assert expected_hold<=official_hold<=initial
    unprocessed=initial-prior_hold-processed_positions
    assert unprocessed>=0 and len(processed)<=initial_unique
    partition=dict(unprocessed_by_human_or_approved_rule=unprocessed,
        processed_not_ROOT_admitted=processed_positions-root_positions,
        ROOT_admitted_cache_pending=official_hold-expected_hold,prior_reviewed_HOLD=prior_hold)
    assert all(v>=0 for v in partition.values()) and sum(partition.values())==official_hold
    return dict(fresh_first_review_unique=len(human),fresh_first_review_positions=human_positions,
        still_first_unreviewed_unique=initial_unique-len(human),
        still_first_unreviewed_positions=initial-prior_hold-human_positions,
        approved_rule_processed_unique=len(rule),approved_rule_processed_positions=sum(rule.values()),
        rule_processed_without_individual_human_full_read_unique=len(set(rule)-set(human)),
        rule_processed_without_individual_human_full_read_positions=sum(rule[k] for k in set(rule)-set(human)),
        processed_by_human_or_approved_rule_unique=len(processed),
        processed_by_human_or_approved_rule_positions=processed_positions,
        unprocessed_by_both_unique=initial_unique-len(processed),
        unprocessed_by_both_positions=unprocessed,
        ROOT_adopted_unique_since_ROOT11=len(root_ids),ROOT_adopted_positions_since_110173=root_positions,
        official_stage_partition=partition)


def run(config_path):
    activate();guard=checked_contract();pins={}

    def read(path,expected=None):
        raw=path.read_bytes();actual=hashlib.sha256(raw).hexdigest().upper()
        assert path.suffix!='.txt' and (expected is None or actual==expected),str(path)
        pins[str(path.relative_to(ROOT))]=actual
        return json.loads(raw)

    c=read(config_path)
    frozen=AUDIT/'analyze_hold110173_stagnation_v1.py';raw=frozen.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper()=='C462277BDC5BF706789BEA0A8D27D15A8FB0A52476C16447B473F3DDC40DD9FB'
    source=raw.decode().split('prior = read(')[0]
    anchor="VERSIONS = {1:'v20',2:'v16',3:'v14',4:'v14',5:'v12',6:'v15',7:'v15',8:'v13',9:'v7',10:'v1'}"
    assert source.count(anchor)==1
    source=source.replace(anchor,'VERSIONS = '+repr({int(k):v for k,v in c['field_versions'].items()}))
    source=source.replace("('remaining_literal_full_counter_v1','v21')",
        "('remaining_literal_full_counter_v1',"+repr(c['literal_version'])+")")
    source=source.replace('GUARDED_SOURCE_METADATA_CONTRACT_V2','GUARDED_SOURCE_METADATA_CONTRACT_V5')
    source=source.replace('E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B',
        '01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338')
    env=dict(__name__='immutable_human_review_metadata_prefix',__file__=str(Path(__file__)))
    exec(compile(source,str(frozen),'exec'),env);pins.update(env['pins'])
    prior=read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json');prior_ids={r['id'] for r in prior['rows']}
    assert set(env['reviewed'])&prior_ids=={'expanded_train:1046282'}
    fresh={key:value for key,value in env['reviewed'].items() if key not in prior_ids}
    human={key:value['source']['occurrences'] for key,value in fresh.items()}
    selection_path=ROOT/c['selection']
    selection=SelectionStore(AUDIT).read(selection_path,c['selection_sha256'])
    pins[c['selection']]=c['selection_sha256']
    assert selection['rows'][:len(prior['rows'])]==prior['rows']
    new=selection['rows'][len(prior['rows']):];root_ids={r['id'] for r in new}
    assert len(root_ids)==len(new)
    rule={};rule_closure_pins={}
    for row in new:
        choice=row['selected']
        if choice.get('approval_mode')!='SOURCE_CLASS_RULE_WITH_ALL_ROW_LITERAL_PROOFS':continue
        assert choice['individual_human_full_text_read_claimed'] is False
        stem=row['guard_closure_id'];path=AUDIT/(stem+'.json')
        if stem not in rule_closure_pins:
            closure=read(path)
            assert closure['root_approved'] is True and closure['automatic_guard_waivers']==0
            assert closure['protected_payload_open_attempts']==0
            rule_closure_pins[stem]={x['id']:x for x in closure['checks']}
        proof=rule_closure_pins[stem][row['id']]
        assert all(proof['guards'].values()) and proof['body']['sha256']==choice['clean_text_sha256']
        rule[row['id']]=proof['occurrences']
    roster=read(ROOT/c['roster_proof'],c['roster_proof_sha256'])
    assert roster['canonical_sources']==297539 and roster['expected_cache_HOLD_positions']==selection['expected_roster_HOLD_positions']
    cache=read(ROOT/c['cache_delta_proof'],c['cache_delta_proof_sha256'])
    chain=[read(AUDIT/name) for name in c['previous_cache_delta_proofs']]
    assert chain[0]['previous_hold_positions']==110173
    for left,right in zip(chain,chain[1:]+[cache]):assert left['current_hold_positions']==right['previous_hold_positions']
    for entry in chain+[cache]:assert entry['previous_hold_positions']-entry['current_hold_positions']==entry['resolved_positions']
    assert cache['current_hold_positions']==c['official_hold_positions']
    counts=reconcile(human,rule,root_ids,c['official_hold_positions'],selection['expected_roster_HOLD_positions'])
    cumulative=sum(x['resolved_positions'] for x in chain+[cache])
    assert cumulative==110173-c['official_hold_positions']
    built=read(ROOT/c['verified_cache_built']);outcomes=built['recovery_outcomes']
    assert outcomes['documents']==460695 and outcomes['input_ids']==462874291
    assert outcomes['HOLD']==c['official_hold_positions']
    counter=read(ROOT/c['counter_snapshot'],c['counter_snapshot_sha256']);assert not counter['errors']
    previous=read(ROOT/c['previous_stage_report'],c['previous_stage_report_sha256'])
    now=datetime.now(timezone.utc);interval=(now-datetime.fromisoformat(previous['recorded_at'])).total_seconds()
    root_parts={k:v for k,v in counts['official_stage_partition'].items() if k!='ROOT_admitted_cache_pending'}
    assert sum(root_parts.values())==selection['expected_roster_HOLD_positions']
    for path in [Path(__file__),frozen,AUDIT/'active_guard_v5_preflight_v1.py',AUDIT/'selection_metadata_store_v1.py']:
        pins[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest().upper()
    receipt=dict(status='HUMAN_FULL_READ_AND_APPROVED_RULE_STAGES_RECONCILED_SEPARATELY',
        stage_schema='HUMAN_FULL_READ_PLUS_APPROVED_SOURCE_CLASS_RULE_V1',recorded_at=now.isoformat(),
        coverage=env['coverage'],**counts,
        human_first_full_read_counts_not_increased_by_rule_processing=True,
        official_verified_cache=c['verified_cache'],official_verified_HOLD_positions=c['official_hold_positions'],
        cumulative_reduction_since_110173=cumulative,
        cumulative_new_unique_accepted_documents=sum(x['new_unique_accepted_documents'] for x in chain+[cache]),
        cumulative_additional_duplicate_positions_excluded=sum(x['additional_duplicate_positions_excluded'] for x in chain+[cache]),
        ROOT_selection=c['selection'],ROOT_expected_HOLD_positions=selection['expected_roster_HOLD_positions'],
        ROOT_remaining_decomposition=root_parts,ROOT_cache_pending_positions=c['official_hold_positions']-selection['expected_roster_HOLD_positions'],
        counter_saved=counter['records'],counter_errors=0,counter_new_first_review_credit=0,
        raw_input_composition=previous['raw_input_composition'],
        comparison_with_previous=dict(previous_recorded_at=previous['recorded_at'],elapsed_seconds=interval,
            new_first_review_unique=len(human)-previous['fresh_first_review_unique'],
            new_first_review_positions=sum(human.values())-previous['fresh_first_review_positions'],rate_is_not_an_ETA=True),
        direct_cause='Root had drifted into individual manual rereading. Source-class rules, inherited regressions, all-row preservation proofs and independent context reviews are now used for delta processing.',
        causal_percentages='NOT_ESTABLISHED',hardware_slowdown='NOT_ESTABLISHED',
        latest_cache_build_seconds=cache['actual_build_seconds'],latest_cache_consumer_seconds=cache['actual_consumer_seconds'],
        active_guard_sha256='01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338',
        recent_cache_limits=c.get('recent_cache_limits',[]),
        raw_original_or_candidate_TXT_opens=0,input_pins=pins,goal_complete=False,training_authorized=False)
    assert_no_protected_opens()
    out=AUDIT/c['output_basename'];payload=(json.dumps(receipt,ensure_ascii=False,indent=2)+chr(10)).encode()
    assert len(payload)<20_000_000
    with out.open('xb') as stream:stream.write(payload)
    print(json.dumps({k:receipt[k] for k in ['status','fresh_first_review_unique','approved_rule_processed_unique',
        'rule_processed_without_individual_human_full_read_unique','unprocessed_by_both_positions',
        'official_verified_HOLD_positions','ROOT_expected_HOLD_positions','ROOT_cache_pending_positions']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    path=Path(args.config).resolve();assert path.parent==AUDIT and not path.is_symlink()
    run(path)
