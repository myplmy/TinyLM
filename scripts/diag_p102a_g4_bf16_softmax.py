"""Measure an experimental BF16-rounded CE without a full logits buffer."""

import argparse
from datetime import datetime, timedelta
import json
import os
import sys

import torch
from torch.nn import functional as F
from torch.autograd.function import once_differentiable

from scripts import diag_p102a_g4_head_strict as strict


TRACE = strict.trace
ROOT = strict.ROOT
TAG = 'p102a_g4_bf16_softmax_v2_20261119'
OUT = strict.OUT.parent / TAG
PREVIOUS = strict.OUT / 'report.json'
TERMINAL = strict.OUT / 'terminal_readback.json'
SOURCE = ROOT / 'scripts/diag_p102a_g4_bf16_softmax.py'
TILE = TRACE.precision.previous.TILE


def identity():
    return strict.identity() | {str(p.relative_to(ROOT)): TRACE.precision.digest(p)
                                 for p in (SOURCE, PREVIOUS, TERMINAL)}


def streaming_logsumexp(projected, table, labels, tile):
    """The bounded online LSE used by the streaming NLL."""
    maximum = torch.full((projected.shape[0],), -torch.inf, dtype=torch.float32, device=projected.device)
    total = torch.zeros_like(maximum)
    chosen = torch.empty_like(maximum)
    for index, part in enumerate(table.split(tile)):
        logits = F.linear(projected, part).float()
        next_max = torch.maximum(maximum, logits.amax(dim=-1))
        total = total * (maximum - next_max).exp() + (logits - next_max[:, None]).exp().sum(dim=-1)
        maximum = next_max
        start = index * tile
        active = labels.ge(start) & labels.lt(start + len(part))
        chosen[active] = logits[active, labels[active] - start]
    return maximum, total.log(), chosen


def rounded_logprob(logits, row_max, log_total):
    return ((logits.float() - row_max[:, None]) - log_total[:, None]).bfloat16()


def logprob_vjp(logprob, labels, outside_index, upstream):
    """Keep the row sum of dlogp even when the label is outside this tile."""
    n = logprob.shape[0]
    padded = torch.cat((logprob, logprob.new_zeros(n, 1)), dim=1)
    g_logprob = torch.zeros_like(padded)
    g_logprob.scatter_(1, labels.masked_fill((labels < 0) | (labels >= outside_index), outside_index)[:, None],
                       -upstream.bfloat16()[:, None])
    grad = torch.ops.aten._log_softmax_backward_data.default(g_logprob, padded, 1, torch.bfloat16)
    return grad[:, :-1].contiguous()


class RoundedBF16NLL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, labels, tile):
        assert projected.dtype == torch.bfloat16 and table.dtype == torch.float32
        assert projected.ndim == table.ndim == 2 and projected.shape[1] == table.shape[1]
        assert labels.shape == (projected.shape[0],) and labels.dtype == torch.long
        assert tile > 0 and labels.numel() and bool((labels.ge(0) & labels.lt(table.shape[0])).all())
        e = table.bfloat16()
        with torch.autocast(projected.device.type, enabled=False):
            row_max, log_total, chosen = streaming_logsumexp(projected, e, labels, tile)
            nll = -((chosen - row_max) - log_total).bfloat16().float()
        ctx.save_for_backward(projected, e, labels, row_max, log_total)
        ctx.tile = tile
        return nll

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        p, e, labels, row_max, log_total = ctx.saved_tensors
        dp = torch.zeros_like(p, dtype=torch.float32)
        de = torch.empty_like(e, dtype=torch.float32)
        with torch.autocast(p.device.type, enabled=False):
            for start, part in enumerate(e.split(ctx.tile)):
                start *= ctx.tile
                logp = rounded_logprob(F.linear(p, part), row_max, log_total)
                delta = logprob_vjp(logp, labels - start, len(part), upstream)
                dp.add_(delta.float() @ part.float())
                de[start:start+len(part)] = (delta.T @ p).float()
        return dp.bfloat16(), de, None, None


def rounded_head(model, hidden, target, tile):
    labels = target.flatten()
    valid = labels.ne(-100)
    projected = F.linear(hidden, model._emb_up_w().t()).flatten(0, 1)
    if not bool(valid.all()):
        projected, labels = projected[valid], labels[valid]
    return RoundedBF16NLL.apply(projected, model._emb_w(), labels, tile).mean()


