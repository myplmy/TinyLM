#!/usr/bin/env python3
"""Bounded, optimizer-free full-window causal/MNTP technical costs; no corpus."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p106b_resource_matrix as resource
from tinylm.train import hybrid_mntp as h

SCHEMA = 'P107_EXPLICIT_VISIBILITY_SHIFT_COST_V1'
TAG = 'p107_hybrid_visibility_v1_20261027'
ORDER = ('default', 'document_causal', 'mntp', 'hybrid', 'hybrid', 'mntp', 'document_causal', 'default')
OWN = ('tinylm/model/visibility.py', 'tinylm/train/hybrid_mntp.py',
       'scripts/test_p107_hybrid_mntp.py', 'scripts/diag_p107_hybrid_mntp.py',
       'scripts/test_p107_hybrid_driver.py', 'scripts/diag_p013_context_curriculum.py',
       'tinylm/train/context_curriculum.py', 'scripts/diag_p014e_packed_deploy.py',
       'scripts/p014e_packed_g128.py', 'tinylm/model/lut.py')
need = resource.need


def identity():
    files = dict(resource.identity()['files'])
    files.update({name: resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def tensor_sha(values):
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest().upper()


def remember_error(report, error):
    """Preserve chained original failures before a cleanup timeout can hide them."""
    chain, seen, current = [], set(), error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(dict(type=type(current).__name__, message=str(current)[:2000],
                          is_timeout=isinstance(current, TimeoutError)))
        current = current.__cause__ if current.__cause__ is not None else current.__context__
    report.setdefault('exception_chains', []).append(chain)
    if 'primary_cost_error' not in report:
        first = chain[-1]
        report['primary_cost_error'] = {k:first[k] for k in ('type','message')}
        report['primary_cost_error_is_timeout'] = all(x['is_timeout'] for x in chain)


def verify_tokenizer_ref(ref):
    path = resource.safe(ref['path']); before = path.stat()
    need(path.is_file() and before.st_size == ref['bytes'], 'actual tokenizer bytes differ')
    actual = resource.digest(path); after = path.stat()
    need(actual == ref['sha256'] and (before.st_ino,before.st_size,before.st_mtime_ns) ==
         (after.st_ino,after.st_size,after.st_mtime_ns), 'actual tokenizer SHA changed')
    return actual


def independent_final_checks(report, actions):
    """One failed cleanup must not prevent source/tokenizer/idle/core checks."""
    errors = []
    for stage, action in actions:
        try:
            action()
        except BaseException as exc:
            errors.append(dict(stage=stage,type=type(exc).__name__,message=str(exc)[:1000]))
    report['final_verification_errors'] = errors
    return not errors


def close_owned_cuda(torch, report):
    # Attach before calling: partial workspace/counter proof survives an exception.
    report['final_cuda_cleanup'] = {}
    resource.close_cuda(torch, proof=report['final_cuda_cleanup'])
    from scripts.diag_p014e_packed_deploy import assert_cuda_clean
    assert_cuda_clean(report['final_cuda_cleanup'])


def fixture(index, *, batch=8, length=1024, micros=16):
    """Four explicit synthetic documents, no real source/document inference."""
    import torch
    need(all(type(value) is int and value > 0 for value in (batch, length, micros))
         and length >= 4 and length % 4 == 0, 'four equal positive document segments required')
    generator = torch.Generator().manual_seed(1337 + index)
    out = []
    for micro in range(micros):
        positions = torch.arange(length + 1)
        starts = (torch.arange(batch) + micro * batch + index * 128) * 7919
        tokens = ((starts[:, None] + positions[None, :] * 1543) % (32768 - 35) + 35).long()
        # This fixture is exactly 4 equal input segments; the off-window final
        # token belongs to the last document, so the causal last target is kept.
        docs = (positions // (length // 4)).clamp_max(3)[None, :].expand(batch, -1).clone().long()
        selected = h.uniform_mntp_selection(tokens, docs, vocab_size=32768,
                                             probability=.15, generator=generator)
        causal = h.causal_batch(tokens, docs, vocab_size=32768)
        masked = h.mntp_batch(tokens, docs, selected, vocab_size=32768)
        need(causal.target_count > 0 and masked.target_count > 0, 'no forced target substitution; fixture must be nonempty')
        out.append((causal, masked))
    return tuple(out)


def batch_to(batch, device, *, explicit):
    return h.ObjectiveBatch(batch.inputs.to(device), batch.targets.to(device),
                             batch.attention_mask.to(device) if explicit else batch.attention_mask,
                             batch.objective, batch.selected_positions)


def tasks(pairs, condition):
    need(condition in set(ORDER), 'unknown cost condition')
    if condition == 'hybrid':
        # Exactly the same 16 input micro-batches, not two full accumulations.
        half = len(pairs) // 2
        need(half > 0 and len(pairs) == 2 * half, 'hybrid needs an even micro count')
        chosen = [(a, 'causal', True) if i < half else (b, 'masked', True)
                  for i, (a, b) in enumerate(pairs)]
        weights = {'causal': .5, 'masked': .5}
    else:
        name = 'masked' if condition == 'mntp' else 'causal'
        chosen = [(b if name == 'masked' else a, name, condition != 'default') for a, b in pairs]
        weights = {name: 1.}
    totals = {name: sum(batch.target_count for batch, kind, _ in chosen if kind == name)
              for name in weights}
    need(all(totals.values()), 'nonempty objective denominators required before forward')
    return chosen, totals, weights


def one_update(model, pairs, condition, progress):
    import torch
    chosen, totals, weights = tasks(pairs, condition)
    metadata = progress
    metadata.update(condition=condition, micro_batches=len(chosen), optimizer_updates=0,
                    planned_input_tokens=sum(b.executed_input_tokens for b, _, _ in chosen),
                    executed_input_tokens=0, completed_micro_batches=0, attempted_micro_batch=None,
                    phase='PREPARED', synchronized_full_update=False,
                    target_counts=totals, objective_weights=weights,
                    normalization='SEPARATE_UPDATE_OBJECTIVE_TARGET_SUMS',
                    input_source_sha256=tensor_sha([t for a, b in pairs for t in (a.inputs, a.targets, b.inputs, b.targets)]))
    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model.zero_grad(set_to_none=True)
    last = batch = logits = loss = None
    for micro, (source, name, explicit) in enumerate(chosen):
        metadata.update(attempted_micro_batch=micro, phase='H2D')
        batch = batch_to(source, 'cuda', explicit=explicit)
        with torch.autocast('cuda', dtype=torch.bfloat16):
            metadata['phase'] = 'FORWARD'
            logits = model(batch.inputs, attention_mask=batch.attention_mask) if explicit else model(batch.inputs)
            metadata['phase'] = 'OBJECTIVE'
            loss, count = h.objective_mean(logits, batch.targets)
            loss = loss * (weights[name] * count / totals[name])
        metadata['phase'] = 'BACKWARD'
        loss.backward()
        metadata['phase'] = 'BACKWARD_SYNC'
        torch.cuda.synchronize()
        metadata['completed_micro_batches'] += 1
        metadata['executed_input_tokens'] += batch.executed_input_tokens
        last = loss.detach()
        logits = loss = batch = None
    torch.cuda.synchronize(); seconds = time.perf_counter() - started
    metadata.update(phase='GRADIENT_AUDIT', synchronized_full_update=True)
    metadata.update(fb_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    fb_peak_reserved_bytes=torch.cuda.max_memory_reserved())
    gradients = [(n, p.grad) for n, p in model.named_parameters()]
    need(gradients and all(v is not None and bool(torch.isfinite(v).all()) for n, v in gradients),
         'every original named parameter must have finite gradients')
    metadata.update(seconds=seconds, gradient_tensors=len(gradients),
                    gradient_l2_norm=float(sum(v.double().square().sum() for n, v in gradients).sqrt()),
                    last_weighted_micro_loss=float(last))
    metadata.update(audit_inclusive_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    audit_inclusive_peak_reserved_bytes=torch.cuda.max_memory_reserved())
    gradients = last = None
    model.zero_grad(set_to_none=True)
    metadata.update(phase='COMPLETE', status='UPDATE_COMPLETE',
                    elapsed_seconds=time.perf_counter()-metadata['attempt_started_perf_counter'])
    return metadata


def record_block(report, block, condition, run_update, torch):
    row = dict(block=block, condition=condition, status='STARTED', warmup=None, measured=[],
               peak_scope='BLOCK_MAX_OF_PER_UPDATE_FB_PLUS_GRADIENT_AUDIT;RESERVED_MAY_CARRY_PRIOR_CACHE',
               timing_scope='ZERO_GRAD_H2D_VISIBLE_MASK_SNAPSHOT_FORWARD_BACKWARD_SYNC_EACH_MICRO;GRAD_AUDIT_EXCLUDED')
    report['blocks'].append(row)
    primary = None
    try:
        row['entry_memory'] = dict(allocated_bytes=torch.cuda.memory_allocated(), reserved_bytes=torch.cuda.memory_reserved())
        torch.cuda.reset_peak_memory_stats()
        row['warmup'] = dict(status='STARTED', completed_micro_batches=0, executed_input_tokens=0,
                             attempt_started_perf_counter=time.perf_counter())
        run_update(0, row['warmup'])
        for index in (1, 2):
            attempt = dict(status='STARTED', completed_micro_batches=0, executed_input_tokens=0,
                           attempt_started_perf_counter=time.perf_counter())
            row['measured'].append(attempt)
            run_update(index, attempt)
        row['status'] = 'BLOCK_COMPLETE'
        return row
    except BaseException as exc:
        primary = dict(type=type(exc).__name__, message=str(exc)[:2000])
        row.update(status='PARTIAL_BLOCK_ERROR', primary_error=primary)
        active = row['measured'][-1] if row['measured'] else row['warmup']
        if active is not None:
            active.update(status='UPDATE_ERROR', error=primary,
                          elapsed_seconds=time.perf_counter()-active['attempt_started_perf_counter'])
        raise
    finally:
        try:
            completed = ([row['warmup']] if row['warmup'] is not None else []) + row['measured']
            row.update(peak_allocated_bytes=max([torch.cuda.max_memory_allocated()] + [x.get('audit_inclusive_peak_allocated_bytes',0) for x in completed]),
                       peak_reserved_bytes=max([torch.cuda.max_memory_reserved()] + [x.get('audit_inclusive_peak_reserved_bytes',0) for x in completed]),
                       fb_peak_allocated_bytes=max([0] + [x.get('fb_peak_allocated_bytes',0) for x in completed]),
                       fb_peak_reserved_bytes=max([0] + [x.get('fb_peak_reserved_bytes',0) for x in completed]))
        except BaseException as exc:
            row['peak_error'] = dict(type=type(exc).__name__, message=str(exc)[:1000])
            if primary is None:
                raise


def validate(profile, args):
    need(profile.get('schema') == SCHEMA and profile.get('tag') == TAG
         and profile.get('root_approved') is True and profile.get('authority_directive') == 96
         and profile.get('source_sha256') == identity()['sha256']
         and profile.get('deadline') == '2026-10-27T08:00:00+00:00'
         and profile.get('optimizer_updates') == profile.get('checkpoint_writes') == 0
         and profile.get('additional_300m') is False and args.max_wall_sec == 900,
         'exact source/authority/no-training profile required')
    if (resource.DEADLINE - datetime.now(timezone.utc)).total_seconds() <= 1080:
        raise TimeoutError('insufficient deadline margin for bounded cost and external closure watchdog')
    contract = profile['cpu_contract']
    need(contract['actual_exit'] == 0 and resource.digest(resource.safe(contract['path'])) == contract['sha256'],
         'closed CPU contract required')
    native = resource.read_ref(profile['historical_native_reference'])
    spec = next(x for x in native['models'] if x['id'] == 'native595-q')
    need(resource.sha(spec) == profile['native_spec_sha256'] and profile['native_source_current'] is False,
         'historical model metadata must not be called current-source validation')
    need(spec['cfg']['grad_checkpoint'] is True and not spec['cfg']['mtp_aux'], 'checkpoint ON/noMTP required')
    verify_tokenizer_ref(native['tokenizer'])
    return native, spec


def run_cost(native, spec, budget, report, runtime):
    import torch
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p102a_logit_margin import memory_point
    from scripts.diag_p013_context_curriculum import cleanup_cost_model
    report['idle_before'] = require_idle_gpu(); report['memory_before'] = memory_point()
    need(report['memory_before']['free_mib'] >= 12288, '12GiB free VRAM admission required')
    start = time.perf_counter(); master = tuple(fixture(index) for index in range(3))
    report['fixture_seconds'] = time.perf_counter() - start
    report['fixture'] = 'FOUR_EXPLICIT_SYNTHETIC_DOCS;NO_CORPUS;RESERVED13;SPECIAL0_34;UNIFORM15PCT'
    report['blocks'] = []; report['source_proof'] = {}
    loaded = model = cfg = tokenizer = route = None
    try:
        with resource.frozen_model(spec, native['tokenizer'], 'cuda', budget, report['source_proof']) as loaded:
            model, cfg, tokenizer, route = loaded
            runtime['model_ref'] = weakref.ref(model)
            primary = None
            try:
                need(tokenizer.id_to_token(13) == '<|reserved_0|>', 'actual reserved token13 differs')
                model.clear_quant(); model.train()
                need(all(p.requires_grad for p in model.parameters()), 'all original master parameters must remain trainable')
                report['actual_trainable_parameters'] = sum(p.numel() for p in model.parameters())
                with patch.object(torch, 'save', side_effect=ValueError('checkpoint serialization forbidden in cost')):
                    for block, condition in enumerate(ORDER):
                        budget.check()
                        row = record_block(report, block, condition,
                                           lambda index, progress: one_update(model, master[index], condition, progress), torch)
                        print(json.dumps(dict(block=block, condition=condition,
                                                measured_seconds=[r['seconds'] for r in row['measured']])), flush=True)
            except BaseException as exc:
                primary = dict(type=type(exc).__name__, message=str(exc)[:2000])
                remember_error(report, exc)
                raise
            finally:
                errors = cleanup_cost_model(model, report)
                if errors and primary is None:
                    raise RuntimeError('model cleanup failed: ' + str(errors))
    finally:
        loaded = model = cfg = tokenizer = route = None
    for index in (0, 1):
        need(len({b['measured'][index]['input_source_sha256'] for b in report['blocks']}) == 1,
             'same full fixture index changed across conditions')
    report['summary'] = {name: dict(measured_updates=4,
        median_seconds=statistics.median(r['seconds'] for b in report['blocks'] if b['condition'] == name for r in b['measured']),
        executed_input_tokens_per_update=131072) for name in set(ORDER)}
    report['not_measured'] = ['OPTIMIZER_TIME','COMPILE','FULL_TRAINING_WALL','QUALITY','CAUSAL_KD','ADAPTIVE_MASKING','PRODUCTION_TRAINER','CORPUS_TRAINING']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True); parser.add_argument('--profile-sha256', required=True)
    parser.add_argument('--max-wall-sec', type=int, required=True)
    group = parser.add_mutually_exclusive_group(); group.add_argument('--check-only', action='store_true'); group.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.check_only:
        try:
            profile = resource.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
            validate(profile, args)
            print(json.dumps(dict(status='P107_METADATA_ONLY', models=0, gpu_calls=0, tokenizer_bytes_verified=True)))
            return 0
        except BaseException as exc:
            rc = 8 if isinstance(exc,TimeoutError) else 9
            print(json.dumps(dict(status='METADATA_ADMISSION_HOLD' if rc==8 else 'METADATA_ADMISSION_ERROR',
                                  actual_exit=rc,models=0,gpu_calls=0,error=dict(type=type(exc).__name__,message=str(exc)[:1000]))))
            return rc
    need(args.execute, 'explicit bounded execution required')
    import torch
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    output = resource.safe('test_result/evidence/' + TAG + '/cost/report.json')
    need(not output.exists(), 'new namespace required')
    budget = resource.Budget(args.max_wall_sec); source = identity(); runtime = {}; rc = 9
    native = spec = None
    report = dict(schema=SCHEMA, tag=TAG, source=source, profile_sha256=args.profile_sha256,
                  status='STARTED', started_at=datetime.now(timezone.utc).isoformat(),
                  optimizer_updates=0, checkpoint_writes=0, quality_claim=False,
                  runtime=dict(torch_version=torch.__version__, cuda_version=torch.version.cuda,
                               precision='BF16_AUTOCAST_FP32_CE', tf32=False, compile=False,
                               grad_checkpoint=True, cpu_threads=2),
                  native_source_current=False, admission_complete=False)
    try:
        with resource.wall(args.max_wall_sec):
            profile = resource.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
            native, spec = validate(profile, args)
            report.update(admission_complete=True, historical_native_reference=profile['historical_native_reference'],
                          tokenizer_ref=native['tokenizer'], tokenizer_verified_before=True)
            run_cost(native, spec, budget, report, runtime)
            need(identity() == source, 'source changed during cost diagnostic')
            report['status'], rc = 'TECHNICAL_COMPLETE_NOT_QUALITY', 0
    except BaseException as exc:
        from scripts.diag_p013_context_curriculum import failure_outcome
        remember_error(report, exc)
        report['status'], rc = failure_outcome(exc, report)
        report['execution_error'] = dict(type=type(exc).__name__, message=str(exc)[:2000])
    finally:
        def release_check():
            gc.collect()
            if 'model_ref' in runtime:
                report['model_released'] = runtime['model_ref']() is None
                need(report['model_released'], 'actual model reference remains live')
        def cuda_check():
            if torch.cuda.is_initialized():
                close_owned_cuda(torch, report)
        def source_check():
            report['source_unchanged'] = identity() == source
            need(report['source_unchanged'], 'final source differs')
        def idle_check():
            from scripts.interactive_research_infer import require_idle_gpu
            if report['admission_complete']:
                report['idle_after'] = require_idle_gpu()
        def tokenizer_check():
            if 'tokenizer_ref' in report:
                report['tokenizer_sha256_after'] = verify_tokenizer_ref(report['tokenizer_ref'])
        def core_check():
            proof = report.get('source_proof', {})
            if proof.get('initial_core_verified'):
                need(proof.get('final_core_verified') and proof.get('gradients_absent')
                     and proof.get('checkpoint_bytes_unchanged') and not report.get('cost_model_cleanup_errors'),
                     'actual model cleanup/core/checkpoint proof incomplete')
        if not independent_final_checks(report, [('model_release',release_check),('cuda_cleanup',cuda_check),
                ('source',source_check),('tokenizer',tokenizer_check),('idle',idle_check),('core',core_check)]):
            rc = 9
        if rc == 9 and report['status'] in ('TECHNICAL_COMPLETE_NOT_QUALITY','BUDGET_HOLD_NOT_FULL_SUITE'):
            report['status'] = 'ERROR_FINAL_CLEANUP_NOT_COMPLETE'
        report.update(exit_code=rc, seconds=time.monotonic()-budget.started, ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output, report)
        print(json.dumps(dict(status=report['status'], actual_exit=rc, seconds=report['seconds'])))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
