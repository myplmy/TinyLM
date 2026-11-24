"""Benchmark alternate CE and training-capacity settings through native train."""

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from unittest.mock import patch

from scripts import diag_p102a_g4_native_vocab_tile as base


ROOT = base.ROOT
TAG = 'p102a_g4_tile_training_capacity_v2_20261119'
OUT = base.OUT.parent / TAG
SOURCE = ROOT / 'scripts/diag_p102a_g4_tile_training_capacity.py'
STEPS, WIDTH, POOL = 12, 1024, 524288
ROW_BUDGET = 16
ARMS = {
    'full_8x2_ckpt': (8, 2, 0, True),
    'tile_8x2_ckpt': (8, 2, 2048, True),
    'tile_8x2_no_ckpt': (8, 2, 2048, False),
    'full_8x2_no_ckpt': (8, 2, 0, False),
    'full_16x1_ckpt': (16, 1, 0, True),
    'tile_16x1_ckpt': (16, 1, 2048, True),
}
NVIDIA = '/usr/lib/wsl/lib/nvidia-smi'


def digest(path):
    return sha256(path.read_bytes()).hexdigest().upper()


def identity():
    return base.source_identity() | {str(p.relative_to(ROOT)): digest(p) for p in (SOURCE, base.PLAN)}


def cli_args(name):
    micro, accum, tile, ckpt = ARMS[name]
    args = ['tinylm', 'train', '--preset', 'm100s12_g4', '--arch', 'tied', '--data', 'synthetic',
            '--tokens', '0.524288M', '--pool-tokens', '0.524288M', '--exact-cache', '--steps', str(STEPS),
            '--micro-bs', str(micro), '--accum', str(accum), '--seq', str(WIDTH), '--eval-every', str(STEPS),
            '--train-repeat', '2', '--optimizer', 'muon', '--muon-scale', 'rms', '--muon-lr-mult', '4',
            '--matrix-weight-decay', '0', '--seed', '1337', '--lr', '1e-3', '--sched', 'wsd',
            '--anneal-start', '0', '--anneal-end', '0.6', '--tag', f'{TAG}_{name}']
    if not ckpt:
        args.append('--no-ckpt')
    if tile:
        args.extend(('--ce-vocab-tile', str(tile)))
    return args


def check_call(name, args, kwargs):
    micro, accum, tile, ckpt = ARMS[name]
    assert (args[:8] == ('m100s12_g4', 'tied', 'synthetic', POOL, STEPS, micro, WIDTH, accum)
            and kwargs['pool_tokens'] == POOL and kwargs['exact_cache'])
    assert args[8:13] == (1e-3, STEPS, False, ckpt, False)
    assert not kwargs['kd'] and kwargs['init_from'] is None
    assert kwargs['ce_vocab_tile'] == tile and kwargs['train_repeat'] == 2
    assert kwargs['anneal_start'] == 0. and kwargs['anneal_end'] == .6


def prepare(torch):
    from tinylm import cli
    from tinylm.data import Loader, prepare as make_cache
    import tinylm.train as train_package

    for name, (micro, accum, _, _) in ARMS.items():
        assert micro * accum == ROW_BUDGET
        with patch.object(sys, 'argv', cli_args(name)), patch.object(train_package, 'train') as stub:
            cli.main()
        stub.assert_called_once()
        check_call(name, *stub.call_args)
    meta = make_cache('synthetic', POOL, exact=True)
    directory = Path(meta['dir'])
    assert directory.is_relative_to(OUT) and meta['train'] >= 2 * STEPS * ROW_BUDGET * WIDTH
    assert meta['vocab'] == 32768 and meta['tokens'] == POOL
    small = Loader('train', 8, WIDTH, 'cpu', directory, seed=1234)
    big = Loader('train', 16, WIDTH, 'cpu', directory, seed=1234)
    start = small.rng.bit_generator.state
    per_update = []
    for _ in range(STEPS):
        first, second, wide = small(), small(), big()
        assert all(torch.equal(torch.cat((a, b), dim=0), c) for a, b, c in zip(first, second, wide, strict=True))
        per_update.append([sha256(x.contiguous().numpy().tobytes()).hexdigest().upper() for x in wide])
    assert small.rng.bit_generator.state == big.rng.bit_generator.state and not torch.cuda.is_initialized()
    base.write_new(OUT / 'profile.json', dict(tag=TAG, sources=identity(), data=meta,
        split_sha256={name: digest(directory / f'{name}.bin') for name in ('train', 'val')},
        sampler_start=start, sampler_end=big.rng.bit_generator.state, update_input_sha256=per_update,
        targets_per_arm=STEPS * ROW_BUDGET * WIDTH, arms=ARMS))
    print('P102A_G4_CAPACITY_READY', len(per_update), flush=True)
    return 0


