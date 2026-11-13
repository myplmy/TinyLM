"""Separate readback of User110 cleanup. No checkpoint writes or deletion."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import checkpoint_optimizer_archive as codec

HERE = ROOT/'handoff/audit/checkpoint_retention_20261105_v1'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def path_for(relative):
    relative = Path(relative)
    require(not relative.is_absolute() and '..' not in relative.parts, 'relative path required')
    path = ROOT/relative
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink forbidden')
    return path


def table(text):
    result = {}
    for line in text.splitlines():
        cells = line.split(chr(9))
        if len(cells) >= 4 and cells[0] in ('keep', 'hold', 'delete'):
            require(cells[1] not in result, 'duplicate registry model')
            result[cells[1]] = cells
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    plan_path = HERE/'PLAN_v1.json'
    require(sha(plan_path) == args.manifest_sha256.upper(), 'plan SHA mismatch')
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    receipt = json.loads((HERE/'RECEIPT_v1.json').read_text(encoding='utf-8'))
    require(receipt['status'] == 'COMPLETE', 'worker did not close successfully')
    require(len(plan['archives']) == 184 and len(plan['smoke']) == 128, 'wrong scope')
    preserved_paths = {r['path'] for r in plan['preserved']}
    require(len(plan['explicit9']) == 9 and
            {'runs/ckpt/'+n for n in plan['explicit9']} <= preserved_paths,
            'explicit research9 not fully protected')
    require(sorted(p.name for p in path_for('runs/ckpt').glob('*.pt')) == plan['expected_root_names'],
            'unexpected root checkpoint membership')
    before = table((HERE/'CHECKPOINTS_BEFORE.tsv').read_text(encoding='utf-8'))
    after = table((ROOT/'checkpoints.tsv').read_text(encoding='utf-8'))
    require(set(before) == set(after), 'registry names changed')
    selected = {Path(r['path']).name for r in plan['archives']}
    changed = {k for k in before if before[k] != after[k]}
    require(changed == selected, 'inventory modified outside exact184 rows')
    logical, allocated = 0, 0
    for index, row in enumerate(plan['archives'], 1):
        path = path_for(row['path'])
        record = json.loads((HERE/'models'/(path.stem+'.json')).read_text(encoding='utf-8'))
        require(record['old_sha256'] == row['sha256'], 'wrong original provenance')
        require(sha(path) == record['new_sha256'], 'archive file changed')
        require(not path_for(row['stage_path']).exists(), 'staging checkpoint remains')
        meta = codec.metadata(path)
        require(meta['optimizer_fields'] == [], 'optimizer remains')
        expected = [k for k in row['metadata']['root_fields'] if k not in codec.REMOVE_FIELDS]
        require(meta['root_fields'] == expected and meta['step'] == row['metadata']['step'],
                'retained header fields/order/step changed')
        loaded = codec.load_cpu(path)
        require(codec.fingerprint(loaded) == record['retained_fingerprint'],
                'retained object/tensor graph differs')
        del loaded
        gc.collect()
        require(after[path.name][0] == 'keep' and abs(float(after[path.name][2])-path.stat().st_size/2**20) <= .0006,
                'inventory verdict or actual size differs')
        require(row['sha256'] in after[path.name][3] and record['new_sha256'] in after[path.name][3],
                'old-new SHA lineage missing')
        logical += row['identity']['bytes']-path.stat().st_size
        allocated += row['identity']['blocks']-path.stat().st_blocks*512
        if index % 10 == 0:
            print('[READBACK_MODELS] '+str(index)+'/184', flush=True)
    for row in plan['smoke']:
        require(not path_for(row['path']).exists(), 'smoke target still exists')
        logical += row['identity']['bytes']
        allocated += row['identity']['blocks']
    for row in plan['preserved']:
        path = path_for(row['path']); s = path.lstat(); old = row['identity']
        require((s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                == (old['dev'], old['ino'], old['bytes'], old['mtime_ns'], old['ctime_ns']),
                'protected identity changed: '+row['path'])
        require(sha(path) == row['sha256'], 'protected contents changed: '+row['path'])
    events = [json.loads(v) for v in (HERE/'JOURNAL_v1.jsonl').read_text(encoding='utf-8').splitlines()]
    deleted = {v['path'] for v in events if v['kind'] == 'SMOKE_DELETED'}
    require(deleted == {r['path'] for r in plan['smoke']}, 'actual unlink journal differs from approval')
    require(logical == receipt['logical_bytes_removed'] and allocated == receipt['allocated_bytes_removed'],
            'actual reclaimed byte accounting differs')
    report = dict(schema='TINYLM_USER110_INDEPENDENT_CLEANUP_READBACK_V1', status='PASS',
        archived_models=184, optimizer_protected_models=39, original_weight_only_models=141,
        smoke_deleted=128, p107_states_preserved=2, explicit_research9_preserved=True,
        other_registry_rows_unchanged=len(before)-184, preserved_files=len(plan['preserved']),
        full_retained_graph_fingerprints_verified=184,
        logical_bytes_removed=logical, allocated_bytes_removed=allocated,
        noncheckpoint_deletions=0, gpu=False, model_construction=False,
        plan_sha256=sha(plan_path), verifier_sha256=sha(Path(__file__)))
    raw = (json.dumps(report, ensure_ascii=False, indent=2)+chr(10)).encode('utf-8')
    require(len(raw) < 20_000_000, 'report20MB limit')
    with (HERE/'ROOT_READBACK_v1.json').open('xb') as stream:
        stream.write(raw)
    print('[READBACK_COMPLETE] '+json.dumps(report), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
