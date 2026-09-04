#!/usr/bin/env python3
"""★체크포인트 판정 표를 **디스크와 맞춘다**(2026-09-04 사용자 지시 9).

## 왜

판정 정본은 **`checkpoints.tsv`** 다(2026-08-19 사용자 지시로 MD -> TSV).
마지막 손질이 **2026-08-27** 이고 그 뒤 런이 계속 쌓였다. 실사(2026-09-04):

    디스크 268개 · 181.3 GB
    판정 표에 없는 파일 **135개**  <- `cleanup_ckpt.py` 가 **손도 못 댄다**(화이트리스트 방식)

★정본이 하나인 설계(함정 18 회피)는 옳은데, **정본이 늙으면 아무것도 못 지운다.**
→ 이 도구가 **기계로 판정 가능한 것만** 채우고 나머지는 `hold` 로 남긴다.

## 기계 판정 규칙 — **둘뿐이다**

| 규칙 | 판정 | 근거 |
|---|---|---|
| `tiny_*` | `delete` | 스모크. `run_smoke_check.bat` 이 매번 재생성한다 |
| 짝 json 의 `steps < 500`(그 런의 `_best` 형제 포함) | `delete` | 기준표 §2.3 — 250스텝급은 **품질 판정 사용 금지** |
| 그 밖 전부 | `hold` | 🚫**축이 닫혔는지는 기계가 모른다** |

### 🚫★`_best` 를 이름만 보고 `delete` 로 적지 않는다

`checkpoints.tsv` 머리말 **규칙 6**(2026-08-20 신설)이 그것을 금지한다 —
`denseb_best` 사고 때 **규칙을 *역할* 이 아니라 *이름* 에 걸어** 부모 계보의 유일본이
삭제 후보가 됐다. ★**그래서 이 도구는 `_best` 접미사를 보지 않는다.**
프로브의 `_best` 를 지우는 근거는 *"이름이 `_best` 라서"* 가 아니라
★***"그 런이 250스텝이라 품질 판정에 못 쓴다"*** 는 **역할** 이다.

🚫**보호는 이 도구가 하지 않는다.** `cleanup_ckpt.py` 의 `PROTECTED` · `PROTECTED_RE` ·
`derived_protection()`(부모·교사로 읽힌 것)이 **삭제 직전에** 다시 막는다 — 두 겹이다.

## 사용법

    python scripts/ckpt_audit.py             # 무엇이 채워질지 인쇄만
    python scripts/ckpt_audit.py --apply     # checkpoints.tsv 에 행을 추가한다
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "checkpoints.tsv"
CKPT = ROOT / "runs" / "ckpt"
LOGS = ROOT / "runs" / "logs"
NL = chr(10)
TAB = chr(9)
FULL_STEPS = 500      # ★실측 분포가 {20,30,40,250} vs {763,2289,4578} 로 깨끗이 갈린다


def listed():
    out = set()
    if not TSV.is_file():
        return out
    for ln in io.open(TSV, encoding="utf-8").read().split(NL):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        c = ln.split(TAB)
        if len(c) >= 2 and c[0].strip() in ("keep", "hold", "delete"):
            out.add(c[1].strip())
    return out


def steps_of(name):
    """`{stem}.pt` -> `runs/logs/{stem}.json` 의 steps. `_best` 형제는 본체를 본다."""
    stem = name[:-3]
    if stem.endswith("_best"):
        stem = stem[:-5]
    p = LOGS / (stem + ".json")
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("steps")
    except Exception:                                       # noqa: BLE001
        return None


def judge(name):
    if name.startswith("tiny_"):
        return "delete", "tiny 스모크 - run_smoke_check.bat 이 매번 재생성한다"
    st = steps_of(name)
    if st is not None and st < FULL_STEPS:
        return "delete", (f"{st}스텝 프로브 - 품질 판정 사용 금지(기준표 2.3). "
                          f"판정 근거는 역할이지 _best 접미사가 아니다(TSV 규칙 6)")
    if st is None:
        return "hold", "짝 json 이 없다 - 어떤 런인지 모른다. 사람이 확인"
    return "hold", f"{st}스텝 full-train - 축이 닫혔는지는 기계가 모른다. 사람이 판정"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if not CKPT.is_dir() or not TSV.is_file():
        print("  🚫 runs/ckpt 또는 checkpoints.tsv 가 없다.", file=sys.stderr)
        return 2
    have = listed()
    news = sorted(p for p in CKPT.glob("*.pt") if p.name not in have)

    print("=" * 96)
    print(f"  체크포인트 판정 갱신 — 정본 `checkpoints.tsv`")
    print("=" * 96)
    n_disk = len(list(CKPT.glob("*.pt")))
    print(f"  디스크 {n_disk}개 · 표 {len(have)}행 · ★**표에 없는 것 {len(news)}개**")
    if not news:
        print("  ✅ 표가 디스크와 맞다.")
        return 0

    rows, tally, gb = [], {}, {}
    for p in news:
        mb = p.stat().st_size / (1024 ** 2)
        v, why = judge(p.name)
        rows.append((v, p.name, mb, why))
        tally[v] = tally.get(v, 0) + 1
        gb[v] = gb.get(v, 0.0) + mb / 1024

    print()
    for v in sorted(tally, key=lambda k: -gb[k]):
        print(f"  {v:<8} {tally[v]:>4}개  {gb[v]:8.1f} GB")
    print(f"  {'합계':<8} {len(news):>4}개  {sum(gb.values()):8.1f} GB")
    print()
    print("  ⚠️★**hold 가 남는 것이 정상이다** — 축이 닫혔는지는 결과문서를 읽어야 안다.")
    print("  🚫이 도구는 지우지 않는다. `cleanup_ckpt.py` 가 보호 규칙을 한 번 더 건다.")

    if not a.apply:
        print(f"{NL}  [DRY-RUN] `--apply` 를 붙이면 {TSV.name} 에 {len(news)}행을 추가한다.")
        return 0

    src = io.open(TSV, encoding="utf-8").read()
    n0 = len(src)
    add = [f"# ★2026-09-04 자동 판정 {len(news)}행 (scripts/ckpt_audit.py) — "
           f"규칙은 tiny_* 와 steps<500 둘뿐이고 나머지는 hold 다"]
    for v, name, mb, why in rows:
        add.append(TAB.join((v, name, f"{mb:.1f}", why)))
    body = (src.rstrip(NL) + NL + NL.join(add) + NL).encode("utf-8")
    tmp = TSV.with_suffix(".tsv.tmp")
    tmp.write_bytes(body)
    assert tmp.stat().st_size == len(body) and len(body) > n0
    os.replace(tmp, TSV)
    print(f"{NL}  ✅ {TSV.name} 에 {len(news)}행 추가 ({n0} -> {len(body)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
