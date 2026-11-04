"""Explicit owned-path preparation and standard local commit; no index surgery."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from handoff.audit.nov01_afternoon.prepare_owned_commit_v3 import git, names
from handoff.audit.nov04_weight_space.prepare_commit import EXACT as PRIMARY_EXACT

BASE=Path('handoff/audit/nov04_p107_cli')
MANIFEST=BASE/'COMMIT_SCOPE_v1.json'
MESSAGE=BASE/'COMMIT_MESSAGE_v1.txt'
RECEIPT=Path('tmp/nov04_weight_space_final_commit_receipt.json')
FOREIGN=frozenset(('handoff/WIP_20261027_작업원장.md','scripts/flag_whitelist.tsv'))
EXTRA=(
 'tinylm/train/document_input.py','scripts/train_p107_documents.py','scripts/diag_p107_document_cli.py',
 'scripts/test_p107_document_input.py','scripts/test_p107_document_cli.py',
 'docs/methods/05_training_speed.md','docs/research/20261104_P107_명시입력과_CLI_연결설계.md',
 'test_plan/P107_문서가시성과-shift를-분리한-causal-MNTP-계약.md',
 'test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md',
 'handoff/202611042233_HANDOFF.md',
)
FOLDERS=('handoff/audit/nov04_weight_space','handoff/audit/nov04_p107_cli',
 'test_result/evidence/p107_document_cli_v1_20261104',
 'test_result/evidence/p108_attenuation_v1_20261104',
 'test_result/evidence/codex_smoke/nov04_p108_p107_v1',
 'test_result/evidence/codex_smoke/nov04_p108_p107_v2')
SMOKE_LOGS=('smoketest_logs/20261104121352_smoke_codex_nov04_p108_p107_v1_424f922.txt',
           'smoketest_logs/20261104122620_smoke_codex_nov04_p108_p107_v2_424f922.txt')


def sha(raw):return hashlib.sha256(raw).hexdigest().upper()


def run_git(*args):
    return subprocess.run(['git',*args],capture_output=True,check=True)


def prepare():
    if MANIFEST.exists() or RECEIPT.exists() or names(git('diff','--cached','--name-only','-z')):
        raise ValueError('fresh manifest/receipt and empty shared index required')
    if json.loads((BASE/'FINAL_DOCUMENT_CHECKS_v3.json').read_text())['actual_exit']!=0:
        raise ValueError('final document checks incomplete')
    static=BASE/'STATIC_AUDIT_v6.json'
    evidence=json.loads(static.read_text())
    if evidence['counts']['errors']!=0 or evidence['counts']['pass']!=6:
        raise ValueError('final owned static audit incomplete')
    candidates={Path(p) for p in PRIMARY_EXACT+EXTRA+SMOKE_LOGS}
    candidates.update(Path('scripts').glob('*p108*.py'))
    candidates.update(Path('docs/research').glob('20261104_P108_*.md'))
    for pattern in ('107_log_20261104_P107_*.txt','108_log_20261104_P108_*.txt'):
        candidates.update(Path('test_result').glob(pattern))
    for name in FOLDERS:
        candidates.update(p for p in Path(name).rglob('*') if p.is_file())
    records=[]
    for p in sorted(candidates):
        name=p.as_posix()
        if (not p.is_file() or p.is_symlink() or any(x.is_symlink() for x in p.parents)
                or name in FOREIGN or name.startswith(('datasets/','data_cache/','runs/','HF/','.agents/','.codex/','agents/'))
                or any(x in name for x in ('hold_resolution_','hold_recovery_','source_cleanup_'))
                or p.suffix in ('.pt','.bin','.lock','.paths')):
            raise ValueError('excluded/linked/invalid commit candidate: '+name)
        raw=p.read_bytes()
        if len(raw)>=20_000_000:raise ValueError('owned result file exceeds20MB: '+name)
        text=raw.decode('utf-8')
        if p.suffix=='.py':ast.parse(text,filename=name)
        if p.suffix=='.json':json.loads(text)
        old=subprocess.run(['git','show','HEAD:'+name],capture_output=True,check=False)
        if old.returncode==0 and old.stdout==raw:continue
        records.append(dict(path=name,bytes=len(raw),sha256=sha(raw)))
    paths=sorted([r['path'] for r in records]+[str(MANIFEST)])
    new_raw=[r['path'] for r in records if r['path'].startswith(('test_result/107_log_', 'test_result/108_log_','smoketest_logs/'))]
    if len(new_raw)!=12 or not set(SMOKE_LOGS)<=set(new_raw):
        raise ValueError('expected10 new experiment logs plus2 complete smoke logs')
    if not set(EXTRA)<=set(paths):raise ValueError('required new implementation/document omitted')
    run_git('diff','--check','--',*paths)
    tracked=names(git('diff','--name-only','-z'))
    value=dict(schema='P107_P108_FINAL_OWNED_COMMIT_SCOPE_V1',authority_directive=107,
        parent=git('rev-parse','HEAD').decode().strip(),branch=git('branch','--show-current').decode().strip(),
        paths=paths,bindings=records,bytes=sum(r['bytes'] for r in records),
        raw_logs=new_raw,maximum_bytes=max(r['bytes'] for r in records),
        foreign_tracked_names_only=sorted(tracked-set(paths)),foreign_contents_read=False,
        final_static_sha256=sha(static.read_bytes()),shared_index_initially_empty=True,
        checkpoint_or_runtime_staging=False,protected_dataset_access=False,push=False,
        post_commit_receipt=str(RECEIPT),post_receipt_is_ignored_runtime_audit=True)
    with MANIFEST.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps(dict(paths=len(paths),bytes=value['bytes'],raw_logs=len(new_raw),maximum_bytes=value['maximum_bytes'],
        parent=value['parent'],manifest_sha256=sha(MANIFEST.read_bytes()))))


def commit(expected):
    if RECEIPT.exists() or sha(MANIFEST.read_bytes())!=expected:raise ValueError('fresh receipt/exact manifest required')
    value=json.loads(MANIFEST.read_text(encoding='utf-8'))
    paths=value['paths'];bindings={r['path']:r['sha256'] for r in value['bindings']}
    bindings[str(MANIFEST)]=expected
    if git('rev-parse','HEAD').decode().strip()!=value['parent'] or git('branch','--show-current').decode().strip()!=value['branch']:
        raise ValueError('HEAD/branch changed before standard local commit')
    if names(git('diff','--cached','--name-only','-z')):raise ValueError('shared index must be empty')
    for name,digest in bindings.items():
        if sha(Path(name).read_bytes())!=digest:raise ValueError('owned bytes changed: '+name)
    run_git('diff','--check','--',*paths)
    run_git('add','--force','--',*paths)
    if names(git('diff','--cached','--name-only','-z'))!=set(paths):
        raise ValueError('shared index differs from the explicit owned path set; do not reset it')
    if git('rev-parse','HEAD').decode().strip()!=value['parent']:raise ValueError('HEAD changed after staging')
    done=run_git('commit','--quiet','--only','--file',str(MESSAGE),'--',*paths)
    head=git('rev-parse','HEAD').decode().strip()
    actual=names(git('diff-tree','--no-commit-id','--name-only','-r','-z',head))
    if git('rev-parse',head+'^').decode().strip()!=value['parent'] or actual!=set(paths):
        raise ValueError('actual commit parent or complete path set differs')
    for name,digest in bindings.items():
        if sha(git('show',head+':'+name))!=digest or sha(Path(name).read_bytes())!=digest:
            raise ValueError('committed blob or current owned bytes differ: '+name)
    if names(git('diff','--name-only','-z','--',*paths)) or names(git('diff','--cached','--name-only','-z')):
        raise ValueError('owned scope dirty or shared index nonempty after commit')
    result=dict(schema='P107_P108_FINAL_LOCAL_COMMIT_RECEIPT_V1',actual_exit=0,commit=head,parent=value['parent'],
        branch=value['branch'],manifest_sha256=expected,paths=len(paths),bytes=value['bytes'],raw_logs=len(value['raw_logs']),
        complete_path_set_exact=True,every_blob_sha256_exact=True,owned_scope_clean=True,shared_index_empty=True,
        foreign_tracked_names_only=sorted(names(git('diff','--name-only','-z'))-set(paths)),
        original_checkpoints_changed=0,push=False,commit_stdout=done.stdout.decode('utf-8'),commit_stderr=done.stderr.decode('utf-8'))
    with RECEIPT.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps({k:result[k] for k in ('actual_exit','commit','parent','paths','bytes','raw_logs','owned_scope_clean','shared_index_empty')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','commit'))
    parser.add_argument('sha256',nargs='?')
    args=parser.parse_args()
    prepare() if args.mode=='prepare' else commit(args.sha256)
