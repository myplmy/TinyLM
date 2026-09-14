#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anneal 수식 단일원천과 opt-in 계측의 CPU 회귀 검사."""
from __future__ import annotations

import json
import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEDULE_PATH = ROOT / "tinylm" / "train" / "anneal_schedule.py"
SPEC = importlib.util.spec_from_file_location("anneal_schedule_under_test", SCHEDULE_PATH)
assert SPEC and SPEC.loader
SCHEDULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCHEDULE)
auxiliary_decay_factor = SCHEDULE.auxiliary_decay_factor
lr_factor = SCHEDULE.lr_factor
quant_anneal_factor = SCHEDULE.quant_anneal_factor
resolve_quant_start = SCHEDULE.resolve_quant_start

try:
    import torch
    import torch.nn as nn
    from tinylm.model.ternary import TLinear
    from tinylm.train.anneal_audit import AnnealAudit
except ModuleNotFoundError as error:
    if error.name != "torch":
        raise
    torch = nn = TLinear = AnnealAudit = None


def legacy_lr(step, warm, steps, sched, decay_frac=0.2):
    if sched == "decay":
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / max(steps, 1)))
    if step < warm:
        return (step + 1) / warm
    progress = (step - warm) / max(steps - warm, 1)
    if sched == "stable":
        return 1.0
    if sched == "wsd":
        if progress < 1.0 - decay_frac:
            return 1.0
        cooldown = (progress - (1.0 - decay_frac)) / decay_frac
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * cooldown))
    return 0.1 + 0.45 * (1 + math.cos(math.pi * progress))


class ScheduleTests(unittest.TestCase):
    def test_lr_is_exactly_legacy_formula(self):
        for sched in ("cosine", "wsd", "stable", "decay"):
            for steps in (1, 17, 2289):
                warm = 0 if sched == "decay" else max(5, min(steps // 10, 100))
                for step in range(steps):
                    self.assertEqual(lr_factor(step, warm, steps, sched, 0.2),
                                     legacy_lr(step, warm, steps, sched, 0.2))

    def test_quant_boundaries_and_legacy_default_start(self):
        start = resolve_quant_start(100, 2289, None)
        self.assertEqual(start, 100 / 2289 + 0.05)
        self.assertEqual(quant_anneal_factor(0, 100, "wsd", "linear", 0.1, 0.8), 0.0)
        self.assertEqual(quant_anneal_factor(80, 100, "wsd", "linear", 0.1, 0.8), 1.0)
        self.assertEqual(quant_anneal_factor(9, 100, "wsd", "step", 0.1, 0.8), 0.0)
        self.assertEqual(quant_anneal_factor(10, 100, "wsd", "step", 0.1, 0.8), 1.0)
        self.assertEqual(quant_anneal_factor(0, 100, "decay", "linear", 0.1, 0.8), 1.0)

    def test_auxiliary_decay_boundaries(self):
        self.assertEqual(auxiliary_decay_factor(0, 100, 0.8), 1.0)
        self.assertEqual(auxiliary_decay_factor(80, 100, 0.8), 0.0)
        self.assertEqual(auxiliary_decay_factor(99, 100, 0.8), 0.0)


class AuditTests(unittest.TestCase):
    @unittest.skipIf(torch is None, "PyTorch가 없는 기본 검사 환경: 수식 fixture만 실행")
    def test_unique_modules_contract_and_two_samples(self):
        class AuditModel(nn.Module):
            def __init__(self):
                super().__init__()
                cfg = SimpleNamespace(micro_group=4, twn_thr_ratio=0.7, ste_clip=1.5,
                                      sparse34=False, center_weights=False,
                                      n_modes=1, mode_rank=0)
                self.first = TLinear(cfg, 4, 2)
                self.alias = self.first
                self.second = TLinear(cfg, 4, 2)

        model = AuditModel()
        for parameter in model.parameters():
            parameter.grad = torch.ones_like(parameter)
        # 실제 exclusive-create/append 계약을 사용자 환경의 임시 디렉터리에서 확인한다.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "anneal.jsonl"
            audit = AnnealAudit(path, model, every=1, max_modules=8,
                                contract={"anneal_end": 0.8})
            self.assertEqual([name for name, _ in audit.selected], ["first", "second"])
            audit.before(0, progress=0.0, anneal=0.0)
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.add_(0.01)
            audit.after(0, applied=True)
            audit.before(1, progress=0.5, anneal=0.5)
            audit.after(1, applied=False)

            contract = json.loads(path.with_suffix(".contract.json").read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(contract["schema"], "tinylm.anneal-audit.v1")
            self.assertEqual(contract["contract"]["anneal_end"], 0.8)
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[0]["applied"])
            self.assertFalse(rows[1]["applied"])
            self.assertIsNotNone(rows[0]["matrices"][0]["update_rms_including_wd"])
            self.assertIsNone(rows[1]["matrices"][0]["update_rms_including_wd"])
            self.assertIsNotNone(rows[1]["matrices"][0]["code_flip_rate_since_previous_sample"])

            with self.assertRaises(FileExistsError):
                AnnealAudit(path, model, every=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
