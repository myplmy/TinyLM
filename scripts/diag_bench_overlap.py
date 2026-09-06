#!/usr/bin/env python3
"""★벤치 문항이 **우리 학습 스트림 안에 있는가** — 오염 실측(학습 0 · GPU 0 · torch 0).

## 왜 이 도구가 있나 (2026-09-05)

🚫★**KorQuAD 는 우리 학습 스트림의 94.8% 였다**(결과 060 §7). 그것을 **쓴 뒤에** 알았다.
그리고 `common_bpb` 가 채점하는 SQuAD train 도 **8.7% 오염**돼 있었다.
★**두 번 다 "받아서 바로 채점" 했기 때문**이다.

지금 새 벤치 둘을 붙이려 한다 — **ARC-Easy 전량**(fineweb-edu 가 웹을 긁는다)과
**KoBEST HellaSwag**(원문이 **한국어 위키** = 우리 풀의 절반). 🚫**같은 실수를 세 번 하지 않는다.**

## 어떻게 재나 — **토큰 n-gram 정확 일치**

문항 텍스트를 **우리 토크나이저**로 인코딩하고, 그 안의 **연속 `--k` 토큰 창**이
`train.bin` 에 **그대로 있는지** 찾는다. 🚫문자열 검색이 아니라 **토큰 검색**이다 —
캐시가 토큰으로 저장돼 있고, 디코드하면 600M 토큰에 수 분이 든다.

빠른 이유: 창의 **첫 토큰이 나오는 위치만** numpy 로 뽑고(평균 `N/V` 개), 그 자리에서만
나머지 `k-1` 개를 대조한다. 어휘 32,768 · 스트림 597M 이면 후보가 **문항당 약 18,000곳**이고
벡터 연산으로 끝난다.

## 성공 기준값 (★결과 전에 고정 — `check_diag_data` 요구)

| 겹침률 | 뜻 | 조치 |
|---|---|---|
| **0 ~ 1%** | 배경 수준(관용구가 우연히 맞는다) | ✅쓴다 |
| 1 ~ 10% | ⚠️일부 오염 | 쓰되 **결과에 수치를 함께 적는다** |
| ★**10% 초과** | 🚫**오염** | **그 과제를 쓰지 않는다.** KorQuAD 94.8% · SQuAD 8.7% 가 눈금이다 |

⚠️★**겹침이 0 이어도 "오염 없음" 이 아니다** — 같은 사실을 **다른 문장**으로 배운 것은 못 잡는다.
이 도구가 답하는 것은 ***"문항 문장이 그대로 스트림에 있는가"*** 하나다.

사용:

    python scripts/diag_bench_overlap.py --task arc_easy_full --data ko-en --tokens 600M
    python scripts/diag_bench_overlap.py --task kobest_hellaswag --sample 300 --k 12
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tinylm                                   # noqa: E402  ★R40

_ = tinylm

BENCH = ROOT / "datasets" / "bench"
CACHE = ROOT / "data_cache"

CLEAN_MAX = 1.0        # ★성공 기준값 — 이 아래면 배경 수준
DIRTY_MIN = 10.0       # ★이 위면 그 과제를 쓰지 않는다
# ★참고 눈금(실측): KorQuAD **94.8%**(결과 060) · SQuAD train **8.7%**(결과 053)
REF = {"KorQuAD": 94.8, "SQuAD-train": 8.7}

# ★2026-09-06 — `prompt` 추가. 우리 Stage1 held-out 이 그 키를 쓴다.
#   🚫없었으면 **검사 문항 0개**로 exit 1 이 났다(다행히 조용하지는 않다).
TEXT_KEYS = ("question", "ctx", "context", "premise", "goal", "sentence",
             "paragraph", "prompt")


def item_text(r):
    """행에서 **문항 본문**을 뽑는다. 후보를 안 넣는다 — 후보는 대개 짧다."""
    for k in TEXT_KEYS:
        v = r.get(k)
        # ★2026-09-06 — 문턱 20 -> 12 자. 우리 held-out 프롬프트가 짧아
        #   **154/300 이 본문 없음으로 빠졌다**. 창 크기(`--k`)가 이미 진짜 게이트이므로
        #   여기서 더 자르면 **검사 범위만 좁아진다**(느슨해지지 않는다).
        if isinstance(v, str) and len(v) > 12:
            return v
    # ARC 는 question 이 dict 안에 있는 판본이 있다
    q = r.get("question")
    if isinstance(q, dict) and isinstance(q.get("stem"), str):
        return q["stem"]
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="600M")
    ap.add_argument("--k", type=int, default=12, help="연속 일치를 볼 토큰 창 크기")
    ap.add_argument("--sample", type=int, default=400, help="검사할 문항 수(0=전부)")
    a = ap.parse_args()

    import numpy as np
    from tokenizers import Tokenizer
    from tinylm.data.prepare import tokenizer_path

    p = BENCH / f"{a.task}.jsonl"
    if not p.exists():
        print(f"  🚫 {p} 가 없다 — 먼저 `fetch_bench_data.py --only {a.task}`", file=sys.stderr)
        return 2
    n_tok = int(float(a.tokens.rstrip("MmBb")) * (1e9 if a.tokens[-1] in "Bb" else 1e6))
    cdir = CACHE / f"{a.data}_{n_tok}"
    tb = cdir / "train.bin"
    if not tb.exists():
        print(f"  🚫 {tb} 가 없다.", file=sys.stderr)
        return 2

    rows = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
    stream = np.memmap(tb, dtype=np.uint16, mode="r")

    print("=" * 96)
    print(f"  벤치 오염 실측 — {a.task}  vs  {cdir.name}/train.bin")
    print("=" * 96)
    print(f"  문항 {len(rows):,}개 중 {a.sample or len(rows):,}개 검사 · 창 {a.k} 토큰 · "
          f"스트림 {len(stream):,} 토큰")
    print(f"  ★성공 기준: 겹침 **{CLEAN_MAX:g}% 이하 = 배경** · "
          f"**{DIRTY_MIN:g}% 초과 = 그 과제를 쓰지 않는다**")
    print(f"  ★눈금(실측): " + " · ".join(f"{k} **{v}%**" for k, v in REF.items()))

    idx = range(len(rows)) if not a.sample else range(min(a.sample, len(rows)))
    n_ck = n_hit = n_skip = 0
    hits = []
    for i in idx:
        txt = item_text(rows[i])
        ids = tok.encode(txt).ids if txt else []
        if len(ids) < a.k:
            n_skip += 1
            continue
        n_ck += 1
        # ★가장 드문 첫 토큰을 고른다 — 후보 자리를 줄인다
        win = ids[: a.k]
        pos = np.flatnonzero(stream[: len(stream) - a.k] == win[0])
        found = False
        if pos.size:
            w = np.asarray(win[1:], dtype=np.uint16)
            for off in range(0, pos.size, 1_000_000):        # 메모리 상한
                pp = pos[off:off + 1_000_000]
                m = np.ones(pp.size, dtype=bool)
                for j, v in enumerate(w, start=1):
                    m &= stream[pp + j] == v
                    if not m.any():
                        break
                if m.any():
                    found = True
                    break
        if found:
            n_hit += 1
            if len(hits) < 5:
                hits.append((rows[i].get("id", i), txt[:60]))

    if n_ck == 0:                                   # ★R19 — 0 을 조용히 통과시키지 않는다
        print(f"  🚫★**검사한 문항이 0개다**(전부 {a.k} 토큰 미만이거나 본문을 못 찾았다). "
              f"건너뜀 {n_skip}", file=sys.stderr)
        return 1

    rate = 100.0 * n_hit / n_ck
    print()
    print(f"  검사 {n_ck:,} · 겹침 **{n_hit:,}** · 건너뜀 {n_skip} → ★**{rate:.2f}%**")
    for hid, t in hits:
        print(f"       {hid}  {t}…")
    print()
    if rate > DIRTY_MIN:
        print(f"  🚫★★**오염이다**({rate:.2f}% > {DIRTY_MIN:g}%). **이 과제를 모델 비교에 쓰지 않는다.**")
        return 1
    if rate > CLEAN_MAX:
        print(f"  ⚠️★**일부 오염**({rate:.2f}%). 쓰되 **결과문서에 이 수치를 함께 적는다.**")
        return 0
    print(f"  ✅ 배경 수준({rate:.2f}% ≤ {CLEAN_MAX:g}%). ⚠️단 **같은 사실을 다른 문장으로 배운 것은 "
          f"이 도구가 못 잡는다.**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
