"""Exercise P109 native route training and actual file resume on an isolated CPU fixture."""

from contextlib import redirect_stdout
from datetime import datetime
import io
import json
import os
import sys
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p109_warm_visit_routes as warm
from scripts import p109_train_visit_policy as experiment
from scripts.diag_p102a_g4_full_delta_train import state_sha


TAG = 'p109_ntp_visit_resume_v2_20261119'
OUT = experiment.ROOT / 'test_result/evidence' / TAG
FIRST = OUT.with_name('p109_ntp_visit_resume_v1_20261119')
STEPS, WIDTH, TOKEN_POOL = 4, 16, 2048


class SplitBoundary(Exception):
    """The trainer has published an intact checkpoint at the chosen boundary."""


def small_config(*args, **kwargs):
    from tinylm.config import TMTConfig

    assert args[:4] == ('m100s12_g4', 'tied', WIDTH, True)
    return TMTConfig(vocab_size=64, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=WIDTH,
                     n_q_heads=4, n_kv_heads=2, n_prelude=2, n_middle=12, n_coda=2,
                     tie_mlp=True, mlp_group=4, cla_group=2, micro_group=8, grad_checkpoint=True)


def fixture():
    OUT.mkdir(exist_ok=False)
    cache = FIRST / 'cache'
    meta = dict(data='synthetic', dir=str(cache), tokens=TOKEN_POOL, vocab=64,
                train=1536, val=512, token_dtype='uint16')
    assert json.loads((cache / 'meta.json').read_bytes()) == meta
    for split, seed in (('train', 1818), ('val', 729)):
        values = np.random.default_rng(seed).integers(4, 64, size=meta[split], dtype=np.uint16)
        assert (cache / f'{split}.bin').read_bytes() == values.tobytes()
    return meta


def command(tag, resume=False, *, seed=1337, steps=STEPS):
    args = ['train', '--preset', 'm100s12_g4', '--arch', 'tied', '--data', 'synthetic',
            '--tokens', '0.002048M', '--pool-tokens', '0.002048M', '--exact-cache',
            '--steps', str(steps), '--seq', str(WIDTH), '--micro-bs', '2', '--accum', '2',
            '--eval-every', '1', '--save-every', '1', '--sched', 'wsd', '--anneal-start', '0',
            '--optimizer', 'muon', '--muon-scale', 'rms', '--muon-lr-mult', '4',
            '--train-repeat', '2', '--seed', str(seed), '--tag', tag]
    if resume:
        args.append('--resume')
    return args


def checkpoint(tag):
    return OUT / 'ckpt' / f'm100s12_g4_synthetic_{TOKEN_POOL}_{tag}.pt'


def read_state(tag):
    return torch.load(checkpoint(tag), weights_only=True, map_location='cpu')


def state_fingerprint(blob):
    from tinylm.train import trainer

    route_state = blob[trainer.CONTEXT_STATE_KEY]
    names = ('cursor', 'validation_rng', 'cpu_rng', 'cuda_rng', 'control')
    return dict(opt={name: state_sha(blob[name]) for name in ('model', 'opt', 'opt_muon')},
                replay=state_sha({name: route_state[name] for name in names}))


def run(policy, tag, resume=False, *, seed=1337, steps=STEPS):
    from tinylm import cli

    args = command(tag, resume, seed=seed, steps=steps)
    stream = io.StringIO()
    try:
        with redirect_stdout(stream):
            if policy is not None:
                return experiment.run_native(policy, args)
            args.extend(('--context-curriculum', f'{steps}:{WIDTH}'))
            with patch.object(sys, 'argv', ['tinylm', *args]):
                cli.main()
    finally:
        with (OUT / (tag + ('_resume' if resume else '') + '_trace.txt')).open('a', encoding='utf-8') as log:
            print(stream.getvalue(), end='', file=log)


