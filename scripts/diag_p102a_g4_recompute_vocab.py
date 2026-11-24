"""Compare full-trainer plain and recomputed CE in the 248,320-ID G4."""

import argparse
from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p102a_g4_recompute_operating as prior


BASE, ROOT, DIGEST = prior.BASE, prior.ROOT, prior.DIGEST
TAG = 'p102a_g4_recompute_248k_v1_20261119'
OUT = prior.OUT.with_name(TAG)
CACHE = OUT / 'cache'
STEPS, WIDTH, POOL, VAL, VOCAB, ROWS = 6, 1024, 1_000_000, 5000, 248_320, 1024
ARMS = {'reference': (4, 4, 0), 'recompute': (4, 4, ROWS), 'wide': (8, 2, ROWS)}
DRAW = 16 * WIDTH * STEPS
SOURCES = (*BASE.SOURCES, Path(__file__).resolve().relative_to(ROOT).as_posix(),
           'tinylm/train/recomputed_ce.py', 'tinylm/train/context_micro_tokens.py',
           'tinylm/train/context_training_state.py', 'scripts/diag_p102a_g4_full_delta_train.py',
           'scripts/diag_p102a_g4_recompute_shapes.py', 'scripts/diag_p102a_g4_recompute_operating.py')


def identity():
    return {name: DIGEST(ROOT / name) for name in (*SOURCES, str(BASE.PLAN.relative_to(ROOT)))}


def command(arm):
    micro, accum, rows = ARMS[arm]
    args = BASE.cli_args('reference')
    replacements = {'--tag': f'{TAG}_{arm}', '--tokens': '1M', '--pool-tokens': '1M',
                    '--micro-bs': str(micro), '--accum': str(accum)}
    for flag, value in replacements.items():
        args[args.index(flag) + 1] = value
    args.extend(('--context-curriculum', f'{STEPS}:{WIDTH}'))
    if rows:
        args.extend(('--ce-recompute-rows', str(rows)))
    return args


def check_call(arm, args, options):
    micro, accum, rows = ARMS[arm]
    if (args[:8] != ('m100s12_g4', 'tied', 'synthetic', POOL, STEPS, micro, WIDTH, accum)
            or args[8:13] != (1e-3, 1, False, True, False)
            or options['pool_tokens'] != POOL or not options['exact_cache']
            or options['ce_recompute_rows'] != rows or options['train_repeat'] != 2
            or options['seed'] != 1337 or options['tag'] != f'{TAG}_{arm}'
            or options['kd'] or options['ce_chunk'] or options['ce_vocab_tile']):
        raise ValueError('public CLI trainer arguments differ from the experiment')


def prepare():
    from tinylm import cli
    from tinylm.data import Loader
    import tinylm.train as train_package
    from tinylm.train.context_micro_tokens import MicroTokensCursor, parse_context_plan
    from tinylm.train.context_training_state import cache_identity

    CACHE.mkdir(parents=True, exist_ok=False)
    data = dict(data='synthetic', dir=str(CACHE), vocab=VOCAB, tokens=POOL,
                train=POOL - VAL, val=VAL, token_dtype='uint32')
    domain = {}
    for name, seed in (('train', 670540), ('val', 670541)):
        value = np.random.default_rng(seed).integers(0, VOCAB, size=data[name], dtype=np.uint32)
        with (CACHE / f'{name}.bin').open('xb') as stream:
            stream.write(value.tobytes())
        domain[name] = dict(seed=seed, min=int(value.min()), max=int(value.max()),
                            above_uint16=int(np.count_nonzero(value > 65_535)))
    BASE.write_new(CACHE / 'meta.json', data)
    cache = cache_identity(CACHE)
    source = {}
    for arm, (micro, accum, _) in ARMS.items():
        args = command(arm)
        with patch.object(sys, 'argv', args), patch.object(train_package, 'train') as stub:
            cli.main()
        stub.assert_called_once()
        check_call(arm, *stub.call_args)
        plan = parse_context_plan(f'{STEPS}:{WIDTH}', micro_bs=micro, accum=accum, seq=WIDTH, steps=STEPS)
        loader = Loader('train', micro, WIDTH, 'cpu', CACHE, seed=1234)
        cursor = MicroTokensCursor(plan, loader, source_sha256=cache['identity_sha256'])
        updates = []
        for _ in range(STEPS):
            update = cursor.prepare()
            receipt = []
            for index in (0, 1):
                values = np.concatenate([batch[index].numpy().flatten() for batch in update.batches])
                assert len(values) == 16 * WIDTH and np.count_nonzero(values > 65535)
                receipt.append(hashlib.sha256(values.astype('<u4').tobytes()).hexdigest().upper())
            updates.append(receipt)
            cursor.finish(optimizer_applied=True)
        source[arm] = dict(updates=updates, cursor=cursor.state_dict()['cursor'])
    assert all(x['updates'] == source['reference']['updates'] for x in source.values())
    assert all(x['cursor']['rng'] == source['reference']['cursor']['rng'] for x in source.values())
    assert data['train'] >= DRAW * 2 and not torch.cuda.is_initialized()
    BASE.write_new(OUT / 'profile.json', dict(identity=identity(), cache=cache, data=data, domain=domain,
        source=source, commands={arm: command(arm) for arm in ARMS}, draw_per_arm=DRAW,
        approval_ref='WIP176', outline='PUBLIC_CE_WITH_SYNTHETIC_UINT32_VOCAB_GEOMETRY'))
    print('P102A_G4_248K_READY', VOCAB, DRAW, domain, flush=True)
    return 0


