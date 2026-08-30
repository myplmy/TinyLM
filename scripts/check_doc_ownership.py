#!/usr/bin/env python3
"""★정적 게이트 19 — **"이 문서의 본문이 남의 것인가"**. torch 불필요.

## 왜 이 게이트가 생겼나 (함정 42, 사용자 지시 Q8)

2026-08-28 `append_repro.py` 의 **쓰기 루프가 읽기 루프의 지역변수를 썼다.**
→ **결과문서 7건의 본문이 남의 문서 내용으로 덮였다**(커밋 1c3f87e·a01f32f).

🚫★**그때 게이트 17종이 전부 통과했다.** 부록은 옳았고 **아무도 "누구 것인가" 를 안 봤다.**
⚠️**058 은 303 → 454줄로 오히려 커졌으므로 "축소 감시" 로는 못 잡는다.**

## ★무엇을 보는가 — 두 신호

| 신호 | 규칙 | 왜 이것이 신호인가 |
|---|---|---|
| ★**E1 로그 귀속** | 결과문서 `NNN` 이 **남의 로그(`MMM_log_`)를 자기 것보다 많이** 인용 | 결과문서 번호 = 실험군 번호이고 **로그 파일명 앞 세 자리가 그것을 말한다.** 본문이 통째로 바뀌면 인용하는 로그도 통째로 바뀐다 |
| ★**E2 본문 중복** | 두 결과문서가 **N줄 연속으로 동일** | 덮어쓰기는 **복사**다. 원본과 사본이 남는다 |
| ★★**E3 H1 번호** | 결과문서 `NNN` 의 첫 `# ` 줄이 **`NNN` 로 시작**하는가 | ★**가장 값싸고 가장 정확하다.** 실제 사고에서 051·053·058 의 첫 줄이 전부 `# 059 — P074 단계1:` 이었다 |

## ★★오경보 실측 (2026-08-30, 결과문서 60개)

**게이트를 만들기 전에 지금 저장소에서 몇 건이 걸리는지 셌다** — 사용자 지시가
*"과교정 혹은 오경보를 울리지 않을지 판단하여 문제가 없는 선에서라면 구현 승인"* 이었기 때문이다.

| N | 교차문서 블록 | 관련 문서쌍 |
|---:|---:|---:|
| 3 | 18종 | **4쌍** |
| 4 | 16종 | **1쌍** |
| ★**6** | 14종 | ★**1쌍** |
| 8 | 12종 | 1쌍 |

★**N=6 에서 문서쌍 1개**뿐이고 그것은 **의도적으로 두 곳에 적은 정정 기록**이다(→ `ALLOW`).
★**E1 은 3개 문서가 남의 로그를 인용하지만 셋 다 "자기 것보다 적다"** → **0건 걸린다.**

→ ✅**오경보 0으로 켤 수 있다.**

## ✅★**게이트가 실패를 본 적이 있는가** — 있다 (2026-08-30 검증)

*"실패를 본 적 없는 게이트는 게이트가 아니다"*(결과 059 §조치 2)에 따라,
**파괴 시점 커밋 `86d24c9` 의 `test_result/` 를 그대로 꺼내 돌렸다**:

```
git archive 86d24c9 test_result | tar -x -C <임시>
python scripts/check_doc_ownership.py
```

| | 파괴 커밋 `86d24c9` | 현재 |
|---|---:|---:|
| 에러 | 🚫**22건** | ✅**0건** |
| E3 서명 | `051`·`053`·`058` 의 H1 이 전부 **`# 059 — P074 단계1:`** | — |
| E2 | 187블록 공유 문서쌍 다수 | 1쌍(허용) |

## 🚫한계

- 🚫**"내용이 옳은가" 는 못 본다.** *"남의 것으로 보이는가"* 만 본다.
- 🚫**손으로 새로 쓴 잘못된 내용은 못 잡는다** — 복사가 아니면 신호가 없다.
- ⚠️**`ALLOW` 를 늘리면 게이트가 약해진다.** 추가할 때는 **이유를 함께 적는다**.
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: ★의도적 중복 — **이유를 반드시 적는다.** 정렬된 파일명 쌍.
ALLOW = {
    ("003_20260725001000_P014-커널-어닐버그.md",
     "051_20260821_P065-B2는-무해하지만-무익하다-그리고-no-ckpt가-열렸다.md"):
        "★2026-08-22 §번호규약 오배정 정정 기록을 **양쪽 문서에 일부러** 남겼다. "
        "두 문서가 그 사고의 당사자라 한쪽만 적으면 다른 쪽을 읽는 사람이 못 본다.",
}

MIN_LINE = 25          # 이보다 짧은 줄은 신호가 아니다(표 구분선·상투구)
DEFAULT_N = 6


def substantive(path):
    """의미 있는 줄만 `(줄번호, 내용)` 으로. 표 구분선·코드펜스·인용은 뺀다."""
    out = []
    try:
        fh = open(path, encoding="utf-8")
    except OSError:
        return out
    with fh:
        for i, ln in enumerate(fh, 1):
            s = ln.strip()
            if not s or len(s) < MIN_LINE:
                continue
            if s.startswith(("|---", "```", "---", ">")):
                continue
            out.append((i, s))
    return out


def check(n_lines=DEFAULT_N, verbose=False):
    paths = [p for p in sorted(glob.glob(str(ROOT / "test_result" / "*.md")))
             if not os.path.basename(p).startswith("실험목록")]
    docs = {os.path.basename(p): p for p in paths}
    errs, warns = [], []

    # ── E1. 로그 귀속 ────────────────────────────────────────────────────
    for name, p in docs.items():
        m = re.match(r"^(\d{3})_", name)
        if not m:
            continue
        num = m.group(1)
        txt = open(p, encoding="utf-8").read()
        cited = collections.Counter(re.findall(r"(\d{3})_log_", txt))
        own = cited.get(num, 0)
        foreign = {k: v for k, v in cited.items() if k != num}
        nf = sum(foreign.values())
        if nf >= 3 and nf > own:
            top = dict(sorted(foreign.items(), key=lambda x: -x[1])[:3])
            errs.append(f"[E1] {name}: 남의 로그 {nf}회 ^> 자기 로그 {own}회 — {top}  "
                        "★본문이 다른 실험군의 것일 수 있다(함정 42)")
        elif nf and verbose:
            warns.append(f"[W1] {name}: 남의 로그 {nf}회(자기 {own}회) — 교차참조로 보인다")

    # ── E3. H1 번호 ──────────────────────────────────────────────────────
    #   ★가장 값싸고 가장 정확한 신호다. 함정 42 의 실제 사고에서
    #     051·053·058 의 첫 줄이 전부 `# 059 — P074 단계1:` 이었다.
    for name, p in docs.items():
        m = re.match(r"^(\d{3})_", name)
        if not m:
            continue
        num = m.group(1)
        with open(p, encoding="utf-8") as fh:
            h1 = ""
            for ln in fh:
                if ln.startswith("# "):
                    h1 = ln.strip()
                    break
        if not h1:
            warns.append(f"[W3] {name}: H1(`# `) 이 없다")
            continue
        # ★초기 문서(001~005)는 `# 실험 001 —` 양식이다 — **양식 차이이지 결함이 아니다**.
        got = re.match(r"^#\s*(?:실험\s*)?(\d{3})", h1)
        if not got:
            warns.append(f"[W3] {name}: H1 이 세 자리 번호로 시작하지 않는다 — {h1[:60]}")
        elif got.group(1) != num:
            errs.append(f"[E3] {name}: ★**H1 이 {got.group(1)} 번 문서라고 말한다** — "
                        f"{h1[:70]}\n"
                        "         🚫파일명과 본문의 주인이 다르다(함정 42 의 정확한 서명)")

    # ── E2. 본문 중복 ────────────────────────────────────────────────────
    blocks = collections.defaultdict(list)
    for name, p in docs.items():
        ls = substantive(p)
        for i in range(len(ls) - n_lines + 1):
            key = tuple(s for _, s in ls[i:i + n_lines])
            blocks[key].append((name, ls[i][0]))

    pair_hits = collections.defaultdict(list)
    for key, hits in blocks.items():
        names = sorted({n for n, _ in hits})
        if len(names) < 2:
            continue
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                pair_hits[(names[a], names[b])].append((key[0], hits))

    for pair, found in sorted(pair_hits.items()):
        if pair in ALLOW:
            warns.append(f"[W2] {pair[0][:34]} <-> {pair[1][:34]}: "
                         f"{len(found)}블록 — ✅**허용됨**: {ALLOW[pair]}")
            continue
        first = found[0][0]
        errs.append(f"[E2] {pair[0]}\n         <-> {pair[1]}\n"
                    f"         {n_lines}줄 연속 동일 블록 {len(found)}종. 첫 줄: {first[:76]}\n"
                    "         ★한쪽 본문이 다른 쪽에서 복사됐을 수 있다 — "
                    "`git log -p` 로 **어느 쪽이 먼저였는지** 확인한다")
    return errs, warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--lines", type=int, default=DEFAULT_N,
                    help=f"몇 줄 연속이면 중복으로 보는가 (기본 {DEFAULT_N})")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    print("=" * 96)
    print("  게이트 19 — 문서 본문 귀속 검사 (함정 42)")
    print("=" * 96)
    print(f"  ★신호 셋: E1 로그 귀속 역전 · E2 {a.lines}줄 연속 중복 · ★E3 H1 번호 불일치")
    print("  ★★오경보 실측(2026-08-30, 문서 60개): **E1 0건 · E2 1쌍(허용 목록에 있다)**")
    print("  🚫이 게이트는 *'내용이 옳은가'* 를 못 본다 — *'남의 것으로 보이는가'* 만 본다.")

    errs, warns = check(a.lines, a.verbose)
    print()
    for w in warns:
        print(f"  ⚠️ {w}")
    for e in errs:
        print(f"  🚫 {e}")
    print(f"\n  에러 {len(errs)}건 · 경고 {len(warns)}건")
    if not errs:
        print("  ✅ 모든 결과문서의 본문이 자기 실험군의 것으로 보인다.")
    print("=" * 96)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
