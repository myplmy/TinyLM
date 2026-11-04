"""Freeze owned small evidence using existing save primitives and exact config."""
from pathlib import Path
from collections import Counter
import argparse, ast, json, re, subprocess, sys
ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
config_path=(ROOT/args.config).resolve();assert config_path.is_relative_to(AUDIT)
c=inv.cache.read(config_path);version=c['version'];previous_version=c['previous_version']
assert isinstance(version,int) and version==previous_version+1 and version>=19
frozen=AUDIT/'prepare_exact_followup_checkpoint_v3.py'
assert inv.file_sha(frozen)=='8C3557C1B7D1600EB953B6422C4F65A1792BAD3D12B047CC4ED0853023E83801'
nodes=[n for n in ast.parse(frozen.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in {'git','pin','copy'}]
assert len(nodes)==3 and all(not n.decorator_list for n in nodes)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(frozen),'exec'),globals())
archive_source=AUDIT/'prepare_exact_followup_checkpoint_v14.py'
assert inv.file_sha(archive_source)=='87494164DA5F3FF5EBF0A5EFDE7608E143D3D6531616555BF4BDD826842FF098'
nodes=[n for n in ast.parse(archive_source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='archive_one']
assert len(nodes)==1 and not nodes[0].decorator_list
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(archive_source),'exec'),globals())
head=git('rev-parse','HEAD').decode().strip();assert head==c['expected_head']
branch=git('branch','--show-current').decode().strip();assert branch and not git('diff','--cached','--name-only','-z')
archive=AUDIT/f'exact_followup_progress_archive_v{version}';assert not archive.exists()
for stem in ['ARCHIVE','LARGE_LOCAL','SAVE_MANIFEST','COMMIT_MESSAGE']:
    extension='txt' if stem=='COMMIT_MESSAGE' else 'json'
    assert not (AUDIT/f'EXACT_FOLLOWUP_PROGRESS_{stem}_V{version}.{extension}').exists()
copies,reused,metadata=[],[],[]
previous_path=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V{previous_version}.json'
previous=inv.cache.read(previous_path);prior_archives={}
for row in previous['rows']+previous.get('unchanged_prior_guides_reused',[]):
    item=row.get('archive',row);prior_archives[item['sha256']]=item
report_path=AUDIT/c['report'];assert inv.file_sha(report_path)==c['report_sha256']
report=inv.cache.read(report_path)
snapshot_specs=[(r['cohort'],r['version']) for r in report['coverage']]
snapshot_specs.append(('root12_independent_admission_counter_v1',c['counter_snapshot_version']))
for cohort,snapshot_version in snapshot_specs:
    path=inv.BASE/(cohort+'_snapshots')/snapshot_version/'complete.json';value=inv.cache.read(path)
    assert not value['errors'] and value['root_adopted']==value['cache_admitted']==0
    archive_one(path,archive/cohort/('snapshot_'+snapshot_version+'_complete.json'))
    metadata.extend(dict(path=item['path'],sha256=item['sha256'],bytes=(ROOT/item['path']).stat().st_size,meaning='REVIEW_RECORD_METADATA_NOT_CORPUS_TXT') for item in value['shards'])
group='root12_independent_admission_counter_v1';manifest_path=inv.BASE/group/'manifest.json'
assert inv.file_sha(manifest_path)=='A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'
sources={r['id']:r for r in inv.cache.read(manifest_path)['rows']}
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
assert inv.file_sha(guard_path)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=inv.cache.read(guard_path)
selection_path=AUDIT/c['selection'];assert inv.file_sha(selection_path)==c['selection_sha256']
selection=inv.cache.read(selection_path);sidecars=set()
for row in selection['rows']:
    choice=row['selected']
    if choice.get('cohort')!=group:continue
    source=sources[row['id']]
    assert row['id'] not in guard['restricted_ids'] and row['original_text_sha256'] not in guard['restricted_hashes']
    directory=inv.BASE/'agents'/source['role']/group
    for name in re.findall(r'hold_[A-Za-z0-9_]+[.]md',choice['reason']):
        path=directory/name
        if path.is_file():sidecars.add(path)