def worker(arm, frozen):
    from tinylm import cli
    import tinylm.train as train_package
    from tinylm.train import muon, trainer

    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 14 * (1 << 30):
        raise RuntimeError('one CUDA device with at least 14 GiB free is required')
    ckpt, logs = OUT / arm / 'ckpt', OUT / arm / 'logs'
    ckpt.mkdir(parents=True, exist_ok=False)
    logs.mkdir(exist_ok=False)
    train, build, model = train_package.train, trainer.build_config, trainer.TiedMLPTransformer
    loader, evaluate, stats, muon_step = trainer.Loader, trainer.evaluate, trainer._step_stats, muon.Muon.step
    hash_state = prior.previous.shapes.previous.state_sha
    states, peaks, times = {}, [], []
    started = time.monotonic()
    initial = None

    def build_vocab(*args, **kwargs):
        cfg = build(*args, **kwargs)
        assert (cfg.vocab_size, cfg.emb_rank) == (32768, 256)
        cfg.vocab_size = VOCAB
        return cfg

    def make_model(cfg):
        nonlocal initial
        instance = model(cfg)
        assert (cfg.vocab_size, cfg.mlp_group, cfg.cla_group) == (VOCAB, 4, 2)
        assert cfg.grad_checkpoint and len(instance.visit_schedule()) == 28
        initial = hash_state(instance.state_dict())
        return instance

    def prepared_data(data, tokens, *, exact, doc_filter, hf_tok, chat32, **_):
        assert data == 'synthetic' and tokens == POOL and exact and not (doc_filter or hf_tok or chat32)
        return dict(frozen['data'])

    def make_loader(split, batch, width, device, directory, **kwargs):
        assert split in ('train', 'val') and width == WIDTH and Path(directory) == CACHE
        expected = 1234 if split == 'train' else 99
        assert kwargs == {'seed': expected} and batch == ARMS[arm][0]
        return loader(split, batch if split == 'train' else 2, width, device, directory, **kwargs)

    def short_eval(instance, source, _iters, device, **kwargs):
        value = evaluate(instance, source, 2, device, **kwargs)
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        return value

    def observed_step(opt, *args, **kwargs):
        value = muon_step(opt, *args, **kwargs)
        torch.cuda.synchronize()
        peaks.append((torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()))
        return value

    def observe_checkpoint(blob, path):
        assert path.parent == ckpt and not path.exists() and blob['cfg']['vocab_size'] == VOCAB
        assert blob.get('ce_recompute_rows', 0) == ARMS[arm][2]
        step = str(blob['step'])
        if step not in states:
            states[step] = {name: hash_state(blob[name]) for name in ('model', 'opt', 'opt_muon')}

    def observed_stats(values):
        times.extend(values)
        return stats(values)

    def checked_train(*args, **kwargs):
        check_call(arm, args, kwargs)
        return train(*args, **kwargs)

    print('P102A_G4_248K_ARM', arm, os.getpid(), flush=True)
    with (patch.object(sys, 'argv', frozen['commands'][arm]), patch.object(train_package, 'train', checked_train),
          patch.object(trainer, 'build_config', build_vocab), patch.object(trainer, 'TiedMLPTransformer', make_model),
          patch.object(trainer, 'prepare', prepared_data), patch.object(trainer, 'Loader', make_loader),
          patch.object(trainer, 'CKPT', ckpt), patch.object(trainer, 'LOGS', logs),
          patch.object(trainer, 'evaluate', short_eval), patch.object(trainer, '_step_stats', observed_stats),
          patch.object(muon.Muon, 'step', observed_step), patch.object(torch, 'save', observe_checkpoint)):
        cli.main()
    (native,) = logs.glob('*.json')
    log = prior.previous.read(native)
    assert log['vocab_size'] == VOCAB and log['tokens'] == DRAW and log['n_skip'] == 0
    assert log['context_source_cursor']['cursor'] == frozen['source'][arm]['cursor']
    assert len(states) == len(times) == len(peaks) == STEPS and not any(ckpt.iterdir())
    BASE.write_new(OUT / arm / 'report.json', dict(arm=arm, initial=initial, states=states, updates=STEPS,
        params=log['params'], peak_allocated=max(x[0] for x in peaks), peak_reserved=max(x[1] for x in peaks),
        step_times_ms=times, median_after_first_ms=median(times[1:]), history=log['history'], final=log['final'],
        native_json=str(native.relative_to(ROOT)), native_sha256=DIGEST(native),
        worker_wall_sec=time.monotonic()-started, checkpoint_writes=0))
    return 0


