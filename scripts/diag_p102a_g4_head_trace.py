"""Observe the actual native and tiled NLL forward/backward on a fixed G4 input."""

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
import sys
from unittest.mock import patch

from scripts import diag_p102a_g4_head_precision as precision


ROOT = precision.ROOT
TAG = 'p102a_g4_head_trace_v1_20261119'
OUT = precision.OUT.parent / TAG
PREVIOUS = precision.OUT / 'report.json'
TERMINAL = precision.OUT / 'terminal_readback.json'
SOURCE = ROOT / 'scripts/diag_p102a_g4_head_trace.py'
ACCUM = precision.previous.ACCUM


def identity():
    return precision.identities() | {str(p.relative_to(ROOT)): precision.digest(p)
                                     for p in (SOURCE, PREVIOUS, TERMINAL)}


def digest_tensor(torch, value):
    return sha256(value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest().upper()


def observe(torch, reference, candidate, *, logits=False):
    assert reference.shape == candidate.shape
    left, right = reference.detach().float(), candidate.detach().float()
    assert torch.isfinite(left).all() and torch.isfinite(right).all()
    delta = (left - right).abs()
    atol, rtol = (1e-5, 1e-4) if logits else (2e-6, 1e-5)
    return dict(elements=delta.numel(), unequal=int(delta.ne(0).sum()),
                outside_tolerance=int((delta > atol + rtol * left.abs()).sum()),
                max_abs=float(delta.max()))


def native_head(torch, model, hidden, targets, amp):
    from torch.nn import functional as F

    h = hidden.detach().requires_grad_()
    labels = targets.reshape(-1)
    valid = labels.ne(-100)
    outputs = []
    original = F.linear

    def capture(*args, **kwargs):
        out = original(*args, **kwargs)
        outputs.append(out)
        return out

    with torch.autocast(h.device.type, dtype=torch.bfloat16, enabled=amp):
        with patch.object(F, 'linear', capture):
            logits = model._head_logits(h if amp else h.float()).reshape(labels.numel(), -1)
        ce = F.cross_entropy(logits, labels)
        nll = F.cross_entropy(logits.detach(), labels, reduction='none')
    assert len(outputs) == 2
    projected = outputs[0]
    tensors = (logits, projected, h, model.emb.weight, model.emb_up.weight)
    values = torch.autograd.grad(ce / ACCUM, tensors)
    valid_all = bool(valid.all())
    grad = dict(zip(('logits', 'projected', 'hidden', 'table', 'projection'), values, strict=True))
    if not valid_all:
        grad['logits'] = grad['logits'][valid]
    flat = projected.detach().reshape(labels.numel(), -1)
    dp = grad['projected'].reshape_as(flat)
    return dict(ce=float(ce.detach()), nll=nll.detach(), logits=logits.detach() if valid_all else logits.detach()[valid],
                projected=flat if valid_all else flat[valid],
                projected_gradient=dp if valid_all else dp[valid], grad=grad)


class TiledTrace:
    """Forward/recompute linear and exact dlogit operand of tiled projected VJP."""

    def __init__(self, torch, ref, hidden_dim, tile):
        from torch.nn import functional as F

        self.torch, self.ref, self.hidden_dim, self.tile = torch, ref, hidden_dim, tile
        self.linear = F.linear
        self.matmul = torch.Tensor.__matmul__
        self.forward = True
        self.projection = None
        self.stats = {key: [] for key in ('forward_logits', 'recomputed_logits', 'logit_vjp')}
        self.native_inputs = {}

    def record(self, key, value, *, logits):
        panel = self.stats[key]
        start = len(panel) * self.tile
        stop = start + value.shape[1]
        ref = self.ref['logits'] if logits else self.ref['grad']['logits']
        panel.append(observe(self.torch, ref[:, start:stop], value, logits=logits))

    def capture_linear(self, x, weight, bias=None):
        value = self.linear(x, weight, bias)
        if self.forward and x.shape[-1] == self.hidden_dim:
            assert self.projection is None
            self.projection = value
        else:
            key = 'forward_logits' if self.forward else 'recomputed_logits'
            modes = (str(x.dtype), str(weight.dtype), str(value.dtype),
                     self.torch.is_autocast_enabled(x.device.type))
            assert self.native_inputs.setdefault(key, modes) == modes
            self.record(key, value, logits=True)
        return value

    def capture_matmul(self, x, weight):
        if (not self.forward and x.ndim == weight.ndim == 2
                and x.shape[0] == self.ref['projected'].shape[0]
                and weight.shape == (x.shape[1], self.ref['projected'].shape[1])):
            self.record('logit_vjp', x, logits=False)
        return self.matmul(x, weight)

    def summary(self):
        expected = (self.ref['logits'].shape[1] + self.tile - 1) // self.tile
        assert all(len(values) == expected for values in self.stats.values())
        return {key: dict(tiles=len(values), elements=sum(v['elements'] for v in values),
                          unequal=sum(v['unequal'] for v in values),
                          outside_tolerance=sum(v['outside_tolerance'] for v in values),
                          max_abs=max(v['max_abs'] for v in values)) for key, values in self.stats.items()}


def tiled_head(torch, model, hidden, targets, amp, tile, ref):
    from torch.nn import functional as F
    from tinylm.train.streaming_head import target_nll

    h = hidden.detach().requires_grad_()
    trace = TiledTrace(torch, ref, h.shape[-1], tile)

    def capture_matmul(x, weight):
        return trace.capture_matmul(x, weight)

    with patch.object(F, 'linear', trace.capture_linear), patch.object(torch.Tensor, '__matmul__', capture_matmul):
        with torch.autocast(h.device.type, dtype=torch.bfloat16, enabled=amp):
            nll, valid = target_nll(model, h if amp else h.float(), targets, chunk=targets.numel(), tile=tile)
            ce = nll.sum() / valid.sum()
        trace.forward = False
        tensors = (trace.projection, h, model.emb.weight, model.emb_up.weight)
        grads = torch.autograd.grad(ce / ACCUM, tensors)
    comparisons = {key: observe(torch, ref['grad'][key], value)
                   for key, value in zip(('hidden', 'table', 'projection'), grads[1:], strict=True)}
    result = dict(reference_ce=ref['ce'], tiled_ce=float(ce.detach()), logit_dtype=str(ref['logits'].dtype),
                  loss_dtype=str(ce.dtype), operand_formats=trace.native_inputs, tiles=trace.summary(),
                  per_target_nll=observe(torch, ref['nll'], nll.detach().reshape(-1), logits=True),
                  projected=observe(torch, ref['projected'], trace.projection, logits=True),
                  projected_vjp=observe(torch, ref['projected_gradient'], grads[0]),
                  output_vjp=comparisons)
    return result, dict(zip(('hidden', 'table', 'projection'), grads[1:], strict=True))


def shared_input(torch, model, hidden, native, tiled):
    parameters = (model.emb.weight, model.emb_up.weight)
    gradients = [torch.autograd.grad(hidden, parameters, value['hidden'], retain_graph=True)
                 for value in (native, tiled, native)]
    result = {}
    for name, a, b, c in zip(('table', 'projection'), *gradients, strict=True):
        result[name] = dict(input_vjp=observe(torch, a, b), repeat_reference=observe(torch, a, c),
                            sum_input_output=observe(torch, a + native[name], b + tiled[name]))
    return result


def prepare(torch):
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    old = json.loads(PREVIOUS.read_text())
    assert json.loads(TERMINAL.read_text())['report_sha256'] == precision.digest(PREVIOUS)
    original = json.loads(precision.FILES[2].read_text())['reference']
    _, hashes = precision.original_inputs(torch, original)
    assert hashes == old['batch_sha256']
    torch.manual_seed(7)
    model = TiedMLPTransformer(TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                                        emb_rank=8, n_prelude=1, n_middle=4, n_coda=1,
                                        tie_mlp=True, mlp_group=2, micro_group=8, max_seq_len=8))
    hidden = torch.randn(2, 4, 32)
    target = torch.tensor([[0, -100, 5, 8], [4, 1, -100, 20]])
    ref = native_head(torch, model, hidden, target, False)
    observed, _ = tiled_head(torch, model, hidden, target, False, 7, ref)
    assert len(observed['tiles']) == 3 and all(x['elements'] == 6 * 35 for x in observed['tiles'].values())
    assert all(not v['outside_tolerance'] for v in observed['output_vjp'].values())
    assert not observed['per_target_nll']['outside_tolerance'] and not torch.cuda.is_initialized()
    precision.previous.write_new(OUT / 'profile.json', dict(tag=TAG, identity=identity(), batch_sha256=hashes[0],
                                                            cpu=observed, active_targets=8192, optimizer_updates=0))
    print('P102A_G4_HEAD_TRACE_READY', flush=True)
    return 0


