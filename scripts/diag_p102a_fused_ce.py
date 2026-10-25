#!/usr/bin/env python3
"""Prepare an opt-in official fused-CE numerical gate; never run on import.

Check-only reads Python source and distribution/provenance metadata using only
the standard library. Execute requires a fresh tag, two reviewed receipts and
an explicit aware deadline/wall reservation. Tiny GPU canaries precede any
parent/data load. The actual gate retains the original 16x8 update, all157 raw
and clipped gradients and all85 original Muon matrices. No checkpoint is saved.

This instrumented first-update gate cannot establish training speedup, quality,
production adoption or real MTP GPU correctness. Actual process exit must be
collected by the caller under an independent OS timeout.
"""
from __future__ import annotations

import argparse
import base64
import copy
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import weakref
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p101a_padding_gpu as old
from scripts import diag_p102a_head_muon_trace as trace

SCHEMA = 'P102A_OFFICIAL_FUSED_CE_GPU_V1'
TAG_PREFIX = 'p102a_fused_ce_v1_s1337_'
SCRIPT = 'scripts/diag_p102a_fused_ce.py'
TEST = 'scripts/test_p102a_fused_ce_driver.py'
PREPARED_PACKAGES = 'handoff/audit/WIP_20261024_ACCEL_PACKAGES_CPU.json'
CCE_COMMIT = '3de376c106a1916bc5e1b619f9c77c87a461ee1c'
EXPECTED_PACKAGES = {'liger-kernel': '0.8.5', 'cut-cross-entropy': '25.9.3'}
BACKENDS = ('reference', 'liger', 'cce_exact')
PRECISIONS = ('fp32_math', 'bf16_eager')
MAX_BYTES = old.MAX_BYTES
ALL_COUNT, MATRIX_COUNT = 157, 85
FULL_FIELDS = ('raw', 'clipped', 'parameters')
MATRIX_FIELDS = ('ns_input', 'ns_output', 'updated', 'buffers')


def wheel_metadata(dist, wheel, root=ROOT):
    """Use pinned archive and dist-info payload manifests when direct_url is absent."""
    path = old.safe_path(wheel['path'], root)
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith('.dist-info/RECORD')]
        if len(names) != 1:
            raise ValueError('one wheel RECORD required')
        wheel_rows = list(csv.reader(io.StringIO(archive.read(names[0]).decode('utf-8'))))
    installed_text = dist.read_text('RECORD')
    installed = {row[0]: row[1:] for row in csv.reader(io.StringIO(installed_text or ''))}
    payload = {row[0]: row[1:] for row in wheel_rows if len(row) == 3 and row[1]}
    mismatches = [name for name, fields in payload.items() if installed.get(name) != fields]
    archive_sha = old.digest(path)
    return dict(archive_sha256=archive_sha, archive_matches=archive_sha == wheel['sha256'],
        payload_record_count=len(payload), payload_record_sha256=old.identity(payload),
        payload_records_match=bool(payload) and not mismatches,
        payload_record_mismatches=mismatches)


def sources(root=ROOT):
    """Source only: helper imports never load the model, corpus or torch."""
    result = trace.sources(root)
    for name in (SCRIPT, TEST, 'tinylm/train/fused_ce.py', 'scripts/test_p102a_fused_ce.py'):
        path = old.safe_path(name, root)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('source exceeds the per-file bound: ' + name)
        result[name] = old.digest(path)
    return dict(sorted(result.items()))


def dependency_metadata(root=ROOT):
    """Read dist-info/provenance, without importing torch or external kernels."""
    prepared_path = old.safe_path(PREPARED_PACKAGES, root)
    prepared = json.loads(prepared_path.read_text(encoding='utf-8'))
    result = dict(prepared_receipt=PREPARED_PACKAGES,
        prepared_receipt_sha256=old.digest(prepared_path),
        cce_source_commit=prepared.get('source_checks', {}).get('cce', {}).get('source_commit'),
        python_executable=sys.executable, python_version=sys.version, packages={})
    expected = dict(EXPECTED_PACKAGES)
    for name in ('torch', 'triton'):
        expected[name] = prepared.get('installed', {}).get(name, {}).get('version')
    wheels = {Path(row['path']).name: row for row in prepared.get('wheels', [])}
    for name, version in expected.items():
        try:
            dist = importlib.metadata.distribution(name)
            direct_text = dist.read_text('direct_url.json')
            direct = json.loads(direct_text) if direct_text else None
            record = dist.read_text('RECORD')
            actual_wheel_sha = None
            if direct:
                actual_wheel_sha = direct.get('archive_info', {}).get('hashes', {}).get('sha256')
            wanted_wheel = next((row for filename, row in wheels.items()
                if filename.startswith(name.replace('-', '_') + '-')), None)
            result['packages'][name] = dict(expected_version=version, installed_version=dist.version,
                version_matches=version is not None and dist.version == version,
                location=str(dist.locate_file('')), direct_url=direct,
                record_sha256=hashlib.sha256(record.encode('utf-8')).hexdigest().upper() if record else None,
                prepared_wheel_sha256=wanted_wheel['sha256'] if wanted_wheel else None,
                installed_wheel_sha256=actual_wheel_sha.upper() if actual_wheel_sha else None,
                wheel_metadata=wheel_metadata(dist, wanted_wheel, root) if wanted_wheel else None,
                prepared_python_source_files=(prepared.get('source_checks', {}).get(
                    'liger' if name == 'liger-kernel' else 'cce', {}).get('files')) if name in EXPECTED_PACKAGES else None)
        except importlib.metadata.PackageNotFoundError:
            result['packages'][name] = dict(expected_version=version, installed_version=None,
                version_matches=False, wheel_metadata=None, location=None)
    result['ready'] = (result['cce_source_commit'] == CCE_COMMIT
        and all(row['version_matches'] for row in result['packages'].values())
        and all(result['packages'][name]['wheel_metadata'] is not None
            and result['packages'][name]['wheel_metadata']['archive_matches']
            and result['packages'][name]['wheel_metadata']['payload_records_match'] for name in EXPECTED_PACKAGES))
    result['scope'] = 'DISTRIBUTION_AND_PREPARED_SOURCE_METADATA_ONLY_NOT_KERNEL_COMPATIBILITY'
    return result