def run(frozen):
    from tinylm.train.context_training_state import cache_identity

    if not prior.previous.shapes.idle():
        raise RuntimeError('GPU is already in use')
    BASE.write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid(), arms=list(ARMS)))
    print('P102A_G4_248K_ACTIVE', os.getpid(), flush=True)
    terminal, results = {}, {}
    for arm in ARMS:
        if (OUT / 'STOP').exists() or not prior.previous.shapes.idle():
            terminal[arm] = None
            break
        call = ['timeout', '--kill-after=6s', '100s', sys.executable, '-u', '-B', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_recompute_vocab', 'worker', arm]
        terminal[arm] = subprocess.run(call, cwd=ROOT).returncode
        print('P102A_G4_248K_EXIT', arm, terminal[arm], flush=True)
        if terminal[arm] == 0:
            results[arm] = prior.previous.read(OUT / arm / 'report.json')
    assert prior.previous.shapes.idle() and identity() == frozen['identity'] and cache_identity(CACHE) == frozen['cache']
    checks = {}
    if len(results) == len(ARMS):
        a, b, wide = results.values()
        checks = dict(shared_start=len({r['initial'] for r in results.values()}) == 1,
                      matched_states=a['states'] == b['states'], matched_history=a['history'] == b['history'],
                      matched_validation=a['final'] == b['final'],
                      different_wide_fingerprints=b['states'] != wide['states'])
    BASE.write_new(OUT / 'report.json', dict(tag=TAG, exits=terminal, arms=results, checks=checks,
        actual_updates=sum(row['updates'] for row in results.values()), device_returned=True,
        profile_sha256=DIGEST(OUT / 'profile.json')))
    print('P102A_G4_248K_COMPLETE', checks, flush=True)
    required = ('shared_start', 'matched_states', 'matched_history', 'matched_validation')
    return 0 if checks and all(checks[key] for key in required) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run', 'worker'))
    parser.add_argument('arm', nargs='?', choices=ARMS)
    args = parser.parse_args()
    if (args.stage == 'worker') != (args.arm is not None):
        parser.error('one explicit training arm is required only for worker')
    if (datetime.now(BASE.CUTOFF.tzinfo) + timedelta(minutes=6) >= BASE.CUTOFF
            or os.environ.get('CUDA_VISIBLE_DEVICES') != ('' if args.stage == 'prepare' else '0')):
        raise RuntimeError('authority window or explicit device isolation is invalid')
    os.environ.update(TINYLM_DIR=str(OUT / 'scratch'), TINYLM_HF=str(OUT / 'scratch/HF'))
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if args.stage == 'prepare':
        return prepare()
    from tinylm.train.context_training_state import cache_identity

    frozen = prior.previous.read(OUT / 'profile.json')
    assert frozen['identity'] == identity() and frozen['cache'] == cache_identity(CACHE)
    assert os.environ['CUBLAS_WORKSPACE_CONFIG'] == prior.previous.shapes.LOSS.STRICT.WORKSPACE
    return run(frozen) if args.stage == 'run' else worker(args.arm, frozen)


if __name__ == '__main__':
    sys.exit(main())
