"""Isolate G4 head GEMMs and measure native BF16 CE recomputed by position."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
import os
import sys

import torch
from torch.autograd.function import once_differentiable
from torch.nn import functional as F

from scripts import diag_p102a_g4_bf16_softmax as rounding


TRACE = rounding.TRACE
STRICT = rounding.strict
ROOT = rounding.ROOT
TAG = 'p102a_g4_bf16_vjp_blocks_v1_20261119'
OUT = rounding.OUT.parent / TAG
PREVIOUS = rounding.OUT / 'report.json'
TERMINAL = rounding.OUT / 'terminal_readback.json'
SOURCE = ROOT / 'scripts/diag_p102a_g4_bf16_vjp_blocks.py'
ROWS = 1024
VOCAB = rounding.TILE


def identity():
    return rounding.identity() | {str(p.relative_to(ROOT)): TRACE.precision.digest(p)
                                   for p in (SOURCE, PREVIOUS, TERMINAL)}


@contextmanager
def fp32_matmul(precision):
    old = torch.get_float32_matmul_precision()
    torch.set_float32_matmul_precision(precision)
    try:
        yield
    finally:
        torch.set_float32_matmul_precision(old)


def native_logprob(projected, table):
    return F.log_softmax(F.linear(projected, table), dim=1)


def native_dlogit(logprob, labels, upstream):
    dlogprob = torch.zeros_like(logprob)
    dlogprob.scatter_(1, labels[:, None], -upstream.bfloat16()[:, None])
    return torch.ops.aten._log_softmax_backward_data.default(dlogprob, logprob, 1, torch.bfloat16)


class PositionBF16NLL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, labels, rows):
        assert projected.dtype == torch.bfloat16 and table.dtype == torch.float32
        assert projected.ndim == table.ndim == 2 and projected.shape[1] == table.shape[1]
        assert labels.dtype == torch.long and labels.shape == (projected.shape[0],) and labels.numel()
        assert rows > 0 and bool((labels.ge(0) & labels.lt(table.shape[0])).all())
        e = table.bfloat16()
        nll = torch.empty_like(labels, dtype=torch.float32)
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, labels.numel(), rows):
                part = slice(start, start + rows)
                logprob = native_logprob(projected[part], e)
                nll[part] = -logprob.gather(1, labels[part, None]).flatten().float()
        ctx.save_for_backward(projected, e, labels)
        ctx.rows = rows
        return nll

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        p, e, labels = ctx.saved_tensors
        dp = torch.empty_like(p)
        de = torch.zeros_like(e, dtype=torch.float32)
        with torch.autocast(p.device.type, enabled=False), fp32_matmul('highest'):
            for start in range(0, labels.numel(), ctx.rows):
                part = slice(start, start + ctx.rows)
                logprob = native_logprob(p[part], e)
                delta = native_dlogit(logprob, labels[part], upstream[part])
                dp[part] = delta @ e
                de.add_(delta.T.float() @ p[part].float())
        return dp, de.bfloat16().float(), None, None


def position_head(model, hidden, targets, rows):
    labels = targets.flatten()
    valid = labels.ne(-100)
    projected = F.linear(hidden, model._emb_up_w().t()).flatten(0, 1)
    if not bool(valid.all()):
        projected, labels = projected[valid], labels[valid]
    return PositionBF16NLL.apply(projected, model._emb_w(), labels, rows).mean()


def source_case():
    previous = json.loads(PREVIOUS.read_text())
    assert json.loads(TERMINAL.read_text())['report_sha256'] == TRACE.precision.digest(PREVIOUS)
    assert previous['logprob_trace']['vjp_using_native_logprob']['unequal'] == 0
    _, original, batch, digest = rounding.source_case()
    assert digest == previous['input_sha256']
    return previous, original, batch, digest


def prepare():
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    _, _, _, digest = source_case()
    torch.manual_seed(11)
    model = TiedMLPTransformer(TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                                        emb_rank=8, n_prelude=1, n_middle=4, n_coda=1, tie_mlp=True,
                                        mlp_group=2, micro_group=8, max_seq_len=8))
    hidden = torch.randn(2, 4, 32, requires_grad=True)
    target = torch.tensor([[0, -100, 5, 8], [4, 1, -100, 20]])
    params = (hidden, model.emb.weight, model.emb_up.weight)
    with torch.autocast('cpu', dtype=torch.bfloat16):
        logits = model._head_logits(hidden).flatten(0, 1)
        native = F.nll_loss(F.log_softmax(logits, dim=1, dtype=torch.bfloat16).float(), target.flatten())
    with torch.autocast('cpu', dtype=torch.bfloat16):
        chunk = position_head(model, hidden, target, 2)
    assert abs(float(native.detach()) - float(chunk.detach())) <= 1e-6
    ref = torch.autograd.grad(native / TRACE.ACCUM, params)
    ours = torch.autograd.grad(chunk / TRACE.ACCUM, params)
    stats = {k: TRACE.observe(torch, a, b) for k, a, b in zip(('hidden', 'table', 'projection'), ref, ours, strict=True)}
    assert not torch.cuda.is_initialized()
    TRACE.precision.previous.write_new(OUT / 'profile.json', dict(tag=TAG, identity=identity(), input_sha256=digest,
            cpu_reference_ce=float(native.detach()), cpu_chunk_ce=float(chunk.detach()), cpu_gradient=stats))
    print('P102A_G4_BF16_VJP_BLOCKS_READY', flush=True)
    return 0


def fixed_vjp(ref, table):
    p, d, e = ref['projected'], ref['grad']['logits'], table.bfloat16()
    assert p.dtype == d.dtype == e.dtype == torch.bfloat16
    dp, de = ref['projected_gradient'], ref['grad']['table']
    table_vjp = {}
    projected_vjp = {}
    with torch.no_grad(), torch.autocast('cuda', enabled=False):
        projected_vjp['full_bf16'] = TRACE.observe(torch, dp, d @ e)
        for rows in (1024, 512):
            blocked = torch.cat([part @ e for part in d.split(rows)], dim=0)
            projected_vjp[f'position_{rows}_bf16'] = TRACE.observe(torch, dp, blocked)
        for precision in ('high', 'highest'):
            acc = torch.zeros_like(dp, dtype=torch.float32)
            with fp32_matmul(precision):
                for left, right in zip(d.split(VOCAB, dim=1), e.split(VOCAB), strict=True):
                    acc.add_(left.float() @ right.float())
            projected_vjp[f'vocab_{VOCAB}_fp32_{precision}'] = TRACE.observe(torch, dp, acc.bfloat16())
        table_vjp['full_bf16'] = TRACE.observe(torch, de, (d.T @ p).float())
        blocked = torch.cat([(part.contiguous().T @ p).float() for part in d.split(VOCAB, dim=1)])
        table_vjp[f'vocab_{VOCAB}_bf16'] = TRACE.observe(torch, de, blocked)
    return dict(projected=projected_vjp, table=table_vjp, shapes=[list(z.shape) for z in (d, p, e)])


def run_position(original, x, y):
    model = TRACE.precision.new_model(torch, original).to('cuda')
    torch.cuda.reset_peak_memory_stats()
    with torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
        ce = position_head(model, hidden, y, ROWS)
    (ce / TRACE.ACCUM).backward()
    torch.cuda.synchronize()
    result = dict(ce=float(ce.detach()), peak_mib=torch.cuda.max_memory_allocated() / TRACE.precision.MIB,
                  hidden_sha256=TRACE.digest_tensor(torch, hidden), max_logits_rows=ROWS)
    return result, {k: p.grad.detach().cpu() for k, p in model.named_parameters()}


def actual():
    profile = json.loads((OUT / 'profile.json').read_text())
    assert profile['identity'] == identity() and os.environ['CUBLAS_WORKSPACE_CONFIG'] == STRICT.WORKSPACE
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * 1024 ** 3
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    prior, original, batch, digest = source_case()
    assert profile['input_sha256'] == digest
    x, y = (z.to('cuda') for z in batch)
    TRACE.precision.previous.write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), device=torch.cuda.get_device_name()))
    print('P102A_G4_BF16_VJP_BLOCKS_ACTIVE', os.getpid(), flush=True)
    reference, left = STRICT.run_arm(torch, original, x, y, 'reference', 'native', 0)
    assert reference['hidden_sha256'] == prior['arms']['native']['hidden_sha256']
    torch.cuda.empty_cache()
    candidate, right = run_position(original, x, y)
    assert reference['hidden_sha256'] == candidate['hidden_sha256']
    grad = TRACE.precision.previous.tensor_comparison(torch, left, right)
    del left, right
    torch.cuda.empty_cache()
    print('P102A_G4_BF16_VJP_BLOCKS_F+B', grad['outside_tolerance'], flush=True)
    model = TRACE.precision.new_model(torch, original).to('cuda')
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
    assert TRACE.digest_tensor(torch, hidden) == reference['hidden_sha256']
    ref = TRACE.native_head(torch, model, hidden, y, True)
    probe = fixed_vjp(ref, model._emb_w())
    assert profile['identity'] == identity()
    TRACE.precision.previous.write_new(OUT / 'report.json', dict(tag=TAG, reference=reference,
        candidate=candidate, gradient=grad, fixed_reference_logit_vjp=probe, input_sha256=digest,
        active_targets=int(y.numel()), source=profile['identity'], optimizer_updates=0, checkpoint_writes=0))
    print('P102A_G4_BF16_VJP_BLOCKS_RESULT', grad['outside_tolerance'], flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'actual'))
    args = parser.parse_args()
    cutoff = TRACE.precision.previous.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(minutes=5) < cutoff
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    if args.phase == 'prepare':
        OUT.mkdir(exist_ok=False)
    else:
        assert not (OUT / 'active.json').exists() and not (OUT / 'report.json').exists()
    os.environ['TINYLM_DIR'] = str(OUT / 'unused_root')
    os.environ['TINYLM_HF'] = str(OUT / 'unused_root/HF')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return (prepare if args.phase == 'prepare' else actual)()


if __name__ == '__main__':
    sys.exit(main())
