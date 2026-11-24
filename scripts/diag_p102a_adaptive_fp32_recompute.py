"""Compare the full and recomputed P107 heads in actual adaptive training."""

import argparse
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
from statistics import median
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p102a_g4_recompute_operating as prior
from scripts import diag_p107_native_scaled_training as p107
from scripts import diag_p109_warm_visit_routes as warm
from scripts import p102a_fp32_target_head as target_head
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.p108_weight_space import tensor_sha


ROOT = p107.training.ROOT
TAG = 'p102a_adaptive_fp32_recompute_v1_20261119'
OUT = p107.OUT.with_name(TAG)
ARMS = ('reference', 'recompute')
BATCH, WIDTH, MICROS, UPDATES, VOCAB, ROWS = 8, 512, 4, 6, 32768, 512
PARENT_SHA = 'D576B9EB6DEF02DF5DCCAD91E484098AFB67A52553A7A735B21249DB2D9EC3D5'
SOURCES = (*p107.SOURCES, 'tinylm/model/visibility.py', 'tinylm/train/recomputed_ce.py',
           'scripts/diag_p102a_adaptive_fp32_recompute.py', 'scripts/p102a_fp32_target_head.py',
           'scripts/diag_p109_warm_visit_routes.py', str(prior.BASE.PLAN.relative_to(ROOT)))
READ, WRITE, SHA = json.loads, p107.training.write, p107.training.digest


def inputs():
    def generate(count, seed):
        rng = torch.Generator().manual_seed(seed)
        base = torch.randint(0, 256, (count, WIDTH + 1), generator=rng)
        linked = (base * 29 + 17) % 256 + 256
        return torch.stack((base, linked), dim=2).reshape(count, -1)[:, :2 * WIDTH + 1] + 35

    return generate(256, 58021), generate(8, 58022)


def make_source(documents):
    from tinylm.train.document_source import ExplicitDocumentSource

    return ExplicitDocumentSource(list(documents), [f'doc-{i}' for i in range(len(documents))],
                                  batch=BATCH, length=WIDTH, micros=MICROS, vocab=VOCAB, seed=1337)