def worker(torch, name):
    dest = OUT / name
    dest.mkdir(exist_ok=False)
    from tinylm import cli
    import tinylm.train as train_package
    from tinylm.train import muon, trainer

    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * 1024 ** 3
    profile = json.loads((OUT / 'profile.json').read_text())
    assert profile['sources'] == identity()
    micro, accum, tile, ckpt = ARMS[name]
    meta = profile['data']
    cache = Path(meta['dir'])
    assert all(digest(cache / f'{split}.bin') == sha for split, sha in profile['split_sha256'].items())
    original_model = trainer.TiedMLPTransformer
    original_loader, original_eval = trainer.Loader, trainer.evaluate
    original_train, original_stats, original_step = train_package.train, trainer._step_stats, muon.Muon.step
    found, loaders, step_ms, peaks = {}, {}, [], []

    def cached_prepare(data, n_tokens, *, exact, doc_filter, hf_tok, chat32, **kwargs):
        assert data == 'synthetic' and n_tokens == POOL and exact and not (doc_filter or hf_tok or chat32)
        return dict(meta)

    def model(cfg):
        assert cfg.grad_checkpoint == ckpt and cfg.train_repeat == 2. and cfg.vocab_size == 32768
        assert cfg.mlp_group == 4 and cfg.cla_group == 2
        candidate = original_model(cfg)
        assert len(candidate.visit_schedule()) == 28
        fingerprint = sha256()
        for p in candidate.parameters():
            fingerprint.update(p.detach().numpy().tobytes())
        found['initial_model_sha256'] = fingerprint.hexdigest().upper()
        return candidate

    def loader(split, batch, seq, device, source, *, seed):
        assert batch == micro and seq == WIDTH and str(source) == str(cache)
        item = original_loader(split, 8 if split == 'val' else batch, seq, device, source, seed=seed)
        loaders[split] = item
        if split == 'train':
            assert item.rng.bit_generator.state == profile['sampler_start']
        return item

    def evaluate(m, val, iters, device, **kwargs):
        return original_eval(m, val, 2, device, **kwargs)

    def save(blob, path):
        assert Path(path).parent == dest / 'ckpt' and not Path(path).exists()
        assert blob.get('ce_vocab_tile', 0) == tile

    def step(obj, *args, **kwargs):
        out = original_step(obj, *args, **kwargs)
        torch.cuda.synchronize()
        peaks.append(dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved()))
        return out

    def stats(values):
        step_ms[:] = values
        return original_stats(values)

    def checked_train(*args, **kwargs):
        check_call(name, args, kwargs)
        return original_train(*args, **kwargs)

    try:
        with (patch.object(sys, 'argv', cli_args(name)), patch.object(train_package, 'train', checked_train),
              patch.object(trainer, 'prepare', cached_prepare), patch.object(trainer, 'TiedMLPTransformer', model),
              patch.object(trainer, 'Loader', loader), patch.object(trainer, 'evaluate', evaluate),
              patch.object(trainer, 'CKPT', dest / 'ckpt'), patch.object(trainer, 'LOGS', dest / 'logs'),
              patch.object(torch, 'save', save), patch.object(muon.Muon, 'step', step),
              patch.object(trainer, '_step_stats', stats)):
            cli.main()
    except torch.cuda.OutOfMemoryError as error:
        base.write_new(dest / 'report.json', dict(status='OUT_OF_MEMORY', arm=name, applied_steps=len(peaks),
            message=str(error), peak_allocated=torch.cuda.max_memory_allocated(), peak_reserved=torch.cuda.max_memory_reserved()))
        return 9
    assert len(peaks) == len(step_ms) == STEPS and not any((dest / 'ckpt').iterdir())
    assert loaders['train'].rng.bit_generator.state == profile['sampler_end']
    logs = tuple((dest / 'logs').glob('*.json'))
    assert len(logs) == 1
    raw = json.loads(logs[0].read_text())
    assert raw['n_skip'] == 0 and raw['steps'] == STEPS and raw['grad_ckpt'] == ckpt
    assert raw.get('ce_vocab_tile', 0) == tile and raw['micro_bs'] == micro and raw['accum'] == accum
    base.write_new(dest / 'report.json', dict(status='COMPLETE', arm=name, real_updates=STEPS,
        initial_model_sha256=found['initial_model_sha256'], targets=profile['targets_per_arm'],
        data_sha256=profile['split_sha256'], sampler_end=loaders['train'].rng.bit_generator.state,
        native_json=str(logs[0].relative_to(ROOT)), step_ms=step_ms, step_peaks=peaks,
        peak_allocated=max(row['allocated'] for row in peaks), peak_reserved=max(row['reserved'] for row in peaks),
        steady_median_ms=statistics.median(step_ms[-4:]), all_steps_ms=sum(step_ms),
        final_val_ce=raw['final']['val_loss'], train_ce=raw['history'][-1]['train_ce'], checkpoint_writes=0))
    print('P102A_G4_CAPACITY_ARM_COMPLETE', name, flush=True)
    return 0


