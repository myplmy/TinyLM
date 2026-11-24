"""Compare full CE and reconstructed BF16 gradients in native G4 training."""

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from unittest.mock import patch

import torch

from scripts import diag_p102a_g4_full_delta as loss


BASE = loss.TRACE.precision.previous
TAG = 'p102a_g4_full_delta_train_v1_20261119'
OUT = loss.OUT.with_name(TAG)
SOURCE = Path(__file__).resolve()
CACHE = BASE.OUT / 'actual_artifacts/data_cache/synthetic_262144'
DEVICE_QUERY = ['/usr/lib/wsl/lib/nvidia-smi', '--query-compute-apps=pid',
                '--format=csv,noheader,nounits']


def state_sha(state):
    h = sha256()

    def add(value):
        if isinstance(value, torch.Tensor):
            tensor = value.detach().cpu().contiguous()
            h.update(repr(('tensor', str(tensor.dtype), tuple(tensor.shape))).encode())
            h.update(tensor.reshape(-1).view(torch.uint8).numpy())
        elif isinstance(value, dict):
            h.update(repr(('dict', len(value))).encode())
            for key in sorted(value, key=repr):
                add(key)
                add(value[key])
        elif isinstance(value, (tuple, list)):
            h.update(repr((type(value).__name__, len(value))).encode())
            for item in value:
                add(item)
        else:
            assert type(value) in (type(None), float, int, str, bool), type(value)
            raw = repr((type(value).__name__, value)).encode()
            h.update(len(raw).to_bytes(8, 'little'))
            h.update(raw)

    add(state)
    return h.hexdigest().upper()


def identity():
    paths = (SOURCE, CACHE / 'train.bin', CACHE / 'val.bin', CACHE / 'meta.json',
             loss.OUT / 'report.json', loss.OUT / 'terminal_readback.json')
    return loss.identity() | {str(path.relative_to(loss.ROOT)): loss.DIGEST(path) for path in paths}


def command(use_candidate):
    argv = BASE.cli_args('tile' if use_candidate else 'reference')
    arm = 'full_delta' if use_candidate else 'reference'
    argv[argv.index('--tag') + 1] = f'{TAG}_{arm}'
    return argv


def check_call(use_candidate, args, kwargs):
    assert args[:8] == ('m100s12_g4', 'tied', 'synthetic', BASE.POOL, BASE.STEPS, BASE.MICRO,
                        BASE.WIDTH, BASE.ACCUM)
    assert args[8:13] == (1e-3, 1, False, True, False)
    assert kwargs['pool_tokens'] == BASE.POOL and kwargs['exact_cache'] and not kwargs['kd']
    assert kwargs['train_repeat'] == 2 and not kwargs.get('ce_chunk')
    assert kwargs['ce_vocab_tile'] == (BASE.TILE if use_candidate else 0)


def prepare():
    from tinylm import cli
    import tinylm.train as train_package

    parent = json.loads((loss.OUT / 'terminal_readback.json').read_bytes())
    report = json.loads((loss.OUT / 'report.json').read_bytes())
    assert parent['report_sha256'] == loss.DIGEST(loss.OUT / 'report.json')
    assert report['gradient']['outside_tolerance'] == 0 and not report['gradient_byte_mismatches']
    assert all(row['unequal'] == 0 for row in report['chunks'].values())
    meta = json.loads((CACHE / 'meta.json').read_bytes())
    assert meta['dir'] == str(CACHE) and meta['data'] == 'synthetic' and meta['vocab'] == 32768
    targets = BASE.STEPS * BASE.MICRO * BASE.ACCUM * BASE.WIDTH
    assert meta['train'] >= 2 * targets and meta['tokens'] == BASE.POOL
    for use_candidate in (False, True):
        with patch.object(sys, 'argv', command(use_candidate)), patch.object(train_package, 'train') as stub:
            cli.main()
        stub.assert_called_once()
        check_call(use_candidate, *stub.call_args)
    assert not torch.cuda.is_initialized()
    BASE.write_new(OUT / 'profile.json', dict(tag=TAG, identity=identity(), data=meta, targets=targets,
                   stage2ik_input=report['input_sha256'], commands=[command(False), command(True)]))
    print('P102A_G4_FULL_DELTA_TRAIN_READY', targets, flush=True)


