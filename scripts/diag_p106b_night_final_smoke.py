#!/usr/bin/env python3
"""Explicitly authorized complete smoke, isolated outputs and Codex checker.

The canonical action list is parsed unchanged. One forbidden legacy document
checker is replaced, and the unchanged field checker reads the isolated logs.
Neither transformation changes a training/model/diagnostic arm or its flags.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.smoke_module import DEFAULT_SOURCE, parse_smoke_module

TAG = 'p106b_night_final_smoke_v1_s1337'
RUNTIME = ROOT / 'runs/validation' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
LOGNAME = 'smoke_codex_20261017_night_final_v1'
SELF = 'scripts/diag_p106b_night_final_smoke.py'
CODEX_CHECKER = '.agents/skills/session-handoff/scripts/check_handoff_codex.py'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def adapt(actions):
    output, edits = [], []
    for action in actions:
        original = list(action.argv)
        argv = list(original)
        if 'scripts/check_handoff.py' in argv:
            index = argv.index('scripts/check_handoff.py')
            argv[index:index+1] = ['-I', '-B', CODEX_CHECKER]
            edits.append(dict(line=action.line, kind='codex_document_checker',
                              before=original, after=argv))
        if 'scripts/check_smoke.py' in argv:
            index = argv.index('scripts/check_smoke.py')
            argv[index:index+1] = [SELF, '--mode', 'contract']
            edits.append(dict(line=action.line, kind='isolated_field_log_path',
                              before=original, after=argv))
        output.append(replace(action, argv=tuple(argv)))
    if [x['kind'] for x in edits] != ['codex_document_checker', 'isolated_field_log_path']:
        raise ValueError('exactly the two declared substitutions required')
    for before, after in zip(actions, output):
        if before.kind != after.kind or before.line != after.line or before.seconds != after.seconds:
            raise ValueError('canonical action topology changed')
        if before.kind == 'run' and 'run100m.py' in before.argv and before.argv != after.argv:
            raise ValueError('training flags must be byte-identical')
    return output, edits


def contract():
    from scripts import check_smoke
    if Path(os.environ.get('TINYLM_DIR', '')).resolve() != RUNTIME.resolve():
        raise ValueError('field checker requires the exact isolated runtime')
    check_smoke.LOGS = RUNTIME / 'runs/logs'
    sys.argv = [SELF]
    return check_smoke.main()


def environment():
    env = dict(os.environ)
    env.update(TINYLM_DIR=str(RUNTIME), TINYLM_HF=str(RUNTIME / 'HF'),
               TL_OUTDIR='smoketest_logs', TL_LOGNAME=LOGNAME, TL_NOPAUSE='1',
               TL_WANDB_AUTO='0', WANDB_MODE='disabled', HF_HUB_OFFLINE='1',
               HF_DATASETS_OFFLINE='1', PYTHONIOENCODING='utf-8',
               PYTHONUNBUFFERED='1', TZ='Asia/Seoul')
    env.pop('TL_STAMP', None)
    return env


def original_snapshot():
    """Only the original synthetic smoke namespace, never real training data."""
    paths = list((ROOT/'runs/ckpt').glob('tiny_synthetic_*.pt'))
    paths += list((ROOT/'runs/logs').glob('tiny_synthetic_*.json'))
    for base in (ROOT/'data_cache').glob('synthetic_*'):
        if base.is_symlink():
            raise ValueError('original synthetic cache must not be linked')
        paths += [base/name for name in ('train.bin', 'val.bin', 'meta.json') if (base/name).is_file()]
    if any(p.is_symlink() for p in paths):
        raise ValueError('original synthetic smoke file must not be linked')
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('check', 'full', 'contract'), default='check')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.mode == 'contract':
        return contract()
    actions = parse_smoke_module(log_name=LOGNAME)
    changed, edits = adapt(actions)
    children = [a for a in actions if a.kind == 'run' and '--' in a.argv]
    trains = [a for a in children if 'run100m.py' in a.argv]
    metadata = dict(schema='P106B_AUTHORIZED_CODEX_COMPLETE_SMOKE_NIGHT_FINAL_V1',
        source=str(DEFAULT_SOURCE.relative_to(ROOT)), source_sha256=digest(DEFAULT_SOURCE),
        driver_sha256=digest(__file__), action_count=len(actions),
        child_count=len(children), training_count=len(trains), substitutions=edits,
        runtime=str(RUNTIME.relative_to(ROOT)), protected_originals_modified='NOT_YET_CHECKED',
        interpretation='all canonical dynamic arms; NOT unmodified canonical wrapper')
    print('[AUTHORIZED_SMOKE_CONTRACT] ' + json.dumps(metadata, ensure_ascii=False), flush=True)
    if args.mode == 'check':
        return 0
    if not args.execute:
        parser.error('full execution requires --execute and current user GPU approval')
    # Leave30 minutes before the root09:00 GPU stop; do not start a late suite.
    if datetime.now(timezone.utc) >= datetime(2026,10,17,0,0,tzinfo=timezone.utc)-timedelta(minutes=30):
        print('[AUTHORIZED_SMOKE_HOLD] less than30 minutes before09:00; no suite started')
        return 8
    report = EVIDENCE / 'smoke_report.json'
    if RUNTIME.exists() or RUNTIME.is_symlink() or report.exists() or list((ROOT/'smoketest_logs').glob(f'*_{LOGNAME}_*.txt')):
        raise FileExistsError('previous smoke output preserved; use a new version')
    before = original_snapshot()
    RUNTIME.mkdir(parents=True, exist_ok=False)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    env = environment()
    start = time.perf_counter()
    receipts = []
    for action in changed:
        if action.kind == 'sleep':
            time.sleep(action.seconds)
            continue
        process = subprocess.run(action.argv, cwd=ROOT, env=env, check=False)
        receipts.append(dict(line=action.line, returncode=process.returncode,
                             child='--' in action.argv))
    logs = list((ROOT/'smoketest_logs').glob(f'*_{LOGNAME}_*.txt'))
    if len(logs) != 1:
        raise ValueError('exactly one write-once smoke session log required')
    summary = subprocess.run([sys.executable, 'scripts/runlog.py', '--name', LOGNAME,
        '--', sys.executable, 'scripts/summarize_smoke.py', '--log', str(logs[0])],
        cwd=ROOT, env=env, check=False)
    if logs[0].stat().st_size >= 20_000_000:
        raise ValueError('log exceeds user 20MB limit; preserve and split before staging')
    unchanged = original_snapshot() == before
    metadata.update(whole_sec=time.perf_counter()-start, receipts=receipts,
        log=str(logs[0].relative_to(ROOT)), log_sha256=digest(logs[0]),
        summary_returncode=summary.returncode,
        failed_calls=sum(x['returncode'] != 0 for x in receipts),
        original_synthetic_sha256=before, original_synthetic_unchanged=unchanged,
        protected_originals_modified=not unchanged)
    with report.open('x', encoding='utf-8') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print('[AUTHORIZED_SMOKE_FINISHED] ' + str(report.relative_to(ROOT)), flush=True)
    return 1 if metadata['failed_calls'] or not unchanged else summary.returncode


if __name__ == '__main__':
    raise SystemExit(main())