def idle_device():
    query = subprocess.run([NVIDIA, '--query-compute-apps=pid', '--format=csv,noheader,nounits'],
                           text=True, capture_output=True, timeout=8, check=True)
    return not query.stdout.strip()


def actual():
    profile = json.loads((OUT / 'profile.json').read_text())
    assert profile['sources'] == identity() and idle_device()
    base.write_new(OUT / 'active.json', dict(pid=os.getpid(), tag=TAG, exact_arms=list(ARMS)))
    print('P102A_G4_CAPACITY_ACTIVE', os.getpid(), flush=True)
    exits, reports = {}, {}
    for name in ARMS:
        assert idle_device(), 'device is no longer free for this queue'
        args = ('timeout', '--kill-after=8s', '90s', sys.executable, '-B', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_tile_training_capacity', 'worker', name)
        exits[name] = subprocess.run(args, cwd=ROOT).returncode
        path = OUT / name / 'report.json'
        if path.is_file():
            reports[name] = json.loads(path.read_text())
        print('P102A_G4_CAPACITY_EXIT', name, exits[name], flush=True)
    assert idle_device() and profile['sources'] == identity()
    complete = [raw for raw in reports.values() if raw['status'] == 'COMPLETE']
    assert len({row['initial_model_sha256'] for row in complete}) <= 1
    base.write_new(OUT / 'report.json', dict(tag=TAG, terminal=exits, arms=reports, profile_sha256=digest(OUT / 'profile.json'),
        device_returned=True, successful_arms=len(complete), updates=sum(row['real_updates'] for row in complete)))
    return 0 if all(code == 0 for code in exits.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'actual', 'worker'))
    parser.add_argument('arm', nargs='?', choices=ARMS)
    args = parser.parse_args()
    assert datetime.now(base.CUTOFF.tzinfo) + timedelta(minutes=11) < base.CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    if args.phase == 'actual':
        assert args.arm is None
        return actual()
    if args.phase == 'prepare':
        assert args.arm is None
        OUT.mkdir(exist_ok=False)
    else:
        assert args.arm and (OUT / 'active.json').is_file()
    local = OUT / ('prepare_artifacts' if args.phase == 'prepare' else args.arm)
    os.environ['TINYLM_DIR'] = str(local)
    os.environ['TINYLM_HF'] = str(local / 'HF')
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return prepare(torch) if args.phase == 'prepare' else worker(torch, args.arm)


if __name__ == '__main__':
    sys.exit(main())
