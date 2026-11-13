"""User110 exact184 optimizer archives and128 synthetic checkpoints only.

No model construction, GPU, downloads, Git or directory deletion. An archived
checkpoint keeps its original name and every non-optimizer field. Only exact
approved smoke .pt paths are unlinked. Original logs/reports are preservation
inputs, never deletion targets. Interrupted verified promotions can be resumed.
"""
from datetime import datetime, timezone
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import checkpoint_optimizer_archive as codec
from scripts import cleanup_ckpt as regular
from scripts import cleanup_isolated_ckpt as isolated

HERE = ROOT/'handoff/audit/checkpoint_retention_20261105_v1'
SCOPE = HERE/'APPROVED_SCOPE_v1.json'
PLAN = HERE/'PLAN_v1.json'
JOURNAL = HERE/'JOURNAL_v1.jsonl'
RECEIPT = HERE/'RECEIPT_v1.json'
SCHEMA = 'TINYLM_USER110_OPTIMIZER_ARCHIVE_V1'
SOURCE = ('scripts/cleanup_optimizer_archive.py', 'scripts/checkpoint_optimizer_archive.py',
          'scripts/test_cleanup_optimizer_archive.py', 'scripts/cleanup_ckpt.py',
          'scripts/cleanup_isolated_ckpt.py')


def now():
    return datetime.now(timezone.utc).isoformat()


def need(value, reason):
    if not value:
        raise ValueError(reason)


def safe(relative):
    p = Path(relative)
    need(not p.is_absolute() and '..' not in p.parts and str(p) == p.as_posix(),
         'canonical relative path required')
    path = ROOT/p
    need(not any(v.is_symlink() for v in (path, *path.parents)), 'symlink forbidden')
    return path


def identity(path):
    s = path.lstat()
    need(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'single-link regular file required')
    return dict(dev=s.st_dev, ino=s.st_ino, bytes=s.st_size, blocks=s.st_blocks*512,
                mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, mode=stat.S_IMODE(s.st_mode))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def reference(relative):
    path = safe(relative)
    before = identity(path)
    result = dict(path=str(relative), identity=before, sha256=sha(path))
    need(identity(path) == before, 'input changed during hash: '+str(relative))
    return result


def check_ref(row, *, content=True):
    path = safe(row['path'])
    need(identity(path) == row['identity'], 'input identity changed: '+row['path'])
    if content:
        need(sha(path) == row['sha256'], 'input SHA changed: '+row['path'])
    return path


def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+chr(10)).encode('utf-8')
    need(len(raw) < 20_000_000, 'audit file20MB limit')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def event(kind, **fields):
    row = dict(time=now(), kind=kind, **fields)
    with JOURNAL.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+chr(10))
        stream.flush()
        os.fsync(stream.fileno())


def space():
    result = {}
    for name, path in (('wsl', ROOT), ('windows_z', Path('/mnt/z'))):
        v = os.statvfs(path)
        result[name] = v.f_bavail*v.f_frsize
    return result


def host_guard():
    need(space()['windows_z'] >= 1_500_000_000, 'host Z reserve below1.5GB; stop before another write')


def validate_scope(scope):
    need(scope['schema'] == 'TINYLM_USER110_OPTIMIZER_CLEANUP_SCOPE_V1', 'wrong approval schema')
    names = [v['name'] for v in scope['archives']]
    need(len(names) == len(set(names)) == 184, 'exact184 unique models required')
    need(all(re.fullmatch(r'[A-Za-z0-9_.-]+[.]pt', n) for n in names), 'unsafe model name')
    need(scope['remove_root_fields'] == list(codec.REMOVE_FIELDS), 'only opt and opt_muon removal approved')
    need(scope['smoke_sessions'] == ['nov01_adaptive_training_v1', 'nov04_p108_p107_v2'],
         'only approved successful smoke sessions')
    need(scope['smoke_exclude'] == ['tiny_synthetic_2M_dense.pt', 'tiny_synthetic_2M_dense_best.pt'],
         'protected dense names must remain')
    need(scope['p107'] == ['runs/isolated/p107_session_disk_v1_20261101/boundary_u2',
         'runs/isolated/p107_document_cli_v1_20261104/boundary_u1'], 'P107 states must be preserved')
    return set(names)


