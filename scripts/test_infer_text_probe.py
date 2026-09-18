#!/usr/bin/env python3
"""실제 텍스트 probe의 cache 선택/offset 계약(모델·GPU 없음)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.infer.text_probe import select_cache, span_offsets, target_token_start


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="text-probe-") as tmp:
        root = Path(tmp)
        cache = root / "en_100000000"
        cache.mkdir()
        (cache / "meta.json").write_text(json.dumps({"tokens": 100_000_000}), encoding="utf-8")
        (cache / "val.bin").write_bytes(b"\0" * 32)
        assert select_cache(root, "en", "100M") == cache.resolve()
        assert select_cache(root, "en", explicit=cache) == cache.resolve()
        other = root / "en_200000000"
        other.mkdir()
        (other / "meta.json").write_text(json.dumps({"tokens": 200_000_000}), encoding="utf-8")
        (other / "val.bin").write_bytes(b"\0" * 32)
        try:
            select_cache(root, "en")
        except ValueError as exc:
            assert "exactly one" in str(exc)
        else:
            raise AssertionError("ambiguous cache was silently selected")
    offsets = span_offsets(1000, 96, 48, 3, 99)
    assert len(offsets) == 3 and offsets == sorted(offsets)
    assert all(0 <= x <= 1000 - 144 for x in offsets)
    start, crossed = target_token_start([(0, 2), (2, 5), (5, 7)], 4)
    assert (start, crossed) == (2, 1)
    try:
        target_token_start([(0, 2)], 2)
    except ValueError as exc:
        assert "no scorable token" in str(exc)
    else:
        raise AssertionError("empty retokenized target was accepted")
    print("[PASS] infer text probe: cache identity, deterministic spans, tokenizer boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
