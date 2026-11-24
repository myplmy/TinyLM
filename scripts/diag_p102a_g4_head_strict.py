"""Separate CE dtype and body nondeterminism without applying optimizer updates."""

import argparse
from datetime import datetime, timedelta
import json
import os
import sys

from scripts import diag_p102a_g4_head_trace as trace


ROOT = trace.ROOT
PREVIOUS = trace.OUT / 'report.json'
TERMINAL = trace.OUT / 'terminal_readback.json'
TAG = 'p102a_g4_head_strict_v1_20261119'
OUT = trace.OUT.parent / TAG
SOURCE = ROOT / 'scripts/diag_p102a_g4_head_strict.py'
WORKSPACE = ':4096:8'
POSITION_CHUNK = 1024


def identity():
    paths = (PREVIOUS, TERMINAL, SOURCE, ROOT / 'tinylm/train/alm.py')
    return trace.identity() | {str(p.relative_to(ROOT)): trace.precision.digest(p) for p in paths}


def head_loss(model, hidden, targets, arm, chunk):
    from torch.nn import functional as F
    from tinylm.train import alm, streaming_head

    if arm in ('native', 'explicit'):
        logits = model._head_logits(hidden).flatten(0, 1)
        logits = logits.float() if arm == 'explicit' else logits
        return F.cross_entropy(logits, targets.flatten())
    if arm == 'position':
        nll, valid = alm.target_nll(model, hidden, targets, chunk=chunk, checkpoint_head=True)
    else:
        assert arm == 'tile'
        nll, valid = streaming_head.target_nll(model, hidden, targets, chunk=targets.numel(), tile=chunk)
    return nll.sum() / valid.sum()


def original_case(torch):
    old = json.loads(PREVIOUS.read_text())
    terminal = json.loads(TERMINAL.read_text())
    assert terminal['report_sha256'] == trace.precision.digest(PREVIOUS)
    assert old['optimizer_updates'] == 0 and terminal['pid'] == 1371967
    original = json.loads(trace.precision.FILES[2].read_text())['reference']
    batches, hashes = trace.precision.original_inputs(torch, original)
    assert old['input_sha256'] == hashes[0]
    return original, batches[0], hashes[0]


def prepare(torch):
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    _, _, signature = original_case(torch)
    torch.manual_seed(11)
    model = TiedMLPTransformer(TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                                        emb_rank=8, n_prelude=1, n_middle=4, n_coda=1, tie_mlp=True,
                                        mlp_group=2, micro_group=8, max_seq_len=8))
    hidden = torch.randn(2, 4, 32, requires_grad=True)
    target = torch.tensor([[0, -100, 5, 8], [4, 1, -100, 20]])
    params = (hidden, model.emb.weight, model.emb_up.weight)
    base = head_loss(model, hidden, target, 'explicit', 7)
    derivatives = torch.autograd.grad(base, params)
    results = {}
    for arm, chunk in (('position', 2), ('tile', 7)):
        value = head_loss(model, hidden, target, arm, chunk)
        assert abs(float(value.detach()) - float(base.detach())) < 2e-6
        observed = torch.autograd.grad(value, params)
        results[arm] = [trace.observe(torch, a, b) for a, b in zip(derivatives, observed, strict=True)]
        assert all(not z['outside_tolerance'] for z in results[arm])
    assert not torch.cuda.is_initialized()
    trace.precision.previous.write_new(OUT / 'profile.json', dict(tag=TAG, identity=identity(), input_sha256=signature,
                                                                 cpu_masks=6, cpu_comparison=results))
    print('P102A_G4_HEAD_STRICT_READY', flush=True)
    return 0


def nll_dtype_control(torch, model, hidden, target):
    from torch.nn import functional as F

    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
        logits = model._head_logits(hidden).flatten(0, 1)
        base = F.cross_entropy(logits, target.flatten(), reduction='none')
        clear = F.cross_entropy(logits.float(), target.flatten(), reduction='none')
        return dict(logits_dtype=str(logits.dtype), native_nll_dtype=str(base.dtype), explicit_nll_dtype=str(clear.dtype),
                    means=[float(base.float().mean()), float(clear.float().mean())],
                    explicit=trace.observe(torch, base, clear, logits=True),
                    rounded_explicit=trace.observe(torch, base, clear.bfloat16(), logits=True))


def run_arm(torch, original, x, y, label, policy, chunk):
    model = trace.precision.new_model(torch, original).to('cuda')
    torch.cuda.reset_peak_memory_stats()
    with torch.autocast('cuda', dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
        ce = head_loss(model, hidden, y, policy, chunk)
    (ce / trace.ACCUM).backward()
    torch.cuda.synchronize()
    peak = torch.cuda.max_memory_allocated() / trace.precision.MIB
    grad = {name: param.grad.detach().cpu() for name, param in model.named_parameters()}
    result = dict(ce=float(ce.detach()), peak_mib=peak, hidden_sha256=trace.digest_tensor(torch, hidden),
                  label=label, policy=policy)
    if label == 'native':
        result['nll_dtype_control'] = nll_dtype_control(torch, model, hidden.detach(), y)
    return result, grad


def actual(torch):
    profile = json.loads((OUT / 'profile.json').read_text())
    assert profile['identity'] == identity()
    assert os.environ['CUBLAS_WORKSPACE_CONFIG'] == WORKSPACE
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * 1024 ** 3
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    original, batch, signature = original_case(torch)
    assert profile['input_sha256'] == signature
    x, y = (v.to('cuda') for v in batch)
    trace.precision.previous.write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), device=torch.cuda.get_device_name()))
    print('P102A_G4_HEAD_STRICT_ACTIVE', os.getpid(), flush=True)
    labels = (('native', 'native', 0, None), ('repeat', 'native', 0, 'native'),
              ('explicit', 'explicit', 0, 'native'), ('tile', 'tile', trace.precision.previous.TILE, 'explicit'),
              ('position', 'position', POSITION_CHUNK, 'explicit'))
    arms, references = {}, {}
    for label, policy, chunk, ref_label in labels:
        row, gradients = run_arm(torch, original, x, y, label, policy, chunk)
        if ref_label is not None:
            base = arms[ref_label]
            assert row['hidden_sha256'] == base['hidden_sha256'], 'common body did not reproduce'
            row['gradient_reference'] = ref_label
            row['gradients'] = trace.precision.previous.tensor_comparison(torch, references[ref_label], gradients)
            row['ce_delta'] = row['ce'] - base['ce']
        if label in ('native', 'explicit'):
            references[label] = gradients
        arms[label] = row
        del gradients
        torch.cuda.empty_cache()
        print('P102A_G4_HEAD_STRICT_ARM', label, row['ce'], flush=True)
    assert profile['identity'] == identity()
    trace.precision.previous.write_new(OUT / 'report.json', dict(tag=TAG, arms=arms, source=profile['identity'],
            active_targets=int(y.numel()), input_sha256=signature, optimizer_updates=0, checkpoint_writes=0,
            deterministic=dict(mode=torch.are_deterministic_algorithms_enabled(), workspace=WORKSPACE,
                               cudnn_sdp=torch.backends.cuda.cudnn_sdp_enabled(), matmul=torch.get_float32_matmul_precision())))
    print('P102A_G4_HEAD_STRICT_RESULT', arms['repeat']['gradients']['outside_tolerance'], flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('prepare', 'actual'))
    a = p.parse_args()
    cutoff = trace.precision.previous.CUTOFF
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