def smoke_paths(scope):
    result, pinned = [], {}
    reg = regular.parse_tsv()
    for sid in scope['smoke_sessions']:
        allowed, window = isolated.successful_report(ROOT, sid, pinned)
        folder = Path('runs/validation/codex_smoke')/sid/'runs/ckpt'
        names = {v.name for v in safe(folder).iterdir()}
        need(names == allowed and len(names) == 66, 'exact66 original synthetic outputs required')
        for name in sorted(names-set(scope['smoke_exclude'])):
            need(reg.get(name, (0, None))[1] not in ('keep', 'hold'), 'protected smoke basename')
            need(name.startswith('tiny_synthetic_') and name.endswith('.pt'), 'synthetic .pt only')
            row = reference(folder/name)
            need(window[0] <= row['identity']['mtime_ns']/1e9 <= window[1], 'smoke time mismatch')
            result.append(row)
    need(len(result) == 128, 'exact128 smoke targets required')
    return result, pinned


def prepare():
    need(not PLAN.exists() and not JOURNAL.exists(), 'fresh plan only; existing plans must be resumed')
    scope = json.loads(SCOPE.read_text(encoding='utf-8'))
    names = validate_scope(scope)
    registry = (ROOT/'checkpoints.tsv').read_bytes()
    with (HERE/'CHECKPOINTS_BEFORE.tsv').open('xb') as stream:
        stream.write(registry)
    table = regular.parse_tsv()
    why = {}
    for line in registry.decode('utf-8').splitlines():
        fields = line.split(chr(9))
        if len(fields) >= 4 and fields[0] in ('keep', 'hold', 'delete'):
            why[fields[1]] = fields[3]
    explicit9 = {n for n, text in why.items() if '사용자102 명시 지시로 종료 연구9개' in text}
    need(len(explicit9) == 9 and not names & explicit9, 'explicit9 must stay untouched')
    guards = set(regular.PROTECTED) | set(regular.derived_protection())
    for name in names:
        need(table.get(name, (0, None))[1] == 'keep', 'approved archive must be currently keep')
        need(name not in guards and not any(re.match(p, name) for p, _ in regular.PROTECTED_RE),
             'current parent/lineage protection conflict')
    roots = sorted((ROOT/'runs/ckpt').glob('*.pt'))
    need(len(roots) == 364 and names <= {p.name for p in roots}, 'root model membership changed')
    archive, preserved, optimizer_count = [], [], 0
    expected = {r['name']:r['expected_optimizer_bytes'] for r in scope['archives']}
    for index, path in enumerate(roots, 1):
        meta = codec.metadata(path)
        optimizer_count += bool(meta['optimizer_fields'])
        row = reference(path.relative_to(ROOT))
        if path.name in names:
            need(meta['optimizer_exclusive_bytes'] == expected[path.name] > 0, 'optimizer byte contract changed')
            row.update(metadata=meta, stage_path='runs/ckpt/'+path.stem+'__optimizer_free_user110.pt')
            need(not safe(row['stage_path']).exists(), 'unexpected staging checkpoint; preserve and inspect')
            archive.append(row)
        else:
            row['optimizer_fields'] = meta['optimizer_fields']
            preserved.append(row)
        if index % 20 == 0:
            print('[PREPARE_HASH] '+str(index)+'/364', flush=True)
    need(optimizer_count == 223 and sum(bool(r['optimizer_fields']) for r in preserved) == 39,
         'expected223 optimizer models and39 protected optimizer models')
    smoke, pinned = smoke_paths(scope)
    targets = {r['path'] for r in smoke}
    for sid in sorted(p.name for p in safe('runs/validation/codex_smoke').iterdir() if p.is_dir()):
        folder = Path('runs/validation/codex_smoke')/sid/'runs/ckpt'
        if safe(folder).is_dir():
            for path in sorted(safe(folder).iterdir()):
                if path.is_file() and str(path.relative_to(ROOT)) not in targets:
                    preserved.append(reference(path.relative_to(ROOT)))
    for folder in scope['p107']:
        manifest = json.loads((safe(folder)/'manifest.json').read_text(encoding='utf-8'))
        need(len(manifest['parts']) == 49, 'P107 complete49-part state required')
        expected_parts = {'manifest.json'} | {v['path'] for v in manifest['parts']}
        need({p.name for p in safe(folder).iterdir()} == expected_parts, 'P107 member mismatch')
        for path in sorted(safe(folder).iterdir()):
            preserved.append(reference(path.relative_to(ROOT)))
    # Closed root training JSONs and exact smoke evidence are preservation-only.
    metadata_paths = set(pinned)
    for p in roots:
        stem = p.stem.removesuffix('_best')
        log = Path('runs/logs')/(stem+'.json')
        if safe(log).is_file():
            metadata_paths.add(str(log))
    existing = {r['path'] for r in preserved}
    for path in sorted(metadata_paths-existing):
        preserved.append(reference(path))
    need(len(archive) == 184 and not names & explicit9, 'archive scope drift')
    plan = dict(schema=SCHEMA, prepared_at=now(), approval=reference(SCOPE.relative_to(ROOT)),
        sources={p:sha(ROOT/p) for p in SOURCE}, registry_before_sha256=sha(ROOT/'checkpoints.tsv'),
        archives=archive, smoke=smoke, preserved=preserved, explicit9=sorted(explicit9),
        expected_root_names=sorted(p.name for p in roots), space_at_prepare=space(),
        semantics='Only optimizer state removal and exact128 synthetic checkpoint unlink. No other deletion.',
        model_construction=False, gpu=False, git=False)
    write_new(PLAN, plan)
    print('[PREPARED] '+json.dumps(dict(archives=184, smoke=128,
        preserved_files=len(preserved), manifest_sha256=sha(PLAN), space=space())), flush=True)