def run_policy(policy):
    full = policy + '_continuous'
    split = policy + '_split'
    observed = run(policy, full)
    real_save = torch.save

    def stop_after_save(blob, path):
        real_save(blob, path)
        if path == checkpoint(split) and blob['step'] == 2:
            raise SplitBoundary

    with patch.object(torch, 'save', stop_after_save):
        try:
            run(policy, split)
        except SplitBoundary:
            pass
        else:
            raise AssertionError('the requested file checkpoint boundary was not reached')
    snapshot = read_state(split)
    assert snapshot['step'] == 2
    binding = snapshot['context_training_state']['binding']['recipe'][experiment.RECIPE_KEY]
    sealed = warm.io.digest(checkpoint(split))
    assert binding['policy'] == policy and binding['steps'] == STEPS and binding['seed'] == 1337
    rejects = []
    wrong = 'second_shuffle_r2' if policy == 'balanced_count' else 'balanced_count'
    for mode, seed, steps in ((None, 1337, STEPS), (wrong, 1337, STEPS),
                              (policy, 2024, STEPS), (policy, 1337, STEPS + 1)):
        try:
            run(mode, split, resume=True, seed=seed, steps=steps)
        except ValueError as error:
            if 'context recipe/cache/source/runtime binding differs' not in str(error):
                raise
            rejects.append(dict(policy=mode, seed=seed, steps=steps, reason=str(error)))
        else:
            raise AssertionError('a changed route recipe was accepted')
    assert sealed == warm.io.digest(checkpoint(split))
    resumed = run(policy, split, resume=True)
    right, left = read_state(split), read_state(full)
    assert right['step'] == left['step'] == STEPS
    assert all(report['optimizer_applied'] for report in observed['updates'])
    assert observed['updates'][2:] == resumed['updates']
    same = state_fingerprint(left) == state_fingerprint(right)
    assert same and left['cfg'] == right['cfg']
    return dict(full=observed, resumed=resumed, boundary_step=2, boundary_sha256=sealed,
                terminal_equal=same, terminal_fingerprint=state_fingerprint(left),
                rejected_recipes=rejects, terminal_checkpoint=str(checkpoint(split).relative_to(experiment.ROOT)))


def main():
    from tinylm.train import trainer

    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '' and datetime.now(warm.CUTOFF.tzinfo) < warm.CUTOFF
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    meta = fixture()
    real_evaluate = trainer.evaluate
    old_ckpt, old_logs = trainer.CKPT, trainer.LOGS

    def evaluate(model, loader, _count, device, **kwargs):
        return real_evaluate(model, loader, 2, device, **kwargs)

    with (patch.object(trainer, 'CKPT', OUT / 'ckpt'), patch.object(trainer, 'LOGS', OUT / 'logs'),
          patch.object(trainer, 'build_config', small_config), patch.object(trainer, 'evaluate', evaluate),
          patch.object(trainer, 'prepare', return_value=meta)):
        uniform = run('uniform_r2', 'routed_r2')
        base_file = FIRST / 'ckpt' / checkpoint('plain_r2').name
        base = torch.load(base_file, weights_only=True, map_location='cpu')
        assert base['step'] == STEPS
        baseline = state_fingerprint(base)
        assert baseline == state_fingerprint(read_state('routed_r2'))
        balanced = run_policy('balanced_count')
        shuffled = run_policy('second_shuffle_r2')
    assert not torch.cuda.is_initialized() and trainer.CKPT == old_ckpt and trainer.LOGS == old_logs
    assert len({b.get('route_sha256') for b in shuffled['full']['updates']}) > 1
    assert [r['index'] for r in balanced['full']['updates']] == list(range(STEPS))
    assert sorted(r['visits'] for r in balanced['full']['updates']) == [16, 28, 28, 40]
    assert all(row['visits'] == 28 for row in shuffled['full']['updates'])
    assert uniform['layer_token_visits'] == balanced['full']['layer_token_visits'] == shuffled['full']['layer_token_visits']
    assert len({baseline['opt']['model'], balanced['terminal_fingerprint']['opt']['model'],
                shuffled['terminal_fingerprint']['opt']['model']}) == 3
    report = dict(tag=TAG, fixture_tokens=TOKEN_POOL, focus='native NTP visit routing with file resume',
                  plain_equals_routed_uniform=True, plain_checkpoint_sha256=warm.io.digest(base_file),
                  uniform=uniform, balanced=balanced, shuffle=shuffled,
                  cpu_only=True, formal_quality=False, source_pins=experiment.source_pins())
    warm.io.write(OUT / 'report.json', report)
    print('P109_NATIVE_VISIT_CPU_PASS', uniform['layer_token_visits'], '4 wrong bindings refused per policy',
          warm.io.digest(OUT / 'report.json'), flush=True)


if __name__ == '__main__':
    main()