for path in sorted(sidecars):archive_one(path,archive/'counter_selected_sidecars'/path.parent.parent.name/path.name)
metadata.extend(pin(path) for path in [config_path,frozen,archive_source,previous_path,report_path,manifest_path,selection_path,guard_path,ROOT/'tmp/COORD_HOLD_01a17740.md'])
inv.write_json(AUDIT/f'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V{version}.json',dict(status='FROZEN_SMALL_METADATA_AND_REVIEWS_NO_TRAINING_TXT',rows=copies,unchanged_prior_guides_reused=reused,first_review_unique=report['fresh_first_review_unique'],official_verified_HOLD_positions=report['official_verified_HOLD_positions'],selected_ROOT_expected_HOLD_positions=selection['expected_roster_HOLD_positions'],source_data_changed=False,goal_complete=False,training_authorized=False))
relative=str(AUDIT.relative_to(ROOT));changed=set()
for arguments in [('ls-files','--others','--exclude-standard','-z','--',relative),('diff','--name-only','-z','--',relative)]:
    changed.update(s.decode() for s in git(*arguments).split(bytes([0])) if s)
# Follow only the small prior hash-index chain; do not hash old large objects again.
old_large_path=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V{previous_version}.json'
old_large_names=set();seen=set();cursor=old_large_path
while cursor is not None:
    assert cursor.resolve().is_relative_to(AUDIT) and cursor not in seen;seen.add(cursor)
    old=inv.cache.read(cursor);old_large_names.update(row['path'] for row in old['rows'])
    link=old.get('prior_large_index')
    if link:
        cursor=ROOT/link['path'];assert inv.file_sha(cursor)==link['sha256']
    else:cursor=None
for name in sorted(changed):
    path=ROOT/name
    if path.parent==AUDIT and path.suffix=='.json' and path.stat().st_size>=500_000 and name not in old_large_names:metadata.append(pin(path))
inv.write_json(AUDIT/f'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V{version}.json',dict(status='LOCAL_ONLY_IMMUTABLE_LARGE_METADATA_SHA_INDEX',rows=metadata,prior_large_index=pin(old_large_path),prior_large_objects_rehashed=False,protected_original_or_candidate_TXT_hashed=False,source_bodies_staged=False))
message=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V{version}.txt'
with message.open('x',encoding='utf-8') as f:f.write(c['message'])
changed.update(str(p.relative_to(ROOT)) for p in [AUDIT/f'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V{version}.json',message])
explicit=[]
for name in sorted(changed):
    path=ROOT/name;assert path.resolve().is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0<path.stat().st_size<20_000_000:continue
    top_small=path.parent==AUDIT and (path.suffix in {'.py','.md'} or path.suffix in {'.json','.log'} and path.stat().st_size<500_000)
    exact_closure=path.name in c['additional_top_level_json'] and path.parent==AUDIT
    reviewed=path.is_relative_to(AUDIT/'exact_cohort_review_archive_v1') and path.suffix=='.md'
    if top_small or exact_closure or reviewed or path.is_relative_to(archive) or path==message:explicit.append(pin(path))
wip_receipt=inv.cache.read(AUDIT/c['wip_applied_receipt']);wip=wip_receipt['wip']
assert wip=='handoff/WIP_20261027_작업원장.md'
explicit.append(dict(path=wip,sha256=wip_receipt['sha256'],bytes=(ROOT/wip).stat().st_size))
assert len(explicit)==len({r['path'] for r in explicit})
excluded=inv.cache.read(ROOT/'.agents/project.json')['excludedPaths']
for row in explicit:assert all(not row['path'].startswith(v) for v in excluded if not v.startswith('.env'))
manifest=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V{version}.json'
inv.write_json(manifest,dict(expected_head=head,branch=branch,rows=explicit,excluded_source_data=True,excluded_large_data=True,foreign_dirty_paths_excluded=True,goal_complete=False,training_authorized=False))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)),expected_head=head,branch=branch,paths=len(explicit)+1,bytes=sum(r['bytes'] for r in explicit)+manifest.stat().st_size,archived_evidence=len(copies),reused_evidence=len(reused),large_index_chain_entries=len(seen),kinds=dict(Counter(Path(r['path']).suffix for r in explicit)),index_empty=True),ensure_ascii=False))
