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
    # (P012) 큐레이션 대칭 믹스: ko=Korean-webtext-edu(FineWeb-Edu 방식 교육필터, Qwen3-80B 채점 ≥3.0),
    #   en=FineWeb-Edu. ko-en(원시 위키)과 공존하며 같은 토큰에서 데이터효율(bpb) 비교용.
    #   config=None(기본 subset), text_key="text". 비교는 반드시 같은 토크나이저로.
    "ko-edu-en": [("eliceai/korean-webtext-edu", None, "train", "text", 0.5),
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


def spam_signature(text, min_chars=50_000):
    """★P037 단계2 — 결과 018 이 실측한 **SEO 스팸 문서의 서명**. 참이면 버린다.

    `ko-edu-en` val 의 손실 53% 를 차지하던 거대 문서 7개는 길이 문제가 아니었다.
    자격증 덤프 판매 문구 + 무관한 소설 + **단어 중간에 삽입된 제품 키워드** 였고,
    언어모델이 예측할 수 있는 텍스트가 아니다. 손실 8~9.6(전체 6.09)이 난 이유가
    난이도가 아니라 **무작위성**이라는 뜻이다.

    측정된 서명(결과 018 §3.2) — 세 조건이 **함께** 성립할 때만 스팸으로 본다:
      · 대형            : min_chars 이상
      · 줄바꿈 ~0%      : 문서 전체가 한 줄
      · 줄 고유율 100%  : 반복 구조가 아니라 통짜 텍스트
    건강한 대조군(`ko-en`)은 줄바꿈 0.3~2.3% / 줄 고유율 94.8~99.6% 라 걸리지 않는다.

    ★길이 상한이 아니라 **내용 필터**인 이유: 길이로 자르면 스팸이 잘린 채 남는다.
    ★보수적으로 설계했다 — 애매하면 남긴다. 데이터를 지우는 쪽이 되돌리기 어렵다.
    """
    if len(text) < min_chars:
        return False
    lines = text.split("\n")
    nl_frac = (len(lines) - 1) / max(len(text), 1)
    uniq = len(set(lines)) / max(len(lines), 1)
    return nl_frac < 1e-4 and uniq >= 0.999


def prepare(name, n_tokens, val_frac=0.005, exact=False,
            doc_filter=False, doc_min_chars=50_000):
    """exact=True 면 상위호환(_find_reusable)을 쓰지 않고 **정확히 {name}_{n_tokens}** 캐시만 사용한다.
    (있으면 그 캐시, 없으면 정확히 그 크기로 신규 생성.) 토큰스윕처럼 '모든 예산이 같은 풀에서 샘플'해야
    할 때, 더 큰 캐시가 존재해도 특정 크기를 콕 집어 요청하는 용도."""
    n_tokens = int(n_tokens)
    DATA_CACHE.mkdir(parents=True, exist_ok=True)

    if name != "synthetic":
        if exact:
            d = DATA_CACHE / (f"{name}_{n_tokens}" + ("_filtered" if doc_filter else ""))
            if (d / "meta.json").exists() and (d / "train.bin").exists():
                m = json.loads((d / "meta.json").read_text()); m["dir"] = str(d)
                print(f"[data] 정확 캐시 사용(exact, 상위호환 무시): {n_tokens/1e6:.1f}M ({name}) -> {d}")
                return _ensure_bpt(m)
            print(f"[data] 정확 캐시({name}_{n_tokens}) 없음 → 정확히 그 크기로 신규 생성(상위호환 무시)")
        else:
            reuse = _find_reusable(name, n_tokens)
            if reuse:
                print(f"[data] 캐시 재사용: {reuse['tokens']/1e6:.1f}M 토큰 ({name}) "
                      f"-> {reuse['dir']}")
                return _ensure_bpt(reuse)

    # ★P037 단계2: 필터를 켜면 **다른 디렉터리**에 쓴다. 기존 캐시로 학습한 런들이
    #   자기 로그와 계속 비교 가능해야 하므로 덮어쓰지 않는다(결과 018 §5).
    suffix = "_filtered" if doc_filter else ""
    cache_dir = DATA_CACHE / f"{name}_{n_tokens}{suffix}"
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
        n_drop, n_drop_chars = 0, 0
        for text in _stream(name):
            if doc_filter and spam_signature(text, doc_min_chars):
                n_drop += 1
                n_drop_chars += len(text)
                continue
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
        if doc_filter:
            print(f"[filter] 스팸 서명으로 제외한 문서 {n_drop:,}개 / {n_drop_chars/1e6:.1f}M 자")
            print(f"[filter] 서명 = 길이 {doc_min_chars:,}자 이상 AND 줄바꿈 ~0% AND 줄 고유율 100%")
            print(f"[filter] ★제외율이 몇 퍼센트를 넘으면 무엇이 걸렸는지 먼저 확인할 것"
                  f"(결과 018 §5).")

    n_val = max(1, int(len(arr) * val_frac))
    arr[:-n_val].tofile(cache_dir / "train.bin")
    arr[-n_val:].tofile(cache_dir / "val.bin")
    meta = {"data": name, "tokens": int(len(arr)), "vocab": VOCAB,
            "train": int(len(arr) - n_val), "val": int(n_val), "dir": str(cache_dir)}
    if name != "synthetic":
        meta["bytes_per_token"] = total_bytes / max(total, 1)
        meta["doc_filter"] = bool(doc_filter)
        if doc_filter:
            meta["doc_min_chars"] = int(doc_min_chars)
            meta["docs_dropped"] = int(n_drop)
    (cache_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[data] train {meta['train']/1e6:.1f}M / val {meta['val']/1e3:.0f}K 토큰 저장 -> {cache_dir}")
    return meta