def compare_tiles(ref, projected, fp32_table, labels, tile):
    projected = projected.contiguous()
    table = fp32_table.bfloat16()
    upstream = torch.full((labels.numel(),), 1. / (labels.numel() * TRACE.ACCUM), device=labels.device)
    with torch.no_grad(), torch.autocast(projected.device.type, enabled=False):
        native_logp = torch.log_softmax(ref['logits'], dim=-1)
        nll = -native_logp.gather(1, labels.unsqueeze(1)).squeeze(1).float()
        assert native_logp.dtype == torch.bfloat16 and nll.shape == ref['nll'].shape
        row_max, total, chosen = streaming_logsumexp(projected, table, labels, tile)
        candidate_nll = -((chosen - row_max) - total).bfloat16().float()
        logps, grads_native_logp, grads_rounded = [], [], []
        for start, part in enumerate(table.split(tile)):
            start *= tile
            end = start + len(part)
            logits = F.linear(projected, part)
            rounded = rounded_logprob(logits, row_max, total)
            logps.append(TRACE.observe(torch, native_logp[:, start:end], rounded, logits=True))
            ref_grad = ref['grad']['logits'][:, start:end]
            grads_native_logp.append(TRACE.observe(torch, ref_grad, logprob_vjp(
                native_logp[:, start:end], labels - start, len(part), upstream)))
            grads_rounded.append(TRACE.observe(torch, ref_grad, logprob_vjp(
                rounded, labels - start, len(part), upstream)))
    result = {'native_logsoftmax_nll': TRACE.observe(torch, ref['nll'], nll, logits=True),
              'rounded_nll': TRACE.observe(torch, ref['nll'], candidate_nll, logits=True)}
    for key, values in (('logprob', logps), ('vjp_using_native_logprob', grads_native_logp),
                        ('vjp_using_tiled_logprob', grads_rounded)):
        result[key] = {name: sum(row[name] for row in values) for name in ('elements', 'unequal', 'outside_tolerance')}
        result[key]['max_abs'] = max(row['max_abs'] for row in values)
    return result


def source_case():
    prior = json.loads(PREVIOUS.read_text())
    receipt = json.loads(TERMINAL.read_text())
    assert receipt['report_sha256'] == TRACE.precision.digest(PREVIOUS)
    assert prior['deterministic']['mode'] and prior['arms']['repeat']['gradients']['max_abs'] == 0.
    original, batch, signature = strict.original_case(torch)
    assert signature == prior['input_sha256']
    return prior, original, batch, signature


def prepare():
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    _, _, _, signature = source_case()
    torch.manual_seed(11)
    model = TiedMLPTransformer(TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                                        emb_rank=8, n_prelude=1, n_middle=4, n_coda=1,
                                        tie_mlp=True, mlp_group=2, micro_group=8, max_seq_len=8))
    first = torch.randn(2, 4, 32, requires_grad=True)
    target = torch.tensor([[0, -100, 5, 8], [4, 1, -100, 20]])
    ref = TRACE.native_head(torch, model, first, target, True)
    with torch.autocast('cpu', dtype=torch.bfloat16):
        logits = model._head_logits(first).flatten(0, 1)
        logprob = F.log_softmax(logits.float(), dim=1).bfloat16()
        rounded_ref = F.nll_loss(logprob.float(), target.flatten())
        candidate = rounded_head(model, first, target, 7)
    parameters = (first, model.emb.weight, model.emb_up.weight)
    reference_vjp = torch.autograd.grad(rounded_ref / TRACE.ACCUM, parameters)
    values = torch.autograd.grad(candidate / TRACE.ACCUM, parameters)
    measured = {key: TRACE.observe(torch, left, right)
                for key, left, right in zip(('hidden', 'table', 'projection'), reference_vjp, values, strict=True)}
    assert abs(float(candidate.detach()) - float(rounded_ref.detach())) < 1e-6
    labels = target.reshape(-1)
    valid = labels.ge(0)
    labels = labels[valid]
    logprob = logprob.detach()[valid]
    upstream = torch.full((labels.numel(),), 1. / (labels.numel() * TRACE.ACCUM))
    grad = torch.zeros_like(logprob).scatter_(1, labels[:, None], -upstream.bfloat16()[:, None])
    expected = torch.ops.aten._log_softmax_backward_data.default(grad, logprob, 1, torch.bfloat16)
    observed = torch.cat([logprob_vjp(part, labels - 7 * index, part.shape[1], upstream)
                          for index, part in enumerate(logprob.split(7, dim=1))], dim=1)
    vjp_check = TRACE.observe(torch, expected, observed)
    assert not vjp_check['outside_tolerance']
    assert not torch.cuda.is_initialized()
    TRACE.precision.previous.write_new(OUT / 'profile.json', dict(tag=TAG, identity=identity(), input_sha256=signature,
        cpu_targets=6, cpu_native_ce=ref['ce'], cpu_reference_rounded_ce=float(rounded_ref.detach()),
        cpu_rounded_ce=float(candidate.detach()), cpu_head_vjp=measured, cpu_aten_vjp=vjp_check))
    print('P102A_G4_BF16_SOFTMAX_READY', flush=True)
    return 0


