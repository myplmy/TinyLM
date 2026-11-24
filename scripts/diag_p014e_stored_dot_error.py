"""New CPU oracle on old packed buffers/synthetic inputs/closed outputs only."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p014e_stored_dot_error import unpack_fp32, decimal_dot_fp32, decimal_error

OLD = ROOT / 'test_result/evidence/p014e_direct_packed_v1_s1337'
BASE = ROOT / 'test_result/evidence/p014e_cpu_body_reduction_v1_20261117'
PACKED = 'runs/deploy/p014e_native595_g128_v1_20261027/ternary5_existing_twn.pt'
CASES = ('model0_matrix000', 'model0_matrix002')
SOURCES = ('scripts/diag_p014e_stored_dot_error.py', 'scripts/p014e_stored_dot_error.py',
           'scripts/test_p014e_stored_dot_error.py')

def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            result.update(block)
    return result.hexdigest().upper()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) >= 20_000_000:
        raise ValueError('owned metadata cap20MB')
    with Path(path).open('xb') as stream:
        stream.write(raw)

def prepare():
    direct = read(OLD / 'profile.json')
    cpu = read(OLD / 'cpu_v1/profile.json')
    closed = read(OLD / 'cpu_v1/actual/report.json')
    assert direct['synthetic_activations_not_model_features'] is True
    assert closed['numerical_gate_failures'] == 3 and len(closed['rows']) == 25
    selected = [row for row in closed['rows'] if row['case'] in CASES]
    assert len(selected) == 4 and sum(not row['original_gate'] for row in selected) == 3
    assert {(r['case'], r['operator']) for r in selected} == {(c, m) for c in CASES for m in ('linear_m1', 'linear_m8')}
    inputs = {str(path.relative_to(ROOT)): sha(path) for path in
              (OLD/'profile.json', OLD/'cpu_v1/profile.json', OLD/'cpu_v1/actual/report.json')}
    for name, expected in cpu['sources'].items():
        assert sha(ROOT/name) == expected
    spec = direct['inputs'][PACKED]
    assert sha(ROOT/PACKED) == spec['sha256']
    inputs[PACKED] = spec['sha256']
    for spec in [cpu['activations'], *[row['vectors'] for row in selected], cpu['library']]:
        assert sha(ROOT/spec['path']) == spec['sha256']
        inputs[spec['path']] = spec['sha256']
    contract = ROOT/'test_result/099_log_20261117_P014E_Stage6Wg0_stored_dot_contracts.txt'
    text = contract.read_text(encoding='utf-8')
    assert 'Ran 3 tests' in text and '[runlog] 종료코드 0' in text
    inputs[str(contract.relative_to(ROOT))] = sha(contract)
    profile = dict(user_directive=158, UTC=datetime.now(timezone.utc).isoformat(),
        sources={name:sha(ROOT/name) for name in SOURCES}, original_sources=cpu['sources'], inputs=inputs,
        selected_rows=selected, cases={c['id']:c for c in cpu['cases'] if c['id'] in CASES},
        original_atol=cpu['linear_atol'], original_rtol=cpu['linear_rtol'],
        original_case_selection='POSTHOC_THREE_NEGATIVES_PLUS_ONE_SAME_MATRIX_PASSING_CONTROL',
        original_gate_changed=False, maximum_seconds=300, maximum_failed_cells=256,
        Decimal_precision=512, minimum_available_RAM_bytes=1<<30, source_payload_reads=1,
        original_checkpoints=0, model_loads=0, operator_or_kernel_calls=0, GPU_calls=0,
        C_compile_or_load=0, original_ABBA_reexecuted=False, quality_claim=False)
    BASE.mkdir(exist_ok=False)
    write(BASE/'profile.json', profile)
    print('STORED_DOT_PROFILE', sha(BASE/'profile.json'), 'four stored cases/one packed tensor payload/model0', flush=True)

def actual():
    profile = read(BASE/'profile.json')
    start = time.perf_counter()
    out = BASE/'actual'
    out.mkdir(exist_ok=False)
    report = dict(status='STARTED', returncode=1, user_directive=158, rows=[],
        profile_sha256=sha(BASE/'profile.json'), original_model_loads=0, original_checkpoint_reads=0,
        original_operator_or_C_calls=0, original_ABBA_reexecuted=False, GPU_calls=0,
        training=0, optimizer_updates=0, checkpoint_writes=0, quality_adoption=False)
    import torch
    import psutil
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    payload = record = None
    references = []
    def check():
        if time.perf_counter()-start > profile['maximum_seconds']:
            raise TimeoutError('CPU oracle wall300s')
        if datetime.now(timezone.utc) >= datetime.fromisoformat('2026-11-17T16:40:00+09:00'):
            raise TimeoutError('current oracle cutoff')
        for name, expected in {**profile['inputs'], **profile['sources'], **profile['original_sources']}.items():
            if sha(ROOT/name) != expected:
                raise ValueError('old input or frozen source changed: '+name)
        if torch.cuda.is_initialized():
            raise ValueError('CPU diagnostic initialized CUDA')
    try:
        check()
        if psutil.virtual_memory().available < profile['minimum_available_RAM_bytes']:
            raise ValueError('available RAM1GiB required')
        report['RSS_entry'] = psutil.Process().memory_info().rss
        payload = torch.load(ROOT/PACKED, map_location='cpu', weights_only=True)
        assert payload['schema'] == 'P014E_ORIGINAL_SCALE_G128_PAYLOAD_V1'
        assert payload['embedding_format'] == 'ternary5_existing_twn'
        with np.load(ROOT/read(OLD/'cpu_v1/profile.json')['activations']['path'], allow_pickle=False) as archive:
            activations = {name:archive[name].copy() for name in CASES}
        for case in CASES:
            spec = profile['cases'][case]
            matrix_index = int(spec['record_id'].removeprefix('matrix'))
            record = payload['matrices'][matrix_index]['weight']
            codes = record['codes'].detach().cpu().numpy().copy()
            scales = record['scales'].detach().cpu().numpy().copy()
            signature = spec['signature']
            assert hashlib.sha256(codes.tobytes()).hexdigest().upper() == signature['code_sha256']
            assert hashlib.sha256(scales.tobytes()).hexdigest().upper() == signature['scale_sha256']
            weight = unpack_fp32(codes, scales, group=signature['group'], width=signature['in_features'])
            assert weight.shape == (signature['out_features'], signature['in_features'])
            x_all = activations[case]
            assert x_all.dtype == np.float32 and x_all.ndim == 2 and x_all.shape[1] == weight.shape[1]
            assert np.isfinite(x_all).all()
            for old in [r for r in profile['selected_rows'] if r['case'] == case]:
                check()
                size = int(old['operator'].removeprefix('linear_m'))
                x = x_all[:size]
                with np.load(ROOT/old['vectors']['path'], allow_pickle=False) as saved:
                    reference = saved['reference'].copy()
                    actual = saved['actual'].copy()
                assert reference.dtype == actual.dtype == np.float32
                assert list(actual.shape) == old['shape']
                bad = ~np.isclose(actual, reference, rtol=profile['original_rtol'], atol=profile['original_atol'])
                assert bool(not bad.any()) == old['original_gate']
                indices = np.argwhere(bad)
                if len(indices) > profile['maximum_failed_cells']:
                    raise ValueError('do not shrink original failed-cell denominator')
                oracle64 = x.astype(np.float64) @ weight.astype(np.float64).T
                oracle32 = oracle64.astype(np.float32)
                record_path = out/(case+'_'+old['operator']+'_oracle.npz')
                with record_path.open('xb') as stream:
                    np.savez_compressed(stream, oracle64=oracle64, oracle32=oracle32)
                cells = []
                for sample, column in indices:
                    exact, flags = decimal_dot_fp32(x[int(sample)], weight[int(column)])
                    c_error = decimal_error(actual[sample,column], exact)
                    ref_error = decimal_error(reference[sample,column], exact)
                    cells.append(dict(sample=int(sample), column=int(column), exact_dot_decimal=str(exact),
                        actual_C=float(actual[sample,column]), reference_FP32=float(reference[sample,column]),
                        oracle64=float(oracle64[sample,column]), actual_error_decimal=str(c_error),
                        reference_error_decimal=str(ref_error), actual_no_worse_than_reference=(c_error <= ref_error),
                        actual_strictly_better=(c_error < ref_error), Decimal_flags=flags))
                actual_oracle = np.isclose(actual, oracle32, rtol=profile['original_rtol'], atol=profile['original_atol'])
                row = dict(case=case, operator=old['operator'], shape=old['shape'],
                    old_gate=old['original_gate'], original_violating_elements=len(indices),
                    actual_C_vs_oracle64_cast_bit_equal=bool(np.array_equal(actual.view(np.uint32), oracle32.view(np.uint32))),
                    actual_C_vs_oracle64_cast_violations=int((~actual_oracle).sum()),
                    actual_C_vs_oracle64_cast_max_abs=float(np.abs(actual.astype(np.float64)-oracle32).max()),
                    reference_FP32_vs_oracle64_cast_max_abs=float(np.abs(reference.astype(np.float64)-oracle32).max()),
                    decimal_failed_cells=cells,
                    oracle=dict(path=str(record_path.relative_to(ROOT)), sha256=sha(record_path), bytes=record_path.stat().st_size))
                report['rows'].append(row)
                print('STORED_DOT_CASE', case, old['operator'], 'old_bad', len(indices), 'C_vs64_bit', row['actual_C_vs_oracle64_cast_bit_equal'], flush=True)
                del x, reference, actual, bad, indices, oracle64, oracle32, actual_oracle
            record = None
            del codes, scales, weight, x_all
        payload = None
        gc.collect()
        assert len(report['rows']) == 4 and sum(not r['old_gate'] for r in report['rows']) == 3
        cells = [c for r in report['rows'] for c in r['decimal_failed_cells']]
        report.update(status='STORED_DOT_PRECISION_DIAGNOSTIC_COMPLETE', returncode=0,
            original_gate_negatives_preserved=3, passing_control=1, Decimal_cells=len(cells),
            all_original_bad_cells_C_closer=all(c['actual_strictly_better'] for c in cells),
            all_four_C_within_original_tol_of_FP64_cast=all(r['actual_C_vs_oracle64_cast_violations']==0 for r in report['rows']),
            selected_packed_payload_reads=1, original_C_or_Torch_reference_reexecuted=False)
        check()
        report['source_inputs_unchanged'] = True
    except BaseException as error:
        report.update(status='STORED_DOT_DIAGNOSTIC_ERROR', returncode=1,
                      error=dict(type=type(error).__name__, message=str(error)))
    finally:
        payload = record = None
        gc.collect()
        report['CUDA_initialized'] = torch.cuda.is_initialized()
        report['RSS_exit'] = psutil.Process().memory_info().rss
        report['wall_seconds'] = time.perf_counter()-start
        write(out/'report.json', report)
    print('STORED_DOT_END', report['status'], report['returncode'], report['wall_seconds'], flush=True)
    return report['returncode']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare','actual'))
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
        return 0
    return actual()

if __name__ == '__main__':
    raise SystemExit(main())
