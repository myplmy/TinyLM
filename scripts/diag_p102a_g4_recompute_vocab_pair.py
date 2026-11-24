"""Recover the 248K CE comparison at an unchanged 2x8 training shape."""

import argparse
from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p102a_g4_recompute_vocab as first


TAG = 'p102a_g4_recompute_248k_pair_v2_20261119'
ORIGINAL, OUT = first.OUT, first.OUT.with_name(TAG)
PAIR = {'reference': (2, 8, 0), 'recompute': (2, 8, first.ROWS)}
PROFILE = OUT / 'profile.json'
READ, DIGEST, WRITE = first.prior.previous.read, first.DIGEST, first.BASE.write_new


def identity():
    inputs = (Path(__file__).resolve(), ORIGINAL / 'profile.json', ORIGINAL / 'report.json')
    return first.identity() | {str(p.relative_to(first.ROOT)): DIGEST(p) for p in inputs}


def cache_identity():
    from tinylm.train.context_training_state import cache_identity as installed

    return installed(first.CACHE)


def prepare():
    from tinylm import cli
    from tinylm.data import Loader
    import tinylm.train as train_package
    from tinylm.train.context_micro_tokens import MicroTokensCursor, parse_context_plan

    original = READ(ORIGINAL / 'profile.json')
    result = READ(ORIGINAL / 'report.json')
    cache = cache_identity()
    if (original['cache'] != cache or result['exits'] != {'reference': 1, 'recompute': 0, 'wide': 0}
            or result['profile_sha256'] != DIGEST(ORIGINAL / 'profile.json')):
        raise ValueError('closed source cache and observed first-stage coverage required')
    prior_input = original['source']['reference']
    source, commands = {}, {}
    for name, (micro, accum, _) in PAIR.items():
        args = first.command(name)
        with patch.object(sys, 'argv', args), patch.object(train_package, 'train') as stub:
            cli.main()
        stub.assert_called_once()
        first.check_call(name, *stub.call_args)
        plan = parse_context_plan('6:1024', micro_bs=micro, accum=accum, seq=first.WIDTH, steps=first.STEPS)
        loader = Loader('train', micro, first.WIDTH, 'cpu', first.CACHE, seed=1234)
        cursor = MicroTokensCursor(plan, loader, source_sha256=cache['identity_sha256'])
        for reference in prior_input['updates']:
            update = cursor.prepare()
            consumed = []
            for index in (0, 1):
                values = np.concatenate([batch[index].numpy().flatten() for batch in update.batches])
                consumed.append(hashlib.sha256(values.astype('<u4').tobytes()).hexdigest().upper())
            assert consumed == reference
            cursor.finish(optimizer_applied=True)
        source[name] = dict(updates=prior_input['updates'], cursor=cursor.state_dict()['cursor'])
        commands[name] = args
    assert source['reference'] == source['recompute'] and not torch.cuda.is_initialized()
    assert source['reference']['cursor']['rng'] == prior_input['cursor']['rng']
    WRITE(PROFILE, dict(tag=TAG, identity=identity(), cache=cache, data=original['data'],
                        source=source, commands=commands, draw_per_arm=first.DRAW))
    print('P102A_G4_248K_PAIR_READY', first.DRAW, DIGEST(PROFILE), flush=True)
    return 0


def run(frozen):
    idle = first.prior.previous.shapes.idle
    exits, results = {}, {}
    for arm in PAIR:
        if not idle() or (OUT / 'STOP').exists():
            exits[arm] = None
            break
        call = ['timeout', '--kill-after=6s', '100s', sys.executable, '-u', '-B', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_recompute_vocab_pair', 'worker', arm]
        exits[arm] = subprocess.run(call, cwd=first.ROOT).returncode
        print('P102A_G4_248K_PAIR_EXIT', arm, exits[arm], flush=True)
        if exits[arm] == 0:
            results[arm] = READ(OUT / arm / 'report.json')
    assert idle() and identity() == frozen['identity'] and cache_identity() == frozen['cache']
    checks = {}
    if len(results) == len(PAIR):
        a, b = results.values()
        checks = dict(shared_start=a['initial'] == b['initial'], states=a['states'] == b['states'],
                      history=a['history'] == b['history'], validation=a['final'] == b['final'])
    WRITE(OUT / 'report.json', dict(tag=TAG, exits=exits, arms=results, checks=checks,
        device_returned=True, profile_sha256=DIGEST(PROFILE),
        actual_updates=sum(row['updates'] for row in results.values())))
    print('P102A_G4_248K_PAIR_COMPLETE', checks, flush=True)
    return 0 if checks and all(checks.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run', 'worker'))
    parser.add_argument('arm', nargs='?', choices=PAIR)
    args = parser.parse_args()
    if (args.stage == 'worker') != (args.arm is not None):
        parser.error('one explicit training arm is required only for worker')
    if (datetime.now(first.BASE.CUTOFF.tzinfo) + timedelta(minutes=5) >= first.BASE.CUTOFF
            or os.environ.get('CUDA_VISIBLE_DEVICES') != ('' if args.stage == 'prepare' else '0')):
        raise RuntimeError('authority window or explicit device isolation is invalid')
    if args.stage == 'prepare':
        OUT.mkdir(exist_ok=False)
    os.environ.update(TINYLM_DIR=str(OUT / 'scratch'), TINYLM_HF=str(OUT / 'scratch/HF'))
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    # Bind the existing trainer probe to the new diagnostic namespace per process.
    with patch.multiple(first, TAG=TAG, OUT=OUT, ARMS=PAIR):
        if args.stage == 'prepare':
            return prepare()
        frozen = READ(PROFILE)
        assert frozen['identity'] == identity() and cache_identity() == frozen['cache']
        assert os.environ['CUBLAS_WORKSPACE_CONFIG'] == first.prior.previous.shapes.LOSS.STRICT.WORKSPACE
        return run(frozen) if args.stage == 'run' else first.worker(args.arm, frozen)


if __name__ == '__main__':
    sys.exit(main())