def read_plan(expected):
    need(expected and sha(PLAN) == expected.upper(), 'explicit reviewed manifest SHA required')
    p = json.loads(PLAN.read_text(encoding='utf-8'))
    need(p['schema'] == SCHEMA and len(p['archives']) == 184 and len(p['smoke']) == 128,
         'wrong plan cardinality/schema')
    check_ref(p['approval'])
    for name, digest in p['sources'].items():
        need(sha(ROOT/name) == digest, 'tool changed after plan: '+name)
    need(len({r['path'] for r in p['archives']+p['smoke']}) == 312, 'unique312 exact inputs')
    need(not {r['path'] for r in p['preserved']} & {r['path'] for r in p['archives']+p['smoke']},
         'preservation/deletion overlap')
    for row in p['archives']:
        need(Path(row['path']).parent == Path('runs/ckpt') and row['path'].endswith('.pt'), 'archive path escape')
        need(row['stage_path'] == 'runs/ckpt/'+Path(row['path']).stem+'__optimizer_free_user110.pt',
             'stage path escape')
    scope = json.loads(SCOPE.read_text(encoding='utf-8'))
    need({Path(r['path']).name for r in p['archives']} == validate_scope(scope), 'approval/plan differ')
    for row in p['smoke']:
        path = Path(row['path'])
        need(path.suffix == '.pt' and path.parent in {
            Path('runs/validation/codex_smoke')/sid/'runs/ckpt' for sid in scope['smoke_sessions']},
             'smoke path escape')
        need(path.name not in scope['smoke_exclude'] and path.name.startswith('tiny_synthetic_'),
             'protected or nonsynthetic smoke target')
    return p


def record_path(row):
    return HERE/'models'/(Path(row['path']).stem+'.json')


def opened_targets(paths):
    result = subprocess.run(['fuser', *[str(ROOT/p) for p in paths]],
                            capture_output=True, text=True, timeout=60)
    need(result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip(),
         'target opened or open-file check unavailable: '+result.stdout[:500]+result.stderr[:500])


def convert(row):
    import torch
    path, stage = safe(row['path']), safe(row['stage_path'])
    rec = record_path(row)
    if rec.exists():
        previous = json.loads(rec.read_text(encoding='utf-8'))
        if not stage.exists() and sha(path) == previous['new_sha256']:
            need(fingerprint_file(path) == previous['retained_fingerprint'], 'recovered archive differs')
            return previous
        need(stage.exists() and sha(stage) == previous['new_sha256'], 'unknown staged recovery state')
        check_ref(row)
    else:
        check_ref(row)
        host_guard()
        loaded = codec.load_cpu(path)
        retained, removed = codec.retained_payload(loaded)
        need(removed == row['metadata']['optimizer_fields'], 'optimizer root fields changed')
        before = codec.fingerprint(retained)
        if stage.exists():
            # A fully written but uncommitted private checkpoint can be verified.
            checked = codec.load_cpu(stage)
            need(not any(k in checked for k in codec.REMOVE_FIELDS), 'uncommitted stage has optimizer')
            need(codec.fingerprint(checked) == before, 'uncommitted stage mismatch; retained for inspection')
            del checked
        else:
            with stage.open('xb') as stream:
                torch.save(retained, stream)
                stream.flush()
                os.fsync(stream.fileno())
        os.chmod(stage, row['identity']['mode'])
        checked = codec.load_cpu(stage)
        need(not any(k in checked for k in codec.REMOVE_FIELDS), 'optimizer removal failed')
        need(codec.fingerprint(checked) == before, 'retained fields/tensor bytes/aliases differ')
        need(stage.stat().st_size < row['identity']['bytes'], 'archive did not shrink')
        previous = dict(path=row['path'], stage_path=row['stage_path'],
            old_sha256=row['sha256'], old_identity=row['identity'],
            new_sha256=sha(stage), new_identity=identity(stage), removed=removed,
            retained_fingerprint=before, optimizer_exclusive_bytes=row['metadata']['optimizer_exclusive_bytes'])
        write_new(rec, previous)
        del checked, retained, loaded
        gc.collect()
    check_ref(row, content=False)
    need(identity(stage) == previous['new_identity'], 'staged checkpoint changed before promotion')
    event('MODEL_PROMOTION_INTENT', path=row['path'], old_sha256=row['sha256'],
          new_sha256=previous['new_sha256'])
    os.replace(stage, path)  # Only the approved checkpoint path is replaced.
    with directory_sync(path.parent):
        pass
    event('MODEL_ARCHIVED', path=row['path'], new_sha256=previous['new_sha256'])
    return previous


