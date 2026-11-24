"""Decode frozen CPU-double edit factors without refitting or loading a model.

Full checkpoint absence is not artifact absence. Admission requires exact delta,
base-weight and realized-after hashes; no tolerance, regeneration or fallback.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def read_pinned(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size >= 20_000_000:
        raise ValueError('small regular frozen artifact required')
    if digest(path) != expected:
        raise ValueError('frozen artifact SHA differs: ' + str(path))
    from scripts.p106b_official_lm_adapter import _unique_object
    return json.loads(path.read_bytes(), object_pairs_hook=_unique_object)


def decode(packet):
    import torch
    from scripts.p108_weight_space import tensor_sha
    if (type(packet.get('layer')) is not int or packet['layer'] < 0
            or type(packet.get('intended_factor_columns')) is not int
            or packet['intended_factor_columns'] < 1):
        raise ValueError('explicit layer and positive factor width required')
    left = torch.tensor(packet['left'], dtype=torch.float64, device='cpu')
    right = torch.tensor(packet['right'], dtype=torch.float64, device='cpu')
    if (left.ndim != 2 or right.ndim != 2
            or left.shape[1] != right.shape[1]
            or left.shape[1] != packet['intended_factor_columns']
            or min(left.shape[0], right.shape[0]) < 1
            or not bool(torch.isfinite(left).all()) or not bool(torch.isfinite(right).all())):
        raise ValueError('finite matching double factors required')
    # Match the original CPU-double product followed by ONE FP32 cast.
    delta = (left @ right.T).float()
    if not bool(torch.isfinite(delta).all()) or tensor_sha(delta) != packet['delta_sha256']:
        raise ValueError('exact frozen delta reconstruction failed')
    return delta


def validate_base_and_after(packet, delta, base, expected_after):
    import torch
    from scripts.p108_weight_space import tensor_sha
    if (base.dtype != torch.float32 or delta.dtype != torch.float32
            or base.shape != delta.shape or not bool(torch.isfinite(base).all())
            or tensor_sha(base) != packet['base_weight_sha256']):
        raise ValueError('original FP32 base weight differs')
    after = base.detach().cpu() + delta.detach().cpu()
    if tensor_sha(after) != expected_after:
        raise ValueError('realized edited weight SHA differs')
    return dict(layer=packet['layer'], delta_sha256=tensor_sha(delta),
                base_weight_sha256=tensor_sha(base), after_weight_sha256=tensor_sha(after),
                exact=True, refit=False)
