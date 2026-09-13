#!/usr/bin/env python3
"""Dynamic regression for CLA-owned K/V during role-mapped parent init.

This is intended for the user-run smoke suite. It loads tiny CPU models and a
temporary checkpoint; it does not train or touch repository checkpoints.
"""
from __future__ import annotations

import dataclasses
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402

from tinylm.config import build_config  # noqa: E402
from tinylm.model import TiedMLPTransformer  # noqa: E402
from tinylm.train.init_utils import _depth_map, init_from_dense  # noqa: E402


def main() -> int:
    teacher_cfg = dataclasses.replace(
        build_config("tiny", "dense", 128, False),
        n_prelude=2,
        n_middle=6,
        n_coda=2,
        cla_group=2,
    )
    student_cfg = dataclasses.replace(teacher_cfg, n_middle=4)
    teacher = TiedMLPTransformer(teacher_cfg)
    student = TiedMLPTransformer(student_cfg)

    with torch.no_grad():
        for layer_index, layer in enumerate(teacher.layers):
            if layer.attn_mod.owns_kv:
                layer.attn_mod.k_proj.weight.fill_(100.0 + layer_index)
                layer.attn_mod.v_proj.weight.fill_(200.0 + layer_index)

    lmap, _ = _depth_map(student_cfg, teacher_cfg)
    exercised_non_owner = False
    with tempfile.TemporaryDirectory(prefix="tinylm-cla-init-") as tmp:
        checkpoint = Path(tmp) / "teacher.pt"
        torch.save({"cfg": dataclasses.asdict(teacher_cfg), "model": teacher.state_dict()}, checkpoint)
        init_from_dense(student, checkpoint, "cpu", depth_init="role")

    for student_index, mapped_teacher in enumerate(lmap):
        if student.owner[student_index] != student_index:
            continue
        teacher_owner = teacher.owner[mapped_teacher]
        if teacher_owner != mapped_teacher:
            exercised_non_owner = True
        student_attn = student.layers[student_index].attn_mod
        teacher_attn = teacher.layers[teacher_owner].attn_mod
        torch.testing.assert_close(student_attn.k_proj.weight, teacher_attn.k_proj.weight)
        torch.testing.assert_close(student_attn.v_proj.weight, teacher_attn.v_proj.weight)

    if not exercised_non_owner:
        raise AssertionError("fixture did not map a student K/V owner to a teacher reuse layer")
    print("PASS: role-mapped CLA parent init resolves K/V through teacher.owner")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
