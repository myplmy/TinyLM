#!/usr/bin/env python3
"""CPU synthetic optimizer trace; never loads TinyLM, assets, or checkpoints.

Observe the existing Muon implementation, not a second optimizer. A synthetic
rounding example is NOT evidence that it caused the stored TinyLM discrepancy.
Inputs to trace_pair are already-clipped gradients of one fresh matrix. This
does not reproduce the full model's clipping or accumulated training history.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tinylm  # project paths before optional external libraries
import torch
from tinylm.train import muon
from scripts.diag_p101a_padding_gpu import literal_tolerances, tensor_table, safe_path, write_new


def trace_pair(reference, candidate, *, lr=2e-4):
    """Trace two CPU matrices without changing inputs, production code, or RNG."""
    if (reference.device.type != 'cpu' or candidate.device.type != 'cpu'
            or reference.dtype != torch.float32 or candidate.dtype != torch.float32
            or reference.ndim != 2 or reference.shape != candidate.shape
            or not reference.numel() or not torch.isfinite(reference).all()
            or not torch.isfinite(candidate).all() or not 0 < lr < 1):
        raise ValueError('finite nonempty matching CPU FP32 matrices and 0<lr<1 required')
    captured = []
    original = muon._newton_schulz
    weights, buffers, sgd = [], [], []
    for gradient in (reference, candidate):
        row = {}
        def observe(value, *args, **kwargs):
            row['ns_input'] = value.detach().clone()
            row['bf16_input'] = value.detach().bfloat16().float()
            answer = original(value, *args, **kwargs)
            row['ns_output'] = answer.detach().clone()
            return answer
        parameter = torch.nn.Parameter(torch.zeros_like(gradient))
        optimizer = muon.Muon([parameter], lr=lr, scale_mode='rms')
        parameter.grad = gradient.detach().clone()
        with patch.object(muon, '_newton_schulz', side_effect=observe):
            optimizer.step()
        captured.append(row)
        weights.append(parameter.detach().clone())
        buffers.append(optimizer.state[parameter]['buf'].detach().clone())
        control = torch.nn.Parameter(torch.zeros_like(gradient))
        control.grad = gradient.detach().clone()
        torch.optim.SGD([control], lr=lr).step()
        sgd.append(control.detach().clone())
    tol = literal_tolerances()['gradients_and_update']
    def compare(a, b):
        return tensor_table(torch, {'matrix': a}, {'matrix': b}, tol)
    return dict(
        input_shape=list(reference.shape), lr=lr, tolerance=tol,
        input_gradient=compare(reference, candidate),
        ns_input=compare(captured[0]['ns_input'], captured[1]['ns_input']),
        bf16_input=compare(captured[0]['bf16_input'], captured[1]['bf16_input']),
        ns_output=compare(captured[0]['ns_output'], captured[1]['ns_output']),
        momentum_buffer=compare(*buffers), updated_weight=compare(*weights),
        linear_sgd_control=compare(*sgd),
        scope='SINGLE_FRESH_MATRIX_ALREADY_CLIPPED_CPU_SYNTHETIC_ONLY',
        quality_claim=False, tinylm_cause_proven=False,
    )


def synthetic_report():
    # The input is chosen before observing any TinyLM result. Nesterov's
    # fresh-buffer factor puts one element either side of a BF16 midpoint.
    g = torch.tensor([[1.0039060 / 1.95, .2], [.1, -.6]], dtype=torch.float32)
    shifted = g.clone()
    shifted[0, 0] = 1.0039065 / 1.95
    return dict(schema='P102A_MUON_CPU_SENSITIVITY_V1', model_calls=0,
                cuda_calls=0, checkpoint_writes=0, quality_claim=False,
                actual_tinylm_cause_proven=False,
                cases={'identical': trace_pair(g, g.clone()),
                       'bf16_boundary': trace_pair(g, shifted)},
                limitation='Rounding sensitivity is possible; actual full-gradient replay NOT_RUN.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-cpu', action='store_true')
    parser.add_argument('--output', help='new JSON under handoff/audit only')
    args = parser.parse_args(argv)
    if not args.synthetic_cpu:
        parser.error('explicit --synthetic-cpu required; there is no model execution route')
    if args.output and Path(args.output).parts[:2] != ('handoff', 'audit'):
        parser.error('only a new explicit handoff/audit output is allowed')
    torch.set_num_threads(1)
    report = synthetic_report()
    if args.output:
        write_new(safe_path(args.output), report)
    print(json.dumps(dict(schema=report['schema'], model_calls=0, cuda_calls=0,
        actual_tinylm_cause_proven=False, output=args.output,
        cases={name: {key: value['close'] for key, value in case.items()
                      if isinstance(value, dict) and 'close' in value}
               for name, case in report['cases'].items()}),
        ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