def verify_installed_sources(metadata):
    """Before CUDA admission, hash installed Python sources against pinned RECORD."""
    result = {}
    for name, namespace in (('liger-kernel', 'liger_kernel'), ('cut-cross-entropy', 'cut_cross_entropy')):
        dist = importlib.metadata.distribution(name)
        files = [item for item in dist.files or () if str(item).startswith(namespace + '/') and str(item).endswith('.py')]
        if len(files) != metadata['packages'][name]['prepared_python_source_files']:
            raise ValueError('prepared package source count changed: ' + name)
        hashes = {}
        for item in files:
            if item.hash is None or item.hash.mode != 'sha256':
                raise ValueError('hashed package Python source required: ' + str(item))
            digest = old.digest(Path(dist.locate_file(item)))
            actual = base64.urlsafe_b64encode(bytes.fromhex(digest)).decode('ascii').rstrip('=')
            if actual != item.hash.value:
                raise ValueError('installed package Python source differs from pinned RECORD: ' + str(item))
            hashes[str(item)] = digest
        result[name] = dict(python_files=len(files), source_sha256=old.identity(hashes), unchanged=True)
    return result


def validate_execution(args, now=None):
    if not getattr(args, 'execute', False) or getattr(args, 'check_only', False):
        raise ValueError('explicit --execute alone required')
    now = old.utc_now() if now is None else now
    deadline = old.aware(args.deadline)
    if type(args.max_wall_sec) is not int or not 60 <= args.max_wall_sec <= 1200:
        raise ValueError('explicit wall reservation must be 60..1200 seconds')
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('aware current time required')
    if not now < deadline or (deadline - now).total_seconds() < args.max_wall_sec:
        raise ValueError('full wall reservation must fit inside the future deadline')
    if not isinstance(args.tag, str) or re.fullmatch(re.escape(TAG_PREFIX) + r'[a-z0-9][a-z0-9_]{0,63}', args.tag) is None:
        raise ValueError('fresh explicit tag must begin ' + TAG_PREFIX + ' and contain lowercase letters/digits/underscores')
    return deadline


class Guard:
    """Independent clock bound; never reads or mutates historical HARD_STOP."""
    def __init__(self, deadline, seconds):
        if (deadline.tzinfo is None or deadline.utcoffset() is None
                or type(seconds) is not int or not 60 <= seconds <= 1200):
            raise ValueError('aware deadline and explicit bounded wall reservation required')
        self.deadline = deadline.astimezone(timezone.utc)
        self.seconds, self.started = seconds, time.perf_counter()

    def check(self, stage):
        if old.utc_now() >= self.deadline or time.perf_counter() - self.started >= self.seconds:
            raise TimeoutError('fused CE deadline/wall reservation reached at ' + stage)


@contextmanager
def total_budget(guard):
    """One alarm for execute preparation, model work and terminal IO together."""
    guard.check('before whole-execute wall alarm')
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise ValueError('refusing to replace another active process alarm')
    remaining = min(guard.seconds - (time.perf_counter() - guard.started),
        (guard.deadline - old.utc_now()).total_seconds())
    if remaining <= 0:
        raise TimeoutError('execute reservation expired before alarm setup')
    previous = signal.getsignal(signal.SIGALRM)
    def alarm(*_args):
        raise TimeoutError('whole-execute wall/deadline alarm reached; partial evidence retained')
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, remaining)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def error_record(error, stage):
    result = dict(type=type(error).__name__, message=str(error), stage=stage)
    if getattr(error, 'tinylm_cleanup_errors', None):
        result['cleanup_errors'] = error.tinylm_cleanup_errors
    return result


def output_path(tag, root=ROOT):
    if not isinstance(tag, str) or re.fullmatch(re.escape(TAG_PREFIX) + r'[a-z0-9][a-z0-9_]{0,63}', tag) is None:
        raise ValueError('registered fresh tag required')
    target = old.safe_path('test_result/evidence/' + tag, root)
    if target.exists() or target.is_symlink():
        raise FileExistsError('existing evidence namespace preserved: ' + str(target))
    return target


class HeadCore:
    """Use the shared MTP mask/chunk/denominator seam for every backend."""
    def __init__(self, backend):
        if backend not in BACKENDS:
            raise ValueError('explicit registered backend required')
        from tinylm.train import mtp_sft
        self.backend, self.core = backend, mtp_sft
        self.pad_records, self.normalized_loss = mtp_sft.pad_records, mtp_sft.normalized_loss

    def components(self, model, hidden, y, segments, *, horizons):
        if horizons:
            raise ValueError('main-only GPU gate; actual MTP GPU correctness is NOT_RUN')
        return self.core.components(model, hidden, y, segments, horizons=(), chunk=64,
            checkpoint_heads=True, ce_backend=self.backend)


def fresh_optimizers(engine, model):
    opts = engine.optimizers(model)
    for group in opts[0].param_groups:
        group['lr'] = 5e-5
    for group in opts[1].param_groups:
        group['lr'] = 2e-4
    return opts


