#!/usr/bin/env python3
"""고정 native 복사본의 적응 통계·optimizer 연결 비용/메모리 재개. 자연어 품질 시험0."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_resource_matrix as resource
from scripts.diag_p107_adaptive_gpu_transfer import collect_ids
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer, SyntheticDocumentStream

DEADLINE = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
SCHEMA = "P107_ACTUAL_OPTIMIZER_MASK_LINK_V1"
TAG = "p107_actual_train_link_v1_20261101"
LIMIT = 8_000_000_000
ALLOCATOR_CAP = 6 * 2**30
OWN = ("tinylm/train/adaptive_training.py", "scripts/test_p107_adaptive_training.py",
       "scripts/diag_p107_adaptive_training.py", "tinylm/train/adaptive_masking.py",
       "scripts/test_p107_training_driver.py", "scripts/diag_p107_hybrid_mntp.py",
       "scripts/diag_p102a_logit_margin.py", "scripts/interactive_research_infer.py",
       "tinylm/train/hybrid_mntp.py", "scripts/diag_p107_adaptive_gpu_transfer.py",
       "scripts/diag_p107_adaptive_masking.py", "tinylm/train/muon.py",
       "tinylm/train/optimizer_audit.py")
ORDER = ("uniform", "observe", "adaptive", "adaptive", "observe", "uniform")
need = resource.need


class ResourceHold(RuntimeError):
    pass


class VramWatch:
    """자기 프로세스만 중단한다. 공유 GPU 전체의 시작값 대비 증가를 보수적으로 감시한다."""
    def __init__(self):
        self.stop_event = threading.Event()
        self.proof = dict(samples=0, query_errors=0, maximum_additional_bytes=0)
        self.reason = None

    @staticmethod
    def used():
        raw = subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi',
            '--query-gpu=memory.used', '--format=csv,noheader,nounits'], text=True, timeout=3)
        values = raw.splitlines()
        need(len(values) == 1, 'single GPU required')
        return int(values[0]) * 2**20

    def start(self):
        self.proof['baseline_used_bytes'] = self.used()
        self.previous = signal.getsignal(signal.SIGTERM)
        def interrupted(*_):
            raise ResourceHold(self.reason or 'owned worker received termination')
        signal.signal(signal.SIGTERM, interrupted)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        consecutive = 0
        while not self.stop_event.wait(.5):
            try:
                current = self.used()
                additional = max(0, current-self.proof['baseline_used_bytes'])
                self.proof['samples'] += 1
                self.proof['maximum_additional_bytes'] = max(additional,self.proof['maximum_additional_bytes'])
                consecutive = 0
                if additional > LIMIT:
                    self.reason = 'shared GPU increase exceeded owned 8GB budget'
            except Exception as exc:
                consecutive += 1;self.proof['query_errors'] += 1
                if consecutive >= 3:self.reason = 'VRAM telemetry unavailable after 3 bounded queries: '+str(exc)
            if self.reason:
                os.kill(os.getpid(), signal.SIGTERM)
                return

    def stop(self):
        self.stop_event.set();self.thread.join(timeout=5)
        signal.signal(signal.SIGTERM,self.previous)
        self.proof.update(reason=self.reason, thread_stopped=not self.thread.is_alive(),
                         scope='SAMPLED_SHARED_GPU_INCREASE_NOT_EXACT_PER_PROCESS_PEAK')
        return self.proof


def identity():
    files = dict(resource.identity()["files"])
    files.update({name: resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def tree_sha(value):
    import torch
    digest = hashlib.sha256()
    def visit(item):
        if isinstance(item, torch.Tensor):
            digest.update(str((item.dtype, tuple(item.shape))).encode())
            digest.update(item.detach().cpu().contiguous().numpy().tobytes())
        elif isinstance(item, dict):
            for key in sorted(item, key=repr):
                digest.update(repr(key).encode()); visit(item[key])
        elif isinstance(item, (tuple, list)):
            digest.update(type(item).__name__.encode())
            for x in item: visit(x)
        else:
            digest.update(repr(item).encode())
    visit(value)
    return digest.hexdigest().upper()


def optimizers(model):
    import torch
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.optimizer_audit import matrix_decay_groups
    groups, _ = matrix_decay_groups(model, 1e-4, None)
    matrices, _ = split_params(model)
    ids = {id(p) for p in matrices}
    others = [dict(g, params=[p for p in g['params'] if id(p) not in ids]) for g in groups]
    others = [g for g in others if g['params']]
    return [torch.optim.AdamW(others, betas=(.9, .95), eps=1e-8),
            Muon(matrices, lr=4e-4, scale_mode='rms', weight_decay=0.)]


def engine(model, mode, profile):
    import torch
    import random
    import numpy as np
    torch.manual_seed(1337); torch.cuda.manual_seed_all(1337)
    random.seed(1337); np.random.seed(1337)
    source = SyntheticDocumentStream(batch=8, length=1024, micros=16, vocab=32768, seed=20261101)
    config = PolicyConfig(32768, .15, .2, 2, 'keep', 1337, 34, 13,
                          resource.sha(source.state_dict()['signature']), profile['source_sha256'])
    return AdaptiveMNTPTrainer(model, optimizers(model), source, policy_config=config,
        mode=mode, masked_micros=8, signature=resource.sha(dict(mode=mode, source=profile['source_sha256'])),
        collect_ids=lambda logits, targets: collect_ids(logits, targets, 'full')[0],
        autocast_dtype=torch.bfloat16, clip=1.)


def measured_update(trainer, budget, progress):
    import torch
    budget.check()
    record = dict(update=trainer.cursor,status='STARTED')
    progress.append(record)
    torch.cuda.reset_peak_memory_stats()
    try:
        row = trainer.update()
    except BaseException as exc:
        record.update(status='ERROR',error_type=type(exc).__name__,
                      completed_cursor=trainer.cursor,requires_full_restore=trainer.dirty)
        raise
    record.update(row)
    row.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(),
               peak_reserved_bytes=torch.cuda.max_memory_reserved())
    record.update(row)
    need(row['peak_reserved_bytes'] <= ALLOCATOR_CAP, 'allocator cap exceeded')
    need(row['executed_input_tokens'] == 8 * 1024 * 16 and row['model_forwards'] == 16,
         'complete 16-micro update required')
    budget.check()
    return row


def cost(model, initial, profile, budget, report):
    import torch
    states = {}
    report['blocks'] = []
    for index, mode in enumerate(ORDER):
        model.clear_quant(); model.load_state_dict(initial, strict=True); model.train()
        trainer = engine(model, mode, profile)
        block = dict(index=index, mode=mode, attempts=[])
        report['blocks'].append(block)
        for _ in range(4):
            measured_update(trainer, budget, block['attempts'])
        snapshot = trainer.state_dict()
        value = dict(model=tree_sha(snapshot['model']), optimizers=tree_sha(snapshot['optimizers']),
                     source=tree_sha(snapshot['source']), masks=[r['masked_targets'] for r in block['attempts']],
                     losses=[r['loss'] for r in block['attempts']])
        block['final_equivalence'] = value
        states.setdefault(mode, []).append(value)
        block['median_seconds'] = statistics.median(r['seconds'] for r in block['attempts'][1:])
        block['weights_changed_types'] = int((trainer.policy.weights != 1).sum()) if trainer.policy else 0
        print(json.dumps(dict(block=index, mode=mode, median_seconds=block['median_seconds'],
                              peak_reserved_bytes=max(r['peak_reserved_bytes'] for r in block['attempts']))), flush=True)
        snapshot = trainer = None
        model.zero_grad(set_to_none=True); model.clear_quant(); gc.collect(); torch.cuda.empty_cache()
    need(states['uniform'][0] == states['uniform'][1] == states['observe'][0] == states['observe'][1],
         'observer-only must preserve exact mask/loss/model/optimizer updates')
    need(states['adaptive'][0] == states['adaptive'][1], 'repeated adaptive trajectory differs')
    report['observer_equivalence'] = 'EXACT'
    report['summary'] = {mode:dict(median_seconds=statistics.median(r['seconds']
        for block in report['blocks'] if block['mode'] == mode for r in block['attempts'][1:]),
        measured_updates=6, warm_updates=2) for mode in set(ORDER)}
    report['physical_optimizer_updates'] = 24


def resume(model, initial, profile, budget, report):
    import torch
    model.clear_quant(); model.load_state_dict(initial, strict=True); model.train()
    trainer = engine(model, 'adaptive', profile)
    report['prefix'] = []
    for _ in range(2): measured_update(trainer, budget, report['prefix'])
    at = time.perf_counter(); snapshot = trainer.state_dict()
    stream = io.BytesIO(); torch.save(snapshot, stream)
    report['serialized_checkpoint_bytes'] = stream.tell()
    report['checkpoint_to_memory_seconds'] = time.perf_counter() - at
    snapshot = None
    report['continued'] = []
    for _ in range(2): measured_update(trainer, budget, report['continued'])
    end = trainer.state_dict()
    keys = ('model', 'optimizers', 'policy', 'source', 'rng')
    expected = {key:tree_sha(end[key]) for key in keys}
    end = None
    at = time.perf_counter(); stream.seek(0)
    restored = torch.load(stream, map_location='cpu', weights_only=True)
    trainer.load_state_dict(restored)
    report['restore_from_memory_seconds'] = time.perf_counter() - at
    restored = stream = None
    gc.collect(); torch.cuda.empty_cache()
    report['resumed'] = []
    for _ in range(2): measured_update(trainer, budget, report['resumed'])
    actual = trainer.state_dict()
    report['expected_hashes'] = expected
    report['actual_hashes'] = {key:tree_sha(actual[key]) for key in keys}
    need(report['actual_hashes'] == expected, 'full training boundary resume differs')
    need([(r['loss'],r['masked_targets']) for r in report['continued']] ==
         [(r['loss'],r['masked_targets']) for r in report['resumed']], 'resumed losses/selection differ')
    report.update(resume_equivalence='EXACT', physical_optimizer_updates=6, checkpoint_writes=0)
    actual = trainer = None
    model.zero_grad(set_to_none=True); model.clear_quant(); gc.collect(); torch.cuda.empty_cache()


def validate(args):
    profile = resource.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    need(profile.get('schema') == SCHEMA and profile.get('tag') == TAG
         and profile.get('source_sha256') == identity()['sha256']
         and profile.get('authority_directive') == 104 and profile.get('deadline') == DEADLINE.isoformat()
         and profile.get('vram_limit_bytes') == LIMIT and profile.get('allocator_cap_bytes') == ALLOCATOR_CAP
         and profile.get('corpus_training') is False, 'current sealed technical profile required')
    need(60 <= args.max_wall_sec <= 900, 'worker must be bounded <=900sec')
    need((DEADLINE-datetime.now(timezone.utc)).total_seconds() > args.max_wall_sec+120,
         'deadline reserve insufficient; do not start')
    cpu = resource.read_ref(profile['cpu_contract'])
    need(cpu['actual_exit'] == 0 and cpu['source_sha256'] == profile['source_sha256'], 'CPU contract/source differ')
    need(resource.digest(resource.safe(cpu['log']['path'])) == cpu['log']['sha256'], 'CPU raw evidence changed')
    native = resource.read_ref(profile['native_reference'])
    spec = next(x for x in native['models'] if x['id'] == 'native595-q')
    need(spec['route'] == 'ternary' and spec['cfg']['grad_checkpoint'] is True
         and spec['cfg']['vocab_size'] == 32768, 'same native route required')
    return profile, native, spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--profile-sha256', required=True)
    parser.add_argument('--mode', choices=('cost','resume'), required=True)
    parser.add_argument('--max-wall-sec', type=int, default=900)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true')
    action.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    profile, native, spec = validate(args)
    if args.check_only:
        print('PREFLIGHT metadata-only; model/GPU/optimizer/checkpoint writes=0')
        return 0
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts.p106b_weight_route import weight_route, load_routed_state
    from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
    from scripts.diag_p102a_logit_margin import memory_point
    output = resource.safe(profile['output']) / args.mode
    need(not output.exists(), 'fresh output required')
    output.mkdir(parents=True)
    report = dict(schema=SCHEMA, mode=args.mode, status='STARTED', source=identity(),
                  quality_claim=False, corpus_training=False, checkpoint_writes=0,
                  vram_limit_bytes=LIMIT, allocator_cap_bytes=ALLOCATOR_CAP,
                  not_measured=['CORPUS_BIAS','FULL_TRAINING_QUALITY','PRODUCTION_LOADER_CLI',
                                'SCHEDULER_GRADSCALER_COMPILE','CAUSAL_KD','POWER_LOSS_DISK_RESUME'])
    model = payload = initial = watch = None
    exitcode = 9
    original_sha = resource.digest(resource.safe(spec['checkpoint']['path']))
    need(original_sha == spec['checkpoint']['sha256'], 'parent file changed')
    try:
        budget = resource.Budget(args.max_wall_sec, deadline=DEADLINE)
        with resource.wall(args.max_wall_sec):
            report['idle_before'] = require_idle_gpu()
            report['memory_before'] = memory_point()
            need(report['memory_before']['free_mib'] * 2**20 > LIMIT, '8GB free admission required')
            total = torch.cuda.get_device_properties(0).total_memory
            torch.cuda.set_per_process_memory_fraction(ALLOCATOR_CAP / total)
            watch = VramWatch();watch.start()
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.use_deterministic_algorithms(True)
            payload = torch.load(resource.safe(spec['checkpoint']['path']), map_location='cpu', weights_only=True)
            need(resource.sha(payload['cfg']) == resource.sha(spec['cfg']) and payload['step'] == spec['updates'], 'parent cfg/step differs')
            model = TiedMLPTransformer(TMTConfig(**payload['cfg']))
            with weight_route(model, 'ternary') as route:
                load_routed_state(model, payload, 'ternary')
                need(state_fingerprint(model) == spec['core_sha256'], 'initial model differs')
                initial = payload['model']; payload = None
                model.to('cuda').train(); model.clear_quant(); model.set_anneal(1.)
                report['trainable_parameters'] = sum(p.numel() for p in model.parameters() if p.requires_grad)
                from torch.nn.attention import sdpa_kernel, SDPBackend
                with sdpa_kernel(SDPBackend.MATH):
                    if args.mode == 'cost':cost(model, initial, profile, budget, report)
                    else:resume(model, initial, profile, budget, report)
                route.assert_active()
            report['status'] = 'COMPLETE';exitcode = 0
    except BaseException as exc:
        hold = isinstance(exc,(TimeoutError,ResourceHold))
        report.update(status='HOLD' if hold else 'ERROR',
                      error=dict(type=type(exc).__name__,message=str(exc)))
        exitcode = 8 if hold else 9
    finally:
        from scripts.diag_p107_hybrid_mntp import independent_final_checks, close_owned_cuda
        if watch is not None:
            report['vram_watch'] = watch.stop()
            if report['vram_watch']['reason']:
                report['status']='HOLD';exitcode=8
            if not report['vram_watch']['thread_stopped']:
                report['status']='ERROR';exitcode=9
        errors = []
        if model is not None:
            for name, action in (('zero_grad',lambda:model.zero_grad(set_to_none=True)),
                                 ('clear_quant',model.clear_quant),('release_model',lambda:model.to('cpu'))):
                try:action()
                except BaseException as exc:errors.append(dict(stage=name,error=str(exc)))
        model = payload = initial = None
        gc.collect()
        def verify_parent():
            report['parent_unchanged'] = resource.digest(resource.safe(spec['checkpoint']['path'])) == original_sha
            need(report['parent_unchanged'],'original checkpoint changed')
        def verify_source():
            report['source_unchanged'] = report['source'] == identity()
            need(report['source_unchanged'],'execution source changed')
        good = independent_final_checks(report,[('cuda_cleanup',lambda:close_owned_cuda(torch,report)),
                                              ('parent',verify_parent),('source',verify_source)])
        report['model_release_errors'] = errors
        if not good or errors:
            report['status']='ERROR';exitcode=9
        attempts = ([r for block in report.get('blocks',[]) for r in block['attempts']]
                    + report.get('prefix',[]) + report.get('continued',[]) + report.get('resumed',[]))
        report['completed_optimizer_updates'] = sum(r['status']=='COMPLETE' for r in attempts)
        report['unfinished_update_records'] = [r for r in attempts if r['status']!='COMPLETE']
        report['final_exit'] = exitcode
        resource.write_new(output/'report.json',report)
        print(json.dumps(dict(status=report['status'],exitcode=exitcode,report=str(output/'report.json'))),flush=True)
    return exitcode


if __name__=='__main__':
    raise SystemExit(main())
