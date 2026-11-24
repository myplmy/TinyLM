"""Exercise the opt-in CE through the ordinary G4 trainer on synthetic tokens."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import os
import statistics
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TAG = 'p102a_g4_native_vocab_tile_v3_20261119'
OUT = ROOT / 'test_result/evidence' / TAG
CUTOFF = datetime.fromisoformat('2026-11-19T16:54:00+09:00')
STEPS, MICRO, ACCUM, WIDTH, TILE, POOL = 6, 8, 2, 1024, 2048, 262144
SOURCES = (
    'scripts/diag_p102a_g4_native_vocab_tile.py', 'tinylm/cli.py', 'tinylm/config.py',
    'tinylm/train/trainer.py', 'tinylm/train/streaming_head.py', 'tinylm/train/muon.py',
    'tinylm/train/optimizer_audit.py', 'tinylm/train/anneal_schedule.py',
    'tinylm/model/transformer.py', 'tinylm/model/modules.py', 'tinylm/model/ternary.py',
    'tinylm/data/prepare.py', 'tinylm/data/loader.py', 'tinylm/eval/evaluate.py', 'tinylm/paths.py',
)
PLAN = ROOT / 'test_plan/P102A_T1-S1-S2-S3-학습시간-기능계약.md'


def source_identity():
    return {path: sha256((ROOT / path).read_bytes()).hexdigest().upper() for path in SOURCES}


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), file=stream)


def cli_args(arm):
    pool_m = f'{POOL / 1_000_000:.6f}M'
    args = ['tinylm', 'train', '--preset', 'm100s12_g4', '--arch', 'tied', '--data', 'synthetic',
            '--tokens', pool_m, '--pool-tokens', pool_m, '--exact-cache', '--steps', str(STEPS),
            '--micro-bs', str(MICRO), '--accum', str(ACCUM), '--seq', str(WIDTH), '--eval-every', '1',
            '--save-every', '1', '--train-repeat', '2', '--optimizer', 'muon', '--muon-scale', 'rms',
            '--muon-lr-mult', '4', '--matrix-weight-decay', '0', '--seed', '1337', '--lr', '1e-3',
            '--sched', 'wsd', '--anneal-start', '0', '--anneal-end', '0.6', '--tag', f'{TAG}_{arm}']
    if arm == 'tile':
        args.extend(('--ce-vocab-tile', str(TILE)))
    return args


def prepare(torch):
    import tinylm.train as train_package
    from tinylm import cli
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.train import trainer

    signatures = {}
    for arm in ('reference', 'tile'):
        with (patch.object(sys, 'argv', cli_args(arm)), patch.object(train_package, 'train') as call,
              patch.object(trainer, 'prepare', side_effect=AssertionError('CLI argument probe reached data preparation'))):
            cli.main()
        call.assert_called_once()
        args, kwargs = call.call_args
        assert args[:4] == ('m100s12_g4', 'tied', 'synthetic', POOL)
        assert args[4:8] == (STEPS, MICRO, WIDTH, ACCUM) and kwargs['pool_tokens'] == POOL
        assert kwargs['anneal_start'] == 0. and kwargs['anneal_end'] == .6
        assert (kwargs['ce_vocab_tile'], kwargs['train_repeat'], kwargs['kd']) == (TILE if arm == 'tile' else 0, 2, False)
        signatures[arm] = kwargs['ce_vocab_tile']
        if arm == 'tile':
            with patch.object(trainer, 'prepare') as untouched:
                try:
                    trainer.train(*args, **(kwargs | {'kd': True}))
                except ValueError as error:
                    assert 'without KD' in str(error)
                else:
                    raise RuntimeError('incompatible KD entered the tiled CE route')
                untouched.assert_not_called()

    torch.manual_seed(1337)
    cfg = TMTConfig(vocab_size=35, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2, emb_rank=8,
                    n_prelude=1, n_middle=4, n_coda=1, tie_mlp=True, mlp_group=2,
                    micro_group=8, max_seq_len=8, grad_checkpoint=False, cla_group=1, train_repeat=2.)
    model = TiedMLPTransformer(cfg).train()
    x = torch.tensor([[1, 14, 24, 24], [8, 2, 7, 0]])
    y = torch.tensor([[14, -100, 24, 34], [2, 7, -100, 0]])
    params = tuple(model.parameters())
    reference = trainer._ce_chunked(model(x).reshape(-1, 35), y.flatten())
    left = torch.autograd.grad(reference, params)
    candidate = trainer._ce_vocab_tiled(model, x, y, 7)
    right = torch.autograd.grad(candidate, params)
    torch.testing.assert_close(candidate, reference, atol=1e-6, rtol=1e-5)
    for a, b in zip(left, right, strict=True):
        torch.testing.assert_close(b, a, atol=2e-6, rtol=1e-5)
    assert not torch.cuda.is_initialized()
    evidence = dict(tag=TAG, sources=source_identity(), plan_sha256=sha256(PLAN.read_bytes()).hexdigest(),
                    shared_parameters=len(params), active_targets=int(y.ne(-100).sum()), cli_tiles=signatures,
                    reference_ce=float(reference.detach()), tile_ce=float(candidate.detach()),
                    steps=STEPS, draw_per_arm=STEPS * MICRO * ACCUM * WIDTH, pool=POOL)
    write_new(OUT / 'profile.json', evidence)
    print('P102A_G4_VOCAB_READY', evidence['shared_parameters'], evidence['active_targets'], flush=True)
    return 0


def tensor_comparison(torch, reference, observed):
    assert reference.keys() == observed.keys()
    summary = {'elements': 0, 'outside_tolerance': 0, 'max_abs': 0., 'mismatches_by_name': {}}
    for name, base in reference.items():
        check = observed[name].detach().cpu()
        assert base.shape == check.shape and torch.isfinite(check).all()
        delta = (check - base).abs()
        absolute = float(delta.max()) if delta.numel() else 0.
        failed = int((delta > 2e-6 + 1e-5 * base.abs()).sum())
        summary['elements'] += base.numel()
        summary['max_abs'] = max(summary['max_abs'], absolute)
        summary['outside_tolerance'] += failed
        if failed or name in ('emb.weight', 'emb_up.weight'):
            summary['mismatches_by_name'][name] = dict(outside_tolerance=failed, max_abs=absolute)
    return summary


def arm(torch, name, baseline):
    import tinylm.train as train_package
    from tinylm import cli
    from tinylm.train import trainer

    directory = OUT / name
    ckpt = directory / 'ckpt'
    logs = directory / 'logs'
    original_model, original_loader = trainer.TiedMLPTransformer, trainer.Loader
    original_eval, original_stats = trainer.evaluate, trainer._step_stats
    original_train = train_package.train
    original_clip = torch.nn.utils.clip_grad_norm_
    model = train_loader = None
    observations = {'memory': [], 'save_steps': []}
    tensors = {}

    def audit(key, values):
        if baseline is None:
            tensors[key] = {k: v.detach().cpu().clone() for k, v in values.items()}
        else:
            observations[key] = tensor_comparison(torch, baseline[key], values)

    def build_model(cfg):
        nonlocal model
        assert model is None
        assert (cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.train_repeat) == (2, 12, 2, 4, 2.)
        model = original_model(cfg)
        assert len(model.visit_schedule()) == 28 and cfg.vocab_size == 32768 and cfg.grad_checkpoint
        signature = sha256()
        for param in model.parameters():
            signature.update(param.detach().numpy().tobytes())
        observations['initial_model_sha256'] = signature.hexdigest().upper()
        return model

    def build_loader(split, *args, **kwargs):
        nonlocal train_loader
        loader = original_loader(split, *args, **kwargs)
        observations[f'{split}_sha256'] = sha256(loader.d.tobytes()).hexdigest().upper()
        if split == 'train':
            train_loader = loader
            observations['sampler_start'] = loader.rng.bit_generator.state
        return loader

    def clip(parameters, *args, **kwargs):
        if not observations['save_steps']:
            audit('first_gradient', {k: v.grad for k, v in model.named_parameters() if v.grad is not None})
        return original_clip(parameters, *args, **kwargs)

    def evaluate(model, loader, iters, device, **kwargs):
        if iters == 50:
            observations['memory'].append(dict(allocated=torch.cuda.max_memory_allocated(),
                                               reserved=torch.cuda.max_memory_reserved()))
        result = original_eval(model, loader, 2, device, **kwargs)
        torch.cuda.reset_peak_memory_stats()
        return result

    def save(blob, path):
        assert path.parent == ckpt and not path.exists()
        assert blob.get('ce_vocab_tile', 0) == (TILE if name == 'tile' else 0)
        assert 'opt' in blob and 'opt_muon' in blob
        if path.name.endswith('_best.pt'):
            return
        observations['save_steps'].append(blob['step'])
        if blob['step'] in (1, STEPS):
            selected = {k: blob['model'][k] for k, _ in model.named_parameters()}
            audit(f"update_{blob['step']}", selected)

    def stats(step_ms):
        observations['step_ms'] = step_ms.copy()
        return original_stats(step_ms)

    def checked_train(*args, **kwargs):
        assert args[:8] == ('m100s12_g4', 'tied', 'synthetic', POOL, STEPS, MICRO, WIDTH, ACCUM)
        assert kwargs['pool_tokens'] == POOL and not kwargs['kd'] and kwargs['init_from'] is None
        assert kwargs['ce_vocab_tile'] == (TILE if name == 'tile' else 0)
        return original_train(*args, **kwargs)

    with (patch.object(sys, 'argv', cli_args(name)), patch.object(train_package, 'train', checked_train),
          patch.object(trainer, 'TiedMLPTransformer', build_model),
          patch.object(trainer, 'Loader', build_loader), patch.object(trainer, 'CKPT', ckpt),
          patch.object(trainer, 'LOGS', logs), patch.object(trainer, 'evaluate', evaluate),
          patch.object(trainer, '_step_stats', stats), patch.object(torch.nn.utils, 'clip_grad_norm_', clip),
          patch.object(torch, 'save', save)):
        torch.cuda.reset_peak_memory_stats()
        cli.main()
    torch.cuda.synchronize()
    paths = tuple(logs.glob('*.json'))
    assert len(paths) == 1 and not any(ckpt.iterdir())
    result = json.loads(paths[0].read_text())
    assert result['steps'] == STEPS and result['n_skip'] == 0
    assert result.get('ce_vocab_tile', 0) == (TILE if name == 'tile' else 0)
    assert observations['save_steps'] == list(range(1, STEPS + 1))
    assert len(observations['memory']) == len(observations['step_ms']) == STEPS
    observations['sampler_end'] = train_loader.rng.bit_generator.state
    observations['median_after_first_ms'] = statistics.median(observations['step_ms'][1:])
    observations['train_ce'] = [row['train_ce'] for row in result['history']]
    observations['json_path'] = str(paths[0].relative_to(ROOT))
    return observations, tensors


def actual(torch):
    profile_path = OUT / 'profile.json'
    profile = json.loads(profile_path.read_text())
    assert profile['sources'] == source_identity() and profile['plan_sha256'] == sha256(PLAN.read_bytes()).hexdigest()
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * (1 << 30)
    write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), device=torch.cuda.get_device_name()))
    print('P102A_G4_VOCAB_ACTIVE', os.getpid(), flush=True)
    reference, baseline = arm(torch, 'reference', None)
    torch.cuda.empty_cache()
    print('P102A_G4_VOCAB_ARM_DONE reference', flush=True)
    tiled, _ = arm(torch, 'tile', baseline)
    torch.cuda.empty_cache()
    for field in ('initial_model_sha256', 'train_sha256', 'val_sha256', 'sampler_start', 'sampler_end'):
        assert reference[field] == tiled[field], field
    comparisons = [tiled[k] for k in ('first_gradient', 'update_1', f'update_{STEPS}')]
    losses = list(zip(reference['train_ce'], tiled['train_ce'], strict=True))
    assert len(losses) == STEPS
    violations = [abs(a - b) > 1e-5 + 1e-4 * abs(a) for a, b in losses]
    passed = not any(row['outside_tolerance'] for row in comparisons) and not any(violations)
    assert profile['sources'] == source_identity()
    result = dict(tag=TAG, reference=reference, tile=tiled, sources=profile['sources'], numerical_pass=passed,
                  loss_outside_tolerance=sum(violations), checkpoint_writes=0, training_updates=STEPS * 2,
                  allocated_pre_exit=torch.cuda.memory_allocated(), reserved_pre_exit=torch.cuda.memory_reserved())
    write_new(OUT / 'report.json', result)
    print('P102A_G4_VOCAB_RESULT', passed, [r['outside_tolerance'] for r in comparisons], flush=True)
    return 0 if passed else 8


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('phase', choices=('prepare', 'actual'))
    args = cli.parse_args()
    assert datetime.now(CUTOFF.tzinfo) < CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    if args.phase == 'prepare':
        OUT.mkdir(exist_ok=False)
    else:
        assert not (OUT / 'active.json').exists() and not (OUT / 'report.json').exists()
    sandbox = OUT / f'{args.phase}_artifacts'
    os.environ['TINYLM_DIR'] = str(sandbox)
    os.environ['TINYLM_HF'] = str(sandbox / 'HF')
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return prepare(torch) if args.phase == 'prepare' else actual(torch)


if __name__ == '__main__':
    sys.exit(main())