def memory_plan(model, muon):
    """Bound two captures; candidate arms are released between comparisons."""
    matrices, others = muon.split_params(model)
    state_bytes = trace.tensor_bytes(model.state_dict())
    all_bytes = sum(p.numel() * p.element_size() for p in model.parameters() if p.requires_grad)
    matrix_bytes = sum(p.numel() * p.element_size() for p in matrices)
    other_bytes = all_bytes - matrix_bytes
    # Per arm: raw+clipped+all updated; NSin/out+Muon buffer; Adam moments+steps.
    per_arm = 3 * all_bytes + 3 * matrix_bytes + 2 * other_bytes + 8 * len(others)
    estimate = state_bytes + 2 * per_arm + trace.CPU_SCRATCH_RESERVE
    if (len(matrices) != MATRIX_COUNT or len(list(model.named_parameters())) != ALL_COUNT
            or estimate > trace.CPU_CAPTURE_LIMIT):
        raise ValueError('complete157/85 CPU capture and scratch must fit the unchanged 8GiB budget')
    available = None
    meminfo = Path('/proc/meminfo')
    if meminfo.is_file():
        for line in meminfo.read_text(encoding='ascii').splitlines():
            if line.startswith('MemAvailable:'):
                available = int(line.split()[1]) * 1024
                break
    if available is not None and available < estimate + trace.CPU_SYSTEM_RESERVE:
        raise MemoryError('insufficient CPU RAM for full captures and unchanged system reserve')
    return dict(initial_bytes=state_bytes, estimated_per_arm_bytes=per_arm,
        estimated_capture_and_scratch_bytes=estimate, capture_limit_bytes=trace.CPU_CAPTURE_LIMIT,
        scratch_reserve_bytes=trace.CPU_SCRATCH_RESERVE,
        system_reserve_bytes=trace.CPU_SYSTEM_RESERVE, available_bytes_at_preflight=available,
        policy='TWO_ARMS_MAX_CPU_RAM_ONLY_NO_TENSOR_FILES_NO_GRADIENT_DROPPING')


def capture_bytes(initial, *captures):
    values = {id(value): value for value in initial.values()}
    for capture in captures:
        for key in (*FULL_FIELDS, *MATRIX_FIELDS, 'optimizer'):
            values.update({id(value): value for value in capture[key].values()})
    return trace.tensor_bytes(values)


def validate_capture(capture):
    update = capture['update']
    if (update['all_parameter_count'] != ALL_COUNT or update['non_none_gradient_count'] != ALL_COUNT
            or update['none_gradient_names'] or any(len(capture[key]) != ALL_COUNT for key in FULL_FIELDS)
            or any(len(capture[key]) != MATRIX_COUNT for key in (*MATRIX_FIELDS, 'options'))
            or set(capture['raw']) != set(capture['clipped'])
            or set(capture['raw']) != set(capture['parameters'])
            or any(set(capture[key]) != set(capture['options']) for key in MATRIX_FIELDS)
            or any(value is None for key in (*FULL_FIELDS, *MATRIX_FIELDS, 'optimizer')
                   for value in capture[key].values())):
        raise ValueError('complete actual157 gradients/parameters and85 Muon captures required')
    matrices = set(capture['options'])
    others = set(capture['raw']) - matrices
    expected_state = {'muon:' + name + ':buf' for name in matrices}
    expected_state.update('adamw:' + name + ':' + slot
        for name in others for slot in ('step', 'exp_avg', 'exp_avg_sq'))
    if set(capture['optimizer']) != expected_state:
        raise ValueError('complete actual Adam/Muon state required')


def run_arm(torch, engine, muon, cls, cfg, initial, initial_sha, pad, backend,
            precision, groups, plan, guard, journal, index):
    model = opts = proxies = capture = observer = parameters = None
    primary = None
    try:
        guard.check('before fresh parent model')
        old.gpu_admission(torch)
        guard.check('after GPU admission query')
        torch.manual_seed(1337)
        model = cls(copy.deepcopy(cfg))
        model.load_state_dict(initial, strict=True)
        model.set_anneal(1.)
        if engine.state_fingerprint(model) != initial_sha:
            raise ValueError('fresh parent initialization differs')
        model._padding_pad_id = pad
        model.train()
        guard.check('immediately before CUDA parent admission')
        model = model.cuda()
        opts = fresh_optimizers(engine, model)
        parameters = dict(model.named_parameters())
        names = {id(p): name for name, p in parameters.items()}
        ids = [id(p) for opt in opts for group in opt.param_groups for p in group['params']]
        if (len(ids) != len(set(ids)) or set(ids) != {id(p) for p in parameters.values() if p.requires_grad}
                or any(opt.state for opt in opts)):
            raise ValueError('fresh original optimizer coverage/state differs')
        options = trace.matrix_options(opts[1], names)
        capture = trace.PostClipCapture(parameters)
        observer = trace.NSObserver(torch, muon._newton_schulz, tuple(options), guard=guard)
        proxies = (trace.OptimizerProxy(opts[0], capture), trace.OptimizerProxy(opts[1], capture,
            step=trace.private_muon_step(torch, opts[1], observer)))
        torch.manual_seed(1337)
        rng_before = old.rng_identity(torch)
        update, raw = old.one_update(torch, HeadCore(backend), model, proxies, groups, plan,
            'fixed1024', precision, guard, journal, index, 0, 'fused_ce_correctness', capture=True)
        observer.finish()
        if capture.values is None:
            raise ValueError('postclip gradients not captured before the original step')
        updated = old.cpu_copy(parameters)
        optimizer = old.optimizer_snapshot(torch, model, opts)
        buffers = {name: optimizer['muon:' + name + ':buf'] for name in options}
        equal_buffers = {name: torch.equal(buffers[name], capture.values[name]) for name in options}
        if not all(equal_buffers.values()):
            raise ValueError('actual fresh Muon buffer differs from actual clipped gradient')
        answer = dict(raw=raw, clipped=capture.values, ns_input=observer.inputs,
            ns_output=observer.outputs, parameters=updated, optimizer=optimizer,
            updated={name: updated[name] for name in options}, buffers=buffers, options=options,
            ns_metadata=observer.metadata, fresh_buffer_equal_values=equal_buffers,
            update=dict(update, ce_backend=backend), initial_rng=rng_before,
            final_rng=old.rng_identity(torch), weak_model=weakref.ref(model),
            weak_parameters=[weakref.ref(p) for p in parameters.values()])
        validate_capture(answer)
        return answer
    except (Exception, KeyboardInterrupt) as error:
        primary = error
        raise
    finally:
        try:
            if model is not None:
                model.clear_quant()
        except (Exception, KeyboardInterrupt) as error:
            record = error_record(error, 'run_arm model.clear_quant')
            owner = primary if primary is not None else error
            owner.tinylm_cleanup_errors = [*getattr(owner, 'tinylm_cleanup_errors', []), record]
            if primary is None:
                raise
        finally:
            model = opts = proxies = capture = observer = parameters = None


