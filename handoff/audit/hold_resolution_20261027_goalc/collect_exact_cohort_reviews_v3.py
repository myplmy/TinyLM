"""Collect one exact cohort, reusing frozen review/binding logic, never admit it.

The historical collector is close to its byte limit. Reuse only its named
function definitions, without executing any top-level historical collection.
Each new snapshot uses immutable shards and preserves all author review bytes.
"""
from collections import Counter, defaultdict
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_text_edits_v2 as edits
from scripts import p106b_hold_resolution_recipe_frame_v3 as frame
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards
from scripts import p106b_hold_resolution_author_output_bindings_v1 as explicit_output

REUSED=('digest','stable','save_content','review_rank','ident','review_entries',
        'decisions','exact_assigned_input_reference','materialize')
ALLOWED={'repeat_named_roles_counter_v2':732,'remaining_birth_full_counter_v1':2743,'repeat_named_full_independent_v1':732}
LIMIT=5_000_000


def load_reused(path,environment):
    """Compile just audited function definitions; top-level calls never execute."""
    tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in REUSED]
    inv.require(len(selected)==len(REUSED) and {n.name for n in selected}==set(REUSED),
                'reused function set changed')
    for node in selected:
        defaults=[*node.args.defaults,*[x for x in node.args.kw_defaults if x is not None]]
        inv.require(not node.decorator_list and all(isinstance(x,ast.Constant) for x in defaults),
                    'definition-time execution is not permitted')
    module=ast.Module(body=selected,type_ignores=[])
    exec(compile(module,str(path),'exec'),environment)
    return environment


def write_json_new(path,value):
    payload=(json.dumps(value,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')
    inv.require(len(payload)<20_000_000,'new artifact needs another shard')
    with path.open('xb') as stream:stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path),bytes=len(payload))


