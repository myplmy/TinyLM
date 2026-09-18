#!/usr/bin/env python3
"""P091 R1 — AdamW/Muon realized update와 WD 분리 계약(CPU fixture)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from tinylm.train.muon import Muon
from tinylm.train.optimizer_audit import OptimizerAudit


class Fixture(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.adam = torch.nn.Linear(4, 4, bias=False)
        self.muon = torch.nn.Linear(4, 4, bias=False)


def main() -> int:
    torch.manual_seed(7)
    model = Fixture()
    opt_adam = torch.optim.AdamW([model.adam.weight], lr=0.01, weight_decay=0.1)
    opt_muon = Muon([model.muon.weight], lr=0.02, weight_decay=0.05, scale_mode="rms")
    for p in model.parameters():
        p.grad = torch.full_like(p, 0.125)

    with tempfile.TemporaryDirectory(prefix="p091-audit-") as tmp:
        out = Path(tmp) / "audit.jsonl"
        audit = OptimizerAudit(out, model, [("adamw", opt_adam), ("muon", opt_muon)],
                               every=1, max_matrices=8, contract={"fixture": True})
        audit.before(0)
        opt_adam.step()
        opt_muon.step()
        audit.after(0, applied=True)

        contract = json.loads(out.with_suffix(".contract.json").read_text(encoding="utf-8"))
        assert contract["schema"] == "tinylm.optimizer-audit.v2"
        row = json.loads(out.read_text(encoding="utf-8").strip())
        assert row["applied"] is True
        assert {m["optimizer"] for m in row["matrices"]} == {"adamw", "muon"}
        for item in row["matrices"]:
            assert item["update_rms_including_wd"] > 0
            assert item["weight_decay_update_rms"] > 0
            assert item["optimizer_update_rms_excluding_wd"] > 0
            assert item["optimizer_update_weight_ratio"] > 0
            want_wd = 0.1 if item["optimizer"] == "adamw" else 0.05
            assert abs(item["weight_decay"] - want_wd) < 1e-12

    print("[PASS] P091 R1 optimizer audit: total, WD, optimizer-only update separated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
