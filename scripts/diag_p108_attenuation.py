#!/usr/bin/env python3
"""Calibration-only linear-signal decomposition; no model/CUDA loading.

This diagnoses a completed negative P108 edit. It does not select new settings
on test data and it does not equate a first-order margin with correctness.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import torch

from scripts import diag_p108_local_linear as previous
from scripts import interactive_research_infer as manual
from scripts import p108_local_linear as local

ROOT = Path(__file__).resolve().parents[1]
TAG = 'p108_attenuation_v1_20261104'
BASE = ROOT/'test_result/evidence'/TAG/'new595-broad-q'
SOURCES = ('scripts/diag_p108_attenuation.py', 'scripts/test_p108_attenuation.py')


def partition_targets(rows, total):
    """Use captured row lengths, never infer boundaries from token values."""
    body, eot, offset, seen = [], [], 0, set()
    for row in rows:
        name, n = row['id'], row['targets']
        if (not name.startswith('calib_') or name in seen or type(n) is not int
                or n < 2 or row['eot_targets'] != 1):
            raise ValueError('unique calibration-only rows with one EOT required')
        seen.add(name)
        body.extend(range(offset, offset+n-1)); eot.append(offset+n-1)
        offset += n
    if offset != total:
        raise ValueError('captured row lengths do not cover all target positions')
    return {'all':list(range(total)), 'body':body, 'eot':eot}


def validate_packet(packet):
    k, v, g, m = (packet[name] for name in ('keys','values','gradients','margins'))
    if (k.ndim != 2 or v.ndim != 2 or g.shape != v.shape or m.ndim != 1
            or k.shape[0] != v.shape[0] or m.numel() != k.shape[0]
            or not k.shape[0] or any(t.device.type != 'cpu' for t in (k,v,g,m))
            or any(not bool(torch.isfinite(t).all()) for t in (k,v,g,m))):
        raise ValueError('finite paired CPU calibration tensors required')
    left, right = packet['factors']['left'], packet['factors']['right']
    if (left.ndim != 2 or right.ndim != 2 or left.shape[1] != right.shape[0]
            or left.shape[0] != v.shape[1] or right.shape[1] != k.shape[1]
            or any(t.device.type != 'cpu' or not bool(torch.isfinite(t).all()) for t in (left,right))):
        raise ValueError('finite stored factor dimensions differ')
    return k.double(), v.double(), g.double(), m.double(), left.double()@right.double()


def reference_ridge(k, v, ridge):
    """Independent FP64 normal-equation readback, not a replacement solver."""
    norms = k.norm(dim=1)
    if bool((norms <= 1e-12).any()):
        raise ValueError('zero calibration key')
    kn, vn = k/norms[:,None], v/norms[:,None]
    a = torch.linalg.solve(kn@kn.T+ridge*torch.eye(len(k),dtype=k.dtype), vn)
    full = a.T@kn
    residual = kn@full.T-vn
    normal = residual.T@kn+ridge*full
    return full, float(residual.square().sum()), float(normal.abs().max())


def statistics(margin, gain, groups):
    if margin.shape != gain.shape or margin.ndim != 1 or not bool(torch.isfinite(gain).all()):
        raise ValueError('finite paired margin/gain required')
    out = {}
    for name, positions in groups.items():
        if not positions or min(positions) < 0 or max(positions) >= margin.numel():
            raise ValueError('nonempty in-range target group required')
        m, d = margin[positions], gain[positions]
        after = m+d
        out[name] = dict(targets=len(positions), original_positive=int((m>0).sum()),
            predicted_positive=int((after>0).sum()),
            predicted_new_positive=int(((m<=0)&(after>0)).sum()),
            predicted_regressions=int(((m>0)&(after<=0)).sum()),
            predicted_at_target_margin=int((after>=1-1e-6).sum()),
            mean_first_order_gain=float(d.mean()),
            gain_quantiles=dict(zip(('min','p10','p50','p90','p99','max'),
                torch.quantile(d,torch.tensor([0.,.1,.5,.9,.99,1.],dtype=d.dtype)).tolist())),
            scope='LINEAR_FIXED_ORIGINAL_COMPETITOR_NOT_ACTUAL_ACCURACY')
    return out


def main():
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '' or torch.cuda.is_initialized():
        raise RuntimeError('CPU-only execution requires CUDA_VISIBLE_DEVICES empty')
    if datetime.now(timezone.utc) >= previous.common.DEADLINE:
        raise RuntimeError('research window ended')
    if BASE.exists():
        raise FileExistsError('fresh calibration audit namespace required')
    torch.set_num_threads(2)
    start = time.monotonic()
    old = previous.verify()
    packet, capture = previous.load_packet(torch)
    search_path = previous.BASE/'search/report.json'
    search = previous.common.read_json(search_path)
    if search['profile_sha256'] != manual.file_sha(previous.BASE/'profile.json'):
        raise ValueError('previous selected search profile differs')
    paths = [previous.BASE/'profile.json', previous.BASE/'capture/report.json', search_path,
             previous.RUNTIME/'features_factors.pt', *(ROOT/p for p in SOURCES)]
    pins = {p.relative_to(ROOT).as_posix():manual.file_sha(p) for p in paths}
    if TAG+'/new595-broad-q' not in (ROOT/'docs/EXPERIMENT_BASELINES.md').read_text(encoding='utf-8'):
        raise ValueError('new diagnostic tag must be reserved before execution')
    k,v,g,m,low = validate_packet(packet)
    groups = partition_targets(capture['rows'],len(k))
    ideal, target = local.margin_targets(g,m,target_margin=old['target_margin'],max_gap=old['max_margin_gap'])
    if not torch.allclose(v,ideal,rtol=1e-6,atol=1e-6):
        raise ValueError('stored target is not the declared original gradient objective')
    full, residual, normal = reference_ridge(k,v,old['ridge'])
    if abs(residual-capture['fit']['untruncated_residual_sq']) > 1e-6 or normal > 1e-8:
        raise ValueError('independent full-ridge reference differs')
    scales = {r['name']:r['budget']['scale'] for r in search['variants'] if 'budget' in r}
    if scales.keys() != {'cap_0.0025','cap_0.01','cap_0.04'} or search['selected']['name'] != 'cap_0.0025':
        raise ValueError('historically selected scale changed')
    projections = {'original':torch.zeros_like(v), 'input_specific_oracle':v,
                   'full_ridge_unbounded':k@full.T, 'rank16_unbounded':k@low.T}
    projections.update({name:projections['rank16_unbounded']*scale for name,scale in scales.items()})
    variants = {name:statistics(m,(g*value).sum(1),groups) for name,value in projections.items()}
    profile = dict(schema='P108_CALIBRATION_ATTENUATION_PROFILE_V1',authority_directive=107,
        deadline=previous.common.DEADLINE.isoformat(),input_pins=pins,
        source_profile_sha256=manual.file_sha(previous.BASE/'profile.json'),
        calibration_rows=len(capture['rows']),calibration_targets=len(k),
        split='CALIBRATION_ONLY_NO_DEV_TEST_READ',relative_scales=scales,
        fixed_original_selected='cap_0.0025',new_selection=False,
        first_order_only=True,model_loads=0,optimizer_updates=0,checkpoint_writes=0)
    previous.common.write_json(BASE/'profile.json',profile)
    positions = []
    offset = 0
    for row in capture['rows']:
        for j in range(row['targets']):
            i = offset+j
            positions.append(dict(id=row['id'],target_offset=j,is_eot=j==row['targets']-1,
                original_margin=float(m[i]),
                first_order_gain={name:float((g[i]*value[i]).sum()) for name,value in projections.items()}))
        offset += row['targets']
    for name,sha in pins.items():
        if manual.file_sha(ROOT/name) != sha:
            raise ValueError('frozen input changed during CPU diagnosis: '+name)
    if torch.cuda.is_initialized():
        raise RuntimeError('CPU diagnosis unexpectedly initialized CUDA')
    report = dict(schema='P108_CALIBRATION_ATTENUATION_V1',status='TECHNICAL_COMPLETE',actual_exit=0,
        profile_sha256=manual.file_sha(BASE/'profile.json'),source_pins=pins,
        full_ridge_normal_max_abs=normal,full_ridge_residual_sq=residual,
        rank16_factor_fp64_reconstructed_norm=float(low.norm()),target_report=target,
        target_counts={name:len(indices) for name,indices in groups.items()},
        relative_scales=scales,variants=variants,positions=positions,
        actual_cuda_initialized=False,model_loads=0,new_gold_positions=0,
        optimizer_updates=0,checkpoint_writes=0,old_inputs_unchanged=True,
        old_test_verdict='GATE_NEGATIVE_UNCHANGED',
        cpu_fp64_reconstruction_is_gpu_fp32_byte_identity=False,
        quality_claim=False,wall_seconds=time.monotonic()-start)
    previous.common.write_json(BASE/'cpu/report.json',report)
    print(json.dumps({k:report[k] for k in ('status','actual_exit','target_counts','relative_scales','wall_seconds')},sort_keys=True))
    for name,groups in variants.items():
        print(name,json.dumps({group:{k:d[k] for k in ('targets','original_positive','predicted_positive','predicted_new_positive','predicted_regressions','mean_first_order_gain')} for group,d in groups.items()},sort_keys=True))


if __name__ == '__main__':
    main()
