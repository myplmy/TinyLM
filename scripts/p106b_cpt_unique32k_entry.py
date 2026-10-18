#!/usr/bin/env python3
"""Separate fourth-cell phase adapter; shared receipts, no stdin."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import json
import subprocess
from scripts.p106b_stage_receipt import pipeline

MODES = ('prepare', 'prepare_eval', 'preflight', 'cost', 'train', 'eval_final', 'eval_best', 'readback')


def phase_commands(mode):
    if mode not in MODES:
        raise ValueError('explicit registered fourth-cell phase required')
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/diag_p106b_cpt_unique32k.py']
    evaluation = py + ['scripts/diag_p106b_cpt_unique32k_eval.py']
    tests = py + ['-m', 'unittest', 'scripts.test_p106b_cpt_unique32k',
        'scripts.test_p106b_cpt_unique32k_entry', 'scripts.test_p106b_cpt_unique32k_eval', '-v']
    phases = [('REGRESSION', tests)]
    if mode == 'prepare':
        return phases + [('PREFLIGHT', driver + ['--mode', 'prepare', '--check-only']),
            ('EXECUTE', driver + ['--mode', 'prepare', '--execute'])]
    if mode == 'preflight':
        return phases + [('PREFLIGHT', driver + ['--mode', 'preflight', '--check-only']),
            ('EXECUTE', driver + ['--mode', 'preflight', '--execute'])]
    phases += [('PREFLIGHT', driver + ['--mode', 'preflight', '--execute'])]
    if mode == 'prepare_eval':
        return phases + [('EXECUTE', evaluation + ['--mode', 'freeze', '--execute'])]
    if mode in ('cost', 'train'):
        return phases + [('EXECUTE', driver + ['--mode', mode, '--max-wall-sec',
            '3600' if mode == 'cost' else '10800', '--execute'])]
    if mode in ('eval_final', 'eval_best'):
        endpoint = 'cpt_unique32k_best' if mode == 'eval_best' else 'cpt_unique32k'
        return phases + [('EXECUTE', evaluation + ['--mode', 'evaluate', '--endpoint', endpoint,
            '--max-wall-sec', '3600', '--execute'])]
    return phases + [('EXECUTE', evaluation + ['--mode', 'readback', '--execute'])]


def run(mode):
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL).returncode
    receipt = pipeline(phase_commands(mode), launch, lambda value: print(value, flush=True),
        experiment='P106B_CPT_UNIQUE32K_' + mode)
    print('[EVIDENCE_BOUNDARY] Phase completion is not correctness, intelligence or adoption.', flush=True)
    return receipt['returncode']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps(dict(mode=args.mode, phases=phase_commands(args.mode), model_loaded=False,
            gpu_initialized=False, optimizer_updates=0))); return 0
    return run(args.mode)


if __name__ == '__main__':
    raise SystemExit(main())
