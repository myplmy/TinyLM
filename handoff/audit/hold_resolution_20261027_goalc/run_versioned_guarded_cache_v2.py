"""Record direct build/consumer workers and reap only their owned process groups."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
PROOFS = ['verified.json', 'recovery_verified.json', 'partial_resolution_verified.json',
          'restricted_metadata_verified.json', 'baseline_preservation_scope.json', 'opaque_hold_verified.json']
CPU = dict(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
           MKL_NUM_THREADS='1', RAYON_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def load_config(path, expected):
    path = path.resolve()
    assert path.is_relative_to(AUDIT) and not path.is_symlink() and sha(path) == expected
    document = json.loads(path.read_bytes())
    assert document['cache_version'] >= 13 and document['goal_complete'] is False
    assert document['training_authorized'] is False
    for name, digest in document['input_pins'].items():
        assert sha(ROOT/name) == digest, ('cache configuration input changed', name)
    proof = json.loads((AUDIT/document['roster_proof']).read_bytes())
    assert proof['expected_cache_HOLD_positions'] == document['expected_HOLD_positions']
    for name, digest in proof['input_pins'].items(): assert sha(ROOT/name) == digest
    return path, document


def owned_stop(process):
    """The child was created here with start_new_session=True; no PID discovery."""
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            return process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    return process.wait()


def run_phase(config_path, expected, c, phase):
    n = c['cache_version']; out = BASE/f'cache_reviewed_partial_v{n}'
    label = 'PROCESS' if phase == 'build' else 'VERIFY'
    start = AUDIT/f'CACHE_REVIEWED_PARTIAL_V{n}_{label}_STARTED_V1.json'
    receipt = AUDIT/f'CACHE_REVIEWED_PARTIAL_V{n}_{label}_EXIT_V1.json'
    log = AUDIT/f'cache_reviewed_partial_v{n}_{phase}_v1.log'
    assert not start.exists() and not receipt.exists() and not log.exists()
    if phase == 'build':
        assert not out.exists()
    else:
        build = json.loads((AUDIT/f'CACHE_REVIEWED_PARTIAL_V{n}_PROCESS_EXIT_V1.json').read_bytes())
        assert build['process_exit_code'] == 0
        assert build['observation_method'] == 'ACTUAL_SUBPROCESS_WAIT_RETURN_CODE'
        assert sha(out/'built.json') == build['built_receipt']['sha256']
        assert not any((out/name).exists() for name in PROOFS)
    command = [sys.executable, '-I', '-B', str(Path(__file__)), '--config', str(config_path),
        '--expected-config-sha', expected, '--phase', phase]
    begin = time.monotonic(); interrupted = False
    with log.open('xb') as stream:
        process = subprocess.Popen(command, cwd=ROOT, env=dict(os.environ, **CPU),
            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            write_new(start, dict(status='ACTUAL_OWNED_CPU_WORKER_STARTED_NOT_VERIFIED',
                argv=command, pid=process.pid, process_group_id=process.pid,
                utc=datetime.now(timezone.utc).isoformat(),
                configuration_sha256=expected, phase=phase, goal_complete=False, training_authorized=False))
            print(json.dumps(dict(phase=phase, pid=process.pid, started_receipt=str(start.relative_to(ROOT)))), flush=True)
            code = process.wait()
        except (KeyboardInterrupt, SystemExit):
            interrupted = True; code = owned_stop(process)
        except BaseException:
            owned_stop(process)
            raise
    result = dict(status='ACTUAL_PHASE_EXIT_ZERO' if code == 0 and not interrupted else
        'INTERRUPTED_OR_FAILED_OWNED_WORKER_REAPED_PRESERVE_OUTPUT',
        process_exit_code=code, observation_method='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE',
        seconds=time.monotonic()-begin, argv=command, pid=process.pid,
        process_group_id=process.pid, interrupted=interrupted,
        owned_worker_wait_completed=True, phase=phase,
        log=dict(path=str(log.relative_to(ROOT)), sha256=sha(log)),
        new_output_exists=out.exists(), goal_complete=False, training_authorized=False)
    if (out/'built.json').exists():
        result['built_receipt'] = dict(path=str((out/'built.json').relative_to(ROOT)), sha256=sha(out/'built.json'))
    if phase == 'verify':
        result['proofs'] = {name: dict(path=str((out/name).relative_to(ROOT)), sha256=sha(out/name))
            for name in PROOFS if (out/name).exists()}
        assert code != 0 or interrupted or set(result['proofs']) == set(PROOFS)
    write_new(receipt, result)
    print(json.dumps({key: result[key] for key in ['status', 'phase', 'process_exit_code', 'seconds']}), flush=True)
    return result


def worker(c, phase):
    os.environ.update(CPU)
    sys.path.insert(0, str(AUDIT))
    import guarded_reviewed_cache_v6 as guarded
    number, roster, selection = c['cache_version'], c['roster_version'], c['selection_version']
    args = dict(base=BASE, roster=BASE/f'roster_reviewed_partial_v{roster}/complete.json',
        output_name=f'cache_reviewed_partial_v{number}',
        selection=AUDIT/f'ROOT_AUTHORED_SELECTIONS_V{selection}.json',
        opaque_path=AUDIT/c['opaque_contract'], opaque_sha=c['opaque_contract_sha256'])
    if phase == 'build':
        result = guarded.build(**args, adoptions=BASE/f'reviewed_partial_adoptions_v{roster}.json',
            proposal_name=f'guarded_partial_proposals_v{roster}')
    else:
        result = guarded.verify(**args)
    print(json.dumps({key: result[key] for key in ['status', 'counts', 'partial_resolution',
        'restricted_metadata', 'baseline_preservation_scope', 'opaque_hold'] if key in result}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--expected-config-sha', required=True)
    parser.add_argument('--phase', choices=['chain', 'build', 'verify'], default='chain')
    args = parser.parse_args()
    path, c = load_config(args.config, args.expected_config_sha)
    if args.phase != 'chain':
        return worker(c, args.phase)
    out = AUDIT/f"CACHE{c['cache_version']}_BUILD_AND_CONSUMER_CHAIN_V1.json"
    assert not out.exists()
    signal.signal(signal.SIGTERM, lambda _signum, _frame: (_ for _ in ()).throw(KeyboardInterrupt()))
    phases = []
    for phase in ['build', 'verify']:
        result = run_phase(path, args.expected_config_sha, c, phase)
        phases.append(result)
        if result['process_exit_code'] or result['interrupted']: break
    success = len(phases) == 2 and all(row['process_exit_code'] == 0 and not row['interrupted'] for row in phases)
    write_new(out, dict(status='ACTUAL_BUILD_AND_CONSUMER_EXIT_ZERO' if success else
        'FAILED_OR_INTERRUPTED_PHASE_PRESERVED_NO_OVERWRITE', phases=phases,
        configuration=dict(path=str(path.relative_to(ROOT)), sha256=args.expected_config_sha),
        runner_sha256=sha(Path(__file__)), consumer_requires_actual_build_exit_zero=True,
        CPU_threads=1, goal_complete=False, training_authorized=False))
    return 0 if success else 1


if __name__ == '__main__': sys.exit(main())
