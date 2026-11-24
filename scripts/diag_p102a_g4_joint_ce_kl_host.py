"""Compare CPU-resident teacher blocks against the recorded 248K G4 update."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys

import torch

from scripts import diag_p102a_g4_joint_ce_kl as joint


prior = joint.prior
TAG = 'p102a_g4_joint_ce_kl_host_v1_20261119'
OUT = joint.OUT.with_name(TAG)
CAP = 65
STORAGES = ('pageable', 'pinned')
REFERENCE_ARM = 'chunk_sum'
STATE_FIELDS = ('initial', 'parent_step', 'first_gradient', 'final', 'history')
MEASURE_FIELDS = ('peak_allocated', 'peak_reserved', 'median_seconds_after_first')
ARCHIVE = prior.ROOT / 'handoff/audit/research_20261118_01a1e647/P102A_JOINT_CE_KL_V2_SOURCES'
CHANGED = ('scripts/diag_p102a_g4_joint_ce_kl.py', 'scripts/p102a_joint_ce_kl.py')
SOURCES = (*joint.SOURCES, 'scripts/diag_p102a_g4_joint_ce_kl_host.py')
read, sha, write = joint.read, joint.SHA, joint.WRITE


def contract(bank, provenance, batches):
    profile = joint.OUT / 'profile.json'
    report = joint.OUT / 'report.json'
    source = read(profile)['contract']
    old = read(report)
    assert old['sources_unchanged'] and old['gpu_returned']
    assert old['exits'][REFERENCE_ARM] == 0 and all(old['comparisons'][REFERENCE_ARM].values())
    assert source['base'] == prior.expected(bank, provenance, batches)
    historical_pins = {}
    for name in joint.SOURCES:
        path = ARCHIVE / (Path(name).name + '.txt') if name in CHANGED else prior.ROOT / name
        historical_pins[name] = sha(path)
    assert source['pins'] == historical_pins
    micro_batches = sum(len(micros) for micros in batches)
    row_bytes = bank.shape[1] * bank.element_size()
    assert row_bytes == prior.VOCAB * 4
    return dict(tag=TAG, base=source['base'], reference=REFERENCE_ARM,
                reference_profile_sha256=sha(profile), reference_report_sha256=sha(report),
                historical_pins=historical_pins, pins={name: sha(prior.ROOT / name) for name in SOURCES},
                teacher_block_bytes=prior.ROWS * row_bytes,
                logical_transfer_bytes_per_arm=2 * micro_batches * prior.BATCH * prior.WIDTH * row_bytes,
                max_worker_s=CAP, storages=list(STORAGES), approval='WIP176', checkpoint_writes=0)


def run(frozen, bank, provenance, batches):
    exits, arms = {}, {}
    for storage in STORAGES:
        if (OUT / 'STOP').exists() or not prior.idle():
            exits[storage] = None
            break
        argv = ['timeout', '--kill-after=5s', f'{CAP}s', sys.executable, '-B', '-u', '-X', 'utf8', '-m',
                'scripts.diag_p102a_g4_joint_ce_kl_host', 'worker', storage]
        exits[storage] = subprocess.run(argv, cwd=prior.ROOT).returncode
        print('P102A_G4_HOST_EXIT', storage, exits[storage], flush=True)
        if exits[storage] == 0:
            arms[storage] = read(OUT / f'{storage}.json')
    ref = read(joint.OUT / 'report.json')['arms'][REFERENCE_ARM]
    comparisons = {name: {field: row[field] == ref[field] for field in STATE_FIELDS} for name, row in arms.items()}
    transfers_match = all(row['host_to_device_bytes'] == frozen['logical_transfer_bytes_per_arm'] for row in arms.values())
    gpu_returned = prior.idle()
    unchanged = frozen == contract(bank, provenance, batches)
    write(OUT / 'report.json', dict(arms=arms, exits=exits, comparisons=comparisons,
                                   reference={k: ref[k] for k in MEASURE_FIELDS},
                                   gpu_returned=gpu_returned, sources_unchanged=unchanged,
                                   logical_transfers_match=transfers_match))
    print('P102A_G4_HOST_COMPLETE', comparisons, gpu_returned, unchanged, flush=True)
    ok = gpu_returned and unchanged and transfers_match and set(arms) == set(STORAGES)
    return 0 if ok and all(all(row.values()) for row in comparisons.values()) else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run', 'worker'))
    parser.add_argument('storage', nargs='?', choices=STORAGES)
    args = parser.parse_args()
    if (args.phase == 'worker') != (args.storage is not None):
        parser.error('only a worker has a storage argument')
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    cutoff = prior.warm.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=len(STORAGES) * (CAP + 5)) < cutoff
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    bank, provenance = prior.frozen_logits(torch)
    bank = bank.float()
    batches = prior.crops()
    current = contract(bank, provenance, batches)
    if args.phase == 'prepare':
        checked = joint.cpu_gate(bank)
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write(OUT / 'profile.json', dict(contract=current, cpu=checked))
        print('P102A_G4_HOST_CPU_READY', checked, flush=True)
        return 0
    assert os.environ.get('PYTORCH_CUDA_ALLOC_CONF') == prior.ALLOCATOR
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    available_kib = next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:'))
    assert available_kib >= 4 * (1 << 20), '4 GiB free host RAM required'
    frozen = read(OUT / 'profile.json')
    assert frozen['contract'] == current and frozen['cpu']
    if args.phase == 'worker':
        return joint.worker(REFERENCE_ARM, bank, batches, out=OUT, teacher_storage=args.storage)
    return run(current, bank, provenance, batches)


if __name__ == '__main__':
    sys.exit(main())
