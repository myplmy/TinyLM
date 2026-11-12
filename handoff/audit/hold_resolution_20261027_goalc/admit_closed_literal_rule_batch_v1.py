"""Config-driven source-class admission with every literal proof and saved review."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse
import importlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from selection_metadata_store_v1 import SelectionStore
from close_remaining_heading_context_v1 import remaining_headings
from verify_category_metadata_delta_v1 import context_deferrals


def run(config_path,apply):
    guard.activate()
    config=json.loads(config_path.read_bytes())
    pins={}
    output=AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(config['next_selection'])+'.json')
    closure_path=AUDIT/(config['closure_stem']+'.json')
    storage_path=AUDIT/('ROOT'+str(config['next_selection'])+'_SELECTION_STORAGE_V1.json')
    assert not any(path.exists() for path in [output,closure_path,storage_path])

    def read(pin):
        path=ROOT/pin['path']
        assert not path.is_symlink() and (path.is_relative_to(AUDIT) or path.is_relative_to(guard.inv.BASE))
        assert guard.inv.file_sha(path)==pin['sha256'],str(path)
        pins[pin['path']]=pin['sha256']
        return json.loads(path.read_bytes())

    def pin_inputs(document):
        for name,sha in document.get('input_pins',{}).items():
            path=ROOT/name
            assert not path.is_symlink() and guard.inv.file_sha(path)==sha,name
            pins[name]=sha

    store=SelectionStore(AUDIT)
    prior=store.read(ROOT/config['prior_selection']['path'],config['prior_selection']['sha256'])
    verified=read(config['prior_verification'])
    verified_selection=verified.get('selection')
    if verified_selection is not None:
        assert verified_selection==config['prior_selection']
    else:
        assert verified['input_pins'][config['prior_selection']['path']]==config['prior_selection']['sha256']
        assert verified['selected_sources']==len(prior['rows'])
    scope=ROOT/config['context_audit']['path']
    assert guard.inv.file_sha(scope)==config['context_audit']['sha256']
    stage=read(config['stage'])
    specs=[dict(row,version=config['snapshot_overrides'].get(row['cohort'],row['version'])) for row in stage['coverage']]
    specs+=config['extra_snapshots']
    contract=guard.checked_contract()
    blocked_ids=set(contract['restricted_ids'])
    blocked_hashes=set(contract['restricted_hashes'])
    reviews=defaultdict(list)
    reuse={}
    for spec in specs:
        path=guard.inv.BASE/(spec['cohort']+'_snapshots')/spec['version']/'complete.json'
        summary=read(dict(path=str(path.relative_to(ROOT)),sha256=guard.inv.file_sha(path)))
        assert not summary['errors']
        for shard in summary['shards']:
            for row in read(shard):
                if row.get('decision')=='NEEDS_ROOT':
                    blocked_ids.add(row['id'])
                    if row.get('original'):
                        blocked_hashes.add(row['original']['sha256'])
                if row.get('review'):
                    reviews[row['id']].append(row)
                if row.get('body') and row.get('clean_text_sha256') not in blocked_hashes:
                    reuse.setdefault(row['clean_text_sha256'],row['body'])
    ids={row['id'] for row in prior['rows']}
    hashes={row['original_text_sha256'] for row in prior['rows']}
    selected=[]
    checks=[]
    deferred=[]
    planned_bodies={}
    body_counts=Counter()
    for batch in config['batches']:
        census=read(batch['census']);pin_inputs(census)
        literal=read(batch['literal']);pin_inputs(literal)
        closure=read(batch['context_closure']);pin_inputs(closure)
        literal_rows={row['id']:row for row in literal['rows']}
        context_rows={row['id']:row for row in closure['rows']}
        policy=importlib.import_module(batch['policy'])
        verifier=importlib.import_module(batch['literal_verifier'])
        directory=ROOT/census['metadata_directory']
        guard.inv.verify(directory,census['metadata_manifest'])
        candidates=[row for row in guard.inv.cache.rows(directory,census['metadata_manifest']) if row['eligible_rule_candidate']]
        assert len(candidates)==len(literal_rows)==len(context_rows)==batch['expected_candidates']
        for row in candidates:
            key=row['id'];original=row['original'];proof=literal_rows[key];context=context_rows[key]
            reason=None
            if not context['eligible'] or not proof['eligible_narrow_literal_delta'] or not all(proof['guards'].values()):
                reason='INDEPENDENT_LITERAL_OR_REMAINING_CONTENT_GATE_DEFERRED'
            elif key in ids or original['sha256'] in hashes:
                reason='ALREADY_SELECTED_PRIOR_OR_SAME_BATCH_PRESERVED'
            elif key in blocked_ids or original['sha256'] in blocked_hashes or row['prior_candidate']['sha256'] in blocked_hashes:
                reason='INDIVIDUAL_OR_PROTECTED_HOLD_NOT_RELEASED'
            if reason:
                deferred.append(dict(id=key,batch=batch['label'],reason=reason));continue
            assert proof['original']==context['original']==original
            assert proof['proposed_body_sha256']==context['proposed_body_sha256']==row['proposed_body_sha256']
            guard.require_payload_context(dict(source_id=key,original=original,candidate=row['prior_candidate']))
            path=ROOT/original['path']
            assert not path.is_symlink() and path.resolve().is_relative_to(guard.inv.BASE)
            source=path.read_bytes().decode('utf-8')
            assert guard.inv.sha(source)==original['sha256']
            proposal=policy.propose(dict(id=key,text=source,complete_eos=True,valid_utf8=True))
            text=proposal.get('candidate',proposal['text'])
            decision=proposal['decision'];digest=guard.inv.sha(text)
            assert decision==row['proposed_decision'] and digest==row['proposed_body_sha256']
            fresh=verifier.evaluate(source,text,decision) if batch['decision_argument'] else verifier.evaluate(source,text)
            assert fresh=={name:proof[name] for name in fresh} and all(fresh['guards'].values()), (
                key,batch['label'],[name for name in fresh if fresh[name]!=proof[name]])
            assert not remaining_headings(text)
            extra=context_deferrals(text)
            if extra:
                deferred.append(dict(id=key,batch=batch['label'],reason='ADDITIONAL_REMAINING_BODY_CONTEXT',details=extra));continue
            saved=[];conflicts=[]
            for item in reviews[key]:
                review=item['review']
                assert guard.inv.file_sha(ROOT/review['path'])==review['sha256']
                pins[review['path']]=review['sha256']
                if not item.get('body') or not item.get('clean_text_sha256'):
                    conflicts.append('SAVED_NONADMISSION');continue
                if item['clean_text_sha256'] in blocked_hashes:
                    conflicts.append('PROTECTED_SAVED_BODY');continue
                manual_path=ROOT/item['body']
                assert not manual_path.is_symlink() and manual_path.resolve().is_relative_to(guard.inv.BASE)
                manual=manual_path.read_bytes()
                assert guard.inv.sha(manual.decode('utf-8'))==item['clean_text_sha256']
                if manual.rstrip(b'\r\n')!=text.encode('utf-8').rstrip(b'\r\n'):
                    conflicts.append('DIFFERENT_SAVED_BODY');continue
                saved.append(review)
            if conflicts:
                deferred.append(dict(id=key,batch=batch['label'],reason='SAVED_REVIEW_CONTEXT_CONFLICT',details=conflicts));continue
            raw=text.encode('utf-8')
            assert 0<len(raw)<20_000_000 and digest not in blocked_hashes
            if decision=='KEEP':
                assert text==source
                body=original['path'];body_counts['original_kept_without_copy']+=1
            elif digest in reuse:
                body=reuse[digest]
                body_path=ROOT/body
                assert not body_path.is_symlink() and body_path.resolve().is_relative_to(guard.inv.BASE)
                assert (planned_bodies[body] if body in planned_bodies else body_path.read_bytes())==raw
                body_counts['existing_identical_body_reused']+=1
            else:
                body_path=guard.inv.BASE/'rule_literal_approved_bodies_v1'/digest[:2]/(digest+'.txt')
                body=str(body_path.relative_to(ROOT))
                if body_path.exists():
                    assert not body_path.is_symlink() and body_path.read_bytes()==raw
                    body_counts['existing_hash_body_reused']+=1
                else:
                    planned_bodies[body]=raw
                    body_counts['new_program_bodies']+=1
                    body_counts['new_program_body_bytes']+=len(raw)
                reuse[digest]=body
            choice=dict(cohort='source_class_'+batch['label'].lower()+'_literal_v1',decision=decision,
                body=body,clean_text_sha256=digest,original=original,review=config['context_audit'],
                reason='기존 본문과 분류 값을 보존하고 실제 빈 별칭·빈 EOF 표제만 정리했다. 독립 문자 proof와 추가 문맥 반례·저장 리뷰를 모두 확인했다.',
                author_output=None,compare_source=None,root_approved=True,
                approval_mode='SOURCE_CLASS_RULE_WITH_ALL_ROW_LITERAL_PROOFS',
                individual_human_full_text_read_claimed=False,program_derived_policy=policy.RULES,
                independent_saved_context_reviews=saved)
            selected.append(dict(id=key,original_text_sha256=original['sha256'],selected=choice,
                original_paths=[original],root_approved=True,cache_admitted=False,
                status='ROOT_APPROVED_NARROW_POLICY_DELTA_WITH_SOURCE_CLASS_CONTEXT_AUDIT',
                guard_closure_id=config['closure_stem']))
            checks.append(dict(id=key,batch=batch['label'],original=original,body=dict(path=body,sha256=digest),
                occurrences=row['occurrences'],guards=fresh['guards'],literal_proof=batch['literal'],
                content_context_closure=batch['context_closure'],saved_reviews=saved,
                independent_populated_stream_sha256=fresh['source_populated_stream_sha256'],
                individual_human_full_text_read_claimed=False))
            ids.add(key);hashes.add(original['sha256'])
    assert selected and len(selected)<=config['maximum_new_unique']
    assert len(selected)+len(deferred)==sum(b['expected_candidates'] for b in config['batches'])
    guard.assert_no_protected_opens()
    result=dict(new_unique=len(selected),new_positions=sum(c['occurrences'] for c in checks),
        deferred=len(deferred),deferred_reasons=dict(Counter(row['reason'] for row in deferred)),
        body_counts=dict(body_counts),protected_payload_open_attempts=0,
        expected_HOLD_unique=prior['expected_roster_HOLD_unique']-len(selected),
        expected_HOLD_positions=prior['expected_roster_HOLD_positions']-sum(c['occurrences'] for c in checks),
        additional_human_full_read_credit=0,cache_admitted=False)
    if not apply:
        print(json.dumps(dict(result,status='REVIEWABLE_DRY_RUN_NO_FILES_WRITTEN'),ensure_ascii=False));return
    for name,raw in planned_bodies.items():
        path=ROOT/name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    for path in [config_path,Path(__file__),scope,guard.CONTRACT,AUDIT/'active_guard_v6_preflight_v1.py',
                 AUDIT/'selection_metadata_store_v1.py',AUDIT/'close_remaining_heading_context_v1.py']:
        pins[str(path.relative_to(ROOT))]=guard.inv.file_sha(path)
    pins[config['prior_selection']['path']]=config['prior_selection']['sha256']
    assert not closure_path.exists()
    closure=dict(result,status='ROOT_APPROVED_CLOSED_LITERAL_RULE_BATCH',checks=checks,deferred=deferred,
        root_approved=True,automatic_guard_waivers=0,active_guard_sha256=guard.EXPECTED,input_pins=pins,
        full_individual_human_read_claimed_for_rule_batch=False,root_manual_training_TXT_authored=0,
        whole_corpus_semantic_completion=False,goal_complete=False,training_authorized=False)
    guard.inv.write_json(closure_path,closure)
    rows=prior['rows']+selected
    document=dict(prior,rows=rows,source_ids=len(rows),selected_sources=len(rows),
        counts=dict(Counter(row['selected']['decision'] for row in rows)),prior_selection=config['prior_selection'],
        prior_selected_rows_preserved_exactly=len(prior['rows']),new_approved_sources=len(selected),
        new_approved_positions=result['new_positions'],closure=dict(path=str(closure_path.relative_to(ROOT)),sha256=guard.inv.file_sha(closure_path)),
        expected_roster_HOLD_unique=result['expected_HOLD_unique'],expected_roster_HOLD_positions=result['expected_HOLD_positions'],
        input_pins=dict(prior['input_pins'],**pins),whole_corpus_semantic_completion=False,
        cache_admitted=False,goal_complete=False,training_authorized=False)
    assert not output.exists()
    storage=store.write(output,document,force_sharded=True)
    guard.inv.write_json(storage_path,storage)
    guard.assert_no_protected_opens()
    print(json.dumps(dict(result,status='ROOT_SELECTED_NOT_CACHE_ADMITTED',selection_sha256=guard.inv.file_sha(output)),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    path=Path(args.config).resolve()
    assert path.parent==AUDIT and not path.is_symlink()
    run(path,args.apply)
