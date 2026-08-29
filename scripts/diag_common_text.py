#!/usr/bin/env python3
"""★P075 단계0 — **공통 원문의 학습 오염을 잰다**(O1·O2·O3). torch 불필요(numpy + tokenizers).

## 왜 이 도구가 생겼나 (핸드오프 Q5 / P075 §2.1)

결과 053 §S1.7 이 **SQuAD v2 context** 로 토크나이저·교사를 판정했다. 그런데
🚫**그 원문이 우리 학습 풀에 들어 있는지 아무도 확인하지 않았다.**
`ko-en` 풀은 **한국어 위키 + fineweb-edu** 이고, **fineweb-edu 는 교육 텍스트 분류기라 위키를 선호**한다.
**SQuAD 는 영어 위키**이고 **KorQuAD 는 한국어 위키**다 — **둘 다 겹칠 이유가 있다.**

★**오염된 원문으로 잰 bpb 는 "본 것을 얼마나 외웠나" 를 잰다.** 그 수로 토크나이저 서열을
매기면 **암기량 순위**가 된다.

## 무엇을 하나

| 검사 | 방법 | 판정 |
|---|---|---|
| ★**O1** 겹침 | 후보 원문을 우리 토크나이저로 인코딩 → **토큰 13-gram 해시 집합** → `data_cache/*/train.bin` 전체 스트림과 대조 | ★**문서별 히트율 ≥ 1% 면 제외**(GPT-3 계열 관행) |
| **O2** 대조군 | **학습 캐시의 val 구간**에서 같은 길이를 떠서 같은 측정 | 🚫**대조군이 높게 안 나오면 도구가 고장난 것**이다 |
| **O3** SE | 후보를 10등분해 **문서 수·토큰 수의 분산** 보고 | bpb SE 는 `common_bpb.py` 가 잰다 — 여기서는 **표본 크기**만 |

⚠️★**13-gram 은 토큰 단위**다. 문자 13-gram 이 아니다 — 캐시가 **토큰 이진 파일**이라
문자로 되돌리려면 600M 토큰을 디코드해야 한다. **토큰 n-gram 이 더 싸고 더 엄격**하다
(같은 문장이라도 토크나이저가 다르면 안 걸린다 → **우리 토크나이저 기준의 오염**을 잰다).

🚫**한계**: 해시 충돌(64비트, 무시 가능) · **패러프레이즈는 못 잡는다** · **val.bin 은 안 본다**
(대조군으로만 쓴다).

사용:
    python scripts/diag_common_text.py --cache data_cache/ko-en_600000000 \\
        --tok data_cache/tok-ko-en-32768.json \\
        --squad datasets/squad/dev-v2.0.json \\
        --korquad datasets/KorQuad/KorQuAD_2.1/KorQuAD_v1.0_dev.json \\
        --klue-mrc datasets/KLUE/klue_benchmark/klue-mrc-v1.1/klue-mrc-v1.1_dev.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N = 13                      # n-gram 길이(토큰)
MOD = (1 << 61) - 1         # Mersenne prime — 곱셈 해시
BASE = 1_000_003


def load_squad_like(p: Path, key="context"):
    """SQuAD / KorQuAD 1.0 / KLUE-MRC 공통 구조: data[].paragraphs[].context"""
    d = json.loads(p.read_text(encoding="utf-8"))
    out, seen = [], set()
    for art in d.get("data", []):
        for para in art.get("paragraphs", []):
            c = (para.get(key) or "").strip()
            if c and c not in seen:
                seen.add(c)
                out.append(c)
    return out


def load_jsonl_field(p: Path, field):
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            j = json.loads(ln)
        except Exception:                                    # noqa: BLE001
            continue
        v = j.get(field)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    return out


def ngram_hashes(ids, n=N):
    """롤링 다항 해시. numpy 로 벡터화."""
    import numpy as np
    a = np.asarray(ids, dtype=np.uint64)
    if a.size < n:
        return np.empty(0, dtype=np.uint64)
    h = np.zeros(a.size - n + 1, dtype=np.uint64)
    for k in range(n):
        h = (h * np.uint64(BASE) + a[k:a.size - n + 1 + k]) % np.uint64(MOD)
    return h


def scan_cache(bin_path: Path, dtype, target, chunk=8_000_000):
    """캐시 전체를 훑으며 `target`(정렬된 uint64 배열)에 있는 n-gram 을 센다."""
    import numpy as np
    mm = np.memmap(bin_path, dtype=dtype, mode="r")
    total = mm.size
    hit = np.zeros(target.size, dtype=bool)
    pos = 0
    while pos < total:
        end = min(pos + chunk, total)
        seg = np.asarray(mm[max(pos - (N - 1), 0):end], dtype=np.uint64)
        h = ngram_hashes(seg)
        if h.size:
            idx = np.searchsorted(target, h)
            idx[idx >= target.size] = 0
            ok = target[idx] == h
            hit[idx[ok]] = True
        pos = end
        pct = pos / total * 100
        print(f"\r    스캔 {pct:5.1f}%  ({pos:,}/{total:,})", end="", flush=True)
    print()
    return hit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, help="data_cache/<name> 폴더")
    ap.add_argument("--tok", required=True, help="tokenizer json 경로")
    ap.add_argument("--squad", default=None)
    ap.add_argument("--korquad", default=None)
    ap.add_argument("--klue-mrc", default=None)
    ap.add_argument("--jsonl", nargs="*", default=[], help="추가 후보 `경로:필드`")
    ap.add_argument("--max-docs", type=int, default=4000, help="후보당 문서 상한")
    ap.add_argument("--thr", type=float, default=1.0, help="문서 제외 히트율 %% (기본 1.0)")
    a = ap.parse_args()

    try:
        import numpy as np
        from tokenizers import Tokenizer
    except ImportError as e:
        print(f"🚫 의존 없음: {e}. 학습 환경에서 돌린다.")
        return 2

    cache = Path(a.cache)
    meta = json.loads((cache / "meta.json").read_text(encoding="utf-8"))
    vocab = meta.get("vocab", 32768)
    dtype = np.uint16 if vocab <= 65536 else np.uint32
    tok = Tokenizer.from_file(a.tok)

    print("=" * 96)
    print("  P075 단계0 — 공통 원문 오염 검사 (O1·O2·O3)")
    print("=" * 96)
    print(f"  캐시 {cache.name}  vocab {vocab:,}  dtype {dtype.__name__}  n-gram {N}(토큰)")
    print(f"  토크나이저 {Path(a.tok).name}")
    print(f"  ★판정: 문서의 n-gram 중 **{a.thr}% 이상**이 학습 스트림에 있으면 **제외**")
    # ★함정 31 — **성공했을 때 나와야 하는 값**을 먼저 인쇄한다. 실패 쪽만 적으면
    #   부호가 뒤집힌 지표를 못 알아본다.
    print("  ★★기준값(성공 시 나와야 하는 값)")
    print("     · **O2 대조군 히트율 ≈ 100%** — 학습 스트림에서 그대로 뜬 조각이다. "
          "**50% 미만이면 도구가 고장난 것**이고 O1 을 믿지 않는다")
    print("     · O1 후보 히트율: 오염이 없으면 **0~1%**, 위키 계열이면 **수십 %** 도 정상 관측이다")
    print("     · 🚫**모든 후보가 0.0% 면 도구를 의심한다** — 해시·dtype·토크나이저 불일치의 얼굴이다")

    cands = {}
    if a.squad:
        cands["SQuAD v2 (영어 위키)"] = load_squad_like(Path(a.squad))
    if a.korquad:
        cands["KorQuAD 1.0 (한국어 위키)"] = load_squad_like(Path(a.korquad))
    if a.klue_mrc:
        cands["KLUE-MRC (뉴스 계열)"] = load_squad_like(Path(a.klue_mrc))
    for spec in a.jsonl:
        p, _, f = spec.partition(":")
        cands[f"{Path(p).name}:{f}"] = load_jsonl_field(Path(p), f or "text")

    # ★O2 대조군 — 학습 캐시의 **train 구간 앞부분**을 그대로 떠서 넣는다.
    #   🚫이것이 높게 안 나오면 도구가 고장난 것이다.
    ctrl_ids = None
    tb = cache / "train.bin"
    if tb.exists():
        mm = np.memmap(tb, dtype=dtype, mode="r")
        ctrl_ids = np.asarray(mm[1_000_000:1_000_000 + 200_000], dtype=np.uint64)

    print("\n## 후보 원문")
    all_h, owner = [], []
    docs_meta = []
    for name, docs in cands.items():
        docs = docs[:a.max_docs]
        enc = tok.encode_batch(docs)
        nb = sum(len(d.encode("utf-8")) for d in docs)
        ntok = sum(len(e.ids) for e in enc)
        print(f"  {name:28} 문서 {len(docs):>6,} · {nb/1024**2:6.2f} MB · 토큰 {ntok:>9,}")
        for di, e in enumerate(enc):
            h = ngram_hashes(e.ids)
            if h.size:
                all_h.append(h)
                owner.append(np.full(h.size, len(docs_meta), dtype=np.int32))
                docs_meta.append((name, di, h.size))
    if ctrl_ids is not None:
        h = ngram_hashes(ctrl_ids)
        all_h.append(h)
        owner.append(np.full(h.size, len(docs_meta), dtype=np.int32))
        docs_meta.append(("★O2 대조군(학습 스트림 자체)", 0, h.size))
        print(f"  {'★O2 대조군':28} 토큰 {ctrl_ids.size:>9,} (학습 캐시 train.bin 에서 직접)")

    if not all_h:
        print("🚫 후보가 없다."); return 1
    H = np.concatenate(all_h)
    O = np.concatenate(owner)
    order = np.argsort(H, kind="stable")
    Hs, Os = H[order], O[order]
    uniq, first = np.unique(Hs, return_index=True)
    print(f"\n  n-gram {H.size:,}개 · 고유 {uniq.size:,}개")

    print("\n## O1 — 학습 스트림 스캔")
    hit_u = scan_cache(tb, dtype, uniq)

    # 문서별 히트율
    hit_map = dict(zip(uniq.tolist(), hit_u.tolist()))
    per_doc = {}
    for h, o in zip(Hs.tolist(), Os.tolist()):
        d = per_doc.setdefault(o, [0, 0])
        d[1] += 1
        if hit_map.get(h):
            d[0] += 1

    print("\n## 결과 — 후보별")
    print(f"  {'후보':30} {'문서':>7} {'제외':>7} {'제외율':>7} {'평균 히트율':>11} {'최대':>7}")
    by_name = {}
    for oi, (name, di, n) in enumerate(docs_meta):
        hits, tot = per_doc.get(oi, [0, 0])
        r = hits / tot * 100 if tot else 0.0
        by_name.setdefault(name, []).append(r)
    for name, rs in by_name.items():
        drop = sum(1 for r in rs if r >= a.thr)
        star = "🚫" if (drop / len(rs) > 0.10 and "대조군" not in name) else "✅"
        if "대조군" in name:
            star = "✅" if (sum(rs) / len(rs)) > 50 else "🚫★도구 고장 의심"
        print(f"  {star}{name:29} {len(rs):>7,} {drop:>7,} {drop/len(rs)*100:>6.1f}% "
              f"{sum(rs)/len(rs):>10.2f}% {max(rs):>6.1f}%")

    print("\n## O3 — 표본 크기(10등분)")
    for name, rs in by_name.items():
        if "대조군" in name:
            continue
        keep = [r for r in rs if r < a.thr]
        k = len(keep) // 10
        print(f"  {name:30} 통과 {len(keep):,} 문서 → 10등분 각 {k:,} 문서 "
              + ("✅" if k >= 100 else "⚠️**등분당 100문서 미만 — SE 가 커진다**"))

    print("\n" + "=" * 96)
    print("  🚫★**대조군이 높게 안 나오면 O1 결과를 믿지 않는다**(P075 §2.1 O2).")
    print("  ⚠️패러프레이즈·번역은 못 잡는다. **이것은 축자 겹침의 하한**이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
