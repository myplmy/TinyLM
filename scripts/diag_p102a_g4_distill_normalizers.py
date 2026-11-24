"""Measure same-objective ALM and ACTD normalization in actual G4 training."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timedelta
from functools import partial
import json
import os
from statistics import median
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_warm_visit_routes as warm
from scripts import p102a_distill_normalizers as compact
from scripts import p106b_actd_consumer as actd
from scripts import p106b_alm_logtail as stable
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.p107_active_optimizer_groups import keep_active_groups
from scripts.p107_scaled_optimizer_group import ScaleConfig, ScaledOptimizerGroup
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train import alm
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.experimental_optimizers import build_experimental_optimizers


ROOT = warm.io.ROOT
TAG = 'p102a_g4_distill_row_recompute_v1_20261119'
OUT = warm.OUT.with_name(TAG)
OBJECTIVES = ('alm', 'actd')
ARMS = tuple(f'{objective}_{mode}' for objective in OBJECTIVES for mode in ('reference', 'recompute'))
BATCH, WIDTH, PREFIX, MICROS, UPDATES, VOCAB = 4, 256, 32, 2, 3, 32768
HEAD_ROWS, NORM_ROWS, CAP = 64, 8, 70
WEIGHT, LR = .3, 6e-4
PARENT_SHA = 'D576B9EB6DEF02DF5DCCAD91E484098AFB67A52553A7A735B21249DB2D9EC3D5'
READ, WRITE, SHA = json.loads, warm.io.write, warm.io.digest
SOURCES = (*warm.SOURCES, 'scripts/diag_p102a_g4_distill_normalizers.py',
           'scripts/p102a_distill_normalizers.py', 'scripts/p106b_actd_consumer.py',
           'scripts/p106b_actd_anchor.py', 'scripts/p106b_alm_logtail.py', 'tinylm/train/alm.py',
           'scripts/p107_active_optimizer_groups.py', 'scripts/p107_scaled_optimizer_group.py',
           'tinylm/train/experimental_optimizers.py', 'tinylm/train/muon.py', 'tinylm/train/anneal_schedule.py')


def make_pool():
    return torch.randint(8, VOCAB, (128, WIDTH + 1), generator=torch.Generator().manual_seed(79713))


def batch_info(raw, prefix, vocab, objective):
    x, labels = raw[:, :-1].contiguous(), raw[:, 1:].contiguous().clone()
    labels[:, :prefix] = alm.IGNORE
    owners = labels.ne(alm.IGNORE).long()
    selected = []
    for row, ids in enumerate(labels.tolist()):
        if objective == 'alm':
            for position in range(prefix, labels.shape[1] - 3, 32):
                selected.append(dict(row=row, positions=list(range(position, position + 4)),
                                     teacher_logprob=-12.0 - row / 8 - position / 32))
        else:
            for position in range(prefix, labels.shape[1], 4):
                target = ids[position]
                anchors = [target, target] + [8 + (target - 8 + offset) % (vocab - 8)
                                              for offset in range(1, 127)]
                selected.append(dict(batch_row=row, student_prefix_raw_index=position,
                                     student_target_raw_index=position + 1, student_target_id=target,
                                     owner=1, distribution=dict(accepted=True, anchor_ids=anchors,
                                                                 native_logits=[-k / 16 for k in range(128)])))
    return x, labels, owners, selected


def batches(pool, objective):
    return [[batch_info(block, PREFIX, VOCAB, objective) for block in group]
            for group in pool[:UPDATES * MICROS * BATCH].reshape(UPDATES, MICROS, BATCH, WIDTH + 1)]


def expected():
    pool = make_pool()
    if SHA(warm.PARENT) != PARENT_SHA:
        raise ValueError('expected P079 checkpoint changed')
    inputs = UPDATES * MICROS * BATCH * WIDTH
    assert pool.numel() >= 2 * inputs and len(pool.unique(dim=0)) == len(pool)
    return dict(tag=TAG, parent_sha256=PARENT_SHA, sources={name: SHA(ROOT / name) for name in SOURCES},
                pool_tokens=pool.numel(), pool_sha256=state_sha(pool), input_positions=inputs,
                fixtures={objective: state_sha(batches(pool, objective)) for objective in OBJECTIVES},
                batch=BATCH, width=WIDTH, micros=MICROS, updates=UPDATES, head_rows=HEAD_ROWS,
                recompute_rows=NORM_ROWS, kd_weight=WEIGHT, lr=LR, gpu_worker_cap=CAP,
                approval='WIP176', checkpoint_writes=0)


def use_normalizer(objective, recompute, rows):
    if not recompute:
        return nullcontext()
    if objective == 'alm':
        return patch.object(stable, 'log_nll_from_logits', partial(compact.log_nll_from_logits, rows=rows))
    return patch.object(actd, 'actd_sums', partial(compact.actd_components, rows=rows))


def loss_terms(model, hidden, y, owners, selected, objective, ce_denominator, kd_denominator):
    if objective == 'alm':
        nll, log_nll, valid = stable.target_dual(model, hidden, y, chunk=HEAD_ROWS)
        main = nll.sum()
        aux, count, stats = stable.chunk_kl(nll, log_nll, valid, selected)
        loss = alm.normalized_loss(main, ce_denominator, aux, kd_denominator, weight=WEIGHT)
        return loss, dict(ce=main, kd=aux, ce_targets=int(valid.sum()), kd_targets=count, **stats)
    terms = actd.components(model, hidden, y, owners, selected, ce_denominator=ce_denominator,
                           actd_denominator=kd_denominator, enable_actd=True, chunk=HEAD_ROWS)
    ce, anchor, residual = (terms[k] for k in ('ce_sum', 'anchor_sum', 'residual_sum'))
    return ce / ce_denominator + WEIGHT * (anchor + residual) / kd_denominator, dict(
        ce=ce, anchor=anchor, residual=residual, ce_targets=terms['ce_targets'], kd_targets=terms['actd_positions'])


def numeric_terms(values):
    return {name: float(value.detach()) if isinstance(value, torch.Tensor) else value
            for name, value in values.items()}


def compare_boundary(reference, candidate, operand, upstream):
    with torch.no_grad():
        for left, right in zip(reference, candidate, strict=True):
            torch.testing.assert_close(left, right, rtol=0, atol=0)
    left = torch.autograd.grad(reference, operand, upstream)[0]
    right = torch.autograd.grad(candidate, operand, upstream)[0]
    torch.testing.assert_close(left, right, rtol=0, atol=0)


def cpu_gate():
    torch.manual_seed(924)
    cfg = TMTConfig(vocab_size=137, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=16,
                    n_q_heads=4, n_kv_heads=2, n_prelude=1, n_middle=2, n_coda=1,
                    tie_mlp=True, mlp_group=2, micro_group=8)
    model = TiedMLPTransformer(cfg)
    hidden = torch.randn(2, 16, 32, requires_grad=True)
    raw = torch.randint(8, cfg.vocab_size, (2, 17))
    tensors = (hidden, model.emb.weight, model.emb_up.weight)
    checks = {}
    for objective in OBJECTIVES:
        _, y, owners, selected = batch_info(raw, 4, cfg.vocab_size, objective)
        for mode in ('fp32', 'bf16'):
            answers = []
            for variant in (False, True):
                precision = torch.autocast('cpu', dtype=torch.bfloat16) if mode == 'bf16' else nullcontext()
                with use_normalizer(objective, variant, 2), precision:
                    loss, terms = loss_terms(model, hidden, y, owners, selected, objective, 24, len(selected))
                    gradients = torch.autograd.grad(loss * 128, tensors)
                answers.append((float(loss.detach()), numeric_terms(terms), gradients))
            ref, got = answers
            assert ref[:2] == got[:2]
            for left, right in zip(ref[2], got[2], strict=True):
                torch.testing.assert_close(left, right, rtol=0, atol=0)
            checks[f'{objective}_{mode}'] = dict(loss=ref[0], ce_targets=24,
                                                kd_targets=len(selected), gradients_exact=True)

    peaked = torch.tensor([[0., -80., -82.], [-90., 0., -91.], [-100., -102., 0.]], requires_grad=True)
    labels = torch.arange(len(peaked))
    upstream = (torch.tensor([.2, -.5, 1.3], dtype=torch.float64),)
    raw_logtail = stable.log_nll_from_logits(peaked, labels)
    compare_boundary((raw_logtail,), (compact.log_nll_from_logits(peaked, labels, rows=2),), peaked, upstream)
    assert bool(torch.isfinite(raw_logtail).all()) and bool(raw_logtail.lt(-79).all())
    logits = torch.randn(3, 4, requires_grad=True)
    anchors = torch.tensor([[0, 0, 2, 2], [0, 1, 2, 3], [1, 1, 2, 1]])
    scores = torch.randn(3, 4)
    reference = actd.actd_sums(logits, anchors, scores, residual_weight=.4)
    candidate = compact.actd_components(logits, anchors, scores, residual_weight=.4, rows=2)
    assert reference['unique_anchor_count'].tolist() == [2, 4, 2]
    assert reference['residual_probabilities'][1] == 0
    sums = ('anchor_sum', 'residual_sum')
    compare_boundary(tuple(reference[k] for k in sums), tuple(candidate[k] for k in sums),
                     logits, (torch.tensor(.2), torch.tensor(1.3)))
    return dict(checks=checks, saturated_logtail=raw_logtail.detach().tolist(),
                actd_unique=reference['unique_anchor_count'].tolist())


def worker(arm):
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 7 * (1 << 30):
        raise RuntimeError('insufficient free memory for the sealed single-GPU profile')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(1337)
    objective, mode = arm.split('_')
    cfg, parent, step = warm.load_parent(torch)
    cfg.train_repeat = 2.0
    model = TiedMLPTransformer(cfg).cuda().train()
    model.load_state_dict(parent, strict=True)
    del parent
    model.set_anneal(1.)
    initial = state_sha(model.state_dict())
    route = build_experimental_optimizers(model, 'muon_matched', lr=LR, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    keep_active_groups(optimizers)
    rates = [[g['lr'] for g in opt.param_groups] for opt in optimizers]
    scaler = ScaledOptimizerGroup([p for p in model.parameters() if p.requires_grad], optimizers,
        run_signature=SHA(OUT / 'profile.json'), expected_backwards=MICROS,
        config=ScaleConfig(init_scale=128., growth_interval=2))
    events, memory = [], []
    with use_normalizer(objective, mode == 'recompute', NORM_ROWS), sdpa_kernel(SDPBackend.MATH):
        for update, micros in enumerate(batches(make_pool(), objective)):
            if (OUT / 'STOP').exists():
                raise RuntimeError('operator stop')
            ce_total = BATCH * (WIDTH - PREFIX) * MICROS
            kd_total = sum(len(row[3]) for row in micros)
            factor = lr_factor(update, 1, UPDATES, 'cosine')
            for opt, base in zip(optimizers, rates, strict=True):
                for group, lr in zip(opt.param_groups, base, strict=True):
                    group['lr'] = lr * factor
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            start = perf_counter()
            micro_results = []
            for x, y, owners, selected in micros:
                x, y, owners = x.cuda(), y.cuda(), owners.cuda()
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    hidden = model(x, return_hidden=True)
                    loss, terms = loss_terms(model, hidden, y, owners, selected, objective, ce_total, kd_total)
                scaler.backward(loss)
                micro_results.append(dict(loss=float(loss.detach()), **numeric_terms(terms)))
                del x, y, owners, hidden, loss, terms
            status = scaler.finish(clip_norm=1.)
            torch.cuda.synchronize()
            assert status['status'] == 'STEPPED_ALL' and status['backward_calls'] == MICROS
            assert sum(row['ce_targets'] for row in micro_results) == ce_total
            assert sum(row['kd_targets'] for row in micro_results) == kd_total
            event = dict(update=update, micros=micro_results, scaler=status)
            measure = dict(seconds=perf_counter() - start, allocated=torch.cuda.max_memory_allocated(),
                           reserved=torch.cuda.max_memory_reserved())
            events.append(event)
            memory.append(measure)
            WRITE(OUT / f'{arm}_update_{update}.json', dict(event=event, measure=measure))
            print('P102A_G4_DISTILL_UPDATE', arm, update, ce_total, kd_total, flush=True)
    final = dict(model=state_sha(model.state_dict()), optimizers=[state_sha(opt.state_dict()) for opt in optimizers],
                 scaler=state_sha(scaler.state_dict()), cpu_rng=state_sha(torch.get_rng_state()),
                 cuda_rng=state_sha(torch.cuda.get_rng_state()))
    assert final['model'] != initial
    WRITE(OUT / f'{arm}.json', dict(initial=initial, parent_step=step, final=final, events=events, memory=memory,
          peak_allocated=max(row['allocated'] for row in memory), peak_reserved=max(row['reserved'] for row in memory),
          median_seconds_after_first=median(row['seconds'] for row in memory[1:]), checkpoint_writes=0))
    return 0


def run(frozen):
    exits, rows = {}, {}
    for arm in ARMS:
        if (OUT / 'STOP').exists() or not idle():
            exits[arm] = None
            break
        argv = ['timeout', '--kill-after=5s', f'{CAP}s', sys.executable, '-B', '-u', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_distill_normalizers', 'worker', arm]
        exits[arm] = subprocess.run(argv, cwd=ROOT).returncode
        print('P102A_G4_DISTILL_EXIT', arm, exits[arm], flush=True)
        if exits[arm] == 0:
            rows[arm] = READ((OUT / f'{arm}.json').read_bytes())
    gpu_returned = idle()
    comparisons = {}
    for objective in OBJECTIVES:
        ref, got = (rows.get(f'{objective}_{mode}') for mode in ('reference', 'recompute'))
        if ref is not None and got is not None:
            comparisons[objective] = {key: ref[key] == got[key] for key in ('initial', 'parent_step', 'events', 'final')}
    WRITE(OUT / 'report.json', dict(exits=exits, gpu_returned=gpu_returned, comparisons=comparisons, arms=rows,
                                    frozen_verified_after=expected() == frozen))
    print('P102A_G4_DISTILL_COMPLETE', comparisons, gpu_returned, flush=True)
    return 0 if gpu_returned and set(comparisons) == set(OBJECTIVES) and all(
        all(pair.values()) for pair in comparisons.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run', 'worker'))
    parser.add_argument('arm', nargs='?', choices=ARMS)
    args = parser.parse_args()
    if (args.phase == 'worker') != (args.arm is not None):
        parser.error('only a worker takes an arm')
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    assert datetime.now(warm.CUTOFF.tzinfo) + timedelta(seconds=len(ARMS) * (CAP + 5)) < warm.CUTOFF
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if args.phase == 'prepare':
        frozen = expected()
        cpu = cpu_gate()
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        WRITE(OUT / 'profile.json', dict(contract=frozen, cpu=cpu))
        print('P102A_G4_DISTILL_CPU', cpu, flush=True)
        return 0
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    frozen = READ((OUT / 'profile.json').read_bytes())
    assert frozen['contract'] == expected() and frozen['cpu']['checks']
    return worker(args.arm) if args.phase == 'worker' else run(frozen['contract'])


if __name__ == '__main__':
    sys.exit(main())
