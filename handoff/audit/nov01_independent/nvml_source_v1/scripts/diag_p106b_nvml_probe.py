#!/usr/bin/env python3
"""SMI와 지속NVML을 idle/작은GEMM에서 대조한다. 학습/모델/체크포인트0."""
import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_nvml_probe import NvmlClient
from scripts import diag_p106b_resource_matrix as resource
from scripts.diag_p107_hybrid_mntp import close_owned_cuda, independent_final_checks

OUTPUT = ROOT / 'test_result/evidence/p106b_nvml_probe_v1_20261101'
DEADLINE = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
SOURCES = ('scripts/p106b_nvml_probe.py', 'scripts/test_p106b_nvml_probe.py',
           'scripts/diag_p106b_nvml_probe.py', 'scripts/diag_p107_adaptive_training.py',
           'scripts/diag_p107_hybrid_mntp.py')


def identity():
    return {name:hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper() for name in SOURCES}


def smi():
    raw = subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi',
        '--query-gpu=memory.used,memory.free,memory.total', '--format=csv,noheader,nounits'], text=True, timeout=3)
    lines = raw.splitlines()
    if len(lines) != 1:
        raise ValueError('single GPU required')
    values = [int(part.strip()) * 2**20 for part in lines[0].split(',')]
    return dict(zip(('used_bytes','free_bytes','total_bytes'), values))


def execute():
    resource.need((DEADLINE-datetime.now(timezone.utc)).total_seconds() > 180, '마감180초예비')
    resource.need(not OUTPUT.exists(), 'fresh NVML experiment required')
    OUTPUT.mkdir(parents=True)
    report = dict(schema='P106B_NVML_PERSISTENT_GPU_PROBE_V1', status='STARTED', source=identity(),
        model_loads=0, optimizer_updates=0, checkpoint_writes=0, resource_limit_bytes=8_000_000_000,
        torch_allocator_cap_bytes=256 * 2**20, query_timeout_seconds=3, rows=[])
    code, client, worker, torch = 9, None, None, None
    a = b = out = None
    stop = threading.Event()
    iterations, worker_errors = [0], []
    started = time.monotonic()
    try:
        baseline = smi()
        report['baseline'] = baseline
        resource.need(baseline['free_bytes'] >= 8_000_000_000, '보수적8GB여유점검')
        import torch
        resource.need(torch.cuda.is_available(), '실제CUDA 필요')
        torch.cuda.set_per_process_memory_fraction(256 * 2**20 / torch.cuda.get_device_properties(0).total_memory)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        client = NvmlClient(timeout=3.)
        with resource.wall(150), torch.no_grad():
            a = torch.ones((2048, 2048), device='cuda', dtype=torch.float32)
            b = torch.ones_like(a)
            out = torch.empty_like(a)
            torch.mm(a, b, out=out)
            torch.cuda.synchronize()
            def load():
                try:
                    with torch.no_grad():
                        while not stop.is_set():
                            torch.mm(a, b, out=out)
                            torch.cuda.synchronize()
                            iterations[0] += 1
                            time.sleep(.005)
                except Exception as exc:
                    worker_errors.append(str(exc))
            for phase, count in [('idle',20),('busy',60)]:
                if phase == 'busy':
                    worker = threading.Thread(target=load, daemon=True)
                    worker.start()
                for index in range(count):
                    row = dict(phase=phase, index=index)
                    for kind in (('smi','persistent') if index % 2 == 0 else ('persistent','smi')):
                        tick = time.monotonic()
                        try:
                            row[kind] = (smi if kind == 'smi' else client.memory)()
                        except Exception as exc:
                            row[kind + '_error'] = dict(type=type(exc).__name__, message=str(exc)[:500])
                        row[kind + '_seconds'] = time.monotonic() - tick
                    if 'smi' in row and 'persistent' in row:
                        row['used_bytes_delta'] = abs(row['smi']['used_bytes'] - row['persistent']['used_bytes'])
                        row['total_bytes_delta'] = abs(row['smi']['total_bytes'] - row['persistent']['total_bytes'])
                    report['rows'].append(row)
                    time.sleep(.1)
            stop.set(); worker.join(timeout=5)
            resource.need(not worker.is_alive() and not worker_errors and iterations[0] > 0, 'GEMM부하종결필요')
            report['gemm_iterations'] = iterations[0]
            report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
            report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
            successful = [row for row in report['rows'] if 'smi' in row and 'persistent' in row]
            resource.need(len(successful) == 80 and all(row['used_bytes_delta'] <= 2 * 2**20
                and row['total_bytes_delta'] <= 2**20 for row in successful), '안정fixture에서API2MiB대조불충족')
            resource.need(max(row['persistent']['used_bytes'] for row in successful) - baseline['used_bytes'] < 8_000_000_000, '8GB표본초과')
            report['summary'] = {phase:{kind:dict(median_seconds=statistics.median(row[kind+'_seconds'] for row in successful if row['phase']==phase),
                maximum_seconds=max(row[kind+'_seconds'] for row in successful if row['phase']==phase))
                for kind in ('smi','persistent')} for phase in ('idle','busy')}
            report['status'], code = 'IDLE_BUSY_NVML_PARITY_COMPLETE', 0
    except Exception as exc:
        report.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:1500])
    finally:
        stop.set()
        if worker is not None:
            worker.join(timeout=5)
        a = b = out = None
        gc.collect()
        def close_client():
            if client is not None: report['client'] = client.close()
        def cuda():
            if torch is not None: close_owned_cuda(torch, report)
        def source():
            report['source_unchanged'] = identity() == report['source']
            resource.need(report['source_unchanged'], '실행중source변경')
        good = independent_final_checks(report, [('client',close_client),('cuda',cuda),('source',source)])
        if not good: report['status'], code = 'ERROR', 9
        report.update(final_exit=code, wall_seconds=time.monotonic()-started,
                      inference_or_training_speed_claim=False, exact_process_peak_claim=False)
        resource.write_new(OUTPUT/'report.json', report)
        print(json.dumps({key:report[key] for key in ('status','final_exit','wall_seconds')}, ensure_ascii=False), flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps(dict(status='SOURCE_ONLY', source=identity(), gpu_runs=0))); return 0
    return execute()


if __name__ == '__main__':
    raise SystemExit(main())