def released_capture(torch, *args):
    capture = run_arm(torch, *args)
    if (capture.pop('weak_model')() is not None
            or any(ref() is not None for ref in capture.pop('weak_parameters'))):
        raise ValueError('prior model/parameters still referenced; no next admission')
    trace.release_cuda(torch)
    return capture


def kernel_canary_arm(torch, projected_cpu, table_cpu, labels_cpu, backend, precision, guard):
    """Low-level official kernel loss/dX/dW control, before any parent load."""
    from tinylm.train import fused_ce
    guard.check('before official kernel canary')
    projected = table = labels = loss = None
    try:
        projected = projected_cpu.cuda().requires_grad_(True)
        table = table_cpu.cuda().requires_grad_(True)
        labels = labels_cpu.cuda()
        with torch.autocast('cuda', dtype=torch.bfloat16, enabled=precision == 'bf16_eager'):
            loss = fused_ce.linear_ce(projected, table, labels, backend=backend, reduction='sum')
        if not bool(torch.isfinite(loss)):
            raise ValueError('nonfinite official kernel canary loss')
        loss.backward()
        if (projected.grad is None or table.grad is None
                or not bool(torch.isfinite(projected.grad).all()) or not bool(torch.isfinite(table.grad).all())):
            raise ValueError('missing/nonfinite official kernel canary gradients')
        answer = dict(loss=float(loss.detach()), gradients=old.cpu_copy(
            {'projected': projected.grad, 'shared_table': table.grad}))
        guard.check('after official kernel canary')
        return answer
    finally:
        projected = table = labels = loss = None


class NumericalCanaryNegative(ValueError):
    """All kernels returned finite values; unchanged tolerances rejected them."""


def run_canaries(torch, tolerances, guard, journal, report):
    generator = torch.Generator(device='cpu').manual_seed(1337)
    table = torch.randn(32768, 256, generator=generator, dtype=torch.float32) * .01
    features = torch.randn(8, 256, generator=generator, dtype=torch.float32) * .1
    labels = torch.tensor([0, 1, -100, 32767, 9, 100, 200, 300], dtype=torch.long)
    report.update(scope='SYNTHETIC_CUDA_OFFICIAL_LOSS_AND_PROJECTED_SHARED_TABLE_GRADIENTS_ONLY',
        shape=dict(rows=8, projection=256, vocabulary=32768), precisions={})
    for precision in PRECISIONS:
        guard.check('before canary precision')
        rows = report['precisions'][precision] = {}
        projected = features if precision == 'fp32_math' else features.to(dtype=torch.bfloat16)
        reference = None
        for backend in BACKENDS:
            guard.check('before independent backend canary')
            try:
                value = kernel_canary_arm(torch, projected, table, labels, backend, precision, guard)
                if backend == 'reference':
                    reference = value
                    rows[backend] = dict(status='COMPLETE', loss=value['loss'], close=True)
                elif reference is None:
                    rows[backend] = dict(status='NO_REFERENCE_ERROR', close=False)
                else:
                    comparisons = dict(loss=old.scalar_difference(reference['loss'], value['loss'],
                        tolerances['loss_and_norm']), gradients=trace.comparison(torch,
                        reference['gradients'], value['gradients'], tolerances['gradients_and_update']))
                    rows[backend] = dict(status='COMPLETE', comparisons=comparisons,
                        close=all(row['close'] for row in comparisons.values()))
                del value
            except (TimeoutError, KeyboardInterrupt):
                raise
            except Exception as error:
                rows[backend] = dict(status='ERROR', close=False,
                    error_type=type(error).__name__, error=str(error))
            finally:
                trace.release_cuda(torch)
            journal.append(dict(event='official_kernel_canary', precision=precision,
                backend=backend, **rows[backend], at=old.utc_now().isoformat()))
        reference = None
    report['complete'] = (set(report['precisions']) == set(PRECISIONS)
        and all(set(rows) == set(BACKENDS) and all(row['status'] == 'COMPLETE' for row in rows.values())
                for rows in report['precisions'].values()))
    report['close'] = report['complete'] and all(row['close']
        for rows in report['precisions'].values() for row in rows.values())
    if report['complete'] and not report['close']:
        report['status'] = 'VALID_NUMERICAL_NEGATIVE_PARENT_DATA_GATE_NOT_RUN'
        raise NumericalCanaryNegative('complete official kernel canary is a strict numerical negative; parent/data NOT_RUN')
    if not report['complete']:
        report['status'] = 'ERROR_INCOMPLETE_PARENT_DATA_GATE_NOT_RUN'
        raise ValueError('mandatory official kernel canary failed; parent/data gate remains NOT_RUN')
    report['status'] = 'NUMERICAL_PASS_ONLY_PARENT_GATE_PENDING'