def actual(torch):
    profile = json.loads((OUT / 'profile.json').read_text())
    assert profile['identity'] == identity()
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * 1024 ** 3
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision('high')
    old = json.loads(PREVIOUS.read_text())
    original = json.loads(precision.FILES[2].read_text())['reference']
    batches, hashes = precision.original_inputs(torch, original)
    assert profile['batch_sha256'] == hashes[0]
    precision.previous.write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), device=torch.cuda.get_device_name()))
    print('P102A_G4_HEAD_TRACE_ACTIVE', os.getpid(), flush=True)
    x, y = (v.to('cuda') for v in batches[0])
    model = precision.new_model(torch, original).to('cuda')
    with torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
    signature = digest_tensor(torch, hidden)
    result = {}
    for key, amp in (('bf16_amp', True), ('fp32_head_high', False)):
        prior = old['comparisons'][key]
        assert signature == prior['reference']['hidden_sha256'][0]
        ref = native_head(torch, model, hidden, y, amp)
        trace, tile = tiled_head(torch, model, hidden, y, amp, precision.previous.TILE, ref)
        assert abs(ref['ce'] - prior['head_only']['reference_ce']) <= 2e-6
        assert abs(trace['tiled_ce'] - prior['head_only']['tile_ce']) <= 2e-6
        head = ref['grad']
        del ref
        del head['logits'], head['projected']
        trace['shared'] = shared_input(torch, model, hidden, head, tile)
        result[key] = trace
        torch.cuda.empty_cache()
        print('P102A_G4_HEAD_TRACE_PAIR', key, flush=True)
    assert profile['identity'] == identity()
    precision.previous.write_new(OUT / 'report.json', dict(tag=TAG, cases=result, hidden_sha256=signature,
        hidden_dtype=str(hidden.dtype), input_sha256=hashes[0], active_targets=int(y.numel()),
        identity=profile['identity'], optimizer_updates=0, checkpoint_writes=0, quality='NOT_RUN'))
    print('P102A_G4_HEAD_TRACE_RESULT', {k: v['tiles']['forward_logits']['unequal'] for k, v in result.items()}, flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('prepare', 'actual'))
    a = p.parse_args()
    cutoff = precision.previous.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(minutes=5) < cutoff
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if a.phase == 'prepare' else '0')
    if a.phase == 'prepare':
        OUT.mkdir(exist_ok=False)
    else:
        assert not (OUT / 'active.json').exists() and not (OUT / 'report.json').exists()
    os.environ['TINYLM_DIR'] = str(OUT / 'unused_root')
    os.environ['TINYLM_HF'] = str(OUT / 'unused_root/HF')
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return (prepare if a.phase == 'prepare' else actual)(torch)


if __name__ == '__main__':
    sys.exit(main())
