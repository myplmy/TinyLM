"""Validate a real warm G4's routed NTP updates and CUDA checkpoint restore."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import torch

from scripts import diag_p102a_g4_recompute_operating as ce
from scripts import diag_p109_ntp_visit_resume as cpu
from scripts import diag_p109_warm_visit_routes as warm
from scripts import p109_train_visit_policy as experiment


TAG = 'p109_native_g4_visit_cuda_v1_20261119'
OUT = cpu.OUT.with_name(TAG)
ROOT, CACHE = experiment.ROOT, ce.CACHE
PLAN = ROOT / 'test_plan/P109_16층-공유-재귀-프리셋-통합.md'
SHA_PARENT = 'D576B9EB6DEF02DF5DCCAD91E484098AFB67A52553A7A735B21249DB2D9EC3D5'
PHASES = ('continuous', 'boundary', 'resume')
POLICY, STEPS, MICROS, ACCUM, WIDTH = 'balanced_count', 4, 8, 2, 1024
CKPT, LOGS = OUT / 'ckpt', OUT / 'logs'


def scope():
    from tinylm.train.context_training_state import cache_identity

    files = (Path(__file__).resolve(), PLAN, warm.PARENT, cpu.OUT / 'report.json',
             ROOT / 'tinylm/train/recomputed_ce.py')
    inputs = {str(p.relative_to(ROOT)): warm.io.digest(p) for p in files}
    if inputs[str(warm.PARENT.relative_to(ROOT))] != SHA_PARENT:
        raise ValueError('exact P079 G4 warm parent required')
    data = json.loads((CACHE / 'meta.json').read_bytes())
    proof = json.loads((cpu.OUT / 'report.json').read_bytes())
    sources = experiment.source_pins()
    if (not proof['balanced']['terminal_equal'] or not proof['shuffle']['terminal_equal']
            or not proof['plain_equals_routed_uniform'] or proof['source_pins'] != sources
            or data['vocab'] != 32768 or data['data'] != 'synthetic' or data['dir'] != str(CACHE)):
        raise ValueError('CPU native resume proof and exact synthetic geometry required')
    return dict(sources=sources, inputs=inputs, cache=cache_identity(CACHE), data=data)


def args_for(phase):
    tag = f"{TAG}_{'split' if phase in ('boundary', 'resume') else 'continuous'}"
    args = ['train', '--preset', 'm100s12_g4', '--arch', 'tied', '--data', 'synthetic',
            '--tokens', '5M', '--pool-tokens', '5M', '--exact-cache', '--steps', str(STEPS),
            '--seq', str(WIDTH), '--micro-bs', str(MICROS), '--accum', str(ACCUM),
            '--eval-every', '2', '--save-every', '2', '--sched', 'wsd', '--anneal-start', '0',
            '--optimizer', 'muon', '--muon-scale', 'rms', '--muon-lr-mult', '4', '--matrix-weight-decay', '0',
            '--train-repeat', '2', '--ce-recompute-rows', '1024', '--seed', '1337', '--tag', tag]
    if phase == 'resume':
        args.append('--resume')
    return args


def worker(phase, frozen):
    from tinylm.train import trainer

    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 12 * (1 << 30):
        raise RuntimeError('one CUDA device with at least 12 GiB free is required')
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    _, weights, parent_step = warm.load_parent(torch)
    routed = experiment.RoutedG4
    real_save, real_eval = torch.save, trainer.evaluate
    states = {}
    tag = args_for(phase)[args_for(phase).index('--tag') + 1]
    stem = 'm100s12_g4_synthetic_5M_' + tag
    target = CKPT / (stem + '.pt')
    if phase == 'resume':
        boundary = json.loads((OUT / 'boundary.json').read_bytes())
        assert warm.io.digest(target) == boundary['checkpoint_sha256']

    def construct(cfg):
        model = routed(cfg)
        model.load_state_dict(weights, strict=True)
        return model

    def source(data, tokens, *, exact, doc_filter, hf_tok, chat32, **_):
        assert data == 'synthetic' and tokens == ce.POOL and exact and not (doc_filter or hf_tok or chat32)
        return dict(frozen['data'])

    def evaluate(model, loader, _n, device, **kwargs):
        return real_eval(model, loader, 2, device, **kwargs)

    def save(blob, path):
        index = str(blob['step'])
        assert path.parent == CKPT and blob['ce_recompute_rows'] == 1024 and index in ('2', '4')
        contract = blob[trainer.CONTEXT_STATE_KEY]['binding']['recipe'][experiment.RECIPE_KEY]
        assert (contract['policy'], contract['steps'], contract['seed']) == (POLICY, STEPS, 1337)
        if index not in states:
            states[index] = cpu.state_fingerprint(blob)
        if phase == 'boundary' and path == target:
            assert index == '2' and not target.exists()
            real_save(blob, target)
            raise cpu.SplitBoundary

    print('P109_NATIVE_VISIT_CUDA_PHASE', phase, os.getpid(), flush=True)
    with (patch.object(trainer, 'CKPT', CKPT), patch.object(trainer, 'LOGS', LOGS),
          patch.object(trainer, 'prepare', source), patch.object(trainer, 'evaluate', evaluate),
          patch.object(experiment, 'RoutedG4', construct), patch.object(torch, 'save', save)):
        try:
            receipt = experiment.run_native(POLICY, args_for(phase))
        except cpu.SplitBoundary:
            if phase != 'boundary':
                raise
            receipt = None
    native = LOGS / (stem + '.json')
    actual = None if receipt is None else json.loads(native.read_bytes())
    checkpoint_sha = None
    if phase in ('boundary', 'resume'):
        assert 0 < target.stat().st_size < 1 << 30
        checkpoint_sha = warm.io.digest(target)
    expected = {'2', '4'} if phase == 'continuous' else {'2'} if phase == 'boundary' else {'4'}
    assert set(states) == expected and (receipt is None) == (phase == 'boundary')
    if receipt is not None:
        assert actual['tokens'] == MICROS * ACCUM * WIDTH * STEPS and actual['n_skip'] == 0
        assert all(row['optimizer_applied'] for row in receipt['updates'])
    result = dict(phase=phase, parent_step=parent_step, states=states, receipt=receipt,
                  native_json=str(native.relative_to(ROOT)) if actual else None,
                  history=actual['history'] if actual else None, final=actual['final'] if actual else None,
                  checkpoint_sha256=checkpoint_sha, checkpoint_bytes=target.stat().st_size if checkpoint_sha else 0)
    warm.io.write(OUT / f'{phase}.json', result)
    return 0


def run(frozen):
    idle = ce.previous.shapes.idle
    exits = {}
    reports = {}
    for phase in PHASES:
        if not idle() or (OUT / 'STOP').exists() or (phase == 'resume' and exits.get('boundary') != 0):
            exits[phase] = None
            break
        call = ['timeout', '--kill-after=5s', '70s', sys.executable, '-u', '-B', '-X', 'utf8', '-m',
                'scripts.diag_p109_ntp_visit_cuda', 'worker', phase]
        exits[phase] = subprocess.run(call, cwd=ROOT).returncode
        print('P109_NATIVE_VISIT_CUDA_EXIT', phase, exits[phase], flush=True)
        if exits[phase] == 0:
            reports[phase] = json.loads((OUT / f'{phase}.json').read_bytes())
    assert idle() and frozen == scope()
    checks = {}
    if set(reports) == set(PHASES):
        full, boundary, resumed = (reports[name] for name in PHASES)
        route = full['receipt']['updates']
        checks = dict(split_states=full['states']['2'] == boundary['states']['2'],
                      resumed_states=full['states']['4'] == resumed['states']['4'],
                      resumed_route=route[2:] == resumed['receipt']['updates'],
                      balanced_visits=sorted(row['visits'] for row in route) == [16, 28, 28, 40],
                      same_loss=full['history'] == resumed['history'] and full['final'] == resumed['final'],
                      single_split_same_sha=boundary['checkpoint_sha256'] == resumed['checkpoint_sha256']
                      and len(list(CKPT.glob('*.pt'))) == 1)
    warm.io.write(OUT / 'report.json', dict(exits=exits, checks=checks, gpu_returned=True, phases=reports))
    print('P109_NATIVE_VISIT_CUDA_COMPLETE', checks, flush=True)
    return 0 if checks and all(checks.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run', 'worker'))
    parser.add_argument('phase', nargs='?', choices=PHASES)
    args = parser.parse_args()
    if (args.mode == 'worker') != (args.phase is not None):
        parser.error('phase belongs to the worker')
    assert datetime.now(warm.CUTOFF.tzinfo) + timedelta(minutes=5) < warm.CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.mode == 'prepare' else '0')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    frozen = scope()
    profile = OUT / 'profile.json'
    if args.mode == 'prepare':
        OUT.mkdir(exist_ok=False)
        assert not torch.cuda.is_initialized()
        warm.io.write(profile, frozen)
        print('P109_NATIVE_VISIT_CUDA_READY', warm.io.digest(profile), flush=True)
        return 0
    assert frozen == json.loads(profile.read_bytes())
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    return run(frozen) if args.mode == 'run' else worker(args.phase, frozen)


if __name__ == '__main__':
    sys.exit(main())
