"""Explicit budget replan; carry completed CPU1 anchor, execute remaining7 once."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

import tinylm
from scripts import diag_p014e_cpu_single_core as driver

ROOT = driver.ROOT
OLD = ROOT / 'test_result/evidence/p014e_cpu1_native_v1_20261117_s1337'
BASE = ROOT / 'test_result/evidence/p014e_cpu1_resume_v2_20261117_s1337'
PROFILE = BASE / 'profile.json'
CONTRACT = 'P014E_CPU1_CARRY_COMPLETE_ANCHOR_AND_REPLAN_V2'


def validate_resume_reports(p, first, stopped):
    driver.require_full_child(first)
    if (p['authority_directive'] != 158 or p['authority_end'] != driver.DEADLINE.isoformat()
            or p['torch_threads'] != 1 or p['workers'] != 1 or p['interop_threads'] != 1
            or first['ordinal'] != 0 or first['arm'] != 'REFERENCE'
            or first['status'] != 'CPU1_CHILD_COMPLETE' or first['exit_code'] != 0
            or first['affinity'] != p['affinity'] or not first['physical_state_unchanged']
            or not first['model_released'] or not first['worker_threads_released'] or first['CUDA_initialized']):
        raise ValueError('only exact completed original CPU1 anchor may carry')
    if (stopped['ordinal'] != 1 or stopped['status'] != 'CPU1_CHILD_HOLD' or stopped['exit_code'] != 8
            or stopped.get('numeric') or stopped.get('records') or stopped.get('answers')
            or stopped.get('error') != 'complete declared CPU1 suite does not fit measured cost'
            or not stopped['physical_state_unchanged'] or not stopped['model_released']
            or not stopped['worker_threads_released'] or stopped['CUDA_initialized']):
        raise ValueError('only a closed cost-admission HOLD, not partial measurements or numerical failure, may replan')


def bind_owned_namespace():
    # Explicit run configuration, not source editing or a skipped authority guard.
    driver.BASE = BASE
    driver.PROFILE = PROFILE


def prepare():
    driver.Budget(18000).check(admission=True)
    if BASE.exists():
        raise FileExistsError('preserve explicit resume namespace')
    if (driver.NEW_WORK_CUTOFF - datetime.now(timezone.utc)).total_seconds() < 18000 + 300:
        raise TimeoutError('whole declared parent cap plus idle does not fit current authority')
    p = driver.validate_profile(driver.read(OLD / 'profile.json'))
    batch = driver.read(OLD / 'actual/batch_report.json')
    if batch['actual_exit_code'] != 8 or batch['status'] != 'CPU1_PARENT_HOLD' or len(batch['children']) != 2:
        raise ValueError('exact closed original cost HOLD required')
    first_path = ROOT / batch['children'][0]['report']['path']
    stopped_path = ROOT / batch['children'][1]['report']['path']
    for child in batch['children']:
        if driver.sha(ROOT / child['report']['path']) != child['report']['sha256']:
            raise ValueError('original closed child report changed')
    first, stopped = driver.read(first_path), driver.read(stopped_path)
    validate_resume_reports(p, first, stopped)
    if not 1800 < stopped['conservative_seconds'] * 1.25 <= 2700:
        raise ValueError('preregistered observed cost envelope differs')
    sources = dict(p['sources'])
    for name in ('scripts/diag_p014e_cpu_single_core_resume.py', 'scripts/test_p014e_cpu_single_core_resume.py'):
        sources[name] = driver.sha(ROOT / name)
    references = dict(p['references'])
    for path in (OLD / 'profile.json', OLD / 'actual/batch_report.json', first_path, stopped_path):
        references[str(path.relative_to(ROOT))] = driver.sha(path)
    # Original reference vector packets remain their exact v1 paths.
    for work in first['numeric']:
        references[work['packet']['path']] = work['packet']['sha256']
    BASE.mkdir()
    with (BASE / 'initial_plan.md').open('xb') as stream:
        stream.write(driver.PLAN.read_bytes())
    p.update(resume_contract=CONTRACT, parent_cap_seconds=18000, child_cap_seconds=2700,
             sources=sources, references=references, initial_plan_sha256=driver.sha(BASE / 'initial_plan.md'),
             carried_anchor=dict(path=str(first_path.relative_to(ROOT)), sha256=driver.sha(first_path)),
             source_profile_sha256=driver.sha(OLD / 'profile.json'), carried_complete_children=1,
             new_children_expected=7, measured_timing_has_interruption_gap=True,
             original_partial_cost_child_excluded_from_ABBA=True,
             original_cost_HOLD_sha256=driver.sha(stopped_path))
    driver.write_new(PROFILE, p)
    print('[CPU1_RESUME_PREPARED]carry exact completed anchor0;seven new children;explicit2700s cap', flush=True)


def check():
    bind_owned_namespace()
    p = driver.check()
    if p.get('resume_contract') != CONTRACT or p['child_cap_seconds'] != 2700 or p['parent_cap_seconds'] != 18000:
        raise ValueError('exact explicit resume/budget contract required')
    return p


def actual():
    p = check()
    out = BASE / 'actual'
    out.mkdir()
    carried_path = ROOT / p['carried_anchor']['path']
    if driver.sha(carried_path) != p['carried_anchor']['sha256']:
        raise ValueError('completed CPU1 anchor changed')
    carried = driver.require_full_child(driver.read(carried_path))
    driver.write_new(out / 'anchor_model0.json', dict(profile_sha256=driver.sha(PROFILE),
        report=p['carried_anchor'], selected_before_answers=True, carried_from_original_complete_CPU1=True))
    report = dict(schema=CONTRACT, status='STARTED', profile_sha256=driver.sha(PROFILE),
        children=[dict(ordinal=0, actual_exit_code=0, status=carried['status'], report=p['carried_anchor'],
                       carried_from_original_CPU1=True)], new_model_loads_expected=7,
        timing_interruption_gap=True, excluded_original_partial_cost_child=True,
        optimizer_updates=0, checkpoint_writes=0, quality_adoption=False)
    started = time.monotonic()
    budget = driver.Budget(p['parent_cap_seconds'], stop_file=BASE / 'STOP')
    active = None
    active_ordinal = None
    code = 0

    def interrupted(_number, _frame):
        raise TimeoutError('owned explicit CPU1 resume interrupted')

    signal.signal(signal.SIGTERM, interrupted)
    try:
        for ordinal in range(1, 8):
            if budget.check() < p['child_cap_seconds']:
                raise TimeoutError('remaining declared parent budget cannot admit a full child')
            logfile = out / ('child' + str(ordinal).zfill(2) + '_stdout.txt')
            argv = [sys.executable, '-B', '-u', '-m', 'scripts.diag_p014e_cpu_single_core_resume', 'child', '--ordinal', str(ordinal)]
            with logfile.open('xb') as stream:
                active = subprocess.Popen(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                    env=dict(driver.os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                             NUMEXPR_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false'))
                active_ordinal = ordinal
                print('[CPU1_RESUME_CHILD_STARTED]' + json.dumps(dict(ordinal=ordinal, pid=active.pid, arm=p['order'][ordinal % 4])), flush=True)
                began = time.monotonic()
                while active.poll() is None:
                    budget.check()
                    if time.monotonic() - began > p['child_cap_seconds'] + 30:
                        raise TimeoutError('owned resume child exceeded wall cap')
                    time.sleep(1)
                rc = active.wait()
                active = None; active_ordinal = None
            path = driver.child_folder(ordinal, p) / 'report.json'
            value = driver.read(path) if path.exists() else None
            report['children'].append(dict(ordinal=ordinal, argv=argv, actual_exit_code=rc,
                stdout=dict(path=str(logfile.relative_to(ROOT)), sha256=driver.sha(logfile)),
                report=None if value is None else dict(path=str(path.relative_to(ROOT)), sha256=driver.sha(path)),
                status=None if value is None else value['status']))
            print('[CPU1_RESUME_CHILD_CLOSED]' + json.dumps(report['children'][-1]), flush=True)
            if rc != 0 or value is None:
                code = rc or 1
                report['status'] = 'CPU1_RESUME_HOLD' if code == 8 else 'CPU1_RESUME_ERROR'
                break
            if ordinal == 4:
                driver.require_full_child(value)
                if value['status'] != 'CPU1_CHILD_COMPLETE':
                    raise ValueError('new second-model reference failed')
                driver.write_new(out / 'anchor_model1.json', dict(profile_sha256=driver.sha(PROFILE),
                    report=dict(path=str(path.relative_to(ROOT)), sha256=driver.sha(path)), selected_before_answers=True))
        else:
            report['status'] = 'CPU1_RESUMED_ABBA_COMPLETE' if all(c['status'] == 'CPU1_CHILD_COMPLETE' for c in report['children']) else 'CPU1_RESUMED_ABBA_NUMERICAL_OR_ID_NEGATIVE'
    except TimeoutError as error:
        report.update(status='CPU1_RESUME_HOLD', error=str(error)); code = 8
        error.__traceback__ = None
    except BaseException as error:
        report.update(status='CPU1_RESUME_ERROR', error=str(error), traceback=traceback.format_exc()); code = 1
        error.__traceback__ = None
    finally:
        if active is not None and active.poll() is None:
            active.terminate()
            try:
                active.wait(timeout=60)
            except subprocess.TimeoutExpired:
                active.kill(); active.wait()
        if active is not None and active_ordinal is not None:
            path = driver.child_folder(active_ordinal, p) / 'report.json'
            report['interrupted_owned_child'] = dict(ordinal=active_ordinal, pid=active.pid, actual_exit_code=active.returncode,
                report=None if not path.exists() else dict(path=str(path.relative_to(ROOT)), sha256=driver.sha(path)))
        report.update(actual_exit_code=code, wall_seconds=time.monotonic() - started,
                      utc_closed=datetime.now(timezone.utc).isoformat(), owned_child_still_live=False)
        driver.write_new(out / 'batch_report.json', report)
    print('[CPU1_RESUME_END]' + json.dumps(dict(status=report['status'], children=len(report['children']), exit_code=code)), flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'actual', 'child'))
    parser.add_argument('--ordinal', type=int)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'check':
        check(); print('[CPU1_RESUME_CHECK]exact original anchor and current bounded seven-child plan')
    elif args.action == 'child':
        if args.ordinal not in range(1, 8):
            raise ValueError('completed ordinal0 must not restart')
        check()
        raise SystemExit(driver.child(args.ordinal))
    else:
        raise SystemExit(actual())


if __name__ == '__main__':
    main()
