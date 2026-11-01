"""memmap 무작위 크롭 로더. 시드가 같으면 두 런이 정확히 같은 배치를 본다."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch


class Loader:
    def __init__(self, split, bs, seq, device, cache_dir, seed=1234):
        # ★★P067(2026-08-22) — 토큰 dtype 은 **meta.json 이 정본**이다.
        #   외부 토크나이저(Qwen3 151,936 / Gemma3 262,144)는 uint16 을 넘어 uint32 로 저장된다.
        #   🚫여기서 uint16 을 하드코딩하면 **바이트를 반씩 잘라 읽고** 손실은 정상처럼 보인다.
        import json as _json
        _mp = Path(cache_dir) / "meta.json"
        _td = np.dtype("uint16")
        if _mp.exists():
            _td = np.dtype(_json.loads(_mp.read_text()).get("token_dtype", "uint16"))
        self.token_dtype = _td
        self.d = np.memmap(Path(cache_dir) / f"{split}.bin", dtype=_td, mode="r")
        self.bs, self.seq, self.device = bs, seq, device
        self.rng = np.random.default_rng(seed)

    def __call__(self):
        ix = self.rng.integers(0, len(self.d) - self.seq - 1, self.bs)
        # ③ 파이썬 루프 대신 NumPy advanced indexing 으로 한 번에 슬라이싱
        x = self.d[ix[:, None] + np.arange(self.seq + 1)].astype(np.int64)
        t = torch.from_numpy(x)
        if self.device == "cuda":
            t = t.pin_memory().to("cuda", non_blocking=True)
        return t[:, :-1], t[:, 1:]