def train_arm(profile, use_candidate):
    from tinylm import cli
    from tinylm.train import muon, trainer
    import tinylm.train as train_package

    name = 'full_delta' if use_candidate else 'reference'
    directory = OUT / name
    ckpt, logs = directory / 'ckpt', directory / 'logs'
    original_model, original_loader = trainer.TiedMLPTransformer, trainer.Loader
    original_evaluate, original_step = trainer.evaluate, muon.Muon.step
    original_stats, original_train = trainer._step_stats, train_package.train
    peaks, states, samplers, elapsed = [], {}, {}, []
    initial, probe_calls = None, 0

    def build_model(cfg):
        nonlocal initial
        assert cfg.train_repeat == 2.0 and cfg.mlp_group == 4 and cfg.cla_group == 2
        model = original_model(cfg)
        assert len(model.visit_schedule()) == 28 and cfg.grad_checkpoint
        initial = state_sha(model.state_dict())
        return model

    def prepare_cache(data, tokens, *, exact, doc_filter, hf_tok, chat32, **_):
        assert data == 'synthetic' and tokens == BASE.POOL and exact
        assert not (doc_filter or hf_tok or chat32)
        return dict(profile['data'])

    def loader(split, *args, **kwargs):
        instance = original_loader(split, *args, **kwargs)
        samplers[split] = (instance, instance.rng.bit_generator.state)
        return instance

    def candidate_ce(model, x, y, tile):
        nonlocal probe_calls
        assert use_candidate and tile == BASE.TILE and y.numel() == 8192
        probe_calls += 1
        return loss.position_loss(model, model(x, return_hidden=True), y, loss.blocks.ROWS)

    def evaluate(model, source, iters, device, **kwargs):
        value = original_evaluate(model, source, 2, device, **kwargs)
        torch.cuda.reset_peak_memory_stats()
        return value

    def step(optimizer, *args, **kwargs):
        outcome = original_step(optimizer, *args, **kwargs)
        torch.cuda.synchronize()
        peaks.append((torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()))
        return outcome

    def save(blob, path):
        assert Path(path).parent == ckpt and not Path(path).exists()
        index = blob['step']
        if index not in states:
            states[index] = {key: state_sha(blob[key]) for key in ('model', 'opt', 'opt_muon')}

    def stats(values):
        elapsed.extend(values)
        return original_stats(values)

    def checked_train(*args, **kwargs):
        check_call(use_candidate, args, kwargs)
        return original_train(*args, **kwargs)

    argv = command(use_candidate)
    assert argv == profile['commands'][int(use_candidate)]
    print('P102A_G4_FULL_DELTA_TRAIN_ARM', name, ' '.join(argv), flush=True)
    with (patch.object(sys, 'argv', argv),
          patch.object(train_package, 'train', checked_train),
          patch.object(trainer, 'TiedMLPTransformer', build_model),
          patch.object(trainer, 'Loader', loader), patch.object(trainer, 'prepare', prepare_cache),
          patch.object(trainer, '_ce_vocab_tiled', candidate_ce),
          patch.object(trainer, 'CKPT', ckpt), patch.object(trainer, 'LOGS', logs),
          patch.object(trainer, 'evaluate', evaluate), patch.object(trainer, '_step_stats', stats),
          patch.object(muon.Muon, 'step', step), patch.object(torch, 'save', save)):
        cli.main()
    native, = logs.glob('*.json')
    raw = json.loads(native.read_bytes())
    assert not any(ckpt.iterdir()) and raw['n_skip'] == 0 and raw['tokens'] == profile['targets']
    assert len(elapsed) == len(peaks) == BASE.STEPS and list(states) == list(range(1, BASE.STEPS + 1))
    assert probe_calls == (BASE.STEPS * BASE.ACCUM if use_candidate else 0)
    result = dict(initial=initial, state_by_step=states, probe_calls=probe_calls, checkpoint_writes=0,
                  native_json=str(native.relative_to(loss.ROOT)), updates=len(peaks),
                  ce_by_step=[event['train_ce'] for event in raw['history']], val_ce=raw['final']['val_loss'],
                  step_ms=elapsed, after_first_median_ms=median(elapsed[1:]),
                  peak_allocated=max(row[0] for row in peaks), peak_reserved=max(row[1] for row in peaks),
                  samplers={key: dict(start=start, end=instance.rng.bit_generator.state)
                            for key, (instance, start) in samplers.items()})
    BASE.write_new(directory / 'report.json', result)
    return result


def actual():
    profile = json.loads((OUT / 'profile.json').read_bytes())
    assert profile['identity'] == identity() and os.environ['CUBLAS_WORKSPACE_CONFIG'] == loss.STRICT.WORKSPACE
    assert not subprocess.check_output(DEVICE_QUERY, timeout=8, text=True).strip()
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * (1 << 30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.set_float32_matmul_precision('high')
    BASE.write_new(OUT / 'active.json', dict(tag=TAG, pid=os.getpid()))
    reference = train_arm(profile, False)
    torch.cuda.empty_cache()
    candidate = train_arm(profile, True)
    torch.cuda.empty_cache()
    assert profile['identity'] == identity()
    assert reference['initial'] == candidate['initial'] and reference['samplers'] == candidate['samplers']
    changed = {str(index): [key for key, digest in left.items() if digest != candidate['state_by_step'][index][key]]
               for index, left in reference['state_by_step'].items()}
    native_ce, proposed_ce = reference['ce_by_step'], candidate['ce_by_step']
    assert len(native_ce) == len(proposed_ce) == BASE.STEPS
    outside = sum(abs(a - b) > 1e-5 + 1e-4 * abs(a) for a, b in zip(native_ce, proposed_ce, strict=True))
    passed = not any(changed.values()) and outside == 0
    BASE.write_new(OUT / 'report.json', dict(tag=TAG, reference=reference, candidate=candidate,
                   state_differences=changed, loss_violations=outside, numerical_pass=passed))
    print('P102A_G4_FULL_DELTA_TRAIN_RESULT', passed, changed, outside, flush=True)
    return 0 if passed else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'actual'))
    args = parser.parse_args()
    assert datetime.now(BASE.CUTOFF.tzinfo) + timedelta(minutes=5) < BASE.CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    if args.phase == 'prepare':
        OUT.mkdir(exist_ok=False)
    else:
        assert not (OUT / 'active.json').exists() and not (OUT / 'report.json').exists()
    local = OUT / 'artifacts'
    os.environ.update(TINYLM_DIR=str(local), TINYLM_HF=str(local / 'HF'))
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return prepare() if args.phase == 'prepare' else actual()


if __name__ == '__main__':
    sys.exit(main())
