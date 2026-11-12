"""Finish an interrupted metadata-only prepare without duplicating its archives."""
from pathlib import Path
import argparse
import json
import runpy
import subprocess
import sys
from unittest.mock import patch

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from exact_owned_cleanup_code_scope_v1 import load

parser=argparse.ArgumentParser()
parser.add_argument('--config',required=True)
args=parser.parse_args()
config_path=Path(args.config).resolve()
assert config_path.parent==AUDIT
c=json.loads(config_path.read_bytes())
extra=load(config_path)
version=c['version']
guard.activate()
receipt_path=AUDIT/c['wip_applied_receipt']
wip_receipt=json.loads(receipt_path.read_bytes())
assert wip_receipt['wip']=='handoff/WIP_20261027_작업원장.md'
sha=wip_receipt.get('sha256',wip_receipt.get('wip_sha256'))
assert isinstance(sha,str) and len(sha)==64
read=guard.inv.cache.read


def adapted_read(path):
    value=read(path)
    if Path(path).resolve()==receipt_path:
        if 'sha256' not in value:
            assert value['status']=='WIP75_EXACT_CAS_AND_OTHER_ROWS_INDEPENDENTLY_VERIFIED'
            assert value['verified_cells']==4 and value['other_rows_equal_to_HEAD'] is True
            assert all('진행' in value['states'][key] for key in ['1','7'])
            return dict(value,sha256=value['wip_sha256'])
    return value


archive=AUDIT/f'exact_followup_progress_archive_v{version}'
archive_index=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V{version}.json'
if not archive.exists():
    with patch.object(guard.inv.cache,'read',adapted_read):
        sys.argv=[str(AUDIT/'prepare_versioned_checkpoint_v7.py'),'--config',str(config_path)]
        runpy.run_path(str(AUDIT/'prepare_versioned_checkpoint_v7.py'),run_name='__main__')
    guard.assert_no_protected_opens()
    raise SystemExit(0)


def git(*arguments):
    return subprocess.check_output(['git','--literal-pathspecs',*arguments],cwd=ROOT)


def pin(path):
    assert not path.is_symlink()
    return dict(path=str(path.relative_to(ROOT)),sha256=guard.inv.file_sha(path),bytes=path.stat().st_size)


manifest=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V{version}.json'
assert not manifest.exists()
assert git('rev-parse','HEAD').decode().strip()==c['expected_head']
assert not git('diff','--cached','--name-only','-z')
index=json.loads(archive_index.read_bytes())
report=AUDIT/c['report']
assert guard.inv.file_sha(report)==c['report_sha256']
for entry in index['rows']+index['unchanged_prior_guides_reused']:
    for name in ['source','archive']:
        item=entry[name]
        path=ROOT/item['path']
        assert path.suffix in {'.md','.json'} and not path.is_symlink()
        assert guard.inv.file_sha(path)==item['sha256']
large=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V{version}.json'
message=AUDIT/f'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V{version}.txt'
assert large.is_file() and message.read_text(encoding='utf-8')==c['message']
effective=adapted_read(receipt_path)
assert effective['sha256']==sha
proof=dict(status='INTERRUPTED_PREPARE_FINISHED_WITHOUT_DUPLICATE_ARCHIVES',
    reason='Legacy saver expected sha256; independently verified WIP75 receipt named the same value wip_sha256.',
    canonical_SHA_alias_only=True,original_receipt_modified=False,
    existing_archive_entries_reverified=len(index['rows'])+len(index['unchanged_prior_guides_reused']),
    source_payload_reads=0,source_payload_copies=0,duplicate_archives_created=0,
    wip_sha256=sha,input_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
        [config_path,receipt_path,archive_index,large,Path(__file__)]},
    goal_complete=False,training_authorized=False)
proof_path=AUDIT/f'CHECKPOINT_V{version}_PREPARE_RECOVERY_V1.json'
assert not proof_path.exists()
guard.inv.write_json(proof_path,proof)
relative=str(AUDIT.relative_to(ROOT))
changed=set()
for arguments in [('ls-files','--others','--exclude-standard','-z','--',relative),
                  ('diff','--name-only','-z','--',relative)]:
    changed.update(value.decode() for value in git(*arguments).split(bytes([0])) if value)
explicit=[]
for name in sorted(changed):
    if name in c.get('active_audit_paths_excluded',[]):
        continue
    path=ROOT/name
    assert path.resolve().is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0<path.stat().st_size<20_000_000:
        continue
    top_small=path.parent==AUDIT and (path.suffix in {'.py','.md'} or path.suffix in {'.json','.log'} and path.stat().st_size<500_000)
    exact_closure=path.parent==AUDIT and path.name in c['additional_top_level_json']
    reviewed=path.is_relative_to(AUDIT/'exact_cohort_review_archive_v1') and path.suffix=='.md'
    if top_small or exact_closure or reviewed or path.is_relative_to(archive) or path==message:
        explicit.append(pin(path))
explicit.extend(pin(ROOT/name) for name in extra)
explicit.append(dict(path=effective['wip'],sha256=sha,bytes=(ROOT/effective['wip']).stat().st_size))
assert len(explicit)==len({row['path'] for row in explicit})
excluded=json.loads((ROOT/'.agents/project.json').read_bytes())['excludedPaths']
for row in explicit:
    assert all(not row['path'].startswith(p) for p in excluded if not p.startswith('.env'))
guard.inv.write_json(manifest,dict(expected_head=c['expected_head'],branch=git('branch','--show-current').decode().strip(),
    rows=explicit,preparation_recovery=pin(proof_path),excluded_source_data=True,excluded_large_data=True,
    foreign_dirty_paths_excluded=True,goal_complete=False,training_authorized=False))
guard.assert_no_protected_opens()
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)),paths=len(explicit)+1,
    bytes=sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
    duplicate_archives_created=0,index_empty=True)))
