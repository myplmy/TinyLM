#!/usr/bin/env python3
"""★선결이 없는데 미뤄 둔 항목을 잡는다 (2026-09-04 신설).

## 왜 (승인된 제안서 `proposal/done/20260904_선결없는-대기항목을-막는다-approved.md`)

2026-09-03 핸드오프 §7.2 *"배치 작성 대기"* 에 이런 줄이 있었다:

    | P084 단계0 | 없음(구현 완료). **배치만 만들면 된다** | 0.1h | 0.2h |
    | 유니크 토큰 축(600M 팔) | ✅조건부 승인됨. 풀 1.2B **있다** | 0 | 5.1h |

★**선결이 0 인데 배치를 안 만들고 다음 세션으로 넘겼다.** 의사결정함정 **D1** —
*"미룬다" 고 쓸 때는 무엇이 선결이고 그것이 얼마인지를 숫자로 적는다. 숫자가 없으면
그건 선결이 아니라 미루는 이유다.* 규약은 **2026-08 에 있었고 2026-09-03 에 또 어겼다.**

★**`check_handoff` 규칙 9 와 짝**이다:
- 규칙 9 = *"없는 배치를 있는 것처럼 적지 마라"*
- ★**이 게이트 = *"만들 수 있는 배치를 안 만들고 넘기지 마라"***

## 검사 셋

| 검사 | 무엇 | 판정 |
|---|---|---|
| ★**W1** | 핸드오프 §7 의 대기표에서 **선결이 비었거나 "없음" 이거나 0h** 인데 배치 이름이 없다 | 🚫**에러** |
| ★**W2** | `proposal/done/*-approved.md` 인데 **이어진 계획서가 없다** | 🚫**에러**(도구 제안·1일 유예는 면제) |
| **W3** | 계획서 단계표가 이름 붙인 배치가 **디스크에 없다** | ⚠️**경고**(`⏸`·`🚫` 표시면 면제) |

## ★탈출구 — 정말 못 만드는 배치도 있다

CLAUDE.md: *"최상위 실험 배치는 **지금 돌아갈 때만** 만든다."*
→ **선결 칸에 이유를 적으면 통과**한다. 막는 것은 **빈칸·"없음"·0h** 뿐이다.

## 사용법

    python scripts/check_pending.py                 # 최신 핸드오프
    python scripts/check_pending.py --file handoff/202609032330_HANDOFF.md   # 재현 검증
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NL = chr(10)
BAT = re.compile(r"run_[A-Za-z0-9_]+\.bat")
FREE = ("없음", "—", "-", "")            # ★선결 **텍스트** 칸이 비었다
# 🚫★시간 칸의 `—` 는 *"모른다"* 이지 *"0"* 이 아니다 — 섞으면 과잉 차단이 된다
#    (제안서 §8 이 미리 적어 둔 위험. 초판이 실제로 3행을 오탐했다).
ZERO = ("0", "0h", "0.0h", "0.0")
GRACE_DAYS = 1.0                                          # W2 유예(승인 직후)


def cells(ln):
    return [c.strip() for c in ln.strip().strip("|").split("|")]


def newest_handoff():
    hs = sorted(ROOT.glob("handoff/*_HANDOFF.md"))
    return hs[-1] if hs else None


def section7(text):
    """★`check_handoff` 와 **같은 방식**으로 §7 을 자른다(함정 18: 한 곳에서만 정한다)."""
    lines = text.split(NL)
    i = next((k for k, l in enumerate(lines) if re.match(r"^##\s*7\.", l)), None)
    if i is None:
        return []
    j = next((k for k in range(i + 1, len(lines)) if re.match(r"^##\s", lines[k])), len(lines))
    return lines[i:j]


def w1(path):
    """선결이 사실상 0 인데 배치가 없는 대기 행."""
    out = []
    seg = section7(io.open(path, encoding="utf-8").read())
    hdr_i = None
    for k, ln in enumerate(seg):
        c = cells(ln)
        if ln.strip().startswith("|") and any("선결" == x or x.startswith("선결") for x in c):
            hdr_i = k
            cols = c
            continue
        if hdr_i is None or not ln.strip().startswith("|"):
            continue
        if set(ln.replace("|", "").strip()) <= set("-: "):
            continue                                       # 구분선
        if len(c) != len(cols):
            continue
        idx = next((n for n, x in enumerate(cols) if x.startswith("선결")), None)
        pre = re.sub(r"[*✅★⚠️🚫`]", "", c[idx]).strip() if idx is not None else ""
        # ⚙선결(시간) 열이 따로 있으면 그것도 본다
        hidx = next((n for n, x in enumerate(cols)
                     if "선결" in x and x != cols[idx]), None)
        hh = re.sub(r"[*`⚙]", "", c[hidx]).strip() if hidx is not None else ""
        free = (pre in FREE) or pre.startswith("없음") or (hh in ZERO)
        if free and not BAT.search(ln):
            _nm = re.sub(r"[*`]", "", c[0]).strip()
            out.append((_nm, pre or "(빈칸)", hh))
    return out


def w2():
    """`-approved` 인데 이어진 계획서가 없다."""
    out = []
    now = time.time()
    for p in sorted((ROOT / "proposal" / "done").glob("*-approved.md")):
        src = io.open(p, encoding="utf-8").read()
        if "계획서 없이" in src or "도구 작업" in src:
            continue                                       # ★도구 제안 — 계획서를 안 만든다
        if (now - p.stat().st_mtime) < GRACE_DAYS * 86400:
            continue                                       # ★승인 직후 유예
        plans = {m for m in re.findall(r"P\d{3}", src)}
        if any(list((ROOT / "test_plan").glob(f"{n}_*.md")) for n in plans):
            continue
        out.append(p.name)
    return out


def _ran(bat):
    """그 단계가 **이미 돌았는가** — `test_result/` 의 로그 파일명으로 판정한다.

    ★배치는 완료 후 삭제되므로(CLAUDE.md 삭제 규칙) *"디스크에 없다"* 가 곧
    *"안 만들었다"* 가 아니다. 🚫이 구분을 안 하면 경고 20건이 전부 잡음이 된다.
    """
    m = re.match(r"^run_(P\d{3,}[A-Za-z]*)_([A-Za-z0-9]+)_", bat)
    if not m:
        return False
    plan, stage = m.group(1), m.group(2).lower()
    for f in (ROOT / "test_result").glob("*.txt"):
        n = f.name.lower()
        if plan.lower() in n and stage in n:
            return True
    return False


def w3():
    """계획서가 이름 붙인 배치가 디스크에도 없고 **돈 적도 없다**."""
    out = []
    for p in sorted((ROOT / "test_plan").glob("P*.md")):
        if p.name.endswith("-done.md"):
            continue                                       # ★종결된 계획
        for ln in io.open(p, encoding="utf-8").read().split(NL):
            if not ln.strip().startswith("|"):
                continue
            if "⏸" in ln or "🚫" in ln or "없음" in ln:
                continue                                   # ★미뤘다고 명시했다
            for b in set(BAT.findall(ln)):
                if (ROOT / b).exists() or (ROOT / b.replace(".bat", "-done.bat")).exists():
                    continue
                if _ran(b):
                    continue                               # ★돌았고 배치는 지워졌다
                out.append((p.name, b))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None, help="검사할 핸드오프(기본: 최신)")
    a = ap.parse_args()

    path = Path(a.file) if a.file else newest_handoff()
    print("=" * 96)
    print("  선결 없는 대기 항목 — D1 을 기계로 (`check_handoff` 규칙 9 의 짝)")
    print("=" * 96)
    if path is None or not path.is_file():
        print("  🚫 핸드오프를 못 찾았다.", file=sys.stderr)
        return 2
    print(f"  대상 핸드오프: {path.name}")

    e1 = w1(path)
    e2 = w2()
    warn3 = w3()

    for name, pre, hh in e1:
        print(f"  🚫 [W1] **{name}** — 선결 `{pre}`"
              + (f" · ⚙`{hh}`" if hh else "")
              + " 인데 **배치 이름이 없다**. 지금 만들 수 있으면 만든다(D1)")
    for n in e2:
        print(f"  🚫 [W2] **{n}** — 승인됐는데 **이어진 계획서가 없다**. "
              f"`test_plan/P0NN_*.md` 를 쓰거나, 도구 제안이면 본문에 그렇게 적으세요")
    for pn, b in warn3:
        print(f"  ⚠️ [W3] {pn} 이 `{b}` 를 가리키는데 **디스크에 없다** "
              f"(미룬 것이면 그 줄에 `⏸` 를 붙이세요)")

    n_err = len(e1) + len(e2)
    print()
    print(f"  에러 {n_err}건 · 경고 {len(warn3)}건")
    print("  ⚠️★**'선결이 있다' 는 것만 본다 — 그 선결이 진짜인지는 사람이 본다.**")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