def compare_pair(torch, reference, candidate, tolerances):
    validate_capture(reference)
    validate_capture(candidate)
    if reference['initial_rng'] != candidate['initial_rng'] or reference['final_rng'] != candidate['final_rng']:
        raise ValueError('paired initial/final RNG differs')
    rows = {key: trace.comparison(torch, reference[key], candidate[key],
        tolerances['gradients_and_update']) for key in (*FULL_FIELDS, *MATRIX_FIELDS, 'optimizer')}
    for key in ('loss', 'preclip_norm'):
        rows[key] = old.scalar_difference(reference['update'][key], candidate['update'][key],
            tolerances['loss_and_norm'])
    return dict(comparisons=rows, close=all(row['close'] for row in rows.values()),
        initial_rng=reference['initial_rng'], final_rng=reference['final_rng'],
        tied_scope='ALL157_INCLUDING_SUMMED_INPUT_OUTPUT_EMB_AND_PROJECTION_BEFORE_GLOBAL_CLIP')


def replay_pair(torch, muon, initial, reference, candidate, tolerance, guard, journal, report, *, device='cuda'):
    """Same actual gradient twice and both actual steps; original NS unchanged."""
    names = tuple(reference['options'])
    if len(names) != MATRIX_COUNT or set(names) != set(candidate['options']):
        raise ValueError('same complete85 original Muon matrices required')
    for capture in (reference, candidate):
        if (not set(names) <= set(initial) or not set(names) <= set(capture['clipped'])
                or any(set(capture[key]) != set(names) for key in MATRIX_FIELDS)):
            raise ValueError('missing actual matrix replay captures')
    report.update(matrices={}, matrix_count=0, same_gradient_controls_exact=False,
        actual_updates_reproduced_exactly=False, complete=False,
        clipping='ACTUAL_POSTCLIP_NO_RECLIP', initial='ACTUAL_PINNED_NONZERO_PARENT',
        optimizer='ORIGINAL_BF16_NS_NO_PRODUCT_CHANGE', tensor_storage='CPU_RAM_ONLY')
    for index, name in enumerate(names):
        trace.check(guard, 'before same-gradient actual matrix replay')
        if reference['options'][name] != candidate['options'][name]:
            raise ValueError('paired actual Muon options differ: ' + name)
        values = {}
        for label, capture in (('reference', reference), ('identical', reference), ('candidate', candidate)):
            values[label] = trace.replay_one(torch, muon, initial[name], capture['clipped'][name],
                capture['options'][name], device=device, guard=guard)
        identical = trace.comparison(torch, values['reference'], values['identical'], tolerance)
        reproduced = {}
        for label, capture in (('reference', reference), ('candidate', candidate)):
            actual = dict(weight=capture['updated'][name], buffer=capture['buffers'][name],
                ns_input=capture['ns_input'][name], ns_output=capture['ns_output'][name])
            reproduced[label] = trace.comparison(torch, actual, values[label], tolerance)
        row = dict(identical_gradient_control=identical, actual_reproduction=reproduced,
            original_pair=trace.comparison(torch, values['reference'], values['candidate'], tolerance))
        report['matrices'][name] = row
        report['matrix_count'] += 1
        journal.append(dict(event='fused_ce_actual_matrix_replay', index=index, matrix=name,
            identical_exact=identical['exact'], actual_reproduction_exact=all(r['exact'] for r in reproduced.values()),
            pair_close=row['original_pair']['close'], at=old.utc_now().isoformat()))
        if not identical['exact'] or not all(r['exact'] for r in reproduced.values()):
            raise ValueError('identical-gradient replay or exact actual-step reproduction failed: ' + name)
        del values
    report.update(complete=True, same_gradient_controls_exact=True, actual_updates_reproduced_exactly=True)


def execute_matrix(torch, engine, muon, cls, cfg, initial, initial_sha, pad, groups, plan, guard, journal, result):
    """Retain reference+one candidate at a time, all six arms fresh."""
    index = 0
    for precision in PRECISIONS:
        pairs = result['pairs'][precision] = {}
        reference = released_capture(torch, engine, muon, cls, cfg, initial, initial_sha,
            pad, 'reference', precision, groups, plan, guard, journal, index)
        index += 1
        result['updates'].append(reference['update'])
        for backend in BACKENDS[1:]:
            guard.check('before candidate actual update')
            candidate = released_capture(torch, engine, muon, cls, cfg, initial, initial_sha,
                pad, backend, precision, groups, plan, guard, journal, index)
            index += 1
            result['updates'].append(candidate['update'])
            measured_bytes = capture_bytes(initial, reference, candidate)
            result['max_cpu_captured_tensor_bytes'] = max(result.get('max_cpu_captured_tensor_bytes', 0), measured_bytes)
            if measured_bytes + trace.CPU_SCRATCH_RESERVE > trace.CPU_CAPTURE_LIMIT:
                raise MemoryError('actual capture exceeded unchanged CPU budget; gradients will not be dropped')
            row = pairs[backend] = compare_pair(torch, reference, candidate, result['tolerances'])
            row['replay'] = {}
            old.gpu_admission(torch)
            replay_pair(torch, muon, initial, reference, candidate,
                result['tolerances']['gradients_and_update'], guard, journal, row['replay'])
            trace.release_cuda(torch)
            del candidate
        del reference


