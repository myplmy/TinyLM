"""토큰화 + 크기별 재사용 캐시.

캐시 규칙
  - 실데이터: data_cache/{name}_{tokens}/ 에 train.bin·val.bin·meta.json 저장.
    요청 토큰 이상을 담은 같은 이름의 캐시가 이미 있으면 재생성 없이 재사용한다
    (가장 작은 상위 호환 캐시 선택). 그래서 architecture_v6 를 만들어도 재토큰화 불필요.
  - 토크나이저: data_cache/tok-{name}-{vocab}.json 에 이름당 하나만 두고 크기 간 공유.
  - 합성(synthetic): 판정 불가 데이터라 항상 재생성(캐시 안 함).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from .. import paths   # HF_HOME 등 설정을 위해 먼저 import
from ..config import VOCAB

DATA_CACHE = paths.DATA_CACHE

DATASETS = {
    # 이름: [(hf_id, config, split, text_key, 혼합 비율), ...]
    "ko-en": [("wikimedia/wikipedia", "20231101.ko", "train", "text", 0.5),
              ("HuggingFaceFW/fineweb-edu", "sample-10BT", "train", "text", 0.5)],
    "ko":    [("wikimedia/wikipedia", "20231101.ko", "train", "text", 1.0)],
    "en":    [("Salesforce/wikitext", "wikitext-103-raw-v1", "train", "text", 1.0)],
}


def tokenizer_path(name, vocab_size=VOCAB):
    return DATA_CACHE / f"tok-{name}-{vocab_size}.json"


def _stream(name):
    from datasets import load_dataset
    specs = DATASETS[name]
    iters, ratios = [], []
    for hf_id, cfg, split, key, r in specs:
        ds = load_dataset(hf_id, cfg, split=split, streaming=True)
        iters.append((iter(ds), key)); ratios.append(r)
    rng = np.random.default_rng(0)
    p = np.array(ratios) / sum(ratios)
    while True:
        i = rng.choice(len(iters), p=p)
        it, key = iters[i]
        try:
            t = next(it)[key]
        except StopIteration:
            continue
        if t and len(t) > 64:
            yield t


def build_tokenizer(name, vocab_size=VOCAB):
    from tokenizers import ByteLevelBPETokenizer
    path = tokenizer_path(name, vocab_size)
    if path.exists():
        from tokenizers import Tokenizer
        print(f"[tok] 캐시 사용 {path}")
        return Tokenizer.from_file(str(path))
    print(f"[tok] {vocab_size} BPE 학습 중 (표본 20만 문서)...")
    tok = ByteLevelBPETokenizer()
    src = _stream(name)
    def sample():
        for i, t in enumerate(src):
            if i >= 200_000:
                break
            yield t
    tok.train_from_iterator(sample(), vocab_size=vocab_size, min_frequency=2,
                            special_tokens=["<pad>", "<bos>", "<eos>"])
    DATA_CACHE.mkdir(parents=True, exist_ok=True)
    tok.save(str(path))
    print(f"[tok] 저장 {path}")
    return tok


def _find_reusable(name, n_tokens):
    """같은 name, tokens>=n_tokens 캐시 중 가장 작은 것(상위 호환)을 고른다."""
    best = None
    for d in sorted(DATA_CACHE.glob(f"{name}_*")):
        mp = d / "meta.json"
        if not (mp.exists() and (d / "train.bin").exists()):
            continue
        try:
            m = json.loads(mp.read_text())
        except Exception:
            continue
        if m.get("tokens", 0) >= n_tokens:
            if best is None or m["tokens"] < best["tokens"]:
                m["dir"] = str(d); best = m
    return best


def _ensure_bpt(meta):
    """bytes_per_token 이 없으면 val.bin 을 디코드해 계산·백필(토크나이저 무관 bpb용)."""
    if meta.get("bytes_per_token") or meta.get("data") == "synthetic":
        return meta
    try:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(tokenizer_path(meta["data"])))
        d = np.memmap(Path(meta["dir"]) / "val.bin", dtype=np.uint16, mode="r")
        ids = d[:min(len(d), 500_000)].tolist()
        meta["bytes_per_token"] = len(tok.decode(ids).encode("utf-8")) / max(len(ids), 1)
        mp = Path(meta["dir"]) / "meta.json"
        m2 = json.loads(mp.read_text()); m2["bytes_per_token"] = meta["bytes_per_token"]
        mp.write_text(json.dumps(m2, indent=2))
        print(f"[bpb] bytes_per_token={meta['bytes_per_token']:.3f} 백필 완료")
    except Exception as e:
        print(f"[bpb] bytes_per_token 계산 실패(무시): {e}")
    return meta


def prepare(name, n_tokens, val_frac=0.005):
    n_tokens = int(n_tokens)
    DATA_CACHE.mkdir(parents=True, exist_ok=True)

    if name != "synthetic":
        reuse = _find_reusable(name, n_tokens)
        if reuse:
            print(f"[data] 캐시 재사용: {reuse['tokens']/1e6:.1f}M 토큰 ({name}) "
                  f"-> {reuse['dir']}")
            return _ensure_bpt(reuse)

    cache_dir = DATA_CACHE / f"{name}_{n_tokens}"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if name == "synthetic":
        print(f"[data] 합성 토큰 {n_tokens/1e6:.1f}M 생성 (동작 확인용, 캐시 안 함)")
        rng = np.random.default_rng(0)
        vocab_eff = min(VOCAB, 4096)
        phrases = [rng.integers(0, vocab_eff, rng.integers(3, 12)) for _ in range(50_000)]
        out, n = [], 0
        while n < n_tokens:
            ph = phrases[rng.integers(len(phrases))]
            out.append(ph); n += len(ph)
        arr = np.concatenate(out)[:n_tokens].astype(np.uint16)
    else:
        tok = build_tokenizer(name)
        eos = tok.token_to_id("<eos>") or 2
        buf, total, total_bytes = [], 0, 0
        t0 = time.time()
        for text in _stream(name):
            ids = tok.encode(text).ids
            buf.append(np.array(ids + [eos], dtype=np.uint16))
            total += len(ids) + 1
            total_bytes += len(text.encode("utf-8"))
            if total >= n_tokens:
                break
            if total % 5_000_000 < 2000:
                print(f"  {total/1e6:>6.1f}M / {n_tokens/1e6:.0f}M  "
                      f"({total/max(time.time()-t0,1e-9)/1e3:.0f}K tok/s)")
        arr = np.concatenate(buf)[:n_tokens]

    n_val = max(1, int(len(arr) * val_frac))
    arr[:-n_val].tofile(cache_dir / "train.bin")
    arr[-n_val:].tofile(cache_dir / "val.bin")
    meta = {"data": name, "tokens": int(len(arr)), "vocab": VOCAB,
            "train": int(len(arr) - n_val), "val": int(n_val), "dir": str(cache_dir)}
    if name != "synthetic":
        meta["bytes_per_token"] = total_bytes / max(total, 1)
    (cache_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[data] train {meta['train']/1e6:.1f}M / val {meta['val']/1e3:.0f}K 토큰 저장 -> {cache_dir}")
    return meta
