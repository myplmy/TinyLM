"""Check preserved-row BF16 CE in native masked and wider G4 training."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from unittest.mock import patch

import torch
from torch.autograd.function import once_differentiable
from torch.nn import functional as F

from scripts import diag_p102a_g4_full_delta_train as previous


BASE = previous.BASE
LOSS = previous.loss
ROWS = LOSS.blocks.ROWS
ROOT = LOSS.ROOT
TAG = 'p102a_g4_recompute_shapes_v1_20261119'
OUT = previous.OUT.with_name(TAG)
SOURCE = Path(__file__).resolve()
LAYOUT = {'masked': (8, 2), 'wide': (16, 1)}
ARM_NAMES = tuple(f'{layout}_{head}' for layout in LAYOUT for head in ('reference', 'recompute'))
TARGETS = BASE.STEPS * 16 * BASE.WIDTH
IGNORE = -100


class PreservedRowNLL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, projected, table, targets, rows):
        assert projected.dtype == torch.bfloat16 and table.dtype == torch.float32
        e = table.bfloat16()
        keep = targets.ne(IGNORE)
        labels = targets.masked_fill(~keep, 0)
        nll = projected.new_empty((len(labels),), dtype=torch.float32)
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), rows):
                part = slice(start, start + rows)
                logp = LOSS.blocks.native_logprob(projected[part], e)
                nll[part] = -logp.gather(1, labels[part, None]).flatten().float()
        ctx.save_for_backward(projected, e, labels, keep)
        ctx.rows = rows
        return nll.masked_fill(~keep, 0.0)

    @staticmethod
    @once_differentiable
    def backward(ctx, upstream):
        projected, table, labels, keep = ctx.saved_tensors
        delta = projected.new_empty((len(labels), len(table)))
        upstream = upstream.masked_fill(~keep, 0)
        with torch.autocast(projected.device.type, enabled=False):
            for start in range(0, len(labels), ctx.rows):
                part = slice(start, start + ctx.rows)
                logp = LOSS.blocks.native_logprob(projected[part], table)
                block = LOSS.blocks.native_dlogit(logp, labels[part], upstream[part])
                delta[part].copy_(block.masked_fill_(~keep[part, None], 0))
            projected_gradient = delta @ table
            table_gradient = delta.T @ projected
        return projected_gradient, table_gradient.float(), None, None


def token_nll(model, hidden, targets, rows=ROWS):
    projected = F.linear(hidden, model._emb_up_w().t()).flatten(0, 1)
    return PreservedRowNLL.apply(projected, model._emb_w(), targets.reshape(-1), rows).reshape_as(targets)


def add_mask(targets):
    row = torch.arange(len(targets), device=targets.device)[:, None]
    col = torch.arange(targets.shape[1], device=targets.device)[None, :]
    keep = (row > 0) & (col >= 128 + 64 * row.remainder(4)) & col.remainder(113).ne(0)
    return targets.masked_fill(~keep, IGNORE)


def identity():
    paths = (SOURCE, previous.OUT / 'report.json', previous.OUT / 'terminal_readback.json')
    return previous.identity() | {str(path.relative_to(ROOT)): LOSS.DIGEST(path) for path in paths}


def command(name):
    layout, head = name.split('_')
    micro, accum = LAYOUT[layout]
    argv = BASE.cli_args('tile' if head == 'recompute' else 'reference')
    for flag, value in (('--tag', f'{TAG}_{name}'), ('--micro-bs', str(micro)), ('--accum', str(accum))):
        argv[argv.index(flag) + 1] = value
    return argv


def check_call(name, args, kwargs):
    layout, head = name.split('_')
    micro, accum = LAYOUT[layout]
    assert args[:8] == ('m100s12_g4', 'tied', 'synthetic', BASE.POOL, BASE.STEPS, micro, BASE.WIDTH, accum)
    assert args[8:13] == (1e-3, 1, False, True, False)
    assert kwargs['pool_tokens'] == BASE.POOL and kwargs['exact_cache'] and not kwargs['kd']
    assert kwargs['train_repeat'] == 2 and not kwargs.get('ce_chunk')
    assert kwargs['ce_vocab_tile'] == (BASE.TILE if head == 'recompute' else 0)


def cpu_loss_fixture():
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    torch.manual_seed(31)
    model = TiedMLPTransformer(TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
                                        emb_rank=8, n_prelude=1, n_middle=4, n_coda=1, tie_mlp=True,
                                        mlp_group=2, micro_group=8, max_seq_len=8))
    hidden = torch.randn(2, 4, 32, requires_grad=True)
    target = torch.tensor([[IGNORE, IGNORE, 5, 8], [4, IGNORE, 1, 20]])
    valid = target.ne(IGNORE)
    with torch.autocast('cpu', dtype=torch.bfloat16):
        logits = model._head_logits(hidden).flatten(0, 1)
        logp = F.log_softmax(logits, dim=1, dtype=torch.bfloat16).float()
        reference = F.nll_loss(logp, target.flatten(), reduction='none').reshape_as(target)
        observed = token_nll(model, hidden, target, rows=2)
    operands = (hidden, model.emb.weight, model.emb_up.weight)
    reference_ce = reference.sum() / valid.sum()
    observed_ce = observed.sum() / valid.sum()
    left = torch.autograd.grad(reference_ce / 2, operands)
    right = torch.autograd.grad(observed_ce / 2, operands)
    gradient = {name: LOSS.TRACE.observe(torch, a, b)
                for name, a, b in zip(('hidden', 'table', 'projection'), left, right, strict=True)}
    assert torch.equal(reference, observed) and bool(observed[~valid].eq(0).all())
    assert all(not item['outside_tolerance'] for item in gradient.values())
    return dict(nll=observed.detach().tolist(), ce=float(observed_ce.detach()), supervised=int(valid.sum()),
                gradient=gradient)


def prepare():
    from tinylm import cli
    from tinylm.data import Loader
    import tinylm.train as train_package

    former = json.loads((previous.OUT / 'report.json').read_bytes())
    end = json.loads((previous.OUT / 'terminal_readback.json').read_bytes())
    assert end['report_sha256'] == LOSS.DIGEST(previous.OUT / 'report.json') and former['numerical_pass']
    meta = json.loads((previous.CACHE / 'meta.json').read_bytes())
    assert meta['dir'] == str(previous.CACHE) and meta['train'] >= 2 * TARGETS
    narrow = Loader('train', 8, BASE.WIDTH, 'cpu', previous.CACHE)
    wide = Loader('train', 16, BASE.WIDTH, 'cpu', previous.CACHE)
    sampler_start = narrow.rng.bit_generator.state
    draw_sha, supervised = [], []
    for _ in range(BASE.STEPS):
        a, b, c = narrow(), narrow(), wide()
        assert all(torch.equal(torch.cat((i, j)), k) for i, j, k in zip(a, b, c, strict=True))
        assert torch.equal(c[0][:, 1:], c[1][:, :-1])
        draw_sha.append(previous.state_sha(c))
        for _, y in (a, b):
            masked = add_mask(y)
            keep = masked.ne(IGNORE)
            assert torch.equal(masked[keep], y[keep]) and not bool(keep[0].any())
            supervised.append(int(keep.sum()))
    assert narrow.rng.bit_generator.state == wide.rng.bit_generator.state
    commands = {arm: command(arm) for arm in ARM_NAMES}
    for arm, argv in commands.items():
        with patch.object(sys, 'argv', argv), patch.object(train_package, 'train') as stub:
            cli.main()
        stub.assert_called_once()
        check_call(arm, *stub.call_args)
    report = dict(tag=TAG, identity=identity(), data=meta, targets=TARGETS, commands=commands,
                  sampler_start=sampler_start, sampler_end=wide.rng.bit_generator.state,
                  owned_inputs_by_update=draw_sha, masked_micro_supervised=supervised, cpu=cpu_loss_fixture())
    assert not torch.cuda.is_initialized()
    BASE.write_new(OUT / 'profile.json', report)
    print('P102A_G4_RECOMPUTE_SHAPES_READY', TARGETS, sum(supervised), flush=True)


def train_arm(profile, name):
    from tinylm import cli
    from tinylm.train import muon, trainer
    import tinylm.train as train_package

    layout, head = name.split('_')
    micro, accum = LAYOUT[layout]
    directory = OUT / name
    ckpt, logs = directory / 'ckpt', directory / 'logs'
    base_model, base_loader = trainer.TiedMLPTransformer, trainer.Loader
    evaluate, optimizer_step = trainer.evaluate, muon.Muon.step
    step_stats, train = trainer._step_stats, train_package.train
    peak, states, elapsed, supervised = [], {}, [], []
    initial, train_loader, bridge_calls = None, None, 0

    class TrainingLoader(base_loader):
        def __call__(self):
            x, y = super().__call__()
            if layout == 'masked':
                y = add_mask(y)
                supervised.append(int(y.ne(IGNORE).sum()))
            else:
                supervised.append(y.numel())
            return x, y

    def new_loader(split, *args, **kwargs):
        nonlocal train_loader
        if split == 'train':
            train_loader = TrainingLoader(split, *args, **kwargs)
            assert train_loader.rng.bit_generator.state == profile['sampler_start']
            return train_loader
        return base_loader(split, *args, **kwargs)

    def new_model(cfg):
        nonlocal initial
        model = base_model(cfg)
        assert cfg.train_repeat == 2.0 and cfg.mlp_group == 4 and cfg.cla_group == 2
        assert cfg.vocab_size == 32768 and len(model.visit_schedule()) == 28 and cfg.grad_checkpoint
        initial = previous.state_sha(model.state_dict())
        return model

    def pinned_cache(data, tokens, *, exact, doc_filter, hf_tok, chat32, **_):
        assert data == 'synthetic' and tokens == BASE.POOL and exact and not (doc_filter or hf_tok or chat32)
        return dict(profile['data'])

    def recomputed_ce(model, x, y, tile):
        nonlocal bridge_calls
        assert head == 'recompute' and tile == BASE.TILE and y.numel() == micro * BASE.WIDTH
        bridge_calls += 1
        nll = token_nll(model, model(x, return_hidden=True), y)
        return nll.sum() / y.ne(IGNORE).sum()

    def short_eval(model, loader, iters, device, **kwargs):
        # Both layouts use their native validation batch and the same two draws inside a pair.
        value = evaluate(model, loader, 2, device, **kwargs)
        torch.cuda.reset_peak_memory_stats()
        return value

    def observed_step(opt, *args, **kwargs):
        value = optimizer_step(opt, *args, **kwargs)
        torch.cuda.synchronize()
        peak.append((torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()))
        return value

    def save_state(blob, path):
        assert Path(path).parent == ckpt and not Path(path).exists()
        index = blob['step']
        if index not in states:
            states[index] = {key: previous.state_sha(blob[key]) for key in ('model', 'opt', 'opt_muon')}

    def observed_stats(values):
        elapsed.extend(values)
        return step_stats(values)

    def checked_train(*args, **kwargs):
        check_call(name, args, kwargs)
        return train(*args, **kwargs)

    argv = command(name)
    assert argv == profile['commands'][name]
    print('P102A_G4_RECOMPUTE_SHAPES_ARM', name, ' '.join(argv), flush=True)
    with (patch.object(sys, 'argv', argv), patch.object(train_package, 'train', checked_train),
          patch.object(trainer, 'prepare', pinned_cache), patch.object(trainer, 'Loader', new_loader),
          patch.object(trainer, 'TiedMLPTransformer', new_model), patch.object(trainer, '_ce_vocab_tiled', recomputed_ce),
          patch.object(trainer, 'CKPT', ckpt), patch.object(trainer, 'LOGS', logs),
          patch.object(trainer, 'evaluate', short_eval), patch.object(trainer, '_step_stats', observed_stats),
          patch.object(muon.Muon, 'step', observed_step), patch.object(torch, 'save', save_state)):
        cli.main()
    native, = logs.glob('*.json')
    raw = json.loads(native.read_bytes())
    expected = profile['masked_micro_supervised'] if layout == 'masked' else [micro * BASE.WIDTH] * BASE.STEPS
    assert supervised == expected and train_loader.rng.bit_generator.state == profile['sampler_end']
    assert raw['tokens'] == TARGETS and raw['n_skip'] == 0 and not any(ckpt.iterdir())
    assert len(elapsed) == len(peak) == BASE.STEPS and list(states) == list(range(1, BASE.STEPS + 1))
    assert bridge_calls == (BASE.STEPS * accum if head == 'recompute' else 0)
    BASE.write_new(directory / 'report.json', dict(initial=initial, updates=len(peak),
        targets=TARGETS, supervised=supervised, sampler_end=train_loader.rng.bit_generator.state,
        states=states, train_ce=[event['train_ce'] for event in raw['history']], val_ce=raw['final']['val_loss'],
        peak_allocated=max(m[0] for m in peak), peak_reserved=max(m[1] for m in peak),
        step_ms=elapsed, median_after_first_ms=median(elapsed[1:]), bridge_calls=bridge_calls,
        checkpoint_writes=0, native_json=str(native.relative_to(ROOT))))


def idle():
    return not subprocess.check_output(previous.DEVICE_QUERY, text=True, timeout=8).strip()


def actual(profile):
    BASE.write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), arms=ARM_NAMES))
    print('P102A_G4_RECOMPUTE_SHAPES_ACTIVE', os.getpid(), flush=True)
    exits = {}
    for arm in ARM_NAMES:
        assert idle(), 'GPU acquired by another process'
        args = ['timeout', '--kill-after=5s', '45s', sys.executable, '-B', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_recompute_shapes', 'worker', arm]
        exits[arm] = subprocess.run(args, cwd=ROOT).returncode
        print('P102A_G4_RECOMPUTE_SHAPES_EXIT', arm, exits[arm], flush=True)
    assert idle() and profile['identity'] == identity()
    pairs = {}
    for layout in LAYOUT:
        names = (f'{layout}_reference', f'{layout}_recompute')
        if any(exits[name] for name in names):
            continue
        left, right = (json.loads((OUT / name / 'report.json').read_bytes()) for name in names)
        for key in ('initial', 'targets', 'supervised', 'sampler_end'):
            assert left[key] == right[key]
        changes = {index: [key for key, value in states.items() if value != right['states'][index][key]]
                   for index, states in left['states'].items()}
        loss_diff = [abs(a - b) for a, b in zip(left['train_ce'], right['train_ce'], strict=True)]
        violations = sum(diff > 1e-5 + 1e-4 * abs(ce) for diff, ce in zip(loss_diff, left['train_ce'], strict=True))
        pairs[layout] = dict(reference=left, candidate=right, state_differences=changes,
                             loss_diff=loss_diff, loss_violations=violations,
                             numerical_pass=not any(changes.values()) and not violations)
    BASE.write_new(OUT / 'report.json', dict(tag=TAG, exits=exits, pairs=pairs, device_returned=True))
    return 0 if len(pairs) == len(LAYOUT) and all(pair['numerical_pass'] for pair in pairs.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'actual', 'worker'))
    parser.add_argument('arm', nargs='?', choices=ARM_NAMES)
    args = parser.parse_args()
    assert datetime.now(BASE.CUTOFF.tzinfo) + timedelta(minutes=5) < BASE.CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    os.environ.update(TINYLM_DIR=str(OUT / 'scratch'), TINYLM_HF=str(OUT / 'scratch' / 'HF'))
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if args.phase == 'prepare':
        OUT.mkdir(exist_ok=False)
        return prepare()
    profile = json.loads((OUT / 'profile.json').read_bytes())
    assert profile['identity'] == identity() and os.environ['CUBLAS_WORKSPACE_CONFIG'] == LOSS.STRICT.WORKSPACE
    if args.phase == 'actual':
        assert args.arm is None and idle()
        return actual(profile)
    assert args.arm and not (OUT / args.arm).exists()
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * (1 << 30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    return train_arm(profile, args.arm)


if __name__ == '__main__':
    sys.exit(main())