def matrix_complete(result):
    if (not result.get('canaries', {}).get('complete') or not result['canaries'].get('close')
            or len(result.get('updates', [])) != len(BACKENDS) * len(PRECISIONS)
            or set(result.get('pairs', {})) != set(PRECISIONS)):
        return False
    expected = {(precision, backend) for precision in PRECISIONS for backend in BACKENDS}
    actual = [(row.get('precision'), row.get('ce_backend')) for row in result['updates']]
    if len(set(actual)) != len(actual) or set(actual) != expected:
        return False
    for rows in result['pairs'].values():
        if set(rows) != set(BACKENDS[1:]):
            return False
        for row in rows.values():
            replay = row.get('replay', {})
            if (not replay.get('complete') or replay.get('matrix_count') != MATRIX_COUNT
                    or len(replay.get('matrices', {})) != MATRIX_COUNT
                    or not replay.get('same_gradient_controls_exact')
                    or not replay.get('actual_updates_reproduced_exactly')):
                return False
            comparisons = row.get('comparisons', {})
            if set(comparisons) != set((*FULL_FIELDS, *MATRIX_FIELDS, 'optimizer', 'loss', 'preclip_norm')):
                return False
            for key in (*FULL_FIELDS, *MATRIX_FIELDS, 'optimizer'):
                count = ALL_COUNT if key in FULL_FIELDS else MATRIX_COUNT
                if key == 'optimizer':
                    count = MATRIX_COUNT + 3 * (ALL_COUNT - MATRIX_COUNT)
                if comparisons[key].get('tensors') != count:
                    return False
            for matrix in replay['matrices'].values():
                if (not matrix.get('identical_gradient_control', {}).get('exact')
                        or set(matrix.get('actual_reproduction', {})) != {'reference', 'candidate'}
                        or not all(v.get('exact') for v in matrix['actual_reproduction'].values())):
                    return False
    return True


def classify(result):
    """Exit zero alone, empty tables and stale positives never authorize PASS."""
    if result.get('errors') or result.get('cleanup_errors'):
        return 'ERROR_PARTIAL_EVIDENCE_NOT_ADOPTED', 9
    if (result.get('canary_negative') and result.get('canaries', {}).get('complete')
            and result['canaries'].get('close') is False and not result.get('updates')
            and not result.get('pairs') and result.get('assets_before') is None):
        return 'CANARY_NUMERICAL_NEGATIVE_PARENT_DATA_NOT_RUN_NOT_ADOPTED', 8
    if not matrix_complete(result):
        return 'ERROR_INCOMPLETE_EVIDENCE_NOT_ADOPTED', 9
    close = all(row['close'] for rows in result['pairs'].values() for row in rows.values())
    return ('NUMERICAL_PASS_NOT_ADOPTED', 0) if close else ('VALID_NUMERICAL_NEGATIVE_NOT_ADOPTED', 8)


def audit_final(torch, identity, source_map, dependencies, assets, result):
    errors = result.setdefault('cleanup_errors', [])
    gc.collect()
    if torch is not None and torch.cuda.is_initialized():
        try:
            trace.release_cuda(torch)
            result['final_allocated_bytes'] = torch.cuda.memory_allocated()
        except Exception as error:
            errors.append('CUDA cleanup: ' + repr(error))
    if identity is not None:
        try:
            identity.check()
            result['original_muon_globals_unchanged'] = True
        except Exception as error:
            errors.append('Muon identity: ' + repr(error))
    for label, action in (
        ('sources_unchanged', lambda: sources() == source_map),
        ('dependencies_unchanged', lambda: dependency_metadata() == dependencies),
    ):
        try:
            result[label] = action()
            if not result[label]:
                errors.append(label + ': mutation detected')
        except Exception as error:
            result[label] = None
            errors.append(label + ': ' + repr(error))
    if assets is not None:
        try:
            result['assets_after'] = {name: old.digest(old.safe_path(name)) for name in assets}
            result['assets_unchanged'] = result['assets_after'] == assets
            if not result['assets_unchanged']:
                errors.append('pinned assets changed during execution')
        except Exception as error:
            result['assets_unchanged'] = None
            errors.append('asset audit: ' + repr(error))


def append_terminal(target, event):
    """Write-once report corrections use append-only vetoes, never overwrite."""
    path = target / 'terminal.jsonl'
    if path.is_symlink():
        raise ValueError('linked terminal evidence refused')
    raw = old.canonical(event) + b'\n'
    size = path.stat().st_size if path.exists() else 0
    if size + len(raw) > MAX_BYTES:
        raise ValueError('20MB cumulative terminal evidence guard')
    with path.open('ab') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def terminal_failure(target, result, stage, error):
    """Always keep the primary error even when recording the veto also fails."""
    result.setdefault('errors', []).append(error_record(error, stage))
    result['status'], result['returncode'] = classify(result)
    event = dict(event='TERMINAL_VETO', stage=stage, at=old.utc_now().isoformat(),
        status=result['status'], returncode=9, errors=result.get('errors', []),
        cleanup_errors=result.get('cleanup_errors', []), actual_process_exit='PENDING_CALLER_CHECK')
    try:
        append_terminal(target, event)
    except (Exception, KeyboardInterrupt) as veto_error:
        result['errors'].append(error_record(veto_error, 'terminal veto storage after ' + stage))
        try:
            print(json.dumps(dict(event='TERMINAL_VETO_STORAGE_ERROR', original=event,
                storage_error=error_record(veto_error, stage))), file=sys.stderr, flush=True)
        except (Exception, KeyboardInterrupt):
            pass


