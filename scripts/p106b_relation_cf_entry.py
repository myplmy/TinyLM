#!/usr/bin/env python3
"""P106B CF phase receipts; never interactive and never a quality verdict."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import json
import subprocess
from scripts.p106b_stage_receipt import pipeline


def phase_commands(mode, model=None, max_wall_sec=3600):
    if mode not in ('prepare', 'evaluate', 'readback'):
        raise ValueError('explicit CF mode required')
    if ((mode == 'evaluate' and model not in ('parent', 'ce', 'contrast'))
            or (mode != 'evaluate' and model is not None)):
        raise ValueError('evaluate requires one endpoint; prepare/readback select all')
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600:
        raise ValueError('bounded wall time required')
    py = [sys.executable, '-B', '-X', 'utf8']
    command = py + ['scripts/p106b_relation_cf_eval.py', '--mode', mode,
                    '--max-wall-sec', str(max_wall_sec)]
    if model is not None:
        command += ['--model', model]
    tests = py + ['-m', 'unittest', 'scripts.test_p106b_relation_cf_eval',
                 'scripts.test_p106b_relation_cf_entry', '-v']
    return [('REGRESSION', tests), ('PREFLIGHT', command + ['--check-only']),
            ('EXECUTE', command + ['--execute'])]


def run(mode, model=None, max_wall_sec=3600):
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL).returncode
    receipt = pipeline(phase_commands(mode, model, max_wall_sec), launch,
        lambda line: print(line, flush=True), experiment='P106B_CF_' + mode + ('_' + model if model else ''))
    print('[EVIDENCE_BOUNDARY] ' + ('CPU source preparation; learned model/GPU0.'
          if mode == 'prepare' else 'Phase completion is not semantic correctness or model adoption.'), flush=True)
    return receipt['returncode']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'evaluate', 'readback'), required=True)
    parser.add_argument('--model', choices=('parent', 'ce', 'contrast'))
    parser.add_argument('--max-wall-sec', type=int, default=3600)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        phases = phase_commands(args.mode, args.model, args.max_wall_sec)
    except ValueError as exc:
        parser.error(str(exc))
    if args.check_only:
        print(json.dumps(dict(phases=phases, model_loaded=False))); return 0
    return run(args.mode, args.model, args.max_wall_sec)


if __name__ == '__main__': raise SystemExit(main())
