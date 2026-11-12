"""Reuse whole-queue nonmatches; recompute only a byte-pinned unchanged source class."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import sys
import time

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from numeric_atom_integrity_v1 import numeric_atom_changes
from scripts import p106b_hold_resolution_inventory as inv


def run(config_path):
    activate()
    guard=checked_contract()
    pins={}

    def read(path,expected=None):
        raw=path.read_bytes()
        digest=hashlib.sha256(raw).hexdigest().upper()
        assert expected is None or digest==expected,str(path)
        pins[str(path.relative_to(ROOT))]=digest
        return json.loads(raw)

    config=read(config_path)
    parent=read(ROOT/config['replay_parent']['path'],config['replay_parent']['sha256'])
    for name,expected in parent['input_pins'].items():
        assert inv.file_sha(ROOT/name)==expected,name
        pins[name]=expected
    for name,expected in config['code_pins'].items():
        assert inv.file_sha(ROOT/name)==expected,name
        pins[name]=expected
    policy=importlib.import_module(config['proposed_policy'])
    previous=importlib.import_module(config['previous_policy'])
    match=importlib.import_module(config['source_class_module'])
    # The exact same source-class implementation selected every parent row.
    match_name=config['source_class_module'].replace('.','/')+'.py'
    assert config['code_pins'][match_name]==parent['input_pins'][match_name]
    directory=ROOT/parent['metadata_directory']
    inv.verify(directory,parent['metadata_manifest'])
    out=inv.BASE/config['metadata_directory_name']
    assert out.parent==inv.BASE and not out.exists()
    report_path=AUDIT/config['report_name']
    assert report_path.parent==AUDIT and not report_path.exists()
    writer=inv.cache.ShardWriter(out,'candidate_metadata',limit=3_999_999)
    counts,weights,transitions,failures=Counter(),Counter(),Counter(),Counter()
    started=time.monotonic()
    for row in inv.cache.rows(directory,parent['metadata_manifest']):
        assert row['id'] not in guard['restricted_ids']
        assert row['original']['sha256'] not in guard['restricted_hashes']
        assert row['prior_candidate']['sha256'] not in guard['restricted_hashes']
        path=(ROOT/row['original']['path']).resolve()
        assert path.is_relative_to(inv.BASE) and not path.is_symlink()
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper()==row['original']['sha256']
        original=raw.decode('utf-8')
        source_proof=match.prove(original)
        assert source_proof and source_proof['proof']==row['source_class']
        source=dict(id=row['id'],text=original,complete_eos=True,valid_utf8=True,previous_holds=[])
        before=previous.propose(source)
        assert before['decision']==row['before_decision'] and before['reasons']==row['before_reasons']
        after=policy.propose(source)
        body=after.get('candidate',after['text'])
        if after['decision'] in {'KEEP','EDIT'}:
            assert body==after['text'],'obsolete pending candidate survived terminal proposal'
            assert (after['decision']=='KEEP')==(body==original)
        numeric=numeric_atom_changes(original,body)
        guards=dict(numeric_atoms=not numeric,code=policy.code_preserved(original,body),
            unicode=policy.unicode_examples_preserved(original,body),
            style=policy.semantic_style_preserved(original,body),
            ordered=policy.ordered_deletion(original,body),no_memo=not bool(inv.corpus.MEMOS.search(body)))
        eligible=before['decision']=='PENDING' and after['decision'] in {'KEEP','EDIT'} and all(guards.values())
        counts['originals_SHA_verified_this_run']+=1
        counts['new_terminal_candidates' if eligible else 'matched_not_new_terminal']+=1
        if eligible:
            weights['new_terminal_positions']+=row['occurrences']
        transitions[before['decision']+'_TO_'+after['decision']]+=1
        failures.update(k for k,v in guards.items() if not v)
        writer.append(dict(row,proposed_decision=after['decision'],proposed_reasons=after['reasons'],
            proposed_body_sha256=inv.sha(body),proposed_characters=len(body),guards=guards,
            numeric_flags=numeric,eligible_rule_candidate=eligible,root_approved=False,cache_admitted=False))
    assert counts['originals_SHA_verified_this_run']==parent['metadata_manifest']['rows']
    assert_no_protected_opens()
    pins[str(Path(__file__).relative_to(ROOT))]=inv.file_sha(Path(__file__))
    manifest=writer.close(lineage=dict(input_pins=pins,accepted_cache_changed=False))
    result=dict(status='WHOLE_QUEUE_COVERAGE_REUSED_UNCHANGED_CLASS_MATCHES_REVERIFIED_NOT_ADMISSION',
        rule=config['rule'],basis=parent['basis'],covered_remaining_unique=parent['covered_remaining_unique'],
        remaining_sources_outside_two_queues=parent['remaining_sources_outside_two_queues'],
        nonmatching_originals_reused_without_payload_read=parent['counts']['source_class_nonmatch'],
        protected_or_individual_not_opened_inherited=parent['counts']['protected_or_individual_not_opened'],
        counts=dict(counts),weights=dict(weights),transitions=dict(transitions),guard_failures=dict(failures),
        metadata_directory=str(out.relative_to(ROOT)),metadata_manifest=manifest,input_pins=pins,
        elapsed_seconds=time.monotonic()-started,source_original_or_candidate_modified=False,
        original_payload_bytes_copied=0,candidate_payload_bytes_stored=0,automatic_root_admissions=0,
        cache_admitted=0,goal_complete=False,training_authorized=False)
    inv.write_json(report_path,result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'metadata_manifest','input_pins','basis'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    args=parser.parse_args()
    path=Path(args.config).resolve()
    assert path.parent==AUDIT and not path.is_symlink()
    run(path)
