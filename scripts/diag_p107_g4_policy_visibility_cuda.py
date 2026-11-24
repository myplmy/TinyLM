"""Run the admitted P109 document-isolation cases on the existing CUDA G4."""

import argparse
from datetime import datetime, timedelta
from functools import partial
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p107_g4_policy_visibility_cpu as cpu
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p109_warm_visit_routes import CUTOFF, PARENT, load_parent


TAG = 'p107_g4_policy_visibility_cuda_v2_20261119'
OUT = cpu.OUT.with_name(TAG)
PROFILE = OUT / 'profile.json'
SOURCES = (*cpu.SOURCES, 'scripts/diag_p107_g4_policy_visibility_cuda.py')
SHA, WRITE = cpu.fixed.head.SHA, cpu.fixed.head.WRITE


def contract():
    source = cpu.OUT / 'report.json'
    previous = json.loads(source.read_bytes())
    assert SHA(PARENT) == cpu.fixed.head.PARENT_SHA
    assert previous['isolated_cases'] == 12 and previous['gpu_calls'] == 0
    for name, value in previous['sources'].items():
        assert SHA(cpu.fixed.ROOT / name) == value, name
    return dict(tag=TAG, parent_sha256=SHA(PARENT), cpu_report_sha256=SHA(source),
        route_receipts=[{k: row[k] for k in ('visits', 'kv', 'policy', 'update', 'route')}
                        for row in previous['routes']],
        sources={name: SHA(cpu.fixed.ROOT / name) for name in SOURCES}, approval='WIP176', checkpoint_writes=0)


def run(frozen):
    if not idle() or torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 7 * 2**30:
        raise RuntimeError('single idle CUDA device with 7 GiB free required')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(1337)
    cfg, state, step = load_parent(torch)
    cfg.train_repeat = 2.0
    model = cpu.policy.RoutedG4(cfg).train()
    model.load_state_dict(state, strict=True)
    del state
    model.cuda()
    model.set_anneal(1.)
    outputs = []
    # Only move fixture constructors. A device dispatch context re-enters the embedding recorder.
    fixture_tensors = SimpleNamespace(tensor=partial(torch.tensor, device='cuda'),
        arange=partial(torch.arange, device='cuda'), zeros_like=torch.zeros_like, equal=torch.equal, bool=torch.bool)
    with patch.object(cpu, 'torch', fixture_tensors), sdpa_kernel(SDPBackend.MATH):
        for expected, (name, index, route) in zip(frozen['route_receipts'], cpu.route_cases(model), strict=True):
            actual = dict(policy=name, update=index, **cpu.probe_route(model, route))
            assert {key: actual[key] for key in ('policy', 'update', 'visits', 'kv')} == {
                key: expected[key] for key in ('policy', 'update', 'visits', 'kv')}
            assert list(actual['route']) == expected['route']
            outputs.append(actual)
            print('P107_G4_POLICY_VISIBILITY_CUDA',name,index,actual['visits'],flush=True)
    torch.cuda.synchronize()
    assert contract() == frozen
    WRITE(OUT / 'report.json', dict(tag=TAG,routes=outputs,parent_step=step,
        closed_cases=sum(len(row['cases']) for row in outputs),
        open_cases=sum('open_logit_delta' in case for row in outputs for case in row['cases']),
        max_allocated=torch.cuda.max_memory_allocated(), checkpoint_writes=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run'))
    args = parser.parse_args()
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.mode == 'prepare' else '0')
    assert datetime.now(CUTOFF.tzinfo) + timedelta(minutes=2) < CUTOFF
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    expected = contract()
    if args.mode == 'prepare':
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        WRITE(PROFILE,expected)
        print('P107_G4_POLICY_VISIBILITY_CUDA_READY',SHA(PROFILE),flush=True)
        return
    assert expected == json.loads(PROFILE.read_bytes())
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    run(expected)


if __name__ == '__main__':
    main()
