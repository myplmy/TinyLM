#!/usr/bin/env python3
"""Bounded P107 file-input/command integration, not a full-corpus trainer.

Only the sealed synthetic technical profile is executable in this research
window. Real corpus admission and full training remain separate user decisions.
The default run100m path and every existing trainer are unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import random
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import interactive_research_infer as manual
from tinylm.train.document_input import load_document_input

TAG = 'p107_document_cli_v1_20261104'
SCHEMA = 'P107_DOCUMENT_CLI_PROFILE_V1'
DEADLINE = datetime(2026, 11, 4, 17, 0, tzinfo=timezone.utc)
INPUT_ROOT = 'runs/isolated/'+TAG+'/inputs'
OUTPUT = 'test_result/evidence/'+TAG
SNAPSHOT = 'runs/isolated/'+TAG+'/boundary_u1'
AUDIT = 'handoff/audit/nov04_p107_cli'
PROFILE_PATH = AUDIT+'/PROFILE_v1.json'
SMOKE_REPORT = 'test_result/evidence/codex_smoke/nov04_p108_p107_v2/smoke_report.json'
MAX_WALL = 600
ALLOCATOR = 6*2**30
VRAM_INCREASE = 8_000_000_000
RECIPE = dict(batch=8, micros=16, length=1024, vocab=32768, seed=1337,
    mode='adaptive', masked_micros=8, mask_rate=.15, error_ema=.2,
    refresh_every=2, masking_mode='keep', special_max=34, mask_id=13,
    horizon=8, warmup=2, schedule='cosine', logical_updates=2, clip=1.,
    matrix_lr=4e-4, other_lr=1e-4, teacher=None, compile=False,
    compute='BF16_AMP_FP32_MASTER_MATH', grad_checkpoint=True)
SOURCES = (
    'scripts/train_p107_documents.py', 'scripts/diag_p107_document_cli.py',
    'scripts/test_p107_document_input.py', 'scripts/test_p107_document_cli.py',
    'tinylm/train/document_input.py', 'tinylm/train/document_source.py',
    'tinylm/train/hybrid_session.py', 'tinylm/train/boundary_store.py',
    'tinylm/train/anneal_schedule.py', 'scripts/p106b_nvml_probe.py',
)


def source_pins():
    from scripts.diag_p107_adaptive_training import identity
    values = dict(identity()['files'])
    values.update({name:manual.file_sha(manual.owned_path(name)) for name in SOURCES})
    return values


def validate_profile_object(value, current_sources, now, *, check_start_budget=True):
    if now.tzinfo is None:
        raise ValueError('aware execution time required')
    if (not isinstance(value, dict) or value.get('schema') != SCHEMA
            or value.get('tag') != TAG or value.get('authority_directive') != 107
            or value.get('deadline') != DEADLINE.isoformat()
            or value.get('model') != 'native595-q'
            or manual.canonical_sha(value.get('recipe')) != manual.canonical_sha(RECIPE)
            or value.get('profile_path') != PROFILE_PATH
            or value.get('source_pins') != current_sources
            or value.get('input_root') != INPUT_ROOT or value.get('output') != OUTPUT
            or value.get('snapshot') != SNAPSHOT or value.get('max_wall_sec') != MAX_WALL
            or value.get('allocator_cap_bytes') != ALLOCATOR
            or value.get('shared_gpu_increase_bytes') != VRAM_INCREASE
            or value.get('corpus_training') is not False
            or value.get('purpose') != 'SYNTHETIC_TECHNICAL'):
        raise ValueError('sealed bounded synthetic CLI contract differs')
    if check_start_budget and (DEADLINE-now).total_seconds() <= MAX_WALL+120:
        raise TimeoutError('deadline reserve insufficient; do not load a model')
    return value


def bound_metadata(ref, allowed_prefix):
    if (not isinstance(ref, dict) or set(ref) != {'path', 'bytes', 'sha256'}
            or not isinstance(ref['path'], str) or not ref['path'].startswith(allowed_prefix+'/')):
        raise ValueError('exact owned metadata descriptor required')
    value, digest = manual.small_json(ref['path'])
    path = manual.owned_path(ref['path'])
    if digest != ref['sha256'] or path.stat().st_size != ref['bytes']:
        raise ValueError('owned metadata SHA/bytes differs')
    return value


def validate(profile_path, expected_sha, *, now=None, check_start_budget=True):
    if profile_path != PROFILE_PATH:
        raise ValueError('only the exact owned profile path is allowed')
    value, digest = manual.small_json(profile_path)
    if digest != expected_sha:
        raise ValueError('profile SHA differs')
    value = validate_profile_object(value, source_pins(), now or datetime.now(timezone.utc),
                                    check_start_budget=check_start_budget)
    cpu = bound_metadata(value['cpu_contract'], AUDIT)
    if (cpu.get('schema') != 'P107_DOCUMENT_CLI_CPU_V1' or cpu.get('actual_exit') != 0
            or cpu.get('tests') != 30 or cpu.get('source_pins') != value['source_pins']):
        raise ValueError('same-source actual CPU30 required')
    for row in cpu['raw_logs']:
        path = manual.owned_path(row['path'])
        if not row['path'].startswith('test_result/107_log_20261104_P107_Stage8'):
            raise ValueError('exact owned CPU raw log required')
        if manual.file_sha(path) != row['sha256']:
            raise ValueError('CPU raw log changed')
    smoke_ref = value['smoke']
    if smoke_ref.get('path') != SMOKE_REPORT:
        raise ValueError('exact successful current smoke required')
    smoke = bound_metadata(smoke_ref, 'test_result/evidence/codex_smoke/nov04_p108_p107_v2')
    if (smoke.get('complete') is not True or smoke.get('returncode') != 0
            or smoke.get('failed_calls') != 0 or smoke.get('source_pins_unchanged') is not True
            or smoke.get('original_synthetic_unchanged') is not True
            or len(smoke.get('receipts', [])) != 106):
        raise ValueError('full canonical smoke did not complete successfully')
    for name, digest in smoke['source_pins_after'].items():
        if name in value['source_pins'] and value['source_pins'][name] != digest:
            raise ValueError('product source changed after smoke')
    packet = load_document_input(ROOT, value['input_manifest'], allowed_root=INPUT_ROOT,
        tokenizer_sha256=manual.TOKENIZER_SHA, vocab_size=32768, allow_admitted=False)
    if packet.contract != value['input_contract'] or packet.contract['purpose'] != 'SYNTHETIC_TECHNICAL':
        raise ValueError('same synthetic input contract required')
    manifest = manual.verify_manifest()
    if manual.canonical_sha(manifest) != value['manual_manifest_sha256']:
        raise ValueError('manual model/source manifest differs')
    return value, packet, manifest


def make_session(model, packet, recipe, signature, *, optimizer_factory,
                 collect_ids, autocast_dtype):
    import numpy as np
    import torch
    from tinylm.train.adaptive_masking import PolicyConfig
    from tinylm.train.adaptive_training import AdaptiveMNTPTrainer
    from tinylm.train.hybrid_session import HybridTrainingSession
    torch.manual_seed(recipe['seed']); random.seed(recipe['seed']);np.random.seed(recipe['seed'])
    if next(model.parameters()).device.type == 'cuda':
        torch.cuda.manual_seed_all(recipe['seed'])
    source = packet.as_source(batch=recipe['batch'], length=recipe['length'],
        micros=recipe['micros'], vocab=recipe['vocab'], seed=recipe['seed'])
    policy = PolicyConfig(recipe['vocab'], recipe['mask_rate'], recipe['error_ema'],
        recipe['refresh_every'], recipe['masking_mode'], recipe['seed'],
        recipe['special_max'], recipe['mask_id'], source.corpus_sha256, signature)
    trainer = AdaptiveMNTPTrainer(model, optimizer_factory(model), source,
        policy_config=policy, mode=recipe['mode'], masked_micros=recipe['masked_micros'],
        signature=manual.canonical_sha(dict(input=packet.contract, source=source.contract,
                                           run=signature)), collect_ids=collect_ids,
        autocast_dtype=autocast_dtype, clip=recipe['clip'])
    return HybridTrainingSession(trainer, total_updates=recipe['horizon'],
        warmup_updates=recipe['warmup'], schedule=recipe['schedule'])


def state_hashes(state):
    from scripts.diag_p107_adaptive_training import tree_sha
    return {key:tree_sha(value) for key,value in state.items()}


def compare_resume(report, prior, profile_sha):
    if prior is None:
        return 'NO_PRIOR_COMPLETE_REFERENCE_NOT_A_COMPARISON_PASS'
    if prior.get('profile_sha256') != profile_sha:
        raise ValueError('prior command/profile differs')
    if prior.get('status') != 'COMPLETE' or prior.get('actual_exit') != 0:
        return 'PRIOR_INCOMPLETE_NOT_A_COMPARISON_PASS'
    keys = ('loss', 'masked_targets', 'causal_targets', 'schedule_lrs')
    same = report['final_state_hashes'] == prior['final_state_hashes']
    same &= {k:report['updates'][-1][k] for k in keys} == {k:prior['updates'][-1][k] for k in keys}
    if not same:
        raise ValueError('fresh-process CLI continuation is not exact')
    return 'EXACT'


def execute(value, packet, manifest, mode, profile_sha):
    import torch
    from scripts import diag_p107_adaptive_training as old
    from scripts.p106b_nvml_probe import watcher_class
    from tinylm.train.boundary_store import load_complete, save_new
    from scripts.diag_p107_hybrid_mntp import independent_final_checks, close_owned_cuda
    from scripts.diag_p102a_logit_margin import memory_point
    spec = manual.resolve_model(value['model'])
    entry = manifest['entries'][spec.name]
    output = manual.owned_path(OUTPUT)/mode
    if output.exists():
        raise FileExistsError('closed or partial CLI output must be preserved')
    snapshot = manual.owned_path(SNAPSHOT)
    if mode == 'run' and snapshot.exists():
        raise FileExistsError('old/partial snapshot must be preserved')
    output.mkdir(parents=True)
    report = dict(schema='P107_DOCUMENT_CLI_ACTUAL_V1', mode=mode, status='STARTED',
        tag=TAG, profile_sha256=profile_sha, source_pins=value['source_pins'],
        origin=entry['checkpoint'], origin_core_sha256=entry['core_sha256'],
        input_contract=packet.contract, recipe=value['recipe'], updates=[],
        corpus_training=False, quality_claim=False, original_checkpoint_writes=0,
        not_run=['ACTUAL_CLEANED_CORPUS','CORPUS_LANGUAGE_NUMBER_RARE_BIAS',
                 'FULL_TRAINING_QUALITY','75M_STREAMING','GRADSCALER_COMPILE'])
    started = time.perf_counter()
    model = payload = session = watch = None
    code = 9
    try:
        budget = old.resource.Budget(MAX_WALL, deadline=DEADLINE)
        with old.resource.wall(MAX_WALL):
            report['idle_before'] = manual.require_idle_gpu()
            report['memory_before'] = memory_point()
            if report['memory_before']['free_mib']*2**20 <= VRAM_INCREASE:
                raise old.ResourceHold('8GB free admission required')
            torch.cuda.set_per_process_memory_fraction(ALLOCATOR/torch.cuda.get_device_properties(0).total_memory)
            watch = watcher_class()(); watch.start()
            torch.set_num_threads(2)
            torch.backends.cuda.matmul.allow_tf32 = False;torch.backends.cudnn.allow_tf32 = False
            torch.use_deterministic_algorithms(True)
            torch_module, config_type, model_type, method = manual.inference_modules()
            if torch_module is not torch:
                raise ValueError('single verified torch runtime required')
            payload = manual.read_selected_payload(torch, spec, entry, ROOT)
            cfg = config_type(**payload['cfg']);manual.validate_cfg(cfg, entry['header'])
            model = model_type(cfg)
            with method.weight_route(model, spec.arm) as route:
                method.load_routed_state(model, payload, spec.arm)
                if manual.state_fingerprint(model) != entry['core_sha256']:
                    raise ValueError('original CPU core differs')
                payload = None
                model.to('cuda').train();model.clear_quant();model.set_anneal(1.)
                session = make_session(model, packet, value['recipe'], manual.canonical_sha(value['source_pins']),
                    optimizer_factory=old.optimizers,
                    collect_ids=lambda logits,targets:old.collect_ids(logits,targets,'full')[0],
                    autocast_dtype=torch.bfloat16)
                report['sampler_contract'] = session.trainer.source.contract
                from torch.nn.attention import sdpa_kernel, SDPBackend
                with sdpa_kernel(SDPBackend.MATH):
                    if mode == 'resume':
                        budget.check(); state = load_complete(snapshot)
                        session.load_state_dict(state);state = None
                        if session.cursor != 1:
                            raise ValueError('exact first-update boundary required')
                    else:
                        old.measured_update(session, budget, report['updates'])
                        budget.check()
                        if shutil.disk_usage(snapshot.parent).free < 2*2**30:
                            raise old.ResourceHold('2GiB disk reserve required for a new research boundary')
                        report['snapshot_manifest'] = save_new(session.state_dict(), snapshot)
                        budget.check()
                    old.measured_update(session, budget, report['updates'])
                    if session.cursor != 2:
                        raise ValueError('exact second logical boundary required')
                    report['final_state_hashes'] = state_hashes(session.state_dict())
                route.assert_active()
            report['completed_logical_cursor'] = 2
            report['physical_updates'] = len(report['updates'])
            report['executed_input_tokens'] = sum(r['executed_input_tokens'] for r in report['updates'])
            if mode == 'resume':
                prior_path = manual.owned_path(OUTPUT)/'run/report.json'
                prior = json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.is_file() else None
                report['fresh_process_resume_equivalence'] = compare_resume(report, prior, profile_sha)
            report['status'] = 'COMPLETE';code = 0
    except BaseException as exc:
        hold = isinstance(exc, (TimeoutError, old.ResourceHold))
        report.update(status='HOLD' if hold else 'ERROR', error=dict(type=type(exc).__name__, message=str(exc)))
        code = 8 if hold else 9
    finally:
        session = payload = None
        errors = []
        if watch is not None:
            try:
                report['vram_watch'] = watch.stop()
                if report['vram_watch'].get('reason') and report['status'] != 'ERROR':
                    code = 8;report['status'] = 'HOLD'
            except BaseException as exc:
                errors.append(dict(stage='watch_cleanup', message=str(exc)))
        if model is not None:
            for stage, action in (('zero_grad',lambda:model.zero_grad(set_to_none=True)),
                                  ('clear_quant',model.clear_quant),('model_to_cpu',lambda:model.to('cpu'))):
                try:action()
                except BaseException as exc:errors.append(dict(stage=stage, message=str(exc)))
        model = None;gc.collect()
        def unchanged_parent():
            if manual.file_sha(manual.owned_path(spec.checkpoint)) != entry['checkpoint']['sha256']:
                raise ValueError('original checkpoint file changed')
            report['original_checkpoint_unchanged'] = True
        def unchanged_inputs_sources():
            current, _, _ = validate(value['profile_path'], profile_sha, check_start_budget=False)
            if current != value:
                raise ValueError('profile/input/source changed')
            report['inputs_sources_unchanged'] = True
        good = independent_final_checks(report, [('cuda_cleanup',lambda:close_owned_cuda(torch,report)),
            ('original_checkpoint',unchanged_parent),('inputs_sources',unchanged_inputs_sources)])
        if not good or errors:
            code = 9;report['status'] = 'ERROR'
        report.update(cleanup_errors=errors, actual_exit=code, wall_seconds=time.perf_counter()-started,
            completed_optimizer_updates=sum(r.get('status') == 'COMPLETE' for r in report['updates']),
            incomplete_update_records=[r for r in report['updates'] if r.get('status') != 'COMPLETE'])
        old.resource.write_new(output/'report.json', report)
        print('[P107_CLI_FINAL] '+json.dumps(dict(mode=mode, status=report['status'], actual_exit=code,
            physical_updates=report.get('physical_updates'), wall_seconds=report['wall_seconds'],
            exact_resume=report.get('fresh_process_resume_equivalence'), report=str(output/'report.json'))),flush=True)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--profile-sha256', required=True)
    parser.add_argument('--mode', choices=('run','resume'), required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true')
    action.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    value, packet, manifest = validate(args.profile, args.profile_sha256)
    if value.get('profile_path') != args.profile:
        raise ValueError('profile path binding differs')
    if args.check_only:
        print(json.dumps(dict(status='METADATA_AND_INPUT_BYTES_VALIDATED', mode=args.mode,
            input_contract=packet.contract, model_loads=0, gpu_runs=0,
            corpus_training=False, full_training_cli_complete=False)))
        return 0
    return execute(value, packet, manifest, args.mode, args.profile_sha256)


if __name__ == '__main__':
    raise SystemExit(main())
