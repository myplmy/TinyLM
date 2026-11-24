"""Recompute BF16 logits by position and preserve the native full VJP shapes."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

import torch
from torch.autograd.function import once_differentiable
from torch.nn import functional as F

from scripts import diag_p102a_g4_bf16_vjp_blocks as blocks


TRACE = blocks.TRACE
STRICT = blocks.STRICT
ROOT = blocks.ROOT
TAG = 'p102a_g4_full_delta_v1_20261119'
OUT = blocks.OUT.parent / TAG
PRIOR = blocks.OUT.with_name('p102a_g4_bf16_vjp_blocks_v2_20261119')
SOURCE = Path(__file__).resolve()
DIGEST = TRACE.precision.digest
WRITE = TRACE.precision.previous.write_new


class FullDeltaBF16NLL(blocks.PositionBF16NLL):
    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        projected, table, labels = ctx.saved_tensors
        delta = projected.new_empty((len(labels), len(table)))
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), ctx.rows):
                part = slice(start, start + ctx.rows)
                logprob = blocks.native_logprob(projected[part], table)
                delta[part].copy_(blocks.native_dlogit(logprob, labels[part], upstream[part]))
            projected_gradient = delta @ table
            table_gradient = delta.T @ projected
        return projected_gradient, table_gradient.float(), None, None


def position_loss(model, hidden, targets, rows):
    labels = targets.flatten()
    valid = labels.ne(-100)
    projected = F.linear(hidden, model._emb_up_w().t()).flatten(0, 1)
    if not bool(valid.all()):
        projected, labels = projected[valid], labels[valid]
    return FullDeltaBF16NLL.apply(projected, model._emb_w(), labels, rows).mean()


def identity():
    paths = (SOURCE, PRIOR / 'report.json', PRIOR / 'terminal_readback.json')
    return blocks.identity() | {str(path.relative_to(ROOT)): DIGEST(path) for path in paths}


def source_case():
    report = json.loads((PRIOR / 'report.json').read_bytes())
    terminal = json.loads((PRIOR / 'terminal_readback.json').read_bytes())
    assert terminal['report_sha256'] == DIGEST(PRIOR / 'report.json')
    for collection in ('projected', 'table'):
        assert not report['fixed_reference_logit_vjp'][collection]['full_bf16']['unequal']
    _, original, batch, signature = blocks.source_case()
    assert signature == report['input_sha256']
    return report, original, batch, signature


def prepare():
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    _, _, _, signature = source_case()
    torch.manual_seed(11)
    model = TiedMLPTransformer(TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                                        emb_rank=8, n_prelude=1, n_middle=4, n_coda=1, tie_mlp=True,
                                        mlp_group=2, micro_group=8, max_seq_len=8))
    hidden = torch.randn(2, 4, 32, requires_grad=True)
    targets = torch.tensor([[0, -100, 5, 8], [4, 1, -100, 20]])
    with torch.autocast('cpu', dtype=torch.bfloat16):
        logits = model._head_logits(hidden).flatten(0, 1)
        reference = F.nll_loss(F.log_softmax(logits, dim=1, dtype=torch.bfloat16).float(), targets.flatten())
        candidate = position_loss(model, hidden, targets, 2)
    operands = (hidden, model.emb.weight, model.emb_up.weight)
    left = torch.autograd.grad(reference / TRACE.ACCUM, operands)
    right = torch.autograd.grad(candidate / TRACE.ACCUM, operands)
    comparisons = {
        name: TRACE.observe(torch, a, b)
        for name, a, b in zip(('hidden', 'table', 'projection'), left, right, strict=True)
    }
    assert not torch.cuda.is_initialized() and abs(float((reference - candidate).detach())) <= 1e-6
    assert all(stats['outside_tolerance'] == 0 for stats in comparisons.values())
    WRITE(OUT / 'profile.json', dict(tag=TAG, identity=identity(), input_sha256=signature,
          reference_ce=float(reference.detach()), candidate_ce=float(candidate.detach()), cpu_gradient=comparisons))
    print('P102A_G4_FULL_DELTA_READY', flush=True)


def measure_candidate(original, x, y):
    model = TRACE.precision.new_model(torch, original).to('cuda')
    torch.cuda.reset_peak_memory_stats()
    with torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
        ce = position_loss(model, hidden, y, blocks.ROWS)
    (ce / TRACE.ACCUM).backward()
    torch.cuda.synchronize()
    result = dict(ce=float(ce.detach()), peak_mib=torch.cuda.max_memory_allocated() / TRACE.precision.MIB,
                  hidden_sha256=TRACE.digest_tensor(torch, hidden),
                  delta_bytes=y.numel() * model.cfg.vocab_size * 2,
                  row_block=blocks.ROWS)
    return result, {name: param.grad.detach().cpu() for name, param in model.named_parameters()}


@torch.no_grad()
def compare_head_chunks(original, x, y):
    model = TRACE.precision.new_model(torch, original).to('cuda')
    with torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
    with torch.enable_grad():
        native = TRACE.native_head(torch, model, hidden, y, True)
    return inspect_head(native, model._emb_w(), y.flatten())


def inspect_head(native, table, labels):
    projected = native['projected']
    assert len(projected) == len(labels) and bool(labels.ge(0).all())
    e = table.bfloat16()
    upstream = torch.full((len(labels),), 1.0 / (len(labels) * TRACE.ACCUM), device=labels.device)
    samples = {'logits': [], 'nll': [], 'delta': []}
    with torch.no_grad(), torch.autocast('cuda', enabled=False):
        for start in range(0, len(labels), blocks.ROWS):
            part = slice(start, start + blocks.ROWS)
            logits = F.linear(projected[part], e)
            logprob = F.log_softmax(logits, dim=1)
            nll = -logprob.gather(1, labels[part, None]).flatten()
            delta = blocks.native_dlogit(logprob, labels[part], upstream[part])
            samples['logits'].append(TRACE.observe(torch, native['logits'][part], logits, logits=True))
            samples['nll'].append(TRACE.observe(torch, native['nll'][part], nll, logits=True))
            samples['delta'].append(TRACE.observe(torch, native['grad']['logits'][part], delta))
    return {
        name: {**{key: sum(row[key] for row in rows) for key in ('elements', 'unequal', 'outside_tolerance')},
               'max_abs': max(row['max_abs'] for row in rows)}
        for name, rows in samples.items()
    }


def actual():
    profile = json.loads((OUT / 'profile.json').read_bytes())
    assert profile['identity'] == identity() and os.environ['CUBLAS_WORKSPACE_CONFIG'] == STRICT.WORKSPACE
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * 1024 ** 3
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    prior, original, batch, signature = source_case()
    assert profile['input_sha256'] == signature
    x, y = (tensor.to('cuda') for tensor in batch)
    WRITE(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), device=torch.cuda.get_device_name()))
    print('P102A_G4_FULL_DELTA_ACTIVE', os.getpid(), flush=True)
    reference, left = STRICT.run_arm(torch, original, x, y, 'reference', 'native', 0)
    assert reference['hidden_sha256'] == prior['reference']['hidden_sha256']
    torch.cuda.empty_cache()
    candidate, right = measure_candidate(original, x, y)
    assert candidate['hidden_sha256'] == reference['hidden_sha256']
    gradient = TRACE.precision.previous.tensor_comparison(torch, left, right)
    byte_mismatches = [name for name, value in left.items() if not torch.equal(
        value.contiguous().view(torch.uint8), right[name].contiguous().view(torch.uint8))]
    del left, right
    torch.cuda.empty_cache()
    chunks = compare_head_chunks(original, x, y)
    assert profile['identity'] == identity()
    WRITE(OUT / 'report.json', dict(tag=TAG, reference=reference, candidate=candidate,
          gradient=gradient, gradient_byte_mismatches=byte_mismatches, chunks=chunks,
          input_sha256=signature, source=profile['identity'], optimizer_updates=0, checkpoint_writes=0))
    print('P102A_G4_FULL_DELTA_RESULT', gradient['outside_tolerance'], len(byte_mismatches), flush=True)


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
    (prepare if args.phase == 'prepare' else actual)()


if __name__ == '__main__':
    main()