class directory_sync:
    def __init__(self, path): self.path = path
    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDONLY|os.O_DIRECTORY)
        os.fsync(self.fd)
    def __exit__(self, *args): os.close(self.fd)


def fingerprint_file(path):
    loaded = codec.load_cpu(path)
    need(not any(k in loaded for k in codec.REMOVE_FIELDS), 'archive still has optimizer')
    result = codec.fingerprint(loaded)
    del loaded
    gc.collect()
    return result


def update_inventory(plan, records):
    before = (HERE/'CHECKPOINTS_BEFORE.tsv').read_text(encoding='utf-8')
    current_sha = sha(ROOT/'checkpoints.tsv')
    if current_sha != plan['registry_before_sha256']:
        after = HERE/'CHECKPOINTS_AFTER.tsv'
        need(after.exists() and current_sha == sha(after), 'inventory changed concurrently')
        return
    indexed = {Path(v['path']).name:v for v in records}
    lines, changed = [], set()
    for line in before.splitlines():
        cells = line.split(chr(9))
        if len(cells) >= 4 and cells[1] in indexed:
            v = indexed[cells[1]]
            need(cells[0] == 'keep', 'archive model verdict must remain keep')
            cells[2] = f"{safe(v['path']).stat().st_size/2**20:.3f}"
            cells[3] += (' / 2026-11-05 사용자110: 가중치·설정·보조필드 동일 검증 후 opt/opt_muon 제거. '
                         '추론/새 학습 초기화용이며 정확 resume 불가. oldSHA='+v['old_sha256']+
                         ' newSHA='+v['new_sha256']+'; checkpoint_retention_20261105_v1/models/'+
                         Path(v['path']).stem+'.json')
            line = chr(9).join(cells)
            changed.add(cells[1])
        lines.append(line)
    need(len(changed) == 184, 'inventory must update exact184 rows only')
    note = ('# 2026-11-05 사용자110:184모델의 optimizer만 제거하고 이름/가중치/기타필드를 보존했다. '
            '보호39/가중치전용141/P107상태·원로그/보고서는 유지. 지정 격리스모크128개만 삭제. '
            '실제 검증/old-new SHA는 handoff/audit/checkpoint_retention_20261105_v1/ 참조.')
    body = (note+chr(10)+chr(10).join(lines)+chr(10)).encode('utf-8')
    with (HERE/'CHECKPOINTS_AFTER.tsv').open('xb') as stream:
        stream.write(body); stream.flush(); os.fsync(stream.fileno())
    temporary = HERE/'INVENTORY_REPLACEMENT.tsv'
    with temporary.open('xb') as stream:
        stream.write(body); stream.flush(); os.fsync(stream.fileno())
    need(sha(ROOT/'checkpoints.tsv') == plan['registry_before_sha256'], 'inventory race')
    os.replace(temporary, ROOT/'checkpoints.tsv')  # Authorized list update; backups remain.
    event('INVENTORY_UPDATED', rows=184, sha256=sha(ROOT/'checkpoints.tsv'))


