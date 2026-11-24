"""New single-logical-CPU packed-table ABBA; preserve completed CPU4 evidence."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import weakref

import tinylm

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'test_result/evidence/p014e_cpu1_native_v1_20261117_s1337'
PROFILE = BASE / 'profile.json'
PARENT_PROFILE = ROOT / 'test_result/evidence/p014e_direct_packed_v1_s1337/cpu_native_v1/profile.json'
PLAN = ROOT / 'test_plan/P014E_회전삼진-민감도와-직접패킹-단계게이트.md'
DEADLINE = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)
NEW_WORK_CUTOFF = datetime(2026, 11, 17, 7, 40, tzinfo=timezone.utc)
ORDER = ('REFERENCE', 'CPU_DIRECT_TABLE', 'CPU_DIRECT_TABLE', 'REFERENCE')
SCHEMA = 'P014E_SINGLE_LOGICAL_CPU_ABBA_V1'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(data) >= 20_000_000:
        raise ValueError('result must be split below20MB')
    with Path(path).open('xb') as stream:
        stream.write(data)


def runtime_modules():
    import numpy as np
    import torch
    from tokenizers import Tokenizer
    from scripts import diag_p014e_cpu_native as prior
    return np, torch, Tokenizer, prior


def repository_module_sources(modules):
    files, generated = set(), []
    for module in modules:
        name = getattr(module, '__file__', None)
        if not isinstance(name, str) or not name.endswith('.py'):
            continue
        path = Path(name).resolve()
        if not path.is_relative_to(ROOT):
            continue
        if not Path(name).is_absolute() and not path.is_file():
            generated.append(dict(module=getattr(module, '__name__', 'unknown'), virtual_file=name))
            continue
        if not path.is_file():
            raise FileNotFoundError('missing actual repository module: ' + str(path))
        files.add(path)
    return files, generated


class Budget:
    def __init__(self, seconds, *, now=None, monotonic=None, stop_file=None):
        self.seconds = seconds
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic or time.monotonic
        self.started = self._monotonic()
        self.stop_file = stop_file
        self.last_disk = float('-inf')

    def check(self, *, admission=False):
        remaining = min(self.seconds - (self._monotonic() - self.started),
                        (NEW_WORK_CUTOFF - self._now()).total_seconds())
        if remaining <= 0 or (self.stop_file is not None and self.stop_file.exists()):
            raise TimeoutError('owned CPU budget/STOP/new-work cutoff reached')
        if admission and remaining < 60:
            raise TimeoutError('less than60sec admission/closure margin')
        if self._monotonic() - self.last_disk > 10:
            self.last_disk = self._monotonic()
            if shutil.disk_usage(ROOT).free < 5_000_000_000:
                raise RuntimeError('less than5GB free; no cleanup authorized')
            if BASE.exists() and sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()) >= 200_000_000:
                raise RuntimeError('owned200MB result cap reached')
        return remaining


def checked_relative(name):
    path = Path(name)
    if (path.is_absolute() or '..' in path.parts or not path.parts
            or path.parts[0] in {'.claude', '.codex', '.agents'}
            or path.parts[:2] == ('datasets', 'TinyDataset')):
        raise ValueError('unowned or traversing input path')
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('input escapes repository')
    return resolved


def validate_profile(p):
    if (p.get('schema') != SCHEMA or p.get('authority_directive') != 158
            or p.get('authority_end') != DEADLINE.isoformat()
            or p.get('new_work_cutoff') != NEW_WORK_CUTOFF.isoformat()
            or p.get('order') != list(ORDER) or p.get('anchor_ordinals') != [0, 4]
            or p.get('workers') != 1 or p.get('torch_threads') != 1
            or p.get('interop_threads') != 1 or len(p.get('affinity', [])) != 1
            or len(p.get('models', [])) != 2
            or p.get('linear_rtol') != .00002 or p.get('linear_atol') != .000002):
        raise ValueError('fixed CPU1 authority/condition contract differs')
    for name, digest in {**p['sources'], **p['references']}.items():
        if sha(checked_relative(name)) != digest:
            raise ValueError('frozen CPU1 input/source changed: ' + name)
    if sha(BASE / 'initial_plan.md') != p['initial_plan_sha256']:
        raise ValueError('initial CPU1 plan changed')
    return p


def check():
    p = validate_profile(read(PROFILE))
    np, torch, tokenizer, prior = runtime_modules()
    if torch.__version__ != p['torch_version']:
        raise ValueError('reuse the same installed torch version')
    if torch.cuda.is_initialized():
        raise RuntimeError('CPU check initialized CUDA')
    Budget(p['parent_cap_seconds']).check(admission=True)
    return p


def prepare():
    Budget(9000).check(admission=True)
    if BASE.exists():
        raise FileExistsError('preserve CPU1 namespace; no automatic retry')
    np, torch, tokenizer, prior = runtime_modules()
    parent = read(PARENT_PROFILE)
    for name, digest in {**parent['sources'], **parent['references']}.items():
        if sha(checked_relative(name)) != digest:
            raise ValueError('historical input/source changed before CPU1 admission: ' + name)
    closed = read(PARENT_PROFILE.parent / 'actual/batch_report.json')
    if (closed['actual_exit_code'] != 0 or closed['status'] != 'CPU_NATIVE_ABBA_COMPLETE'
            or len(closed['children']) != 8):
        raise ValueError('closed complete CPU4 evidence required, not rerun')
    for child in closed['children']:
        if child['actual_exit_code'] != 0 or sha(ROOT / child['report']['path']) != child['report']['sha256']:
            raise ValueError('historical completed child receipt changed')
    affinity = sorted(os.sched_getaffinity(0))
    if not affinity:
        raise ValueError('no visible logical CPU')
    # Pin the complete loaded repository implementation and model source tree.
    files, generated_modules = repository_module_sources(tuple(sys.modules.values()))
    files.update((ROOT / 'tinylm').rglob('*.py'))
    files.update(ROOT / n for n in ('scripts/diag_p014e_cpu_single_core.py',
                                    'scripts/test_p014e_cpu_single_core.py', 'scripts/p014e_direct_cpu.c'))
    source_pins = {str(path.relative_to(ROOT)): sha(path) for path in sorted(files)}
    references = dict(parent['references'])
    references[str(PARENT_PROFILE.relative_to(ROOT))] = sha(PARENT_PROFILE)
    references[str((PARENT_PROFILE.parent / 'actual/batch_report.json').relative_to(ROOT))] = sha(PARENT_PROFILE.parent / 'actual/batch_report.json')
    references[parent['library']['path']] = parent['library']['sha256']
    BASE.mkdir()
    with (BASE / 'initial_plan.md').open('xb') as stream:
        stream.write(PLAN.read_bytes())
    p = dict(schema=SCHEMA, authority_directive=158, authority_end=DEADLINE.isoformat(),
             new_work_cutoff=NEW_WORK_CUTOFF.isoformat(), parent_cap_seconds=9000, child_cap_seconds=1800,
             sources=source_pins, references=references, models=parent['models'], library=parent['library'],
             workers=1, torch_threads=1, interop_threads=1, affinity=[affinity[0]],
             visible_affinity_before=affinity, torch_version=torch.__version__, order=list(ORDER), anchor_ordinals=[0, 4],
             linear_rtol=.00002, linear_atol=.000002, initial_plan_sha256=sha(BASE / 'initial_plan.md'),
             primary_numerical_reference='FIRST_FRESH_CPU1_REFERENCE_WITH_IDENTICAL_AFFINITY',
             prior_CPU4_is_separate_condition=True, quality_adoption=False, optimizer_updates=0,
             checkpoint_writes=0, original_checkpoint_reads=0, owned_max_bytes=200_000_000,
             technical_payload_loads_expected=8, expected_max_forwards_per_child=404,
             idle_before_actual_seconds=300, STOP=str((BASE / 'STOP').relative_to(ROOT)))
    p['generated_module_labels_not_source_files'] = generated_modules
    write_new(PROFILE, p)
    if torch.cuda.is_initialized():
        raise RuntimeError('CPU1 preparation initialized CUDA')
    print('[CPU1_PREPARED]new CPU1 profile; original CPU4 evidence preserved', flush=True)


def child_folder(ordinal, p):
    return BASE / 'actual' / ('child' + str(ordinal).zfill(2) + '_' + p['models'][ordinal // 4]['id'] + '_' + p['order'][ordinal % 4])


def require_full_child(result):
    numeric = result.get('numeric', [])
    records = result.get('records', [])
    answers = result.get('answers', [])
    if (len(numeric) != 4 or any(len(n.get('rows', [])) != 4 for n in numeric)
            or len(records) != 4 or any(len(r.get('repeats', [])) != 3 for r in records)
            or len(answers) != 4):
        raise ValueError('partial or empty CPU1 child cannot complete')
    return result


def child(ordinal):
    if type(ordinal) is not int or not 0 <= ordinal < 8:
        raise ValueError('fixed ordinal0..7 required')
    p = check()
    np, torch, Tokenizer, prior = runtime_modules()
    out = child_folder(ordinal, p)
    out.mkdir()
    started = time.monotonic()
    budget = Budget(p['child_cap_seconds'], stop_file=BASE / 'STOP')
    budget.check(admission=True)
    spec = p['models'][ordinal // 4]
    arm = p['order'][ordinal % 4]
    result = dict(schema=SCHEMA, status='STARTED', ordinal=ordinal, arm=arm, model=spec['id'],
                  profile_sha256=sha(PROFILE), numeric=[], records=[], answers=[], contexts=[],
                  affinity=p['affinity'], original_checkpoint_reads=0, optimizer_updates=0,
                  checkpoint_writes=0, quality_adoption=False, load_phases={}, host_load_before=os.getloadavg())
    model = payload = operator = runtime = tok = model_cfg = None
    failure = None
    exit_code = 0

    def interrupted(_number, _frame):
        raise TimeoutError('owned CPU1 parent requested closure')

    signal.signal(signal.SIGTERM, interrupted)
    try:
        os.sched_setaffinity(0, set(p['affinity']))
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        for task in Path('/proc/self/task').iterdir():
            os.sched_setaffinity(int(task.name), set(p['affinity']))
        if sorted(os.sched_getaffinity(0)) != p['affinity']:
            raise RuntimeError('single logical CPU affinity did not apply')
        anchor = None
        if ordinal not in p['anchor_ordinals']:
            receipt = read(BASE / 'actual' / ('anchor_model' + str(ordinal // 4) + '.json'))
            target = ROOT / receipt['report']['path']
            if receipt['profile_sha256'] != sha(PROFILE) or sha(target) != receipt['report']['sha256']:
                raise ValueError('declared CPU1 anchor receipt changed')
            anchor = require_full_child(read(target))
            if anchor['status'] != 'CPU1_CHILD_COMPLETE' or anchor['ordinal'] != p['anchor_ordinals'][ordinal // 4]:
                raise ValueError('only completed predeclared CPU1 reference may anchor')
        phase = time.perf_counter()
        runtime = prior.cpu.direct.KernelRuntime(ROOT / p['library']['path'], p['library']['sha256'], workers=1)
        if runtime.pool is not None:
            raise RuntimeError('single-worker runtime unexpectedly started a pool')
        payload = prior.owner.load(ROOT / spec['payload'])
        result['load_phases']['payload_read_seconds'] = time.perf_counter() - phase
        phase = time.perf_counter()
        model = prior.owner.direct.reference.load_payload(payload, device='cpu', tile_rows=4096)
        model_ref = weakref.ref(model)
        model_cfg = model.cfg
        tok = Tokenizer.from_file(str(ROOT / spec['tokenizer']['path']))
        result['load_phases']['model_tokenizer_build_seconds'] = time.perf_counter() - phase
        if model_cfg.vocab_size != spec['expected_vocab'] or model_cfg.max_seq_len != 1024:
            raise ValueError('same native vocabulary/context required')
        before = prior.identity.state_fingerprint(model)
        result.update(initial_state_sha256=before, storage=prior.common.model_storage(model),
                      torch_threads=torch.get_num_threads(), interop_threads=torch.get_num_interop_threads(),
                      worker_pool_created=False, extra_weight_storage_bytes=0)
        operator = prior.cpu.direct.PackedCPUOperator(payload['embedding'], runtime)
        operator.packed_codes = model.packed_embedding.packed_codes
        operator.group_scales = model.packed_embedding.group_scales
        payload = None
        with torch.no_grad():
            context = nullcontext(None) if arm == 'REFERENCE' else prior.adapter.direct_head(model, operator)
            with context as proof:
                probes = [prior.cost_probe(model, spec['workloads'][i], budget) for i in (0, 2)]
                forecast = 3 * (24 * max(v['prefill_seconds'] for v in probes)
                                + 376 * max(v['decode_seconds'] for v in probes)) + 60
                result.update(cost_probes=probes, conservative_seconds=forecast)
                if forecast > budget.check():
                    raise TimeoutError('complete declared CPU1 suite does not fit measured cost')
                for work in spec['workloads']:
                    result['numeric'].append(prior.numeric(model, work, out, anchor, p, budget))
                    warm = prior.make_generation(model, model_cfg, tok, spec, work['ids'], 16, False, False, budget)
                    repeats = [prior.make_generation(model, model_cfg, tok, spec, work['ids'], 16, False, False, budget) for _ in range(3)]
                    expected = None if anchor is None else next(r for r in anchor['records'] if r['workload'] == work['id'])
                    wanted = warm if expected is None else expected['warmup']
                    same = all(g['generated_ids'] == wanted['generated_ids'] and g['metadata'] == wanted['metadata'] for g in [warm, *repeats])
                    result['records'].append(dict(workload=work['id'], warmup=warm, repeats=repeats,
                        median_seconds=float(np.median([r['seconds'] for r in repeats])), all_anchor_IDs_and_stops_equal=same))
                    print('[CPU1_WORKLOAD]' + str(ordinal) + '/' + work['id'], flush=True)
                for item in spec['natural_questions']:
                    generation = prior.make_generation(model, model_cfg, tok, spec, item['ids'], 32, True, item['case']['mode'] == 'chatml', budget)
                    expected = None if anchor is None else next(r for r in anchor['answers'] if r['case'] == item['case'])
                    wanted = generation if expected is None else expected['generation']
                    result['answers'].append(dict(case=item['case'], generation=generation,
                        anchor_IDs_and_stops_equal=generation['generated_ids'] == wanted['generated_ids'] and generation['metadata'] == wanted['metadata']))
            if proof is not None:
                result['contexts'].append(proof)
        require_full_child(result)
        failures = sum(not row['primary_allclose'] or not row['primary_argmax_equal'] for item in result['numeric'] for row in item['rows'])
        changed = sum(not row['all_anchor_IDs_and_stops_equal'] for row in result['records']) + sum(not row['anchor_IDs_and_stops_equal'] for row in result['answers'])
        result.update(numerical_gate_failures=failures, changed_generation_records=changed,
                      status='CPU1_CHILD_COMPLETE' if failures == 0 and changed == 0 else 'CPU1_CHILD_NUMERICAL_OR_ID_NEGATIVE')
    except TimeoutError as error:
        result.update(status='CPU1_CHILD_HOLD', error=str(error)); exit_code = 8
        error.__traceback__ = None
    except BaseException as error:
        failure = str(error)
        result.update(status='CPU1_CHILD_ERROR', error=failure, traceback=traceback.format_exc()); exit_code = 1
        error.__traceback__ = None
    finally:
        cleanup_started = time.monotonic()
        if model is not None and 'initial_state_sha256' in result:
            result['physical_state_unchanged'] = prior.identity.state_fingerprint(model) == result['initial_state_sha256']
            if not result['physical_state_unchanged']:
                failure = failure or 'original CPU1 physical state changed'; exit_code = 1
        model = payload = operator = tok = model_cfg = None
        if runtime is not None:
            runtime.close()
        runtime = None
        gc.collect()
        result.update(model_released=True if 'model_ref' not in locals() else model_ref() is None,
                      worker_threads_released=not any(t.name.startswith('p014e-cpu') for t in threading.enumerate()),
                      CUDA_initialized=torch.cuda.is_initialized(), host_load_after=os.getloadavg(),
                      thread_affinities_at_close={task.name: sorted(os.sched_getaffinity(int(task.name)))
                          for task in Path('/proc/self/task').iterdir()},
                      RSS_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      cleanup_seconds=time.monotonic() - cleanup_started, wall_seconds=time.monotonic() - started,
                      exit_code=exit_code)
        if not result['model_released'] or not result['worker_threads_released'] or result['CUDA_initialized']:
            failure = failure or 'CPU1 resource closure failed'; result['exit_code'] = exit_code = 1
        if any(affinity != p['affinity'] for affinity in result['thread_affinities_at_close'].values()):
            failure = failure or 'CPU1 thread affinity escaped'; result['exit_code'] = exit_code = 1
        write_new(out / 'report.json', result)
    print('[CPU1_CHILD_END]' + json.dumps(dict(ordinal=ordinal, status=result['status'], exit_code=exit_code, error=failure)), flush=True)
    return exit_code


def actual():
    p = check()
    out = BASE / 'actual'
    out.mkdir()
    started = time.monotonic()
    budget = Budget(p['parent_cap_seconds'], stop_file=BASE / 'STOP')
    report = dict(schema=SCHEMA, status='STARTED', profile_sha256=sha(PROFILE), children=[],
                  parent_model_loads=0, optimizer_updates=0, checkpoint_writes=0, quality_adoption=False)
    active = None
    active_ordinal = None
    exit_code = 0

    def interrupted(_number, _frame):
        raise TimeoutError('owned CPU1 parent interrupted')

    signal.signal(signal.SIGTERM, interrupted)
    try:
        for ordinal in range(8):
            if budget.check() < p['child_cap_seconds']:
                raise TimeoutError('insufficient budget for a complete declared child')
            logfile = out / ('child' + str(ordinal).zfill(2) + '_stdout.txt')
            argv = [sys.executable, '-B', '-u', '-m', 'scripts.diag_p014e_cpu_single_core', 'child', '--ordinal', str(ordinal)]
            with logfile.open('xb') as stream:
                active = subprocess.Popen(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                    env=dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                             NUMEXPR_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false'))
                active_ordinal = ordinal
                print('[CPU1_CHILD_STARTED]' + json.dumps(dict(ordinal=ordinal, pid=active.pid, arm=p['order'][ordinal % 4])), flush=True)
                began = time.monotonic()
                while active.poll() is None:
                    budget.check()
                    if time.monotonic() - began > p['child_cap_seconds'] + 30:
                        raise TimeoutError('owned child exceeded declared wall cap')
                    time.sleep(1)
                rc = active.wait()
                active = None
                active_ordinal = None
            path = child_folder(ordinal, p) / 'report.json'
            value = read(path) if path.exists() else None
            report['children'].append(dict(ordinal=ordinal, argv=argv, actual_exit_code=rc,
                stdout=dict(path=str(logfile.relative_to(ROOT)), sha256=sha(logfile)),
                report=None if value is None else dict(path=str(path.relative_to(ROOT)), sha256=sha(path)),
                status=None if value is None else value['status']))
            print('[CPU1_CHILD_CLOSED]' + json.dumps(report['children'][-1]), flush=True)
            if rc != 0 or value is None:
                exit_code = rc or 1
                report['status'] = 'CPU1_PARENT_HOLD' if exit_code == 8 else 'CPU1_PARENT_ERROR'
                break
            if ordinal in p['anchor_ordinals']:
                require_full_child(value)
                if value['status'] != 'CPU1_CHILD_COMPLETE':
                    raise RuntimeError('declared CPU1 reference failed; independent model not restarted')
                write_new(out / ('anchor_model' + str(ordinal // 4) + '.json'),
                          dict(profile_sha256=sha(PROFILE), report=dict(path=str(path.relative_to(ROOT)), sha256=sha(path)), selected_before_answers=True))
        else:
            report['status'] = 'CPU1_ABBA_COMPLETE' if all(c['status'] == 'CPU1_CHILD_COMPLETE' for c in report['children']) else 'CPU1_ABBA_NUMERICAL_OR_ID_NEGATIVE'
    except TimeoutError as error:
        report.update(status='CPU1_PARENT_HOLD', error=str(error)); exit_code = 8
        error.__traceback__ = None
    except BaseException as error:
        report.update(status='CPU1_PARENT_ERROR', error=str(error), traceback=traceback.format_exc()); exit_code = 1
        error.__traceback__ = None
    finally:
        if active is not None and active.poll() is None:
            active.terminate()
            try:
                active.wait(timeout=60)
            except subprocess.TimeoutExpired:
                active.kill(); active.wait()
        if active is not None and active_ordinal is not None:
            path = child_folder(active_ordinal, p) / 'report.json'
            logfile = out / ('child' + str(active_ordinal).zfill(2) + '_stdout.txt')
            report['interrupted_owned_child'] = dict(ordinal=active_ordinal, pid=active.pid,
                actual_exit_code=active.returncode, stdout=dict(path=str(logfile.relative_to(ROOT)), sha256=sha(logfile)),
                report=None if not path.exists() else dict(path=str(path.relative_to(ROOT)), sha256=sha(path)))
        report.update(wall_seconds=time.monotonic() - started, actual_exit_code=exit_code,
                      utc_closed=datetime.now(timezone.utc).isoformat(), owned_child_still_live=False)
        write_new(out / 'batch_report.json', report)
    print('[CPU1_PARENT_END]' + json.dumps(dict(status=report['status'], children=len(report['children']), exit_code=exit_code)), flush=True)
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'actual', 'child'))
    parser.add_argument('--ordinal', type=int)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'check':
        check(); print('[CPU1_CHECK]current authority and exact frozen inputs')
    elif args.action == 'child':
        raise SystemExit(child(args.ordinal))
    else:
        raise SystemExit(actual())


if __name__ == '__main__':
    main()
