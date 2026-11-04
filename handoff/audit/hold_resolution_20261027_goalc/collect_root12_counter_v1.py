"""Bind only saved counter reviews using the immutable parser/materializer."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
assert inv.file_sha(AUDIT/'collect_exact_cohort_reviews_v5.py')=='DAB0FBC8312B4331DD147F0B78AD185E9A2B1BC830B5BDB479C72A48514FDB48'
import collect_exact_cohort_reviews_v5 as frozen
from exact_review_header_alias_v2 import wrap_review_entries

GROUP='root12_independent_admission_counter_v1'
parser=argparse.ArgumentParser();parser.add_argument('--version',required=True);args=parser.parse_args()
assert re.fullmatch(r'v[1-9][0-9]*',args.version)
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
assert inv.file_sha(guard_path)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=inv.cache.read(guard_path)
manifest_path=inv.BASE/GROUP/'manifest.json'
assert inv.file_sha(manifest_path)=='A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'
manifest=inv.cache.read(manifest_path);sources={row['id']:row for row in manifest['rows']}
assert len(sources)==len(manifest['rows'])==3688
assert not set(sources)&set(guard['restricted_ids'])
assert not {row[label]['sha256'] for row in sources.values() for label in ['original','candidate']}&set(guard['restricted_hashes'])
output=inv.BASE/(GROUP+'_snapshots')/args.version;assert not output.exists()
reused=AUDIT/'collect_supplemental_candidates_v63.py'
assert inv.file_sha(reused)=='F9C7816AC034EDE872251C84426AB4935096C61EBB29DF22CF5DC4FD7E7E8D39'
env=dict(ROOT=ROOT,BASE=inv.BASE,AUDIT=AUDIT,Path=Path,re=re,hashlib=hashlib,inv=inv,
    edits=frozen.edits,frame=frozen.frame,safeguards=frozen.safeguards,explicit_output=frozen.explicit_output,
    archive_dir=AUDIT/'exact_cohort_review_archive_v1',rendered_dir=inv.BASE/'exact_cohort_rendered_v1',
    bindings=[],auxiliary_by_path={},retractions=[],auxiliary_review_history=[],review_pins=[],
    input_pins={},errors=[],retracted_history=[],unparsed_review_history=[],invalid_task_rows=[],
    strict_task_cohorts={GROUP},views_manifest=dict(rows=[]))
env=frozen.load_reused(reused,env)
env['review_entries']=wrap_review_entries(env['review_entries'])
for name,sha in {**manifest['input_pins'],**manifest['source_code_pins']}.items():
    assert inv.file_sha(ROOT/name)==sha;env['input_pins'][name]=sha
for path in [manifest_path,guard_path,reused,Path(__file__),AUDIT/'collect_exact_cohort_reviews_v5.py',
             AUDIT/'exact_review_header_alias_v2.py',AUDIT/'ROOT12_COUNTER_COLLECTION_SCOPE_V1.md']:
    env['input_pins'][str(path.relative_to(ROOT))]=inv.file_sha(path)
choices={};coverage={};seen=[]
for role,ids in manifest['assignments'].items():
    directory=inv.BASE/'agents'/role/GROUP
    chosen=env['decisions'](directory,set(ids));assert set(chosen)<=set(ids)
    coverage[role]=dict(expected=len(ids),saved=len(chosen),awaiting_review=len(set(ids)-set(chosen)))
    for key,row in chosen.items():
        assert key not in choices and sources[key]['primary_author_role']!=role
        choices[key]=dict(row,role=role,cohort=GROUP,manifest=str(manifest_path.relative_to(ROOT)))
    seen+=ids
assert len(seen)==len(set(seen))==3688
unreviewed=sorted(set(sources)-set(choices))
allowed_paths={(ROOT/sources[key][label]['path']).resolve() for key in choices for label in ['original','candidate']}
all_paths={(ROOT/row[label]['path']).resolve() for row in sources.values() for label in ['original','candidate']}
attempted_unreviewed=[];actual_source_paths=set()


def observe(event,args):
    if event!='open' or not args or not isinstance(args[0],str):return
    path=Path(args[0]).resolve()
    if path not in all_paths:return
    if path not in allowed_paths:
        attempted_unreviewed.append(str(path));raise PermissionError('unreviewed source payload must not be opened')
    actual_source_paths.add(str(path.relative_to(ROOT)))


sys.addaudithook(observe)
records=[];viewed=[]
for key,row in sorted(choices.items()):
    source=sources[key];directory=inv.BASE/'agents'/row['role']/GROUP
    try:
        assert source['role']==row['role']
        if row['decision'] not in {'EXCLUDE','NEEDS_ROOT'}:
            views={}
            for label in ['original','candidate']:
                pin=source[label];assert inv.file_sha(ROOT/pin['path'])==pin['sha256']
                text=(ROOT/pin['path']).read_text(encoding='utf-8')
                views[label]=[dict(source_path=pin['path'],sha256=inv.sha(text[n:n+6000]),
                    source_characters=[n,min(n+6000,len(text))]) for n in range(0,len(text),6000)]
            env['views_manifest']['rows'].append(dict(id=key,role=row['role'],views=views));viewed.append(key)
            absolute={label:dict(source[label],path=str(ROOT/source[label]['path'])) for label in ['original','candidate']}
            name=frozen.explicit_output.declared_txt_basename(row['declared_output_cell'],key,directory,absolute,row['decision'])
            row['body_references']=[name]
        env['materialize'](row,source,directory)
        if row.get('body'):
            assert inv.file_sha(ROOT/row['body'])==row['clean_text_sha256']
            row['cache_admitted']=False
    except (ValueError,OSError) as exc:
        row.update(status='MECHANICAL_REJECTION_NOT_APPLIED',error=str(exc));env['errors'].append(dict(id=key,error=str(exc)))
    records.append(row)
assert not attempted_unreviewed
shards=frozen.shard_records(output,records)
summary=dict(status='EXACT_COUNTER_SAVED_ROWS_SNAPSHOT_WITH_EXPLICIT_UNREVIEWED_IDS_NOT_ADMISSION',
    cohort=GROUP,version=args.version,expected=3688,records=len(records),coverage=coverage,
    unreviewed_ids=unreviewed,unreviewed_count=len(unreviewed),
    counts=dict(Counter(row['status'] for row in records)),errors=env['errors'],
    invalid_task_rows=env['invalid_task_rows'],unparsed_review_history=env['unparsed_review_history'],
    review_pins=env['review_pins'],shards=shards,input_pins=env['input_pins'],
    lazy_view_source_ids=viewed,source_payload_paths_opened=sorted(actual_source_paths),
    unreviewed_payload_open_attempts=len(attempted_unreviewed),
    full_source_scope_is_owned_by_manifest=True,new_first_review_credit=0,
    reused_definitions=list(frozen.REUSED),reused_historical_top_level_executed=False,
    root_adopted=0,cache_admitted=0,goal_complete=False,training_authorized=False)
assert summary['records']+summary['unreviewed_count']==summary['expected']
receipt=frozen.write_json_new(output/'complete.json',summary)
print(json.dumps(dict(counts=summary['counts'],coverage=coverage,errors=len(summary['errors']),
    saved=len(records),view_sources=len(viewed),unreviewed_payload_open_attempts=0,receipt=receipt),ensure_ascii=False))
