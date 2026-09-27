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
    m5 = ("val = np.memmap(CACHE / 'val.bin', mode='r')\n"
          "loss = F.cross_entropy(logits, raw[:, 1:])\n"
          "result = {'scientific_quality': 'SAME_CHECKPOINT_CROSS_OS_FUNCTION_ONLY'}\n")
    errors, warnings, _ = audit(Path("diag_m5_real_bridge.py"), source_text=m5)
    if errors or warnings:
        raise RuntimeError("real-val same-checkpoint M5 was flagged as synthetic quality")
    errors, warnings, _ = audit(Path("diag_m5_real_bridge.py"),
                                source_text=m5.replace("np.memmap(CACHE / 'val.bin', mode='r')", "None"))
    if errors or len(warnings) != 2:
        raise RuntimeError("M5 warning vanished after the real-val read was removed")
    m5_bad = m5 + "labels = torch.randint(0, 10, (3,))\nloss = F.cross_entropy(logits, labels)\n"
    errors, _, _ = audit(Path("diag_m5_real_bridge.py"), source_text=m5_bad)
    if not errors:
        raise RuntimeError("M5 paired marker hid an actual random-target CE failure")
    p076 = ("loader = Loader('val', 2, 512, 'cuda', CACHE)\n"
            "ce = F.cross_entropy(logits, labels)\n"
            "if any(not 5.0 <= row[3] <= 9.4 for row in values):\n"
            "    print('[GATE NEGATIVE] init band')\n")
    errors, warnings, _ = audit(Path("diag_p076_attn_only.py"), source_text=p076)
    if errors or warnings:
        raise RuntimeError("P076 explicit two-sided CE band was not recognized")
    errors, warnings, _ = audit(Path("diag_p076_attn_only.py"),
                                source_text=p076.replace("not 5.0 <= row[3] <= 9.4", "row[3] > 9.4"))
    if errors or len(warnings) != 1:
        raise RuntimeError("P076 success-reference warning vanished without a two-sided band")
    print("[PASS] difference-only random targets allowed; absolute-quality CE still guarded")


if __name__ == "__main__":
    main()