def run_rounded(original, x, y):
    model = TRACE.precision.new_model(torch, original).to('cuda')
    torch.cuda.reset_peak_memory_stats()
    with torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
        ce = rounded_head(model, hidden, y, TILE)
    (ce / TRACE.ACCUM).backward()
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated() / TRACE.precision.MIB
    return dict(ce=float(ce.detach()), peak_mib=peak, hidden_sha256=TRACE.digest_tensor(torch, hidden)), {
        name: p.grad.detach().cpu() for name, p in model.named_parameters()}


def actual():
    profile = json.loads((OUT / 'profile.json').read_text())
    assert profile['identity'] == identity() and os.environ['CUBLAS_WORKSPACE_CONFIG'] == strict.WORKSPACE
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * 1024 ** 3
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    prior, original, batch, signature = source_case()
    assert signature == profile['input_sha256']
    x, y = (v.to('cuda') for v in batch)
    TRACE.precision.previous.write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), device=torch.cuda.get_device_name()))
    print('P102A_G4_BF16_SOFTMAX_ACTIVE', os.getpid(), flush=True)
    reference, raw = strict.run_arm(torch, original, x, y, 'reference', 'native', 0)
    assert reference['hidden_sha256'] == prior['arms']['native']['hidden_sha256']
    torch.cuda.empty_cache()
    arms = {'native': reference}
    for key in ('tile', 'rounded'):
        if key == 'tile':
            row, grad = strict.run_arm(torch, original, x, y, key, key, TILE)
        else:
            row, grad = run_rounded(original, x, y)
        assert reference['hidden_sha256'] == row['hidden_sha256']
        row['gradient'] = TRACE.precision.previous.tensor_comparison(torch, raw, grad)
        arms[key] = row
        del grad
        torch.cuda.empty_cache()
        print('P102A_G4_BF16_SOFTMAX_ARM', key, row['gradient']['outside_tolerance'], flush=True)
    del raw
    model = TRACE.precision.new_model(torch, original).to('cuda')
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
    assert TRACE.digest_tensor(torch, hidden) == reference['hidden_sha256']
    ref = TRACE.native_head(torch, model, hidden, y, True)
    details = compare_tiles(ref, ref['projected'], model._emb_w(), y.flatten(), TILE)
    assert profile['identity'] == identity()
    TRACE.precision.previous.write_new(OUT / 'report.json', dict(tag=TAG, arms=arms, logprob_trace=details,
        input_sha256=signature, active_targets=int(y.numel()), optimizer_updates=0, checkpoint_writes=0,
        source=profile['identity']))
    print('P102A_G4_BF16_SOFTMAX_RESULT', details['rounded_nll']['unequal'], flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('prepare', 'actual'))
    a = p.parse_args()
    cutoff = TRACE.precision.previous.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(minutes=5) < cutoff
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if a.phase == 'prepare' else '0')
    if a.phase == 'prepare':
        OUT.mkdir(exist_ok=False)
    else:
        assert not (OUT / 'active.json').exists() and not (OUT / 'report.json').exists()
    os.environ['TINYLM_DIR'] = str(OUT / 'unused_root')
    os.environ['TINYLM_HF'] = str(OUT / 'unused_root/HF')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return (prepare if a.phase == 'prepare' else actual)()


if __name__ == '__main__':
    sys.exit(main())
