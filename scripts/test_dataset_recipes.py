#!/usr/bin/env python3
"""Network-free contracts for P097 dataset recipes."""
from __future__ import annotations

import gzip
import importlib
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PREP = importlib.import_module("tinylm.data.prepare")
from tinylm.data.prepare import (
    DATASETS,
    MADLAD_CLEAN_SHARDS,
    MADLAD_REVISION,
    TOKEN_BALANCED_DATASETS,
    _buffer_shuffle,
    _madlad_rows,
    _validate_token_balanced_cache,
    exact_token_quotas,
)


def main() -> int:
    expected = {"ko-en-control-v2", "ko-en-fw2", "ko-en-edu-v2", "ko-en-madlad"}
    assert TOKEN_BALANCED_DATASETS == expected
    assert expected <= set(DATASETS)
    assert exact_token_quotas(600_000_000, [0.5, 0.5]) == [300_000_000, 300_000_000]
    assert exact_token_quotas(11, [1, 1, 1]) == [3, 3, 5]
    for name in expected:
        specs = DATASETS[name]
        assert len(specs) == 2
        assert all(len(spec) == 5 and spec[3] == "text" for spec in specs)
        assert sum(spec[4] for spec in specs) == 1.0
    assert MADLAD_CLEAN_SHARDS == {"ko": 13, "en": 947}
    assert len(MADLAD_REVISION) == 40

    class ClosingIterator:
        def __init__(self):
            self.values = iter(range(20))
            self.closed = False

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.values)

        def close(self):
            self.closed = True

    source = ClosingIterator()
    shuffled = _buffer_shuffle(source, seed=0, buffer_size=4)
    first = [next(shuffled) for _ in range(3)]
    assert len(first) == 3
    shuffled.close()
    assert source.closed

    madlad_calls = []
    with tempfile.TemporaryDirectory() as temp_name:
        shard = Path(temp_name) / "fixture.jsonl.gz"
        with gzip.open(shard, "wt", encoding="utf-8") as stream:
            stream.write(json.dumps({"text": "검증 문장 " * 20}, ensure_ascii=False) + "\n")

        def fake_download(**kwargs):
            madlad_calls.append(kwargs)
            return str(shard)

        with mock.patch("huggingface_hub.hf_hub_download", side_effect=fake_download):
            rows = _madlad_rows("ko", "clean")
            assert next(rows)["text"].startswith("검증 문장")
            rows.close()
    assert len(madlad_calls) == 1
    assert madlad_calls[0]["repo_id"] == "allenai/MADLAD-400"
    assert madlad_calls[0]["revision"] == MADLAD_REVISION
    assert madlad_calls[0]["filename"].startswith("data/ko/ko_clean_")

    loaded = []
    def fake_load(spec):
        loaded.append(spec)
        return iter([{"text": "x" * 65}]), "text"
    with mock.patch.object(PREP, "_load_stream", side_effect=fake_load):
        mixed = PREP._stream("ko-en-madlad")
        text, source_index = next(mixed)
        mixed.close()
    assert text == "x" * 65 and source_index in {0, 1}
    assert len(loaded) == 2

    with tempfile.TemporaryDirectory() as temp_name:
        cache = Path(temp_name)
        (cache / "train.bin").write_bytes(b"\0" * 6)
        (cache / "val.bin").write_bytes(b"\0" * 2)
        meta = {
            "data": "ko-en-control-v2",
            "token_dtype": "uint16",
            "train": 3,
            "val": 1,
            "tokens": 4,
            "requested_tokens": 4,
            "mix_policy": "exact-token-quota-v1",
            "mix_tokens": [2, 2],
            "val_mix_tokens": [1, 0],
        }
        assert _validate_token_balanced_cache(cache, meta) is meta
        (cache / "val.bin").write_bytes(b"")
        try:
            _validate_token_balanced_cache(cache, meta)
        except RuntimeError as exc:
            assert "val.bin" in str(exc)
        else:
            raise AssertionError("truncated exact-token cache was accepted")

    print("[PASS] P097 recipes: exact quotas/cache, MADLAD direct shards, stream close")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
