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
    p103_path = ROOT / "scripts/diag_p103a_cache_tail_readback.py"
    p103 = p103_path.read_text(encoding="utf-8")
    errors, warnings, _ = audit(p103_path, source_text=p103)
    if errors or warnings:
        raise RuntimeError("P103A real train.bin target and exact-difference gate were not recognized")
    mutations = (
        (p103.replace('CACHE / "train.bin"', 'CACHE / "synthetic.bin"')
         + '\n# load_model is a text-only decoy\n', 1,
         "P103A train.bin removal hid the real-target warning"),
        (p103.replace('y = torch.from_numpy(block[1:].copy()).long().unsqueeze(0).cuda()',
                      'y = torch.randint(0, 10, (1, SEQ), device="cuda")'), 1,
         "P103A random CE target hid the real-target warning"),
        (p103.replace("MAX_ABS = 5e-5", "MAX_ABS = -5e-5")
         + '\n# reference is a text-only decoy\n', 1,
         "P103A invalid exact bound hid the success-reference warning"),
        (p103.replace(") > MAX_ABS]", ") < MAX_ABS]"), 1,
         "P103A reversed exact gate hid the success-reference warning"),
    )
    for mutated, expected_warnings, message in mutations:
        if mutated == p103:
            raise RuntimeError("P103A regression mutation did not alter the source")
        _, warnings, _ = audit(p103_path, source_text=mutated)
        if len(warnings) != expected_warnings:
            raise RuntimeError(message)
    fake = ('"""CACHE / "train.bin" and MAX_ABS = 5e-5 are only text."""\n'
            'loss = F.cross_entropy(logits, labels)\n')
    errors, warnings, _ = audit(p103_path, source_text=fake)
    if errors or len(warnings) != 2:
        raise RuntimeError("P103A filename/constant text bypassed the AST contract")
    print("[PASS] difference-only and P103A real-target/exact-gate contracts; damaged paths warn")


if __name__ == "__main__":
    main()
