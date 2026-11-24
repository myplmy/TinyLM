"""Test fixed G4 R2 document visibility and its adaptive FP32 head on CUDA."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import torch
import torch.nn.functional as F

from scripts import diag_p102a_adaptive_fp32_recompute as head
from scripts import p070b_cla_routes as cla
from tinylm.model import transformer, visibility
from tinylm.train.hybrid_mntp import causal_batch, mntp_batch, objective_mean


ROOT = head.ROOT
TAG = 'p107_g4_r2_visibility_v1_20261119'
R1 = head.OUT
OUT = R1.with_name(TAG)
PHASES = ('probe', 'reference', 'recompute')
SOURCES = (*head.SOURCES, str(Path(__file__).resolve().relative_to(ROOT)),
           'scripts/p070b_cla_routes.py', 'test_plan/P107_문서가시성과-shift를-분리한-causal-MNTP-계약.md',
           str((R1 / 'profile.json').relative_to(ROOT)), str((R1 / 'report.json').relative_to(ROOT)))


def prepare_r2(mask, tokens, cfg, schedule, **kwargs):
    first = list(range(cfg.n_prelude))
    middle = list(range(cfg.n_prelude, cfg.n_prelude + cfg.n_middle))
    last = list(range(cfg.n_prelude + cfg.n_middle, cfg.n_layers))
    if ((cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.cla_group) != (2, 12, 2, 4, 2)
            or not cfg.tie_mlp or cfg.mlp_split or cfg.train_repeat != 2.0 or cfg.infer_repeat != 1.0
            or cfg.repeat_mode != 'uniform' or cfg.repeat_kv_reuse
            or list(schedule) != first + middle + middle + last):
        raise ValueError('experimental visibility requires the fixed G4 R2 sequence')
    # The schedule was checked above. Keep the native flag, tensor, and snapshot checks.
    return visibility.prepare_visibility(mask, tokens, cfg, range(cfg.n_layers), **kwargs)


def observe(model, batch, docs, own_doc, *, open_boundary=False, mutate_after=False):
    device = batch.inputs.device
    own = docs.eq(own_doc)
    saved_input = []
    original_embedding = F.embedding

    def embedding(*args, **kwargs):
        output = original_embedding(*args, **kwargs)
        saved_input.append(output)
        return output

    mask = batch.attention_mask.clone()
    if open_boundary:
        mask.fill_(True)
        if batch.objective == 'CAUSAL':
            mask.tril_()
    targets = batch.targets.masked_fill(~own[None, :], -100)
    amp = torch.autocast('cuda', dtype=torch.bfloat16) if device.type == 'cuda' else nullcontext()
    model.clear_quant()
    with patch.object(F, 'embedding', embedding), amp:
        logits = model(batch.inputs, attention_mask=mask)
        loss, count = objective_mean(logits, targets)
    assert count > 0 and len(saved_input) == 1
    if mutate_after:
        mask.fill_(True)
    gradient = torch.autograd.grad(loss, saved_input[0])[0].detach()
    return logits[:, own, :].detach(), gradient, int(count)


def probe(model, device):
    cfg = model.cfg
    docs = torch.tensor([[0] * 7 + [1] * 8 + [-1] * 2], device=device)
    tokens = torch.arange(35, 52, device=device)[None, :].masked_fill(docs.lt(0), 0)
    selected = torch.zeros_like(tokens, dtype=torch.bool)
    selected[:, [2, 5, 9, 12]] = True
    schedule = model.visit_schedule()
    topology = cla.trace(cfg, model.owner, schedule)
    assert topology['visits'] == 28 and topology['kv_entries'] == 14
    result = {}
    for kind in ('causal', 'masked'):
        def batch(raw):
            if kind == 'causal':
                return causal_batch(raw, docs, vocab_size=cfg.vocab_size)
            return mntp_batch(raw, docs, selected, vocab_size=cfg.vocab_size)

        original = batch(tokens)
        result[kind] = []
        for target in (0, 1):
            edit = tokens.clone()
            edit[docs.eq(1 - target)] += 17
            modified = batch(edit)
            own = docs[0, :-1].eq(target)
            baseline, grad, count = observe(model, original, docs[0, :-1], target)
            perturbed, perturbed_grad, _ = observe(model, modified, docs[0, :-1], target)
            _, changed_mask_grad, _ = observe(model, original, docs[0, :-1], target, mutate_after=True)
            masked_diff = float((baseline.float() - perturbed.float()).abs().max())
            outside = float(grad[:, ~own].abs().max())
            assert masked_diff == outside == 0. and torch.equal(grad, perturbed_grad)
            assert torch.equal(grad, changed_mask_grad) and bool(grad[:, own].ne(0).any())
            checked = dict(doc=target, targets=count, cross_document_logit_max=masked_diff,
                           forbidden_gradient_max=outside, mask_snapshot_exact=True)
            if target == 1 or kind == 'masked':
                open_a, open_grad, _ = observe(model, original, docs[0, :-1], target, open_boundary=True)
                open_b, _, _ = observe(model, modified, docs[0, :-1], target, open_boundary=True)
                diff = float((open_a.float() - open_b.float()).abs().max())
                leak = float(open_grad[:, docs[0, :-1].eq(1 - target)].abs().max())
                assert diff > 0. and leak > 0.
                checked.update(open_boundary_logit_max=diff, open_boundary_gradient_max=leak)
            result[kind].append(checked)
    example = causal_batch(tokens, docs, vocab_size=cfg.vocab_size)
    wrong = list(schedule)
    wrong[17], wrong[18] = wrong[18], wrong[17]
    for fn, order in ((visibility.prepare_visibility, schedule), (prepare_r2, wrong)):
        try:
            fn(example.attention_mask, example.inputs, cfg, order)
        except ValueError:
            pass
        else:
            raise AssertionError('native R2 or changed R2 order was not refused')
    return dict(visits=topology['visits'], kv=topology['kv_entries'], rejected_orders=2, cases=result)


def make_model(device):
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    torch.manual_seed(1337)
    if device == 'cuda':
        cfg, state, _ = head.warm.load_parent(torch)
    else:
        cfg = TMTConfig(vocab_size=96, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=16,
                        n_q_heads=4, n_kv_heads=2, n_prelude=2, n_middle=12, n_coda=2,
                        tie_mlp=True, mlp_group=4, cla_group=2, micro_group=8, grad_checkpoint=True)
        state = None
    cfg.train_repeat = 2.0
    model = TiedMLPTransformer(cfg).to(device).train()
    if state is not None:
        model.load_state_dict(state, strict=True)
    model.set_anneal(1.)
    return model


def run(frozen):
    idle = head.prior.previous.shapes.idle
    exits, reports = {}, {}
    for phase in PHASES:
        if (OUT / 'STOP').exists() or not idle() or (phase != 'probe' and exits.get('probe') != 0):
            exits[phase] = None
            break
        call = ['timeout', '--kill-after=5s', '90s' if phase != 'probe' else '25s',
                sys.executable, '-u', '-B', '-X', 'utf8', '-m', 'scripts.diag_p107_g4_r2_visibility', 'worker', phase]
        exits[phase] = subprocess.run(call, cwd=ROOT).returncode
        print('P107_G4_R2_EXIT', phase, exits[phase], flush=True)
        if exits[phase] == 0:
            reports[phase] = json.loads((OUT / f'{phase}.json').read_bytes())
    assert idle() and frozen['contract'] == head.expected()
    checks = {}
    if set(reports) == set(PHASES):
        a, b = reports['reference'], reports['recompute']
        checks = dict(initial=a['initial'] == b['initial'], observations=a['observations'] == b['observations'],
            losses=[row['loss'] for row in a['updates']] == [row['loss'] for row in b['updates']],
            components={name: value == b['states'][name] for name, value in a['states'].items()})
    head.WRITE(OUT / 'report.json', dict(tag=TAG, exits=exits, checks=checks, reports=reports, gpu_returned=True))
    print('P107_G4_R2_COMPLETE', checks, flush=True)
    return 0 if checks and all(all(v.values()) if isinstance(v, dict) else v for v in checks.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run', 'worker'))
    parser.add_argument('phase', nargs='?', choices=PHASES)
    args = parser.parse_args()
    if (args.mode == 'worker') != (args.phase is not None):
        parser.error('one explicit phase belongs to the worker')
    assert datetime.now(head.warm.CUTOFF.tzinfo) + timedelta(minutes=5) < head.warm.CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.mode == 'prepare' else '0')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from torch.nn.attention import SDPBackend, sdpa_kernel
    import tinylm.model as package

    original = package.TiedMLPTransformer

    def g4_r2(cfg):
        cfg.train_repeat = 2.0
        return original(cfg)

    with (patch.multiple(head, TAG=TAG, OUT=OUT, SOURCES=SOURCES),
          patch.object(transformer, 'prepare_visibility', prepare_r2), sdpa_kernel(SDPBackend.MATH)):
        profile = OUT / 'profile.json'
        contract = head.expected()
        if args.mode == 'prepare':
            baseline = json.loads((R1 / 'profile.json').read_bytes())
            r1 = json.loads((R1 / 'report.json').read_bytes())
            assert contract['updates'] == baseline['contract']['updates'] and r1['comparison']['same_losses']
            record = probe(make_model('cpu'), 'cpu')
            assert not torch.cuda.is_initialized()
            OUT.mkdir(exist_ok=False)
            head.WRITE(profile, dict(contract=contract, cpu=record))
            print('P107_G4_R2_CPU_READY', record, flush=True)
            return 0
        frozen = json.loads(profile.read_bytes())
        assert frozen['contract'] == contract and os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
        if args.mode == 'run':
            return run(frozen)
        if args.phase == 'probe':
            if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 12 * (1 << 30):
                raise RuntimeError('isolated GPU with 12 GiB free required')
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            torch.use_deterministic_algorithms(True)
            result = probe(make_model('cuda'), 'cuda')
            head.WRITE(OUT / 'probe.json', result)
            print('P107_G4_R2_CUDA_VISIBILITY', result, flush=True)
            return 0
        with patch.object(package, 'TiedMLPTransformer', g4_r2):
            return head.worker(args.phase, contract)


if __name__ == '__main__':
    sys.exit(main())
