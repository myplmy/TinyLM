"""Exercise the actual cache class on every ROOT29 to ROOT39 source change."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys
import time

AUDIT=Path(__file__).resolve().parent
sys.path[:0]=[str(AUDIT),str(AUDIT.parents[2])]
import guarded_reviewed_cache_v10 as guarded
import guarded_scan_metadata_v1 as metadata
from selection_metadata_store_v1 import SelectionStore

ROOT,inv=guarded.ROOT,guarded.inv


def main():
    start=time.monotonic()
    output=AUDIT/'CACHE17_ROOT39_ACTUAL_DELTA_GUARDS_PREFLIGHT_V1.json'
    inv.require(not output.exists(),'preflight evidence already exists')
    store=SelectionStore(AUDIT)
    prior_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V29.json'
    current_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V39.json'
    prior=store.read(prior_path,'CD799C190B8BAED74DC210A441FB64420E311AA836771521B309808A12461B7B')
    current=store.read(current_path,'C4BA3D979C76082D9E59EA1BE6357C2AF6EAFB342C2EC1E06C2A25336FA01F84')
    prior_rows={row['id']:row for row in prior['rows']}
    delta=[row for row in current['rows'] if row!=prior_rows.get(row['id'])]
    inv.require(len(delta)==2551 and all(row['selected']['decision'] in {'KEEP','EDIT'} for row in delta),
        'unexpected delta or nonterminal choice')
    by_hash={row['original_text_sha256']:row for row in delta}
    inv.require(len(by_hash)==len(delta),'delta is not unique by original SHA')
    roster_path=inv.BASE/'roster_reviewed_partial_v29/complete.json'
    inv.require(inv.file_sha(roster_path)=='7A12C8FA95C9F241EFEFF479260A53679B1FF30A6368978D4482D49437A16B4C',
        'approved roster changed')
    roster=inv.cache.read(roster_path)
    records=roster_path.parent/roster['records_directory']
    inv.verify(records,roster['manifest'])
    proposals={}
    with patch.object(metadata,'FIELDS',metadata.FIELDS|{'decision','manual','clean_text_sha256'}):
        for shard in roster['manifest']['shards']:
            with (records/shard['path']).open('rb') as stream:
                for line in stream:
                    match=metadata.SOURCE_SHA.search(line)
                    inv.require(match is not None,'roster row lacks original hash')
                    if match[1].decode('ascii').upper() in by_hash:
                        row=metadata.project_metadata(line)
                        key=row['original_text_sha256']
                        inv.require(key not in proposals,'duplicate delta proposal')
                        proposals[key]=row
    inv.require(set(proposals)==set(by_hash),'delta proposal metadata incomplete')
    config=inv.cache.read(AUDIT/'CACHE16_ROOT39_ROSTER29_CONFIG_V1.json')
    results=[]
    with guarded.opaque_contract(AUDIT/config['opaque_contract'],config['opaque_contract_sha256']):
        with guarded.runtime(current_path) as inputs:
            with guarded.first.reviewed.reviewed_inputs():
                with guarded.first.reviewed.partial.revision():
                    cls=guarded.first.reviewed.ReviewedResolutionEngine
                    engine=object.__new__(cls)
                    engine.guard=inputs
                    engine.literal_cases=guarded.first.reviewed.literal.load_registry()
                    class_names=[c.__module__+'.'+c.__name__ for c in cls.__mro__]
                    inv.require(any(n.startswith('guarded_reviewed_cache_v6.') for n in class_names),
                        'actual opaque guard class was not installed')
                    for row in delta:
                        choice=row['selected'];key=row['original_text_sha256'];proposal=proposals[key]
                        inv.require(row.get('root_approved') is True and choice['decision']==proposal['decision']
                            and choice['clean_text_sha256']==proposal['clean_text_sha256'],
                            'roster choice differs from ROOT approval')
                        original=choice.get('original') or row['original_paths'][0]
                        body=dict(path=choice.get('body') or original['path'],sha256=choice['clean_text_sha256'])
                        guarded.guard.require_payload_context(dict(source_id=row['id'],original=original,candidate=body),
                            contract=inputs.document)
                        for pin in [original,body]:
                            path=ROOT/pin['path']
                            inv.require(path.resolve().is_relative_to(ROOT) and not path.is_symlink()
                                and inv.file_sha(path)==pin['sha256'],'exact source or body changed')
                        source=(ROOT/original['path']).read_bytes().decode('utf-8')
                        clean=(ROOT/body['path']).read_bytes().decode('utf-8')
                        inv.require(inv.sha(source)==key and inv.sha(clean)==body['sha256'],
                            'source or body decoding changed bytes')
                        engine.current=(dict(id=row['id'],original_text_sha256=key),3)
                        with patch.object(guarded.previous.inner_runtime.GuardedResolutionEngine,
                                'code_guard',guarded.BASE_CODE_GUARD):
                            old=engine.code_guard(source,clean,manual=proposal.get('manual'))
                        new=engine.code_guard(source,clean,manual=proposal.get('manual'))
                        results.append(dict(id=row['id'],original_text_sha256=key,
                            body_sha256=body['sha256'],old_guard=bool(old),new_guard=bool(new)))
    guarded.guard.assert_no_protected_opens()
    old_fail=[r['id'] for r in results if not r['old_guard']]
    new_fail=[r['id'] for r in results if not r['new_guard']]
    report=dict(status='ACTUAL_CACHE_DELTA_GUARDS_PASS' if not new_fail else 'ACTUAL_CACHE_DELTA_GUARDS_FAIL',
        compared_unique_sources=len(results),old_guard_rejections=old_fail,new_guard_rejections=new_fail,
        actual_engine_mro=class_names,source_state=3,model_or_full_index_constructed=False,
        exact_source_and_body_identity_checked=True,roster_manual_metadata_reused=True,
        source_or_body_payload_copies=0,protected_source_view_opens=0,
        previous_selection=dict(path=str(prior_path.relative_to(ROOT)),sha256=inv.file_sha(prior_path)),
        selection=dict(path=str(current_path.relative_to(ROOT)),sha256=inv.file_sha(current_path)),
        roster=dict(path=str(roster_path.relative_to(ROOT)),sha256=inv.file_sha(roster_path)),
        code=dict(path=str(Path(__file__).relative_to(ROOT)),sha256=inv.file_sha(Path(__file__))),
        cache_adapter=dict(path=str((AUDIT/'guarded_reviewed_cache_v10.py').relative_to(ROOT)),
            sha256=inv.file_sha(AUDIT/'guarded_reviewed_cache_v10.py')),
        results=results,elapsed_seconds=time.monotonic()-start,goal_complete=False,training_authorized=False)
    inv.write_json(output,report)
    print(json.dumps({k:report[k] for k in ['status','compared_unique_sources','old_guard_rejections',
        'new_guard_rejections','elapsed_seconds']},ensure_ascii=False),flush=True)
    inv.require(old_fail==['expanded_train:12122'] and not new_fail,'unexpected actual cache guard outcome')


if __name__=='__main__':main()