def shard_records(directory,rows):
    directory.mkdir(parents=True,exist_ok=False)
    shards=[]
    batch=[]
    size=2
    for row in rows:
        encoded=json.dumps(row,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        inv.require(len(encoded)<LIMIT,'single review record must be split explicitly')
        if batch and size+len(encoded)+1>=LIMIT:
            shards.append(write_json_new(directory/f'records_{len(shards):03}.json',batch))
            batch=[]
            size=2
        batch.append(row)
        size+=len(encoded)+1
    if batch:shards.append(write_json_new(directory/f'records_{len(shards):03}.json',batch))
    return shards


def collect(cohort,version):
    inv.require(cohort in ALLOWED and re.fullmatch(r'v[1-9][0-9]*',version),'unknown exact cohort/version')
    started=time.time()
    base=inv.BASE
    output=base/(cohort+'_snapshots')/version
    inv.require(not output.exists(),'new immutable cohort snapshot required')
    manifest_path=base/cohort/'manifest.json'
    contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
    reused_path=AUDIT/'collect_supplemental_candidates_v63.py'
    manifest=inv.cache.read(manifest_path)
    contract=inv.cache.read(contract_path)
    sources={r['id']:r for r in manifest['rows']}
    inv.require(len(sources)==len(manifest['rows'])==ALLOWED[cohort],'full cohort source count changed')
    blocked_ids=set(contract['restricted_ids'])
    blocked_hashes=set(contract['restricted_hashes'])
    inv.require(not (set(sources)&blocked_ids),'restricted source id in cohort')
    inv.require(not ({r['original']['sha256'] for r in sources.values()}&blocked_hashes),
                'restricted source body in cohort')
    auxiliary_path=AUDIT/'EXACT_COHORT_AUXILIARY_REVIEW_DISPOSITIONS_V1.json'
    auxiliary_records=inv.cache.read(auxiliary_path)['rows']
    auxiliary_by_path={r['path']:r for r in auxiliary_records}
    inv.require(len(auxiliary_by_path)==len(auxiliary_records),'duplicate explicit auxiliary')
    for auxiliary in auxiliary_records:
        inv.require(auxiliary['root_approved'] is True and auxiliary['original_auxiliary_preserved'] is True,
                    'unapproved auxiliary explanation')
        inv.require(inv.file_sha(ROOT/auxiliary['path'])==auxiliary['sha256'],'auxiliary bytes changed')
        inv.require(inv.file_sha(ROOT/auxiliary['canonical_review'])==auxiliary['canonical_review_sha256'],
                    'canonical restored review changed')
    environment=dict(ROOT=ROOT,BASE=base,AUDIT=AUDIT,Path=Path,re=re,hashlib=hashlib,inv=inv,
        edits=edits,frame=frame,safeguards=safeguards,explicit_output=explicit_output,
        archive_dir=AUDIT/'exact_cohort_review_archive_v1',rendered_dir=base/'exact_cohort_rendered_v1',
        bindings=[],auxiliary_by_path=auxiliary_by_path,retractions=[],auxiliary_review_history=[],
        review_pins=[],input_pins={},errors=[],retracted_history=[],unparsed_review_history=[],
        invalid_task_rows=[],strict_task_cohorts={cohort},views_manifest=dict(rows=[]))
    env=load_reused(reused_path,environment)
    for pin_path in [manifest_path,contract_path,reused_path,auxiliary_path,Path(__file__)]:
        env['input_pins'][str(pin_path.relative_to(ROOT))]=inv.file_sha(pin_path)
    for name,sha in manifest['source_code_pins'].items():
        inv.require(inv.file_sha(ROOT/name)==sha,'frozen source check changed')
    for name,sha in manifest['input_pins'].items():
        inv.require(inv.file_sha(ROOT/name)==sha,'source assignment evidence changed')
        env['input_pins'][name]=sha
    for source in sources.values():
        views={}
        for label in ('original','candidate'):
            pin=source[label]
            inv.require(inv.file_sha(ROOT/pin['path'])==pin['sha256'],'assigned source bytes changed')
            text=(ROOT/pin['path']).read_text(encoding='utf-8')
            views[label]=[dict(source_path=pin['path'],sha256=inv.sha(text[n:n+6000]),
                source_characters=[n,min(n+6000,len(text))]) for n in range(0,len(text),6000)]
        env['views_manifest']['rows'].append(dict(id=source['id'],role=source['role'],views=views))
    records=[]
    histories=[]
    coverage={}
    sidecars=[]
    all_assigned=[]
    for role,assignment in manifest['assignments'].items():
        ids=assignment['ids'] if isinstance(assignment,dict) else assignment
        inv.require(len(ids)==len(set(ids)),'repeated role source id')
        all_assigned.extend(ids)
        directory=base/'agents'/role/cohort
        expected=set(ids)
        invalid_latest={}
        for review in sorted([p for p in directory.glob('review*.md') if str(p.relative_to(ROOT)) not in auxiliary_by_path],key=env['review_rank']):
            payload=env['stable'](review)
            entries=env['review_entries'](payload)
            seen=set()
            for entry in entries:
                key=env['ident'](entry['cells'][0])
                if key in seen:
                    invalid_latest[key]=dict(review=str(review.relative_to(ROOT)),
                        error='DUPLICATE_SOURCE_ROWS_IN_ONE_EXPLICIT_REVIEW')
                seen.add(key)
            histories.append(dict(path=str(review.relative_to(ROOT)),sha256=env['digest'](payload),
                role=role,rank=list(env['review_rank'](review)),declared_ids=sorted(seen)))
        choices=env['decisions'](directory,expected)
        coverage[role]=dict(expected=len(ids),saved=len(choices),awaiting_review=len(expected-set(choices)))
        for key in ids:
            inv.require(sources[key]['role']==role,'review role differs from source assignment')
            if key not in choices:
                records.append(dict(id=key,role=role,cohort=cohort,status='NO_SAVED_REVIEW_ROW',
                    original=sources[key]['original'],root_approved=False,cache_admitted=False))
                continue
            row=dict(choices[key],role=role,cohort=cohort,manifest=str(manifest_path.relative_to(ROOT)))
            try:
                invalid=invalid_latest.get(key)
                if invalid and invalid['review']==row['review']['path']:
                    raise ValueError(invalid['error'])
                if row['decision'] not in {'EXCLUDE','NEEDS_ROOT'}:
                    absolute={label:dict(sources[key][label],path=str(ROOT/sources[key][label]['path']))
                        for label in ('original','candidate')}
                    name=explicit_output.declared_txt_basename(row['declared_output_cell'],key,
                        directory,absolute,row['decision'])
                    row['body_references']=[name]
                env['materialize'](row,sources[key],directory)
                if row.get('body'):
                    inv.require(inv.file_sha(ROOT/row['body'])==row['clean_text_sha256'],'saved body changed')
                    row['cache_admitted']=False
            except (ValueError,OSError) as exc:
                row.update(status='MECHANICAL_REJECTION_NOT_APPLIED',error=str(exc))
                env['errors'].append(dict(id=key,role=role,error=str(exc),review=row['review']))
            records.append(row)
        for note in sorted(directory.glob('*.md')):
            if note.name.startswith(('TASK_','START','review')):continue
            inv.require(not note.is_symlink(),'author sidecar must be a regular assigned file')
            payload=env['stable'](note)
            archive,key=env['save_content'](env['archive_dir'],payload,'.md')
            sidecars.append(dict(path=str(note.relative_to(ROOT)),sha256=key,archive=archive,role=role))
    inv.require(len(all_assigned)==len(set(all_assigned))==len(sources),'cohort assignment is incomplete/overlapping')
    for guide in sorted((base/cohort).glob('ROOT_*.md')):
        env['input_pins'][str(guide.relative_to(ROOT))]=inv.file_sha(guide)
    shards=shard_records(output,records)
    summary=dict(status='EXACT_COHORT_FULL_COVERAGE_SNAPSHOT_NOT_ROOT_ADMISSION',cohort=cohort,version=version,
        expected=len(sources),records=len(records),coverage=coverage,
        counts=dict(Counter(r['status'] for r in records)),
        needs_root=[r['id'] for r in records if r.get('decision')=='NEEDS_ROOT'],
        errors=env['errors'],invalid_task_rows=env['invalid_task_rows'],
        unparsed_review_history=env['unparsed_review_history'],
        review_history=histories,review_pins=env['review_pins'],sidecars=sidecars,
        auxiliary_review_history=[dict(r,excluded_as_duplicate_decision=False,excluded_as_nondecision_auxiliary=True) for r in env['auxiliary_review_history']],
        shards=shards,input_pins=env['input_pins'],source_code_pins=manifest['source_code_pins'],
        reused_definitions=list(REUSED),reused_top_level_executed=False,
        elapsed_seconds=time.time()-started,root_adopted=0,cache_admitted=0,
        goal_complete=False,training_authorized=False,
        limits='Version precedence applies only to explicit revisions in the same assigned TASK. No cross-cohort merge or source admission.')
    receipt=write_json_new(output/'complete.json',summary)
    print(json.dumps(dict(cohort=cohort,version=version,counts=summary['counts'],coverage=coverage,
        needs_root=summary['needs_root'],errors=len(summary['errors']),receipt=receipt),ensure_ascii=False))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--cohort',required=True,choices=sorted(ALLOWED))
    parser.add_argument('--version',required=True)
    args=parser.parse_args()
    collect(args.cohort,args.version)
