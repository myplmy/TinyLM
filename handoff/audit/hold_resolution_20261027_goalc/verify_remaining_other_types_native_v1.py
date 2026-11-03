"""Reuse the frozen native reader/policy, emitting bounded pages for the entire type."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy
import guarded_scan_metadata_v1 as metadata

SOURCE=inv.BASE/'remaining_other_types_full_sources_v1'
OUT=inv.BASE/'remaining_other_types_native_proofs_v1'
assert not OUT.exists()
census_path=SOURCE/'complete.json';census=inv.cache.read(census_path)
draft_path=inv.BASE/'draft_proposals_v26_delta_v1/complete.json'
scope_path=inv.BASE/'scope.json'
draft,scope=map(inv.cache.read,[draft_path,scope_path])
for name,sha in census['input_pins'].items():assert inv.file_sha(ROOT/name)==sha
for name,sha in draft['lineage']['source_code_sha256'].items():assert inv.file_sha(ROOT/name)==sha
inv.verify(SOURCE/'rows',census['rows'])
targets={r['original_text_sha256']:r for r in inv.cache.rows(SOURCE/'rows',census['rows'])}
assert len(targets)==census['counts']['queued_unique']==50162
ids={r['id'] for r in targets.values()}
contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract=inv.cache.read(contract_path)
blocked_ids=set(contract['restricted_ids']);blocked_sha=set(contract['restricted_hashes'])
assert not (ids&blocked_ids) and not (set(targets)&blocked_sha)
pages={};page_for_key={}
for pin in census['pages']:
    assert inv.file_sha(ROOT/pin['path'])==pin['sha256']
    page=inv.cache.read(ROOT/pin['path']);number=pin['page']
    pages[number]=dict(source_pin=pin,rows=[],counts=Counter())
    for r in page['rows']:
        key=r['original_text_sha256'];assert key not in page_for_key
        page_for_key[key]=number
assert set(page_for_key)==set(targets)
inv.verify(draft_path.parent/'unique',draft['unique_manifest'])
sources={}
for shard in draft['unique_manifest']['shards']:
    with (draft_path.parent/'unique'/shard['path']).open('rb') as stream:
        for line in stream:
            first=metadata.IDENT.search(line)
            assert first is not None
            if first[1].decode('ascii') not in ids:continue
            meta=metadata.project_metadata(line)
            ident,key=meta['id'],meta['original_text_sha256']
            if ident in blocked_ids or key in blocked_sha:continue
            if ident not in ids:continue
            assert key in targets and key not in sources
            row=json.loads(line)
            assert row['id']==ident and row['original_text_sha256']==key
            sources[key]=row
assert set(sources)==set(targets)
paths=[census_path,draft_path,scope_path,contract_path,Path(__file__),
    AUDIT/'guarded_scan_metadata_v1.py',ROOT/'scripts/p106b_hold_resolution_repeat_context_v1.py']
pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in paths}
counts=Counter();started=time.monotonic()
with ExitStack() as stack:
    reader=inv.OriginalReader(scope,stack)
    for index,(key,row) in enumerate(sources.items(),1):
        assert row['id'] not in blocked_ids and key not in blocked_sha
        raw,eos,valid=reader.text(row)
        assert eos and valid and inv.sha(raw)==key
        result=policy.propose(dict(row,text=raw,complete_eos=True,valid_utf8=True,
            previous_holds=row.get('previous_holds',[])),False)
        clean=result.get('candidate',result['text'])
        agrees=inv.sha(clean)==inv.sha(row['diagnostic_candidate']) and result['decision']=='PENDING' and result['reasons']==targets[key]['previous_reasons']
        number=page_for_key[key];page=pages[number]
        directory=OUT/'pages'/('page_'+str(number).zfill(3))/'inputs'
        directory.mkdir(parents=True,exist_ok=True)
        pair={}
        for label,text in [('original',raw),('candidate',clean)]:
            path=directory/(row['id'].replace(':','_')+'_'+label+'.txt')
            payload=text.encode('utf-8');assert 0<len(payload)<20_000_000
            with path.open('xb') as f:f.write(payload)
            pair[label]=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
        record={name:row[name] for name in ['id','source','split','source_ids','source_ids_sha256',
            'original_text_sha256','input_ids','occurrences','language_bucket']}
        remaining=set(result['reasons'])
        guards=dict(code=policy.code_preserved(raw,clean),unicode=policy.unicode_examples_preserved(raw,clean),
            style=policy.semantic_style_preserved(raw,clean),ordered=policy.ordered_deletion(raw,clean))
        record.update(**pair,named_review_strata=targets[key]['named_review_strata'],
            native_proof_agrees=agrees,proof=dict(classification_only=True,named_review_strata=targets[key]['named_review_strata']),
            remaining_reasons=sorted(remaining),guards=guards,candidate_decision='CONTEXT_REVIEW_REQUIRED',
            complete_eos=True,valid_utf8=True,root_approved=False,cache_admitted=False)
        page['rows'].append(record)
        delta=dict(fresh_native_sources=1,occurrences=row['occurrences'])
        delta['fresh_regeneration_and_proof_match' if agrees else 'regeneration_or_proof_mismatch_not_released']=1
        page['counts'].update(delta);counts.update(delta)
        if index%100==0:print(json.dumps(dict(phase='fresh_native_full_other_types',sources=index,total=50162)),flush=True)
reports=[]
for number,page in sorted(pages.items()):
    assert len(page['rows'])==page['source_pin']['sources']
    path=OUT/'pages'/('page_'+str(number).zfill(3))/'complete.json'
    report=dict(status='FRESH_NATIVE_PAGE_VERIFIED_CONTEXT_REVIEW_STILL_REQUIRED',rows=page['rows'],
        counts=dict(page['counts']),page=number,parent_total_pages=98,parent_total_sources=50162,
        input_pins=dict(pins,**{page['source_pin']['path']:page['source_pin']['sha256']}),
        source_code_pins=draft['lineage']['source_code_sha256'],native_source_freshly_decoded=True,
        new_cleaned_prose_authored_by_root=False,cache_admitted=0,goal_complete=False,training_authorized=False)
    payload=(json.dumps(report,ensure_ascii=False,indent=2)+chr(10)).encode();assert len(payload)<20_000_000
    with path.open('xb') as f:f.write(payload)
    reports.append(dict(page=number,path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path),
        sources=len(page['rows']),counts=dict(page['counts'])))
assert counts['fresh_native_sources']==50162 and len(reports)==98
summary=dict(status='ENTIRE_OTHER_TYPES_FRESH_NATIVE_PREPARATION_NOT_REVIEW_OR_ADMISSION',
    counts=dict(counts),pages=reports,input_pins=pins,native_source_freshly_decoded=True,
    protected_parent_full_bodies_opened=False,new_cleaned_prose_authored_by_root=False,
    goal_complete=False,training_authorized=False,seconds=time.monotonic()-started)
inv.write_json(OUT/'complete.json',summary)
print(json.dumps(dict(status=summary['status'],counts=dict(counts),pages=98,seconds=summary['seconds'])))
