"""실제 validation text probe의 캐시 선택·span 배치 순수 함수."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def parse_tokens(value):
    if value is None:
        return None
    text = str(value).strip()
    scale = 1
    if text[-1:].lower() == "m":
        scale, text = 1_000_000, text[:-1]
    elif text[-1:].lower() == "b":
        scale, text = 1_000_000_000, text[:-1]
    return int(float(text) * scale)


def select_cache(cache_root, data, pool_tokens=None, explicit=None):
    """기존 meta.json+val.bin 캐시 하나만 선택한다. 생성·다운로드는 하지 않는다."""
    if explicit:
        candidates = [Path(explicit)]
    else:
        root = Path(cache_root)
        want = parse_tokens(pool_tokens)
        candidates = []
        for directory in sorted(root.glob(f"{data}_*")):
            meta_path = directory / "meta.json"
            if not meta_path.is_file() or not (directory / "val.bin").is_file():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            nominal = parse_tokens(meta.get("requested_tokens", meta.get("tokens")))
            name_tokens = None
            suffix = directory.name[len(data) + 1:].split("_", 1)[0]
            try:
                name_tokens = parse_tokens(suffix)
            except (ValueError, IndexError):
                pass
            if want is None or want in {nominal, name_tokens}:
                candidates.append(directory)
    valid = [p.resolve() for p in candidates
             if (p / "meta.json").is_file() and (p / "val.bin").is_file()]
    if len(valid) != 1:
        names = ", ".join(str(p) for p in valid) or "none"
        raise ValueError(
            f"validation cache must resolve to exactly one directory (found {len(valid)}: {names}). "
            "Use --cache-dir or --pool-tokens.")
    return valid[0]


def span_offsets(length, context_tokens, target_tokens, samples, seed=99):
    width = int(context_tokens) + int(target_tokens)
    if min(width, samples) < 1 or length < width:
        raise ValueError("validation span size/count is invalid")
    starts = np.arange(0, length - width + 1, dtype=np.int64)
    rng = np.random.default_rng(seed)
    picked = rng.choice(starts, size=min(int(samples), len(starts)), replace=False)
    return sorted(int(x) for x in picked)


def target_token_start(offsets, character_boundary):
    """재토큰화 결과에서 target의 첫 완전한 토큰 위치를 찾는다.

    context/target 경계를 가로지르는 토큰은 부분 문자열 NLL로 분해할 수 없으므로 한 토큰을
    버리고, 시작 offset이 경계 이상인 첫 실제 토큰부터 채점한다.
    """
    boundary = int(character_boundary)
    crossed = 0
    for index, pair in enumerate(offsets):
        start, end = map(int, pair)
        if start < boundary < end:
            crossed += 1
        if end > start and start >= boundary:
            if index < 1:
                raise ValueError("target must have at least one conditioning token")
            return index, crossed
    raise ValueError("retokenized target has no scorable token")
