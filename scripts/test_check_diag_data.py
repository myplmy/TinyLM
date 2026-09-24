#!/usr/bin/env python3
"""Difference-only diagnostic exemptions must not hide random-target CE failures."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_diag_data import audit


def main():
    name = Path("diag_p102a_model_loss_first.py")
    diff_case = "loss = F.cross_entropy(logits, labels)"
    errors, warnings, info = audit(name, source_text=diff_case)
    if errors or warnings or not info:
        raise RuntimeError("difference-only CE warning exemption differs")
    bad = "labels = torch.randint(0, 10, (3,))\nloss = F.cross_entropy(logits, labels)"
    errors, warnings, _ = audit(name, source_text=bad)
    if errors or warnings:
        raise RuntimeError("difference-only random target was misclassified as quality")
    errors, _, _ = audit(Path("diag_absolute_quality.py"), source_text=bad)
    if not errors:
        raise RuntimeError("absolute-quality random target escaped nested CE check")
    nested = "labels = torch.randint(0, 10, (3,))\nloss = F.cross_entropy(logits.reshape(-1, 10), labels.reshape(-1))"
    errors, _, _ = audit(Path("diag_absolute_quality.py"), source_text=nested)
    if not errors:
        raise RuntimeError("nested cross_entropy target escaped AST check")
    errors, warnings, _ = audit(Path("diag_absolute_quality.py"), source_text=diff_case)
    if errors or len(warnings) != 2:
        raise RuntimeError("unlisted absolute-quality warning was suppressed")
    print("[PASS] difference-only random targets allowed; absolute-quality CE still guarded")


if __name__ == "__main__":
    main()
