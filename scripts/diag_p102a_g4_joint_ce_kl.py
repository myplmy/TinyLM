"""Train the same 248K G4 with a shared row-recomputed CE/KL head."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timedelta
import json
from math import prod
import os
import resource
from statistics import median
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p102a_g4_full_kl_recompute as prior
from scripts.p102a_joint_ce_kl import joint_ce_kl
from tinylm.config import TMTConfig


TAG = 'p102a_g4_joint_ce_kl_v2_20261119'
OUT = prior.OUT.with_name(TAG)
ARMS = {'full_sum': 'reference', 'chunk_sum': 'chunk'}
CAP = 75
SOURCES = (*prior.SOURCES, 'scripts/diag_p102a_g4_joint_ce_kl.py', 'scripts/p102a_joint_ce_kl.py')
WRITE, SHA, state_sha = prior.WRITE, prior.SHA, prior.state_sha


def read(path):
    return json.loads(path.read_bytes())


def contract(bank, provenance, batches):
    parent = prior.OUT / 'profile.json'
    report = prior.OUT / 'report.json'
    source = read(parent)
    assert source['contract'] == prior.expected(bank, provenance, batches)
    previous = read(report)
    assert previous['sources_unchanged'] and previous['gpu_returned'] and set(previous['exits'].values()) == {0}
    return dict(tag=TAG, base=source['contract'], base_profile_sha256=SHA(parent), base_report_sha256=SHA(report),
                pins={name: SHA(prior.ROOT / name) for name in SOURCES}, rows=prior.ROWS,
                workers=ARMS, max_worker_s=CAP, checkpoint_writes=0, approval='WIP176')


def cpu_gate(bank):
    torch.manual_seed(468)
    cfg = TMTConfig(vocab_size=prior.VOCAB, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=8,
                    n_q_heads=4, n_kv_heads=2, n_prelude=1, n_middle=2, n_coda=1,
                    tie_mlp=True, mlp_group=2, micro_group=8)
    model = prior.TiedMLPTransformer(cfg)
    hidden = torch.randn(1, 7, 32, requires_grad=True)
    targets = torch.tensor([[-100, 32767, -100, 65535, 65536, prior.VOCAB-2, prior.VOCAB-1]])
    teacher = bank[torch.arange(targets.numel()).remainder(2)]
    params = (hidden, model.emb.weight, model.emb_up.weight)
    cpu_rows = 4
    results = {}
    for precision in ('fp32', 'bf16'):
        for arm, reference in ARMS.items():
            amp = torch.autocast('cpu', dtype=torch.bfloat16) if precision == 'bf16' else nullcontext()
            with amp:
                native = model._head_logits(hidden).flatten(0, 1)
                ce, kl, loss = prior.objective(reference, native, teacher, targets.flatten(), rows=cpu_rows)
                expected = torch.autograd.grad(loss * 57., params)
                a, b = joint_ce_kl(model, hidden, targets, teacher, temperature=prior.TEMPERATURE,
                                   rows=cpu_rows, full_sum=arm == 'full_sum')
                actual = torch.autograd.grad(((1.-prior.ALPHA)*a + prior.ALPHA*b) * 57., params)
            assert torch.equal(ce, a) and torch.equal(kl, b)
            rtol, atol = (0., 0.) if precision == 'bf16' else (1e-5, 5e-8)
            for want, got in zip(expected, actual, strict=True):
                torch.testing.assert_close(want, got, rtol=rtol, atol=atol)
            results[f'{precision}_{arm}'] = dict(losses_exact=True,
                gradients_exact=all(torch.equal(want, got) for want, got in zip(expected, actual, strict=True)),
                gradient_max_abs=[float((want-got).abs().max()) for want,got in zip(expected,actual,strict=True)])
    return results


def reject_full_head(*args, **kwargs):
    raise RuntimeError('joint loss worker must not call the materialized native student head')


def worker(arm, bank, batches, *, out=OUT, teacher_storage='cuda'):
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 14 * (1 << 30):
        raise RuntimeError('single CUDA device with 14 GiB free required')
    if teacher_storage not in ('cuda', 'pageable', 'pinned'):
        raise ValueError('unknown teacher storage')
    if len(batches) != prior.UPDATES or not batches[0]:
        raise ValueError('the scheduled update groups are required')
    micro_count = len(batches[0])
    shape = batches[0][0][1].shape
    if len(shape) != 2 or any(len(group) != micro_count for group in batches):
        raise ValueError('all updates must have the same microbatch geometry')
    if any(x.shape != shape or y.shape != shape for group in batches for x, y in group):
        raise ValueError('all frozen inputs and targets must have the same shape')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(1337)
    model, step = prior.initialize()
    initial = state_sha(model.state_dict())
    model.cuda()
    route = prior.build_experimental_optimizers(model, 'muon_matched', lr=prior.LR, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    prior.keep_active_groups(optimizers)
    rates = [[g['lr'] for g in opt.param_groups] for opt in optimizers]
    n_rows = prod(shape)
    host_teacher = None
    if teacher_storage == 'cuda':
        bank = bank.cuda()
        selector = torch.arange(n_rows, device='cuda').remainder(2)
    else:
        host_teacher = torch.empty((n_rows, bank.shape[1]), dtype=bank.dtype,
                                   device='cpu', pin_memory=teacher_storage == 'pinned')
        selector = torch.arange(n_rows, device='cpu').remainder(2)
        torch.index_select(bank, 0, selector, out=host_teacher)
        assert host_teacher.is_pinned() == (teacher_storage == 'pinned')
    key = arm if host_teacher is None else teacher_storage
    history, measures, first_gradient, head_blocks = [], [], None, 0
    with patch.object(model, '_head_logits', reject_full_head), sdpa_kernel(SDPBackend.MATH):
        for index, micros in enumerate(batches):
            if (out / 'STOP').exists():
                raise RuntimeError('operator stop')
            factor = prior.lr_factor(index, 1, prior.UPDATES, 'cosine')
            for opt, base in zip(optimizers, rates, strict=True):
                for group, lr in zip(opt.param_groups, base, strict=True):
                    group['lr'] = lr * factor
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            start = perf_counter()
            values = []
            for x, y in micros:
                x, y = x.cuda(), y.cuda()
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    h = model(x, return_hidden=True)
                    teacher = bank.index_select(0, selector) if host_teacher is None else host_teacher
                    ce, kl = joint_ce_kl(model, h, y, teacher, temperature=prior.TEMPERATURE,
                                        rows=prior.ROWS, full_sum=arm == 'full_sum')
                    loss = (1. - prior.ALPHA) * ce + prior.ALPHA * kl
                (loss / micro_count).backward()
                head_blocks += (y.numel() + prior.ROWS - 1) // prior.ROWS
                values.append([float(t.detach()) for t in (ce, kl, loss)])
                del h, teacher, ce, kl, loss, x, y
            torch.cuda.synchronize()
            audit = 0.
            if index == 0:
                audit_begin = perf_counter()
                first_gradient = state_sha({name: p.grad for name, p in model.named_parameters()})
                audit = perf_counter() - audit_begin
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            for opt in optimizers:
                opt.step()
                opt.zero_grad(set_to_none=True)
            torch.cuda.synchronize()
            measure = dict(seconds=perf_counter()-start-audit, allocated=torch.cuda.max_memory_allocated(),
                           reserved=torch.cuda.max_memory_reserved())
            event = dict(update=index, micros=values, grad_norm=float(norm), targets=n_rows*micro_count)
            assert bool(torch.isfinite(torch.tensor(values)).all())
            measures.append(measure)
            history.append(event)
            WRITE(out / f'{key}_update_{index}.json', dict(event=event, measure=measure))
            print('P102A_G4_JOINT_UPDATE',teacher_storage,arm,index,event['targets'],measure['allocated'],flush=True)
    final = dict(model=state_sha(model.state_dict()), optimizers=[state_sha(o.state_dict()) for o in optimizers])
    assert initial != final['model'] and first_gradient
    host_bytes = 0 if host_teacher is None else host_teacher.nbytes
    WRITE(out / f'{key}.json', dict(initial=initial,parent_step=step,first_gradient=first_gradient,
        final=final,history=history,measures=measures,peak_allocated=max(m['allocated'] for m in measures),
        peak_reserved=max(m['reserved'] for m in measures), median_seconds_after_first=median(m['seconds'] for m in measures[1:]),
        forward_head_blocks=head_blocks,full_student_logits_calls=0,checkpoint_writes=0,
        teacher_storage=teacher_storage,host_teacher_bytes=host_bytes,
        host_peak_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        host_to_device_bytes=2*sum(len(micros) for micros in batches)*host_bytes))


def run(frozen):
    exits, arms = {}, {}
    for arm in ARMS:
        if not prior.idle() or (OUT / 'STOP').exists():
            exits[arm] = None
            break
        command = ['timeout','--kill-after=5s',f'{CAP}s',sys.executable,'-B','-u','-X','utf8','-m',
                   'scripts.diag_p102a_g4_joint_ce_kl','worker',arm]
        exits[arm] = subprocess.run(command,cwd=prior.ROOT).returncode
        print('P102A_G4_JOINT_EXIT',arm,exits[arm],flush=True)
        if exits[arm] == 0:
            arms[arm] = read(OUT / f'{arm}.json')
    reference = read(prior.OUT / 'report.json')['arms']
    comparisons = {arm:{k: row[k] == reference[ARMS[arm]][k]
                       for k in ('initial','parent_step','first_gradient','final','history')} for arm,row in arms.items()}
    gpu_returned = prior.idle()
    bank, provenance = prior.frozen_logits(torch)
    unchanged = frozen == contract(bank.float(),provenance,prior.crops())
    WRITE(OUT / 'report.json',dict(arms=arms,exits=exits,comparisons=comparisons,
                                   gpu_returned=gpu_returned,sources_unchanged=unchanged))
    print('P102A_G4_JOINT_COMPLETE',comparisons,gpu_returned,flush=True)
    return 0 if gpu_returned and unchanged and len(arms) == len(ARMS) and all(
        all(row.values()) for row in comparisons.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','run','worker'))
    parser.add_argument('arm',nargs='?',choices=tuple(ARMS))
    args = parser.parse_args()
    if (args.phase == 'worker') != (args.arm is not None):
        parser.error('only a worker has an arm')
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    stopwatch = prior.warm.CUTOFF
    assert datetime.now(stopwatch.tzinfo) + timedelta(seconds=len(ARMS)*(CAP+5)) < stopwatch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    bank, provenance = prior.frozen_logits(torch)
    bank = bank.float()
    batches = prior.crops()
    current = contract(bank,provenance,batches)
    if args.phase == 'prepare':
        checked = cpu_gate(bank)
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        WRITE(OUT / 'profile.json',dict(contract=current,cpu=checked))
        print('P102A_G4_JOINT_CPU_READY',checked,flush=True)
        return 0
    assert os.environ.get('PYTORCH_CUDA_ALLOC_CONF') == prior.ALLOCATOR
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    frozen = read(OUT / 'profile.json')
    assert frozen['contract'] == current and frozen['cpu']
    return worker(args.arm,bank,batches) if args.phase == 'worker' else run(current)


if __name__ == '__main__':
    sys.exit(main())
