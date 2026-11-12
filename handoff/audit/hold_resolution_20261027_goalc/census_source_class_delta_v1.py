"""Apply a pinned narrow source-class rule once across current remaining queues.

Writes only delta identity/proof metadata. Nonmatches, original text and proposed
bodies are not copied. The frozen prior rule chain and source manifests are reused.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from selection_metadata_store_v1 import SelectionStore
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
    for name,expected in config['code_pins'].items():
        assert inv.file_sha(ROOT/name)==expected,name
        pins[name]=expected
    inherited=read(ROOT/config['prior_census']['path'],config['prior_census']['sha256'])
    for name,expected in inherited['input_pins'].items():
        assert inv.file_sha(ROOT/name)==expected,name
        pins[name]=expected
    modules=[]
    for name in [config['previous_policy'],config['proposed_policy'],config['source_class_module']]:
        assert name.startswith('scripts.p106b_hold_resolution_')
        assert name.replace('.','/')+'.py' in config['code_pins']
        modules.append(importlib.import_module(name))
    previous,policy,source_class=modules
    opaque=read(ROOT/config['hold_basis']['path'],config['hold_basis']['sha256'])
    selection_pin=config['selection']
    selection=SelectionStore(AUDIT).read(ROOT/selection_pin['path'],selection_pin['sha256'])
    pins[selection_pin['path']]=selection_pin['sha256']
    hold_hashes=set(opaque['hold_hashes'])-{r['original_text_sha256'] for r in selection['rows']
                                         if r['selected']['decision']!='HOLD'}
    assert len(hold_hashes)==config['expected_remaining_unique']
    blocked_ids=set(guard['restricted_ids'])|set(guard['trusted_metadata'])
    blocked_hashes=set(guard['restricted_hashes'])
    individual_hashes={r['original_text_sha256'] for r in selection['rows'] if r['selected']['decision']=='HOLD'}
    stage=read(ROOT/config['stage']['path'],config['stage']['sha256'])
    for spec in stage['coverage']+[config['counter_snapshot']]:
        summary=read(inv.BASE/(spec['cohort']+'_snapshots')/spec['version']/'complete.json')
        assert not summary['errors']
        for shard in summary['shards']:
            for row in read(ROOT/shard['path'],shard['sha256']):
                if row.get('decision')=='NEEDS_ROOT':
                    blocked_ids.add(row['id'])
                    if row.get('original'):
                        individual_hashes.add(row['original']['sha256'])
    out=inv.BASE/config['metadata_directory_name']
    report_path=AUDIT/config['report_name']
    assert not out.exists() and not report_path.exists()
    writer=inv.cache.ShardWriter(out,'candidate_metadata',limit=3_999_999)
    seen=set()
    all_queued=set()
    counts,transitions,weights,failures=Counter(),Counter(),Counter(),Counter()
    started=time.monotonic()
    for group in ['remaining_field_title_readers_v1','remaining_other_types_readers_v1']:
        index=read(inv.BASE/group/'complete.json')
        for page in index['pages']:
            manifest=read(ROOT/page['path'],page['sha256'])
            for row in manifest['rows']:
                digest=row['original_text_sha256']
                all_queued.add(digest)
                if digest not in hold_hashes:
                    continue
                assert digest not in seen
                seen.add(digest)
                if (row['id'] in blocked_ids or digest in individual_hashes or any(
                        row[k]['sha256'] in blocked_hashes for k in ['original','candidate'])):
                    counts['protected_or_individual_not_opened']+=1
                    continue
                path=(ROOT/row['original']['path']).resolve()
                assert path.is_relative_to(inv.BASE) and not path.is_symlink()
                raw=path.read_bytes()
                assert hashlib.sha256(raw).hexdigest().upper()==row['original']['sha256']==digest
                counts['originals_SHA_verified']+=1
                original=raw.decode('utf-8')
                proof=source_class.prove(original)
                if proof is None:
                    counts['source_class_nonmatch']+=1
                    continue
                input_row=dict(row,text=original,previous_holds=[])
                before=previous.propose(input_row)
                after=policy.propose(input_row)
                candidate=after.get('candidate',after['text'])
                numeric=numeric_atom_changes(original,candidate)
                guards=dict(numeric_atoms=not numeric, code=policy.code_preserved(original,candidate),
                    unicode=policy.unicode_examples_preserved(original,candidate),
                    style=policy.semantic_style_preserved(original,candidate),
                    ordered=policy.ordered_deletion(original,candidate),
                    no_memo=not bool(inv.corpus.MEMOS.search(candidate)))
                eligible=before['decision']=='PENDING' and after['decision'] in {'KEEP','EDIT'} and all(guards.values())
                transitions[before['decision']+'_TO_'+after['decision']]+=1
                counts['new_terminal_candidates' if eligible else 'matched_not_new_terminal']+=1
                if eligible:
                    weights['new_terminal_positions']+=row['occurrences']
                failures.update(k for k,v in guards.items() if not v)
                proof_raw=(json.dumps(proof['proof'],ensure_ascii=False,sort_keys=True)+chr(10)).encode()
                writer.append(dict(id=row['id'],original=row['original'],prior_candidate=row['candidate'],
                    original_text_sha256=digest,occurrences=row['occurrences'],cohort=group,
                    source_manifest=dict(path=page['path'],sha256=page['sha256']),
                    before_decision=before['decision'],before_reasons=before['reasons'],
                    proposed_decision=after['decision'],proposed_reasons=after['reasons'],
                    proposed_body_sha256=inv.sha(candidate),proposed_characters=len(candidate),
                    source_class=proof['proof'],source_proof_count=len(proof['changes']),
                    source_proofs_sha256=hashlib.sha256(proof_raw).hexdigest().upper(),
                    guards=guards,numeric_flags=numeric,eligible_rule_candidate=eligible,
                    candidate_body_stored=False,root_approved=False,cache_admitted=False))
            assert_no_protected_opens()
    assert seen==hold_hashes&all_queued
    manifest=writer.close(lineage=dict(input_pins=pins,accepted_cache_changed=False))
    assert counts['originals_SHA_verified']==counts['source_class_nonmatch']+manifest['rows']
    pins[str(Path(__file__).relative_to(ROOT))]=inv.file_sha(Path(__file__))
    result=dict(status='WHOLE_CURRENT_QUEUE_NARROW_SOURCE_CLASS_DELTA_CANDIDATES_NOT_ADMISSION',
        rule=config['rule'],basis=config['selection'],covered_remaining_unique=len(seen),
        remaining_sources_outside_two_queues=len(hold_hashes-seen),counts=dict(counts),weights=dict(weights),
        transitions=dict(transitions),guard_failures=dict(failures),metadata_directory=str(out.relative_to(ROOT)),
        metadata_manifest=manifest,input_pins=pins,elapsed_seconds=time.monotonic()-started,
        source_original_or_candidate_modified=False,original_payload_bytes_copied=0,
        candidate_payload_bytes_stored=0,automatic_root_admissions=0,cache_admitted=0,
        goal_complete=False,training_authorized=False)
    inv.write_json(report_path,result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'metadata_manifest','input_pins','basis'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    args=parser.parse_args()
    config_path=Path(args.config).resolve()
    assert config_path.parent==AUDIT and not config_path.is_symlink()
    run(config_path)
