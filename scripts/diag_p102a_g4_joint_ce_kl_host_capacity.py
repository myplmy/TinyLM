"""Train 4x2 G4 with the same samples as 2x4 and compare teacher placement."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys

import torch

from scripts import diag_p102a_g4_joint_ce_kl_host as host


prior, joint = host.prior, host.joint
read, sha, write = host.read, host.sha, host.write
TAG = 'p102a_g4_joint_ce_kl_host_capacity_v1_20261119'
OUT = host.OUT.with_name(TAG)
WORKER = 'scripts/diag_p102a_g4_joint_ce_kl.py'
ARCHIVED_WORKER = host.ARCHIVE / 'diag_p102a_g4_joint_ce_kl_host_v1_worker.py.txt'
STORAGES = {'cuda': host.REFERENCE_ARM, 'pinned': 'pinned'}


def merge_micros(batches):
    assert len(batches) == prior.UPDATES and all(len(group) == 4 for group in batches)
    return [[(torch.cat((x0, x1)), torch.cat((y0, y1)))
             for (x0, y0), (x1, y1) in zip(group[::2], group[1::2], strict=True)] for group in batches]


def ordered_tokens_sha(batches):
    tensors = [(torch.cat([x.flatten() for x, _ in group]), torch.cat([y.flatten() for _, y in group]))
               for group in batches]
    return prior.state_sha(tensors)


def contract(bank, provenance, original, merged):
    profile_path, report_path = host.OUT / 'profile.json', host.OUT / 'report.json'
    base = host.contract(bank, provenance, original)
    archived_pins = dict(base['pins'])
    archived_pins[WORKER] = sha(ARCHIVED_WORKER)
    assert read(profile_path)['contract'] == dict(base, pins=archived_pins)
    history = read(report_path)
    assert history['gpu_returned'] and history['sources_unchanged'] and history['logical_transfers_match']
    assert history['exits'] == dict.fromkeys(host.STORAGES, 0)
    assert all(all(checks.values()) for checks in history['comparisons'].values())
    ordering = ordered_tokens_sha(original)
    assert ordering == ordered_tokens_sha(merged)
    assert all(len(group) == 2 and all(x.shape == (4, prior.WIDTH) for x, _ in group) for group in merged)
    return dict(tag=TAG, base=base, replay_2x4_profile_sha256=sha(profile_path),
                replay_2x4_report_sha256=sha(report_path), replay_2x4=history['reference'],
                runner_sha256=sha(Path(__file__)), frozen_ordered_tokens_sha256=ordering,
                merged_batch_sha256=prior.state_sha(merged), micro_bs=4, accum=2, storages=STORAGES)


def run(frozen, bank, provenance, original, merged):
    arms, exits = {}, {}
    for name, receipt in STORAGES.items():
        if (OUT / 'STOP').exists() or not prior.idle():
            exits[name] = None
            break
        argv = ['timeout', '--kill-after=5s', f'{host.CAP}s', sys.executable, '-B', '-u', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_joint_ce_kl_host_capacity', 'worker', name]
        exits[name] = subprocess.run(argv, cwd=prior.ROOT).returncode
        print('P102A_G4_HOST_CAPACITY_EXIT', name, exits[name], flush=True)
        if exits[name] == 0:
            arms[name] = read(OUT / f'{receipt}.json')
    comparisons, budget = {}, {}
    if set(arms) == set(STORAGES):
        comparisons = {field: arms['cuda'][field] == arms['pinned'][field] for field in host.STATE_FIELDS}
        budget = {key: arms['pinned'][key] <= frozen['replay_2x4'][key] for key in ('peak_allocated','peak_reserved')}
        assert arms['pinned']['host_to_device_bytes'] == frozen['base']['logical_transfer_bytes_per_arm']
    gpu_returned = prior.idle()
    unchanged = frozen == contract(bank, provenance, original, merged)
    write(OUT / 'report.json', dict(arms=arms, exits=exits, comparisons=comparisons, fits_prior_2x4_budget=budget,
                                   reference_2x4=frozen['replay_2x4'], gpu_returned=gpu_returned,
                                   sources_unchanged=unchanged))
    print('P102A_G4_HOST_CAPACITY_COMPLETE', comparisons, budget, gpu_returned, unchanged, flush=True)
    return 0 if gpu_returned and unchanged and comparisons and all(comparisons.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run', 'worker'))
    parser.add_argument('storage', nargs='?', choices=STORAGES)
    args = parser.parse_args()
    if (args.phase == 'worker') != (args.storage is not None):
        parser.error('only a worker has a storage argument')
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    cutoff = prior.warm.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=len(STORAGES) * (host.CAP + 5)) < cutoff
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    bank, provenance = prior.frozen_logits(torch)
    bank = bank.float()
    original = prior.crops()
    merged = merge_micros(original)
    current = contract(bank, provenance, original, merged)
    if args.phase == 'prepare':
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write(OUT / 'profile.json', current)
        print('P102A_G4_HOST_CAPACITY_CPU_READY', current['frozen_ordered_tokens_sha256'], flush=True)
        return 0
    assert os.environ.get('PYTORCH_CUDA_ALLOC_CONF') == prior.ALLOCATOR
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    available_kib = next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:'))
    assert available_kib >= 4 * (1 << 20), '4 GiB free host RAM required'
    assert read(OUT / 'profile.json') == current
    if args.phase == 'worker':
        return joint.worker(host.REFERENCE_ARM, bank, merged, out=OUT, teacher_storage=args.storage)
    return run(current, bank, provenance, original, merged)


if __name__ == '__main__':
    sys.exit(main())
