#!/usr/bin/env python3
"""Muon RMS4·KD off 기본값과 WD 라우팅의 정적 계약 시험."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.training_defaults import (
    DEFAULT_KD,
    DEFAULT_MATRIX_WEIGHT_DECAY,
    DEFAULT_MUON_LR_MULT,
    DEFAULT_MUON_SCALE,
    DEFAULT_OPTIMIZER,
    effective_matrix_weight_decay,
)
from tinylm.train.trainer import train


def main() -> int:
    assert DEFAULT_OPTIMIZER == "muon"
    assert DEFAULT_MUON_LR_MULT == 4.0
    assert DEFAULT_MUON_SCALE == "rms"
    assert DEFAULT_MATRIX_WEIGHT_DECAY is None
    assert DEFAULT_KD is False

    sig = inspect.signature(train)
    assert sig.parameters["optimizer"].default == DEFAULT_OPTIMIZER
    assert sig.parameters["muon_lr_mult"].default == DEFAULT_MUON_LR_MULT
    assert sig.parameters["muon_scale"].default == DEFAULT_MUON_SCALE
    assert sig.parameters["matrix_weight_decay"].default is None
    assert sig.parameters["kd"].default is False

    assert effective_matrix_weight_decay("muon", None) == 0.0
    assert effective_matrix_weight_decay("adamw", None) == 0.1
    assert effective_matrix_weight_decay("muon", 0.025) == 0.025

    cli = (ROOT / "tinylm" / "cli.py").read_text(encoding="utf-8")
    for anchor in (
        'default=DEFAULT_OPTIMIZER',
        'default=DEFAULT_MUON_LR_MULT',
        'default=DEFAULT_MUON_SCALE',
        'default=DEFAULT_MATRIX_WEIGHT_DECAY',
        'p.add_argument("--kd", action="store_true"',
    ):
        assert anchor in cli, anchor
    print("[PASS] training defaults: Muon RMS4, matrix WD0 policy, KD off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
