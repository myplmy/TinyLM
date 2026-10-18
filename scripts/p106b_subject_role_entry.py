#!/usr/bin/env python3
"""Explicit three-phase subject/role study adapter; no interactive input."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import json
import math
import subprocess
from scripts.p106b_stage_receipt import pipeline

MODES = ('prepare', 'preflight', 'cost', 'train', 'evaluate', 'probe_old', 'readback', 'budget')
ARMS = ('ce', 'role_only', 'all_axes')


def phase_commands(mode, arm=None, endpoint=None, model=None, max_wall_sec=7200, budget_hours=8.):
    if mode not in MODES:
        raise ValueError('explicit registered subject/role phase required')
    if (type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600
            or type(budget_hours) not in (int, float) or not math.isfinite(budget_hours)
            or not 0 < budget_hours <= 8):
        raise ValueError('bounded wall time and positive finite budget required')
    if ((mode in ('cost', 'train') and arm not in ARMS)
            or (mode not in ('cost', 'train') and arm is not None)
            or (mode == 'evaluate' and endpoint not in ('parent', *ARMS))
            or (mode != 'evaluate' and endpoint is not None)
            or (mode == 'probe_old' and model not in ('ce', 'contrast'))
            or (mode != 'probe_old' and model is not None)):
        raise ValueError('exactly the endpoint selector owned by this phase is required')
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/diag_p106b_subject_role.py']
    tests = py + ['-m', 'unittest', 'scripts.test_p106b_subject_role_data',
        'scripts.test_p106b_subject_role_loss', 'scripts.test_p106b_subject_role',
        'scripts.test_p106b_subject_role_entry', '-v']
    command = driver + ['--mode', mode, '--max-wall-sec', str(max_wall_sec),
                         '--budget-hours', str(budget_hours)]
    for flag, value in (('--arm', arm), ('--endpoint', endpoint), ('--model', model)):
        if value is not None:
            command += [flag, value]
    preflight = (command + ['--check-only'] if mode in ('prepare', 'preflight')
                 else driver + ['--mode', 'preflight', '--execute'])
    return [('REGRESSION', tests), ('PREFLIGHT', preflight),
            ('EXECUTE', command + ['--execute'])]


def run(mode, arm=None, endpoint=None, model=None, max_wall_sec=7200, budget_hours=8.):
    phases = phase_commands(mode, arm, endpoint, model, max_wall_sec, budget_hours)
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        try:
            return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                  timeout=max_wall_sec + 600).returncode
        except (subprocess.TimeoutExpired, OSError) as exc:
            print('[SUBJECT_ROLE_ENTRY_CHILD] ' + type(exc).__name__ + '; partial raw preserved; TOOL_ERROR9', flush=True)
            return 9
        except KeyboardInterrupt:
            print('[SUBJECT_ROLE_ENTRY_CHILD] interrupted130; partial raw preserved', flush=True)
            return 130
    receipt = pipeline(phases, launch, lambda line: print(line, flush=True),
        experiment='P106B_SUBJECT_ROLE_' + mode + '_' + str(arm or endpoint or model or 'all'))
    print('[EVIDENCE_BOUNDARY] Technical phase completion is not answer quality or model adoption.', flush=True)
    return receipt['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--endpoint', choices=('parent', *ARMS))
    parser.add_argument('--model', choices=('ce', 'contrast'))
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    parser.add_argument('--budget-hours', type=float, default=8.)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    values = dict(mode=args.mode, arm=args.arm, endpoint=args.endpoint, model=args.model,
                  max_wall_sec=args.max_wall_sec, budget_hours=args.budget_hours)
    try:
        phases = phase_commands(**values)
    except ValueError as exc:
        parser.error(str(exc))
    if args.check_only:
        print(json.dumps(dict(phases=phases, model_loaded=False, gpu_initialized=False,
                              optimizer_updates=0, source_read=False)))
        return 0
    return run(**values)


if __name__ == '__main__':
    raise SystemExit(main())
