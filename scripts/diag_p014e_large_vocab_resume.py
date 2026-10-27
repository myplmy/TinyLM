#!/usr/bin/env python3
"""Reuse closed large-vocab baselines with a PathLike-safe tensor-load guard."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p014e_large_vocab_deploy as prior

resource = prior.resource
need = resource.need
TAG = prior.TAG + '_safe_loader_v1'
SCHEMA = 'P014E_LARGE_VOCAB_PATHLIKE_RECOVERY_V1'
OWN = ('scripts/diag_p014e_large_vocab_resume.py', 'scripts/test_p014e_large_vocab_resume.py')


def identity():
    files = dict(prior.identity()['files'])
    files.update({name: resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def checked_load_path(file, directory, *, weights_only):
    # A Path has .name too, but it is a basename rather than a file handle path.
    raw = file if isinstance(file, (str, os.PathLike)) else getattr(file, 'name', None)
    need(isinstance(raw, (str, os.PathLike)), 'named safe tensor path required')
    path = Path(raw).resolve()
    need(path.is_relative_to(directory.resolve()) and path.suffix == '.pt'
         and weights_only is True, 'only prior new deployment/oracle safe loads allowed')
    return path


@contextmanager
def guarded_new_tensor_loads(report):
    import torch
    original = torch.load
    report['torch_load_files'] = []
    def checked(file, *args, **kwargs):
        path = checked_load_path(file, prior.folder(), weights_only=kwargs.get('weights_only'))
        report['torch_load_files'].append(path.relative_to(ROOT).as_posix())
        return original(file, *args, **kwargs)
    try:
        torch.load = checked
        yield
    finally:
        torch.load = original


def validate_prior_error(error):
    need(error.get('mode') == 'deploy-cpu' and error.get('exit_code') == 9
         and error.get('status') == 'ERROR_NOT_COMPLETE'
         and error.get('original_checkpoint_loads') == 0, 'closed prior path-guard error required')
    rows = error.get('variants', [])
    need(len(rows) == 1 and rows[0].get('variant') == 'fp32_unchanged'
         and rows[0].get('model_released') is True and rows[0].get('cleanup_errors') == []
         and rows[0].get('execution_error', {}).get('message') == 'only new deployment/oracle safe loads allowed'
         and rows[0].get('result', {}).get('numeric') == []
         and rows[0].get('result', {}).get('records') == [],
         'prior must be the known pre-numeric loader error with cleanup closed')


def validate(profile, args):
    need(profile.get('schema') == SCHEMA and profile.get('tag') == TAG
         and profile.get('root_approved') is True and profile.get('authority_directive') == 96
         and profile.get('source_sha256') == identity()['sha256']
         and profile.get('training_updates') == 0 and profile.get('additional_300m') is False
         and profile.get('deadline') == '2026-10-27T08:00:00+00:00'
         and args.mode in ('deploy-cpu', 'deploy-cuda')
         and args.max_wall_sec == prior.CAPS[args.mode], 'exact bounded no-training recovery authority required')
    contract = profile['cpu_contract']
    need(contract['actual_exit'] == 0 and resource.digest(resource.safe(contract['path'])) == contract['sha256'],
         'closed meaningful recovery CPU contract required')
    original = resource.read_ref(profile['prior_profile'])
    header, base = prior.validate(original, args)
    original['_sha256'] = profile['prior_profile']['sha256']
    for mode in ('export', 'baseline-cpu', 'baseline-cuda'):
        ref = profile['closed_receipts'][mode]
        need(ref['path'] == prior.report_path(mode).relative_to(ROOT).as_posix()
             and resource.read_ref(ref) == prior.completed(mode, original), 'exact unchanged successful receipt required')
    ref = profile['prior_cpu_error']
    need(ref['path'] == prior.report_path('deploy-cpu').relative_to(ROOT).as_posix(), 'exact original CPU error path required')
    error = resource.read_ref(ref)
    need(error.get('source') == prior.identity() and error.get('profile_sha256') == original['_sha256'],
         'prior CPU error lineage changed')
    validate_prior_error(error)
    return original, header, base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('deploy-cpu', 'deploy-cuda'), required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--profile-sha256', required=True)
    parser.add_argument('--max-wall-sec', type=int, required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check-only', action='store_true')
    action.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    profile = resource.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    original, header, base = validate(profile, args)
    if args.check_only:
        print(json.dumps(dict(status='RECOVERY_METADATA_ONLY', model_loads=0, gpu_calls=0)))
        return 0
    need(args.execute, 'explicit no-training recovery execution required')
    import torch
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p102a_logit_margin import memory_point
    torch.set_num_threads(2 if args.mode.endswith('cuda') else 1)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    output = resource.safe('test_result/evidence/'+TAG+'/'+args.mode+'/report.json')
    need(not output.exists(), 'new recovery namespace required')
    source = identity()
    budget = resource.Budget(args.max_wall_sec)
    report = dict(schema=SCHEMA, tag=TAG, mode=args.mode, source=source,
        prior_runtime_source=prior.identity(), profile_sha256=args.profile_sha256,
        previous_profile=profile['prior_profile'], previous_error=profile['prior_cpu_error'],
        checkpoint=header, tokenizer=original['tokenizer'], status='STARTED', quality_claim=False,
        training_updates=0, checkpoint_writes=0, original_checkpoint_loads=0,
        started_at=datetime.now(timezone.utc).isoformat())
    rc = 9
    try:
        with resource.wall(args.max_wall_sec):
            report['idle_before'] = require_idle_gpu()
            report['memory_before'] = memory_point()
            need(report['memory_before']['free_mib'] >= 4096, '4GiB free admission required')
            if args.mode.endswith('cuda'):
                torch.cuda.init()
                torch.cuda.reset_peak_memory_stats()
            with guarded_new_tensor_loads(report):
                rc = prior.perform(args, original, header, base, budget, report)
            report['status'] = 'TECHNICAL_COMPLETE_NOT_QUALITY' if rc == 0 else 'BUDGET_HOLD_NOT_FULL_SUITE'
    except BaseException as exc:
        report['status'], rc = 'ERROR_NOT_COMPLETE', 9
        report['execution_error'] = dict(type=type(exc).__name__, message=str(exc)[:2000])
    finally:
        gc.collect()
        if torch.cuda.is_initialized():
            try:
                report['final_cuda_cleanup'] = resource.close_cuda(torch)
                prior.prior.assert_cuda_clean(report['final_cuda_cleanup'])
            except BaseException as exc:
                report['final_cleanup_error'] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                rc = 9
        try:
            report['idle_after'] = require_idle_gpu()
            report['source_unchanged'] = identity() == source
            need(report['source_unchanged'], 'recovery or prior source changed')
        except BaseException as exc:
            report['final_verification_error'] = dict(type=type(exc).__name__, message=str(exc)[:1000])
            rc = 9
        if rc == 9 and report['status'] == 'TECHNICAL_COMPLETE_NOT_QUALITY':
            report['status'] = 'ERROR_FINAL_VERIFICATION_NOT_COMPLETE'
        report.update(exit_code=rc, seconds=time.monotonic()-budget.started,
                      cuda_initialized=torch.cuda.is_initialized(), ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output, report)
        print(json.dumps(dict(mode=args.mode, status=report['status'], actual_exit=rc, seconds=report['seconds'])))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