def apply(plan):
    need(not RECEIPT.exists(), 'already applied; use verify')
    host_guard()
    prior = [json.loads(v) for v in JOURNAL.read_text().splitlines()] if JOURNAL.exists() else []
    intents = {v['path'] for v in prior if v['kind'] == 'SMOKE_DELETE_INTENT'}
    alive = []
    for row in plan['smoke']:
        if not safe(row['path']).exists():
            need(row['path'] in intents, 'missing smoke without owned prior intent')
        else:
            check_ref(row); alive.append(row['path'])
    for row in plan['archives']:
        if not record_path(row).exists():
            check_ref(row)
            alive.append(row['path'])
    opened_targets(alive)
    for row in plan['preserved']:
        check_ref(row, content=False)
    baseline = space()
    event('APPLY_BEGIN', space=baseline, archives=184, smoke=128)
    for row in plan['smoke']:
        path = safe(row['path'])
        if path.exists():
            check_ref(row)
            event('SMOKE_DELETE_INTENT', path=row['path'], sha256=row['sha256'], identity=row['identity'])
            path.unlink()  # The only unlink in this tool: exact128 approved .pt paths.
            event('SMOKE_DELETED', path=row['path'])
    print('[SMOKE_REMOVED] exact128; logs and reports retained', flush=True)
    records = []
    for index, row in enumerate(plan['archives'], 1):
        records.append(convert(row))
        if index % 5 == 0 or index == 184:
            print('[ARCHIVE_PROGRESS] '+json.dumps(dict(models=index, total=184, space=space())), flush=True)
    update_inventory(plan, records)
    after = verify(plan, report_name='FINAL_VERIFICATION_v1.json')
    result = dict(schema=SCHEMA, status='COMPLETE', finished_at=now(),
        archives=184, smoke_deleted=128, model_weights_changed=0,
        protected_optimizer_models=39, p107_states_preserved=2,
        noncheckpoint_deletions=0, log_report_deletions=0, gpu=False, git=False,
        logical_bytes_removed=sum(r['old_identity']['bytes']-r['new_identity']['bytes'] for r in records)
                              +sum(r['identity']['bytes'] for r in plan['smoke']),
        allocated_bytes_removed=sum(r['old_identity']['blocks']-r['new_identity']['blocks'] for r in records)
                              +sum(r['identity']['blocks'] for r in plan['smoke']),
        space_before=baseline, space_after=space(), verification=after)
    write_new(RECEIPT, result)
    print('[CLEANUP_COMPLETE] '+json.dumps(result), flush=True)


def verify(plan, report_name):
    need(sorted(p.name for p in safe('runs/ckpt').glob('*.pt')) == plan['expected_root_names'],
         'root checkpoint membership changed or staging remains')
    need(all(not safe(r['path']).exists() for r in plan['smoke']), 'approved smoke remains')
    for index, row in enumerate(plan['preserved'], 1):
        check_ref(row)
        if index % 75 == 0:
            print('[PRESERVE_VERIFY] '+str(index)+'/'+str(len(plan['preserved'])), flush=True)
    for index, row in enumerate(plan['archives'], 1):
        saved = json.loads(record_path(row).read_text(encoding='utf-8'))
        path = safe(row['path'])
        need(sha(path) == saved['new_sha256'], 'new archive SHA mismatch')
        need(fingerprint_file(path) == saved['retained_fingerprint'], 'new archive retained graph mismatch')
        if index % 10 == 0:
            print('[ARCHIVE_VERIFY] '+str(index)+'/184', flush=True)
    need(sha(ROOT/'checkpoints.tsv') == sha(HERE/'CHECKPOINTS_AFTER.tsv'), 'inventory not published exactly')
    result = dict(schema=SCHEMA, status='VERIFIED', checked_at=now(),
        root_models=364, converted=184, deleted_smoke=128,
        protected_files_sha_identity_unchanged=len(plan['preserved']),
        protected_optimizer_models=39, p107_complete_states=2,
        tensor_bytes_dtype_shape_view_storage_aliases_and_other_fields=True,
        model_execution=False, gpu=False, space=space())
    write_new(HERE/report_name, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'apply', 'verify'))
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(); return 0
    plan = read_plan(args.manifest_sha256)
    try:
        if args.mode == 'apply':
            apply(plan)
        else:
            verify(plan, 'INDEPENDENT_VERIFICATION_v1.json')
    except BaseException as exc:
        import uuid
        write_new(HERE/('FAILURE_'+uuid.uuid4().hex+'.json'), dict(
            schema=SCHEMA, time=now(), mode=args.mode, error_type=type(exc).__name__,
            error=str(exc), space=space(), journal_preserved=JOURNAL.exists(),
            instruction='Keep existing checkpoints, stages, source logs and journal; inspect before resume.'))
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
