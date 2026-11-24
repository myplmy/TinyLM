"""Compare full, chunked and recomputed FP32 KL on the same 248K G4 updates."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timedelta
import json
import os
from statistics import median
import subprocess
import sys
from time import perf_counter

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p102a_g4_recompute_vocab as vocab_trial
from scripts import diag_p109_warm_visit_routes as warm
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p102a_tiled_bonsai_exact_kd import WITNESS, frozen_logits
from scripts.p102a_full_kl_recompute import full_kl
from scripts.p107_active_optimizer_groups import keep_active_groups
from tinylm.data import Loader
from tinylm.model import TiedMLPTransformer
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.experimental_optimizers import build_experimental_optimizers
from tinylm.train.trainer import _ce_chunked, _kd_kl


ROOT = warm.io.ROOT
TAG = 'p102a_g4_full_kl_recompute_v1_20261119'
OUT = warm.OUT.with_name(TAG)
ARMS = ('reference', 'chunk', 'recompute')
BATCH, WIDTH, MICROS, UPDATES, ROWS, CAP = 2, 512, 4, 6, 128, 100
VOCAB = vocab_trial.VOCAB
ALPHA, TEMPERATURE, LR = .3, 2., 6e-4
PARENT_SHA = 'D576B9EB6DEF02DF5DCCAD91E484098AFB67A52553A7A735B21249DB2D9EC3D5'
ALLOCATOR = 'expandable_segments:False'
WRITE, SHA = warm.io.write, warm.io.digest
SOURCES = (*warm.SOURCES, 'scripts/diag_p102a_g4_full_kl_recompute.py',
           'scripts/p102a_full_kl_recompute.py', 'scripts/diag_p102a_g4_recompute_vocab.py',
           'scripts/diag_p102a_tiled_bonsai_exact_kd.py', 'scripts/diag_p102a_g4_full_delta_train.py',
           'scripts/p107_active_optimizer_groups.py', 'tinylm/data/loader.py', 'tinylm/train/trainer.py',
           'tinylm/train/experimental_optimizers.py', 'tinylm/train/muon.py', 'tinylm/train/anneal_schedule.py')


def crops():
    loader = Loader('train', BATCH, WIDTH, 'cpu', vocab_trial.CACHE, seed=1234)
    return [[loader() for _ in range(MICROS)] for _ in range(UPDATES)]


def expected(bank, provenance, batches):
    if SHA(warm.PARENT) != PARENT_SHA:
        raise ValueError('P079 G4 parent changed')
    meta = json.loads((vocab_trial.CACHE / 'meta.json').read_bytes())
    count = BATCH * MICROS * WIDTH * UPDATES
    assert meta['data'] == 'synthetic' and meta['token_dtype'] == 'uint32'
    assert meta['train'] >= 2 * count and meta['vocab'] == VOCAB and bank.shape == (2, VOCAB)
    assert all(y.max() < VOCAB and y.min() >= 0 and (y > 65535).any() for group in batches for _, y in group)
    source = {name: SHA(vocab_trial.CACHE / name) for name in ('train.bin', 'meta.json')}
    return dict(tag=TAG, sources={name: SHA(ROOT / name) for name in SOURCES}, parent_sha256=PARENT_SHA,
                cache=source, corpus_tokens=meta['train'], teacher_receipts=provenance,
                teacher_bank_sha256=state_sha(bank), teacher_witness_sha256=SHA(WITNESS),
                teacher_order='ALTERNATING_TWO_VECTORS_EVERY_MICRO', inputs=state_sha(batches),
                teacher_temperature=TEMPERATURE, alpha=ALPHA, max_worker_s=CAP, allocator=ALLOCATOR,
                selected_dtypes=['BF16_STUDENT_LOGITS','FP32_FROZEN_TEACHER'],
                width=WIDTH, batch=BATCH, micros=MICROS, steps=UPDATES, draw_targets=count,
                rows=ROWS, lr=LR, approval='WIP176', checkpoint_writes=0)


def kl_for(arm, student, teacher, *, rows=ROWS):
    if arm == 'recompute':
        return full_kl(student, teacher, temperature=TEMPERATURE, rows=rows)
    chunk = rows if arm == 'chunk' else 0
    return _kd_kl(student, teacher, TEMPERATURE, chunk=chunk, fp32=True)


def objective(arm, student, teacher, targets, *, rows=ROWS):
    ce = _ce_chunked(student, targets, chunk=0)
    kl = kl_for(arm, student, teacher, rows=rows)
    return ce, kl, (1. - ALPHA) * ce + ALPHA * kl


def cpu_gate(bank):
    rng = torch.Generator().manual_seed(76413)
    source = torch.randn((7, VOCAB), generator=rng)
    teacher = bank[torch.arange(7).remainder(2)]
    targets = torch.tensor([3, 32767, 32768, 65535, 65536, VOCAB - 2, VOCAB - 1])
    checks = {}
    for dtype in (torch.float32, torch.bfloat16):
        arms = {}
        for arm in ARMS:
            s = source.to(dtype).detach().requires_grad_()
            amp = torch.autocast('cpu', dtype=torch.bfloat16) if dtype == torch.bfloat16 else nullcontext()
            with amp:
                ce, kl, loss = objective(arm, s, teacher, targets, rows=4)
            grad = torch.autograd.grad(loss * 71., s)[0]
            arms[arm] = dict(values=[float(t.detach()) for t in (ce, kl, loss)], grad=grad)
        ref, got = arms['reference'], arms['recompute']
        assert ref['values'] == got['values'] and torch.equal(ref['grad'], got['grad'])
        checks[str(dtype)] = dict(recompute_exact=True, values={arm:r['values'] for arm, r in arms.items()},
                                  chunk_grad_differences=int(arms['chunk']['grad'].ne(ref['grad']).sum()),
                                  gradient_elements=ref['grad'].numel())
    return checks


def initialize():
    cfg, state, parent_step = warm.load_parent(torch)
    cfg.vocab_size, cfg.train_repeat = VOCAB, 2.
    model = TiedMLPTransformer(cfg)
    prefix = state['emb.weight']
    assert prefix.shape == (32768, cfg.emb_rank)
    weight = model.emb.weight.detach()
    with torch.no_grad():
        weight[:len(prefix)].copy_(prefix)
    state['emb.weight'] = weight
    model.load_state_dict(state, strict=True)
    model.set_anneal(1.)
    model.train()
    assert cfg.grad_checkpoint and len(model.visit_schedule()) == 28 and not model.embedding_quantized()
    return model, parent_step


def worker(arm, bank, batches):
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 14 * (1 << 30):
        raise RuntimeError('single CUDA device with 14 GiB free is required')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(1337)
    model, parent_step = initialize()
    initial = state_sha(model.state_dict())
    model.cuda()
    route = build_experimental_optimizers(model, 'muon_matched', lr=LR, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    keep_active_groups(optimizers)
    rates = [[g['lr'] for g in opt.param_groups] for opt in optimizers]
    bank = bank.cuda()
    selector = torch.arange(BATCH * WIDTH, device='cuda').remainder(2)
    history, measures, first_gradient = [], [], None
    with sdpa_kernel(SDPBackend.MATH):
        for index, micros in enumerate(batches):
            if (OUT / 'STOP').exists():
                raise RuntimeError('operator stop')
            factor = lr_factor(index, 1, UPDATES, 'cosine')
            for opt, base in zip(optimizers, rates, strict=True):
                for group, lr in zip(opt.param_groups, base, strict=True):
                    group['lr'] = lr * factor
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            begin = perf_counter()
            sums = []
            for x, y in micros:
                x, y = x.cuda(), y.cuda().reshape(-1)
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    student = model(x).reshape(-1, VOCAB)
                    teacher = bank.index_select(0, selector)
                    assert student.dtype == torch.bfloat16 and teacher.dtype == torch.float32
                    ce, kl, loss = objective(arm, student, teacher, y)
                (loss / MICROS).backward()
                sums.append([float(t.detach()) for t in (ce, kl, loss)])
                del student, teacher, ce, kl, loss, x, y
            torch.cuda.synchronize()
            gradient_audit = 0.
            if index == 0:
                audit_begin = perf_counter()
                first_gradient = state_sha({name: p.grad for name, p in model.named_parameters()})
                gradient_audit = perf_counter() - audit_begin
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            for opt in optimizers:
                opt.step()
                opt.zero_grad(set_to_none=True)
            torch.cuda.synchronize()
            measure = dict(seconds=perf_counter()-begin-gradient_audit,
                           allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())
            event = dict(update=index, micros=sums, grad_norm=float(norm), targets=BATCH * WIDTH * MICROS)
            assert all(torch.isfinite(torch.tensor(sums)).flatten())
            history.append(event)
            measures.append(measure)
            WRITE(OUT / f'{arm}_update_{index}.json', dict(event=event, measure=measure))
            print('P102A_G4_FULL_KL_UPDATE', arm, index, event['targets'], measure['allocated'], flush=True)
    final = dict(model=state_sha(model.state_dict()), optimizers=[state_sha(opt.state_dict()) for opt in optimizers])
    assert initial != final['model'] and first_gradient
    WRITE(OUT / f'{arm}.json', dict(initial=initial, parent_step=parent_step, first_gradient=first_gradient,
          final=final, history=history, measures=measures, peak_allocated=max(r['allocated'] for r in measures),
          peak_reserved=max(r['reserved'] for r in measures),
          median_seconds_after_first=median(r['seconds'] for r in measures[1:]), checkpoint_writes=0))
    return 0


def run(frozen):
    exits, results = {}, {}
    for arm in ARMS:
        if (OUT / 'STOP').exists() or not idle():
            exits[arm] = None
            break
        argv = ['timeout', '--kill-after=5s', f'{CAP}s', sys.executable, '-B', '-u', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_full_kl_recompute', 'worker', arm]
        exits[arm] = subprocess.run(argv, cwd=ROOT).returncode
        print('P102A_G4_FULL_KL_EXIT', arm, exits[arm], flush=True)
        if exits[arm] == 0:
            results[arm] = json.loads((OUT / f'{arm}.json').read_bytes())
    comparisons = {}
    if 'reference' in results:
        ref = results['reference']
        for arm, got in results.items():
            if arm != 'reference':
                comparisons[arm] = {key: ref[key] == got[key]
                                    for key in ('initial', 'first_gradient', 'final', 'history')}
    gpu_returned = idle()
    bank, provenance = frozen_logits(torch)
    unchanged = frozen == expected(bank.float(), provenance, crops())
    WRITE(OUT / 'report.json', dict(arms=results, comparisons=comparisons, exits=exits,
                                    sources_unchanged=unchanged, gpu_returned=gpu_returned))
    print('P102A_G4_FULL_KL_COMPLETE', comparisons, gpu_returned, flush=True)
    return 0 if gpu_returned and unchanged and len(results) == len(ARMS) and all(
        comparisons['recompute'].values()) else 8


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
    bank, provenance = frozen_logits(torch)
    bank = bank.float()
    batches = crops()
    contract = expected(bank, provenance, batches)
    if args.phase == 'prepare':
        checks = cpu_gate(bank)
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        WRITE(OUT / 'profile.json', dict(contract=contract, cpu=checks))
        print('P102A_G4_FULL_KL_CPU_READY', checks, flush=True)
        return 0
    assert os.environ.get('PYTORCH_CUDA_ALLOC_CONF') == ALLOCATOR
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    frozen = json.loads((OUT / 'profile.json').read_bytes())
    assert frozen['contract'] == contract and frozen['cpu']
    return worker(args.arm, bank, batches) if args.phase == 'worker' else run(contract)


if __name__ == '__main__':
    sys.exit(main())
