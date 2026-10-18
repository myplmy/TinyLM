#!/usr/bin/env python3
"""P106B relation-only phase adapter; reuse shared P106B receipt, never stdin."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import json
import subprocess
from scripts.p106b_stage_receipt import pipeline

MODES = ('prepare', 'cost_ce', 'cost_contrast', 'train_ce', 'train_contrast', 'evaluate', 'readback')


def phase_commands(mode):
    if mode not in MODES: raise ValueError('explicit relation phase required')
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/diag_p106b_relation_bind.py']
    tests = py + ['-m', 'unittest', 'scripts.test_p106b_relation_bind_data',
        'scripts.test_p106b_relation_bind_loss', 'scripts.test_p106b_relation_bind',
        'scripts.test_p106b_relation_bind_entry', '-v']
    if mode == 'prepare':
        before = driver + ['--mode', 'prepare', '--check-only']
        execute = driver + ['--mode', 'prepare', '--execute']
    elif mode.startswith('cost_') or mode.startswith('train_'):
        phase, arm = mode.split('_', 1)
        before = driver + ['--mode', 'preflight', '--execute']
        execute = driver + ['--mode', phase, '--arm', arm, '--execute', '--budget-hours', '4',
                            '--max-wall-sec', '3600' if phase == 'cost' else '10800']
    else:
        before = driver + ['--mode', 'preflight', '--execute']
        execute = driver + ['--mode', mode, '--execute', '--max-wall-sec', '10800']
    return [('REGRESSION', tests), ('PREFLIGHT', before), ('EXECUTE', execute)]


def run(mode):
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL).returncode
    receipt = pipeline(phase_commands(mode), launch, lambda text: print(text, flush=True),
                       experiment='P106B_RELATION_' + mode)
    print('[EVIDENCE_BOUNDARY] ' + ('CPU data preparation only; model loading/GPU/training0.'
          if mode == 'prepare' else 'Phase completion is not correctness or model adoption.'), flush=True)
    return receipt['returncode']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=MODES, required=True)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = p.parse_args()
    if args.check_only:
        print(json.dumps(dict(mode=args.mode, phases=phase_commands(args.mode), models_loaded=False))); return 0
    return run(args.mode)


if __name__ == '__main__': raise SystemExit(main())