def expected():
    from tinylm.train.hybrid_mntp import causal_batch

    train, val = inputs()
    source = make_source(train)
    updates = []
    for _ in range(UPDATES):
        pack = source.next_update()
        updates.append(dict(causal=sum(causal_batch(x, d, vocab_size=VOCAB).target_count
                                       for x, d in pack[:MICROS // 2]),
                            source_rng=tensor_sha(source.rng.get_state()),
                            micro=[tensor_sha(torch.stack((x, d))) for x, d in pack]))
    pins = {name: SHA(ROOT / name) for name in SOURCES}
    if SHA(warm.PARENT) != PARENT_SHA:
        raise ValueError('expected P079 G4 checkpoint changed')
    return dict(tag=TAG, pins=pins, parent=PARENT_SHA, corpus=source.contract, updates=updates,
                val_sha256=tensor_sha(val), approval='WIP176', rows=ROWS)


def cpu_gate():
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.hybrid_mntp import objective_mean

    torch.manual_seed(5220)
    cfg = TMTConfig(vocab_size=137, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=16,
                    n_q_heads=4, n_kv_heads=2, n_prelude=1, n_middle=2, n_coda=1,
                    tie_mlp=True, mlp_group=2, micro_group=8)
    model = TiedMLPTransformer(cfg)
    h = torch.randn(2, 8, 32, requires_grad=True)
    targets = torch.randint(0, cfg.vocab_size, (2, 8))
    targets[:, :3] = -100
    heads = (h, model.emb.weight, model.emb_up.weight)
    result = {}
    for mode in ('fp32', 'bf16'):
        autocast = torch.autocast('cpu', dtype=torch.bfloat16) if mode == 'bf16' else nullcontext()
        with autocast:
            logits = model._head_logits(h)
            reference, count = objective_mean(logits, targets)
            compact, observed, ids = target_head.objective(model, h, targets, rows=4)
            left = torch.autograd.grad(reference * 32., heads)
            right = torch.autograd.grad(compact * 32., heads)
        agree = bool(torch.equal(logits.argmax(-1), ids))
        torch.testing.assert_close(compact, reference, rtol=0, atol=2e-6)
        for a, b in zip(left, right, strict=True):
            torch.testing.assert_close(a, b, rtol=1e-5, atol=1e-6)
        assert observed == count and agree and not ids.requires_grad
        result[mode] = dict(targets=count, loss=[float(reference), float(compact)], ids_equal=agree,
                            gradient_max_abs=[float((a - b).abs().max()) for a, b in zip(left, right)])
    zero = torch.zeros_like(h)
    _, _, winners = target_head.objective(model, zero, targets, rows=4)
    assert bool(winners.eq(0).all())
    return result


@dataclass
class HeadInput:
    hidden: torch.Tensor
    predictions: torch.Tensor | None = None

    def detach(self):
        if self.predictions is None:
            raise RuntimeError('masked item must have its computed prediction IDs')
        return self.predictions.detach()


def worker(arm, frozen):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.p107_active_optimizer_groups import keep_active_groups
    from scripts.p107_scaled_optimizer_group import ScaleConfig, ScaledOptimizerGroup
    from tinylm.model import TiedMLPTransformer
    from tinylm.train import adaptive_training as adaptive
    from tinylm.train.adaptive_masking import PolicyConfig
    from tinylm.train.experimental_optimizers import build_experimental_optimizers
    from tinylm.train.hybrid_session import HybridTrainingSession

    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 12 * (1 << 30):
        raise RuntimeError('isolated CUDA device with 12 GiB free required')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.manual_seed(1337)
    random.seed(1337)
    np.random.seed(1337)
    cfg, parent, parent_step = warm.load_parent(torch)
    cfg.train_repeat = 1.0
    model = TiedMLPTransformer(cfg).cuda().train()
    model.load_state_dict(parent, strict=True)
    del parent
    model.set_anneal(1.)
    initial = state_sha(model.state_dict())
    route = build_experimental_optimizers(model, 'muon_matched', lr=6e-4, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    keep_active_groups(optimizers)
    source = make_source(inputs()[0])
    signature = SHA(OUT / 'profile.json')
    cfg_policy = PolicyConfig(VOCAB, .15, .2, 2, 'keep', 1337, 34, 13, source.corpus_sha256, signature)

    def scaler():
        return ScaledOptimizerGroup([p for p in model.parameters() if p.requires_grad], optimizers,
            run_signature=signature, expected_backwards=MICROS, config=ScaleConfig(init_scale=128., growth_interval=2))

    def ids_for(loss_output, _):
        return (loss_output if arm == 'recompute' else loss_output.argmax(-1)).cpu()

    trainer = adaptive.AdaptiveMNTPTrainer(model, optimizers, source, policy_config=cfg_policy,
        mode='adaptive', masked_micros=MICROS // 2, signature=signature,
        collect_ids=ids_for, autocast_dtype=torch.bfloat16, scaled_group_factory=scaler,
        overflow_policy=adaptive.CONSUME_SCALED_GROUP)
    session = HybridTrainingSession(trainer, total_updates=UPDATES, warmup_updates=1, schedule='cosine')
    monitor = trainer.policy.observe
    observations = []
    head_count = 0

    def observe(batch, ids, *, observation_index):
        selected = batch.targets.ne(-100)
        observations.append(dict(mask=tensor_sha(batch.selected_positions), ids=tensor_sha(ids),
                                 supervised_ids=tensor_sha(ids[selected]), targets=tensor_sha(batch.targets)))
        return monitor(batch, ids, observation_index=observation_index)

    def native_inputs(hidden):
        return HeadInput(hidden)

    def compact(out, targets):
        nonlocal head_count
        if not isinstance(out, HeadInput):
            raise ValueError('only authenticated native head inputs are accepted during the probe')
        want_ids = head_count % MICROS >= MICROS // 2  # Same causal-then-masked order as the trainer.
        loss, count, out.predictions = target_head.objective(model, out.hidden, targets,
                                                             rows=ROWS, collect_ids=want_ids)
        head_count += 1
        return loss, count

    source_update = source.next_update

    def checked_source():
        index = source.cursor
        pack = source_update()
        assert [tensor_sha(torch.stack((x, d))) for x, d in pack] == frozen['updates'][index]['micro']
        return pack

    traces, peaks = [], []
    head = patch.object(model, '_head_logits', native_inputs) if arm == 'recompute' else nullcontext()
    loss = patch.object(adaptive, 'objective_mean', compact) if arm == 'recompute' else nullcontext()
    with (head, loss, patch.object(trainer.policy, 'observe', observe),
          patch.object(source, 'next_update', checked_source), sdpa_kernel(SDPBackend.MATH)):
        for index, proof in enumerate(frozen['updates']):
            torch.cuda.reset_peak_memory_stats()
            row = session.update()
            assert row['update'] == index and row['causal_targets'] == proof['causal']
            assert tensor_sha(source.rng.get_state()) == proof['source_rng'] and row['optimizer_applied']
            assert row['masked_targets'] > 0 and row['model_forwards'] == MICROS
            traces.append(row)
            peaks.append((torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()))
            print('P102A_ADAPTIVE_TARGET_UPDATE', arm, index, row['masked_targets'], flush=True)
    assert len(observations) == UPDATES * (MICROS // 2) and head_count == (UPDATES * MICROS if arm == 'recompute' else 0)
    state = trainer.state_dict()
    parts = ('model', 'optimizers', 'policy', 'source', 'uniform_rng', 'rng', 'scaled_optimizer_group')
    pins = {name: state_sha(state[name]) for name in parts}
    after = dict(arm=arm, initial=initial, states=pins, parent_step=parent_step,
        observations=observations, updates=traces, peak_allocated=max(p[0] for p in peaks),
        peak_reserved=max(p[1] for p in peaks), elapsed_after_first=median(r['seconds'] for r in traces[1:]),
        gpu_checkpoint_writes=0)
    WRITE(OUT / f'{arm}.json', after)
    return 0


def run(frozen):
    idle = prior.previous.shapes.idle
    exits, rows = {}, {}
    for arm in ARMS:
        if not idle() or (OUT / 'STOP').exists():
            exits[arm] = None
            break
        call = ['timeout', '--kill-after=5s', '90s', sys.executable, '-u', '-B', '-X', 'utf8', '-m',
                'scripts.diag_p102a_adaptive_fp32_recompute', 'worker', arm]
        exits[arm] = subprocess.run(call, cwd=ROOT).returncode
        print('P102A_ADAPTIVE_TARGET_EXIT', arm, exits[arm], flush=True)
        if exits[arm] == 0:
            rows[arm] = READ((OUT / f'{arm}.json').read_bytes())
    assert idle() and frozen['contract'] == expected()
    comparison = {}
    if set(rows) == set(ARMS):
        ref, got = (rows[arm] for arm in ARMS)
        comparison = dict(same_initial=ref['initial'] == got['initial'],
            same_observations=ref['observations'] == got['observations'],
            same_final_components={field: value == got['states'][field] for field, value in ref['states'].items()},
            same_losses=all(a['loss'] == b['loss'] for a, b in zip(ref['updates'], got['updates'], strict=True)),
            same_targets=[r['masked_targets'] for r in ref['updates']] == [r['masked_targets'] for r in got['updates']])
    WRITE(OUT / 'report.json', dict(exits=exits, comparison=comparison, arms=rows, gpu_returned=True))
    print('P102A_ADAPTIVE_TARGET_COMPLETE', comparison, flush=True)
    return 0 if comparison and all((all(value.values()) if isinstance(value, dict) else value)
                                   for value in comparison.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run', 'worker'))
    parser.add_argument('arm', nargs='?', choices=ARMS)
    args = parser.parse_args()
    if (args.mode == 'worker') != (args.arm is not None):
        parser.error('arm is only required for a worker')
    assert datetime.now(warm.CUTOFF.tzinfo) + timedelta(minutes=5) < warm.CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.mode == 'prepare' else '0')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile = OUT / 'profile.json'
    if args.mode == 'prepare':
        record = dict(contract=expected(), cpu=cpu_gate())
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        WRITE(profile, record)
        print('P102A_ADAPTIVE_TARGET_CPU_READY', record['cpu'], flush=True)
        return 0
    frozen = READ(profile.read_bytes())
    assert frozen['contract'] == expected() and os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    return run(frozen) if args.mode == 'run' else worker(args.arm, frozen['contract'])


if __name__ == '__main__':
    sys.exit(main())
