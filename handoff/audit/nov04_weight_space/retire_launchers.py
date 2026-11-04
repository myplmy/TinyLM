"""One-session P108 launcher archival and explicitly scoped retirement.

prepare preserves exact bytes/commands and produces a reviewable result patch.
apply accepts that manifest's SHA, verifies result preservation, marks closed
attempts -done and removes only those sixteen SH files. Unrun replacements are
kept as -cancel. Original logs, checkpoints and unrelated launchers are untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess

from scripts.sync_experiments_tsv import batch_commands, norm

BASE = Path('handoff/audit/nov04_weight_space')
RESULT = Path('test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md')
MANIFEST = BASE/'LAUNCHER_ARCHIVE_v1.json'
UNRUN = frozenset(('run_P108_Stage2W_weight_direction_search.sh',
                  'run_P108_Stage3W_weight_direction_confirm.sh',
                  'run_P108_Stage3bW_weight_direction_confirm.sh'))


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def write_new(path, obj):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))


def prepare():
    if MANIFEST.exists():
        raise FileExistsError(MANIFEST)
    paths = sorted(Path('.').glob('run_P108_*.sh'))
    if len(paths) != 19 or not UNRUN <= {p.name for p in paths}:
        raise ValueError('exact 19 owned P108 launchers required')
    (BASE/'launchers').mkdir(exist_ok=False)
    rows, text = [], ['## 11. 수행 명령 원형과 완료 런처 정리', '',
        '실제 수행16개는 실패1시도를 포함한 종료 기록이며 성공16개를 뜻하지 않는다. '
        '미수행3개는 더 엄격한 새 단계로 대체됐으므로 취소 보존한다. '
        '원형/정확 argv/SHA를 아래와 [명령 보존 영수증](../handoff/audit/nov04_weight_space/LAUNCHER_ARCHIVE_v1.json)에 남긴다. '
        '삭제는 봉인된 출력의 반복 실행을 요청하는 뜻이 아니며 재실행에는 새 승인·태그가 필요하다.', '']
    for p in paths:
        subprocess.run(['bash', '-n', str(p)], check=True, capture_output=True)
        raw = p.read_bytes()
        blob = BASE/'launchers'/(p.name+'.txt')
        with blob.open('xb') as stream:
            stream.write(raw)
        log = Path('test_result')/('108_log_20261104_'+p.stem.removeprefix('run_')+'.txt')
        codes = re.findall(r'종료코드\s+(-?\d+)', log.read_text(encoding='utf-8')) if log.exists() else []
        unrun = p.name in UNRUN
        if unrun == bool(codes):
            raise ValueError('actual log/NOT_RUN classification differs: '+p.name)
        commands = batch_commands(p)
        if not commands:
            raise ValueError('exact executable command missing')
        row = dict(original=p.name, sha256=sha(raw), bytes=len(raw),
            mode=stat.S_IMODE(p.stat().st_mode), archive=str(blob), commands=commands,
            disposition='UNRUN_REPLACED_CANCEL_KEEP' if unrun else 'CLOSED_DONE_THEN_DELETE',
            after=p.stem+('-cancel.sh' if unrun else '-done.sh'),
            actual_exit=None if unrun else int(codes[-1]),
            raw_log=None if unrun else str(log),
            raw_log_sha256=None if unrun else sha(log.read_bytes()))
        rows.append(row)
        text += ['### '+p.name, '',
            ('NOT_RUN·대체되어 취소 보존.' if unrun else '실제 종료코드 '+codes[-1]+'. 종료한 시도이며 과학적 채택과 별개다.'),
            '', '```sh', *raw.decode('utf-8').splitlines(), '```', '']
    manifest = dict(schema='P108_LAUNCHER_ARCHIVE_V1',
        authority='CURRENT_USER107_AND_STANDING_COMMAND_PRESERVING_LAUNCHER_CLEANUP',
        exact_owned_launchers=19, planned_done_delete=16, planned_cancel_keep=3,
        original_log_writes=0, checkpoint_actions=0, unrelated_launcher_actions=0,
        no_completed_rerun_planned=True, entries=rows)
    write_new(MANIFEST, manifest)
    last = RESULT.read_text(encoding='utf-8').rstrip().splitlines()[-1]
    patch = ('*** Begin Patch\n*** Update File: /home/uranus/tinyLM/'+str(RESULT)+
        '\n@@\n '+last+'\n+'+chr(10)+
        ''.join('+'+line+chr(10) for line in text)+'*** End Patch'+chr(10))
    with (BASE/'LAUNCHER_COMMANDS_v1.patch').open('x', encoding='utf-8') as stream:
        stream.write(patch)
    print(json.dumps(dict(manifest=str(MANIFEST), sha256=sha(MANIFEST.read_bytes()),
                          done_delete=16, cancel_keep=3, syntax_checked=19)))


def apply(expected):
    if sha(MANIFEST.read_bytes()) != expected:
        raise ValueError('exact retirement manifest SHA required')
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    result = norm(RESULT.read_text(encoding='utf-8'))
    receipt = BASE/'LAUNCHER_RETIREMENT_v1.json'
    renamed = BASE/'LAUNCHER_DONE_RENAME_v1.json'
    if receipt.exists() or renamed.exists():
        raise FileExistsError('retirement already started; inspect preserved receipt')
    for row in m['entries']:
        src, backup, dst = map(Path, (row['original'], row['archive'], row['after']))
        if (sha(src.read_bytes()) != row['sha256'] or sha(backup.read_bytes()) != row['sha256']
                or dst.exists() or src.is_symlink()):
            raise ValueError('retirement original/archive/destination differs')
        if any(norm(command) not in result for command in row['commands']):
            raise ValueError('result omitted an exact executable command')
        if row['raw_log'] and sha(Path(row['raw_log']).read_bytes()) != row['raw_log_sha256']:
            raise ValueError('closed raw log changed')
    for row in m['entries']:
        Path(row['original']).rename(row['after'])
        if sha(Path(row['after']).read_bytes()) != row['sha256']:
            raise ValueError('rename byte mismatch')
    write_new(renamed, dict(schema='P108_DONE_RENAME_V1', manifest_sha256=expected,
        entries=[dict(path=r['after'], sha256=r['sha256'], disposition=r['disposition']) for r in m['entries']]))
    removed, kept = [], []
    for row in m['entries']:
        path = Path(row['after'])
        if row['disposition'] == 'CLOSED_DONE_THEN_DELETE':
            if sha(path.read_bytes()) != row['sha256']:
                raise ValueError('changed completed launcher; do not delete')
            path.unlink()
            removed.append(row['after'])
        else:
            kept.append(row['after'])
    write_new(receipt, dict(schema='P108_LAUNCHER_RETIREMENT_V1', manifest_sha256=expected,
        renamed_done_then_deleted=removed, cancelled_preserved=kept,
        raw_logs_preserved=True, original_checkpoints_changed=0,
        unrelated_paths_changed=0, recovered_via='EXACT_ARCHIVE_BYTES_AND_RECORDED_MODE',
        only_empty_namespace_reruns=False))
    print(json.dumps(dict(deleted=len(removed), cancel_preserved=len(kept), raw_logs='PRESERVED')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'apply'))
    parser.add_argument('manifest_sha256', nargs='?')
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare()
    else:
        apply(args.manifest_sha256)