def terminalize(target, journal, guard, result, began):
    """Numerical report is provisional until terminal audit and caller exit agree."""
    def attempt(stage, action):
        try:
            value = action()
        except (Exception, KeyboardInterrupt) as error:
            terminal_failure(target, result, stage, error)
            value = None
        try:
            guard.check('after ' + stage)
        except (Exception, KeyboardInterrupt) as error:
            terminal_failure(target, result, 'clock after ' + stage, error)
        return value

    attempt('event journal close', journal.close)
    result['matrix_complete'] = matrix_complete(result)
    result['status'], result['returncode'] = classify(result)
    result.update(finished_at=old.utc_now().isoformat(), wall_seconds=time.perf_counter() - began,
        wall_seconds_scope='THROUGH_FINAL_AUDIT_BEFORE_REPORT_STDOUT_TERMINAL_IO',
        terminal_audit='REQUIRES_TERMINAL_JSONL_WITHOUT_VETO_AND_CALLER_PROCESS_EXIT',
        returncode_scope='NUMERICAL_PRE_TERMINAL_REPORT; TERMINAL_VETO_OVERRIDES_REPORT_AND_STDOUT')
    snapshot = copy.deepcopy(result)
    expected_sha = old.identity(snapshot)
    report_path = target / 'report.json'
    attempt('report write', lambda: old.write_new(report_path, snapshot))
    def reread():
        if report_path.stat().st_size > MAX_BYTES:
            raise ValueError('written report exceeds the per-file guard')
        observed = json.loads(report_path.read_text(encoding='utf-8'))
        if old.identity(observed) != expected_sha:
            raise ValueError('report roundtrip does not match the written numerical snapshot')
        return True
    roundtrip = attempt('report reread', reread)
    result['status'], result['returncode'] = classify(result)
    summary = {key: result[key] for key in ('schema', 'tag', 'status', 'matrix_complete',
        'wall_seconds', 'checkpoint_writes', 'actual_process_exit')}
    summary.update(numerical_returncode=result['returncode'], terminal_audit='PENDING_TERMINAL_JSONL_AND_CALLER_EXIT')
    attempt('stdout flush', lambda: print(json.dumps(summary, ensure_ascii=False), flush=True))
    result['status'], result['returncode'] = classify(result)
    if result.get('errors') or result.get('cleanup_errors'):
        # Persist original runtime failures even when there was no terminal IO error.
        event = dict(event='TERMINAL_VETO', stage='execution or cleanup error retained',
            at=old.utc_now().isoformat(), status=result['status'], returncode=9,
            wall_seconds_before_terminal_append=time.perf_counter() - began,
            errors=result.get('errors', []), cleanup_errors=result.get('cleanup_errors', []))
    else:
        event = dict(event='TERMINAL_AUDIT_COMPLETE', at=old.utc_now().isoformat(),
            status=result['status'], returncode=result['returncode'], report_sha256=expected_sha,
            wall_seconds_before_terminal_append=time.perf_counter() - began,
            report_roundtrip=roundtrip is True, after_stdout_clock=True,
            actual_process_exit='PENDING_CALLER_EXIT_AND_GPU_PROCESS_CHECK')
    attempt('terminal audit append', lambda: append_terminal(target, event))
    result['status'], result['returncode'] = classify(result)
    try:
        guard.check('immediately before returning from terminal audit')
    except (Exception, KeyboardInterrupt) as error:
        terminal_failure(target, result, 'final return clock', error)
    return result['returncode']


def run(args, source_map=None):
    deadline = validate_execution(args)
    began = time.perf_counter()
    guard = Guard(deadline, args.max_wall_sec)
    state = {}
    try:
        with total_budget(guard):
            code = run_guarded(args, source_map, deadline, began, guard, state)
        guard.check('after whole-execute alarm cleanup immediately before return')
        return code
    except (Exception, KeyboardInterrupt) as error:
        if not state:
            raise
        try:
            state['journal'].close()
        except (Exception, KeyboardInterrupt) as close_error:
            state['result'].setdefault('errors', []).append(error_record(close_error, 'outer event journal close'))
        terminal_failure(state['target'], state['result'], 'outer execute/terminal budget', error)
        return 9


