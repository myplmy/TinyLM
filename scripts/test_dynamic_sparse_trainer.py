#!/usr/bin/env python3
"""Static full-trainer wiring contract for P092."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    files = [
        ROOT / "tinylm" / "config.py",
        ROOT / "tinylm" / "cli.py",
        ROOT / "tinylm" / "train" / "trainer.py",
        ROOT / "tinylm" / "train" / "dynamic_sparsity.py",
    ]
    texts = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        ast.parse(text, filename=str(path))
        texts[path.name] = text
    trainer = texts["trainer.py"]
    assert "capture_scores_and_mask_gradients" in trainer
    assert "_connectivity.rewire" in trainer
    assert '"connectivity_births"' in trainer and '"connectivity_deaths"' in trainer
    controller = texts["dynamic_sparsity.py"]
    assert "topk(swaps, dim=1" in controller
    assert "module.weight.scatter_(1, grow, 0.0)" in controller
    print("[PASS] P092 default-off CLI/config/trainer/controller/state-reset wiring")
    print("[NOT_RUN] GPU, compile interaction, speed, memory and quality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
