#!/usr/bin/env python3
"""Static wiring contract for P098; model execution is deliberately absent."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    paths = [
        ROOT / "tinylm" / "config.py",
        ROOT / "tinylm" / "cli.py",
        ROOT / "tinylm" / "train" / "trainer.py",
        ROOT / "tinylm" / "model" / "transformer.py",
    ]
    texts = {path: path.read_text(encoding="utf-8") for path in paths}
    for path, text in texts.items():
        ast.parse(text, filename=str(path))
        assert "repeat_embed_reinject" in text, path
    transformer = texts[paths[-1]]
    assert "_mid_visits % cfg.n_middle == 0" in transformer
    assert "x = x + embed_state" in transformer
    trainer = texts[paths[2]]
    assert "repeat-mode=uniform" in trainer
    assert "--train-repeat > 1" in trainer
    print("[PASS] P098 default-off CLI/config/trainer/JSON and uniform-cycle reinjection wiring")
    print("[NOT_RUN] model forward, GPU training and quality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