def run_guarded(args, source_map, deadline, began, guard, state):
    source_map = sources() if source_map is None else source_map
    guard.check('after source receipt preparation')
    if args.source_sha256 != old.identity(source_map):
        raise ValueError('source-only receipt changed; no GPU or model admission')
    dependencies = dependency_metadata()
    guard.check('after dependency metadata preparation')
    if args.dependency_sha256 != old.identity(dependencies) or not dependencies['ready']:
        raise ValueError('dependency receipt missing, changed or not ready; no GPU or model admission')
    dependency_sources = verify_installed_sources(dependencies)
    guard.check('after installed dependency source verification')
    tolerances = old.literal_tolerances()
    target = output_path(args.tag)
    admission = old.gpu_admission()
    guard.check('after initial GPU admission')
    target.mkdir()
    journal = old.Journal(target / 'events.jsonl')
    result = dict(schema=SCHEMA, tag=args.tag, sources=source_map,
        source_sha256=old.identity(source_map), dependencies=dependencies,
        dependency_sha256=old.identity(dependencies), started_at=old.utc_now().isoformat(),
        dependency_source_verification=dependency_sources,
        deadline=deadline.isoformat(), max_wall_sec=args.max_wall_sec,
        checkpoint_writes=0, production_adopted=False, quality_claim=False, speed_adoption=False,
        mtp_gpu='NOT_RUN_MAIN_ONLY_GATE', full_training='NOT_RUN',
        dataset_quality='KNOWN_V3_SUPERVISION_DEFECTS_NUMERICAL_CONTROL_ONLY_NOT_ADMITTED',
        timing_scope='CANARY_PREWARMED_INSTRUMENTED_FIRST_UPDATE_CPU_CAPTURES_CHECKPOINT_RECOMPUTATION_NOT_STEADY_STATE',
        memory_scope='CUDA_ALLOCATED_RESERVED_UPDATE_PEAKS; CPU_CAPTURE_BUDGET_SEPARATE; NOT_TOTAL_PROCESS_RSS',
        external_os_timeout_required=True, actual_process_exit='PENDING_CALLER_EXIT_AND_GPU_PROCESS_CHECK',
        max_wall_scope='EXECUTE_ENTRY_SOURCE_METADATA_ADMISSION_RUNTIME_CLEANUP_REPORT_STDOUT_TERMINAL_AUDIT',
        tolerances=tolerances, gpu_admission=admission, status='STARTED', returncode=9,
        canaries={}, pairs={}, updates=[], assets_before=None, errors=[])
    state.update(target=target, result=result, journal=journal)
    old.write_new(target / 'admission.json', result)
    torch = identity = assets = template = initial = None
    try:
        import tinylm  # establish original runtime search path
        import torch
        from tinylm.train import muon
        guard.check('after framework imports')
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        result['cpu_control'] = trace.cpu_control(torch, muon)
        identity = trace.GlobalIdentity(muon)
        run_canaries(torch, result['tolerances'], guard, journal, result['canaries'])
        identity.check()
        guard.check('before original engine/corpus admission')
        from scripts import diag_p101a_sft_mtp as engine
        from scripts import diag_p101a_clean_bilingual as clean
        report = engine.corpus_report(old.safe_path(old.CORPUS))
        assets = old.asset_manifest(engine, report)
        result['assets_before'] = assets
        guard.check('before pinned parent load')
        torch, template, cfg, tok, initial_sha = engine.load_runtime('parent_ntp')
        if (cfg.cla_group != 2 or not cfg.grad_checkpoint or cfg.mtp_aux or cfg.train_repeat != 1.
                or any(isinstance(module, torch.nn.Dropout) and module.p for module in template.modules())):
            raise ValueError('original CLA2/checkpoint/R1/MTPoff/dropout0 required')
        result['cpu_memory_plan'] = memory_plan(template, muon)
        initial = old.cpu_copy(template.state_dict())
        records = clean.encoded(old.safe_path(old.CORPUS), report, tok)
        if len(records['train']) != 22528 or len(records['val']) != 512:
            raise ValueError('full frozen known-V3 row identity required')
        groups = next(iter(engine.batches(records['train'], 0)))
        plan = old.update_plan(groups)
        cls = type(template)
        pad = tok.token_to_id('<|pad|>')
        if pad is None:
            pad = tok.token_to_id('<pad>')
        if type(pad) is not int or not 0 <= pad < 32768:
            raise ValueError('original PAD ID required')
        result.update(initial_core_sha256=initial_sha, parent_sha256=old.PARENT_SHA,
            tokenizer_sha256=old.TOKENIZER_SHA, plan=plan, seed=1337,
            optimizer=dict(factory='diag_p101a_sft_mtp.optimizers', adam_lr=5e-5,
                muon_lr=2e-4, clip=1., fresh_each_arm=True, reclip_in_replay=False))
        template = None
        gc.collect()
        execute_matrix(torch, engine, muon, cls, cfg, initial, initial_sha, pad, groups, plan, guard, journal, result)
        identity.check()
        guard.check('after complete official kernel update/replay matrix')
    except NumericalCanaryNegative as negative:
        result['canary_negative'] = error_record(negative, 'official kernel numerical canary')
    except (Exception, KeyboardInterrupt) as error:
        result['errors'].append(error_record(error, 'official kernel/runtime gate'))
    finally:
        # Preserve failures from the original run; a successful final audit cannot erase them.
        template = initial = None
        try:
            audit_final(torch, identity, source_map, dependencies, assets, result)
            guard.check('after cleanup and final audit')
        except (Exception, KeyboardInterrupt) as error:
            result.setdefault('cleanup_errors', []).append(error_record(error, 'final cleanup/audit clock'))
    return terminalize(target, journal, guard, result, began)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-only', action='store_true')
    modes.add_argument('--execute', action='store_true')
    parser.add_argument('--tag')
    parser.add_argument('--deadline')
    parser.add_argument('--max-wall-sec', type=int)
    parser.add_argument('--source-sha256')
    parser.add_argument('--dependency-sha256')
    args = parser.parse_args(argv)
    try:
        if args.check_only:
            source_map = sources()
            dependencies = dependency_metadata()
            print(json.dumps(dict(schema=SCHEMA, evidence='STATIC_ONLY_NOT_KERNEL_PASS',
                tag_prefix=TAG_PREFIX, source_sha256=old.identity(source_map), source_count=len(source_map),
                dependency_sha256=old.identity(dependencies), dependencies_ready=dependencies['ready'],
                package_versions={name: row['installed_version'] for name, row in dependencies['packages'].items()},
                model_calls=0, cuda_calls=0, kernel_calls=0, asset_reads=0,
                prepared_dependency_metadata=PREPARED_PACKAGES, max_file_bytes=MAX_BYTES,
                mandatory_execute_arguments=['tag', 'deadline', 'max-wall-sec', 'source-sha256', 'dependency-sha256'])))
            return 0
        return run(args)
    except (ValueError, FileExistsError, TimeoutError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
