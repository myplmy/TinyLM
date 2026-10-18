#!/usr/bin/env python3
"""Scoped smoke adapter: canonical arms, fresh synthetic storage, Codex docs.

Never mutate the canonical smoke, environment tools, or prior synthetic runs.
Only the legacy document checker and fixed check_smoke log directory are
adapted. This is not a claim that the untouched shell wrapper was executed.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import smoke_module

DEFAULT_ROOT = ROOT / 'test_result/evidence/local/p106b_relation_bind_v1_s1337/smoke_20261019'


def output_root(path):
    path = Path(path).absolute()
    allowed = ROOT / 'test_result/evidence/local'
    path.relative_to(allowed)
    if '..' in path.parts or path == allowed:
        raise ValueError('explicit scoped smoke output required')
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise ValueError('linked smoke output forbidden')
        if parent == ROOT: break
    return path


def adapted_actions(root):
    root = output_root(root)
    actions = smoke_module.parse_smoke_module()
    changes = []
    result = []
    for action in actions:
        argv = list(action.argv)
        if action.kind == 'run' and '--' in argv:
            at = argv.index('--')
            child = argv[at + 1:]
            if child == [sys.executable, 'scripts/check_handoff.py']:
                argv[at + 1:] = [sys.executable, '-I', '-B',
                    '.agents/skills/session-handoff/scripts/check_handoff_codex.py']
                changes.append('legacy_handoff_to_codex')
            elif child == [sys.executable, 'scripts/check_smoke.py']:
                argv[at + 1:] = [sys.executable, '-B', '-X', 'utf8',
                    'scripts/p106b_relation_smoke.py', '--contract', '--root', str(root)]
                changes.append('contract_reads_fresh_isolated_logs')
        result.append(replace(action, argv=tuple(argv)))
    if changes != ['legacy_handoff_to_codex', 'contract_reads_fresh_isolated_logs']:
        raise ValueError('canonical adapter sites changed; inspect before execution')
    return result, dict(adaptations=changes, output_root=str(root),
        canonical_sha256=hashlib.sha256(smoke_module.DEFAULT_SOURCE.read_bytes()).hexdigest().upper(),
        canonical_actions=len(actions), actual_actions=len(result),
        prior_checkpoint_writes=False, protected_dataset_access=False,
        source='scripts/batch/tool_smoke.bat', action_manifest=[asdict(a) for a in result])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    action.add_argument('--contract', action='store_true')
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = output_root(args.root)
    if args.contract:
        from scripts import check_smoke
        check_smoke.LOGS = root / 'runs/logs'
        sys.argv = [sys.argv[0]]
        return check_smoke.main()
    actions, proof = adapted_actions(root)
    if args.check_only:
        print(json.dumps(proof, ensure_ascii=False)); return 0
    if root.exists(): raise FileExistsError('old smoke output preserved; new exact root required')
    root.mkdir(parents=True, exist_ok=False)
    with (root / 'isolation.json').open('x', encoding='utf-8') as stream:
        json.dump(proof, stream, ensure_ascii=False, indent=2)
    os.environ.update(TINYLM_DIR=str(root), TL_OUTDIR='smoketest_logs',
        TL_LOGNAME='smoke', TL_NOPAUSE='1', PYTHONIOENCODING='utf-8',
        HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1')
    smoke_module.execute(actions[:1], log_name='smoke')
    runlog = [sys.executable, '-B', '-X', 'utf8', 'scripts/runlog.py', '--name', 'smoke']
    subprocess.run(runlog + ['--note', '[SMOKE_ISOLATION] ' + json.dumps({
        k:v for k,v in proof.items() if k != 'action_manifest'})], cwd=ROOT,
        stdin=subprocess.DEVNULL, check=True)
    smoke_module.execute(actions[1:], log_name='smoke')
    return subprocess.run(runlog + ['--', sys.executable, '-B', '-X', 'utf8',
        'scripts/summarize_smoke.py'], cwd=ROOT, stdin=subprocess.DEVNULL).returncode


if __name__ == '__main__': raise SystemExit(main())
