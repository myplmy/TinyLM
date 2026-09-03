#!/usr/bin/env python3
"""★★스모크 로그의 **종료코드를 전수로 세어** 마지막에 한 화면으로 보여준다.

## 왜 이 도구가 생겼나 (2026-09-03 사용자 지시)

> *"현재 스모크테스트에서는 **모든 결과의 종료코드를 사용자가 직접 확인해야** 하는데 (…)
>  종료코드가 한개라도 오류나 특이사항이 있으면 마지막 출력에 **어떤 항목에서 어떤 오류코드와
>  어떤 오류로 종료됐는지 정리해서** 보여주는 스크립트"*

★**그 필요를 사고가 스스로 증명했다.** 2026-09-03 스모크의 마지막 출력은 이랬다:

    총 에러 0건 — 0 이면 계측 계약이 지켜지고 있습니다.
    VERDICT: zero -> the contract holds. Long runs are safe to start.

🚫**팔 27개 중 하나가 `exit 1` 이었는데도** *"장기 런을 시작해도 안전하다"* 를 찍었다.
`check_smoke.py` 의 *총 에러* 는 **계측 필드 계약**만 센다 — **종료코드를 하나도 안 본다.**
**함정 38**(*"인쇄와 판정이 갈라진다"*)의 재발이고, ★**미탐이 오탐보다 비싸다.**

## 무엇을 보나 — 두 가지

| | 무엇 | 왜 |
|---|---|---|
| **A** | ★`exit != 0` 인 팔 — 명령·코드·**마지막 예외 줄** | 사용자가 손으로 세던 것 |
| **B** | ★★`exit 0` 인데 **오류 표지가 있는 팔** | 세션 규칙 *"exit 0 인 것도 있다"* 의 기계화 |

## 🚫이 도구가 하지 않는 것

- **`runlog.py` 를 안 거친 명령은 못 센다.** 배치가 `python ...` 를 직접 부르면 보이지 않는다.
  → ⚠️**스모크에 새 팔을 넣을 때는 반드시 `runlog.py` 를 경유**시킨다.
- **계측 필드 계약을 대신 보지 않는다.** 그것은 `check_smoke.py` 몫이고,
  ★**이 도구는 둘을 한 줄로 합쳐서 판정한다**(둘 다 0 일 때만 "안전").

사용법
    python scripts/summarize_smoke.py                # smoketest_logs 의 최신 스모크 로그
    python scripts/summarize_smoke.py --log <경로>
종료코드 0 = 실패 팔 0개 / 1 = 실패 팔이 있다 / 2 = 로그를 못 찾았다
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGDIR = ROOT / "smoketest_logs"

RE_CMD = re.compile(r"^\[runlog\] cmd=(.+?)\s*$")
RE_END = re.compile(r"^\[runlog\] 종료코드 (\d+)\s")
RE_CONTRACT = re.compile(r"총 에러 (\d+)건")

# ★오류 표지 — exit 0 인 팔에서도 이것이 보이면 특이사항으로 올린다.
#   🚫팔 제목·안내문에 섞이므로 **줄 전체가 표지로 시작하거나 예외 형태일 때만** 센다.
RE_MARK = re.compile(r"^\s*(Traceback \(most recent call last\)|"
                     r"[A-Za-z_.]*(?:Error|Exception)\s*:|"
                     r"\[ERROR\]|\[FAIL\]|🚫\s*실패)")


def newest():
    if not LOGDIR.is_dir():
        return None
    cands = sorted(LOGDIR.glob("*_smoke_*.txt"))
    return cands[-1] if cands else None


def short(cmd: str, n: int = 62) -> str:
    cmd = cmd.replace("python ", "").strip()
    return cmd if len(cmd) <= n else cmd[: n - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None, help="스모크 로그 경로(기본: 최신)")
    a = ap.parse_args()

    path = Path(a.log) if a.log else newest()
    if path is None or not path.is_file():
        print("=" * 96)
        print("  [STOP] 스모크 로그를 못 찾았다 — smoketest_logs/*_smoke_*.txt")
        print("=" * 96)
        return 2

    text = io.open(path, encoding="utf-8", errors="replace").read()
    lines = text.split(chr(10))

    arms, cur, buf = [], None, []
    for ln in lines:
        m = RE_CMD.match(ln)
        if m:
            cur, buf = m.group(1), []
            continue
        if cur is None:
            continue
        m = RE_END.match(ln)
        if m:
            arms.append((cur, int(m.group(1)), buf))
            cur, buf = None, []
        else:
            buf.append(ln)

    failed = [(c, code, b) for c, code, b in arms if code != 0]
    odd = []
    for c, code, b in arms:
        if code != 0:
            continue
        hits = [x.strip() for x in b if RE_MARK.match(x)]
        if hits:
            odd.append((c, hits))

    contract = RE_CONTRACT.search(text)
    n_contract = int(contract.group(1)) if contract else None

    print("=" * 96)
    print("  스모크 종료코드 요약 — %s" % path.name)
    print("=" * 96)
    print("  팔 %d개 (runlog 경유분만)  ·  실패 %d개  ·  exit 0 인데 오류 표지 %d개"
          % (len(arms), len(failed), len(odd)))
    print("  계측 필드 계약(check_smoke): %s"
          % ("총 에러 %d건" % n_contract if n_contract is not None else "🚫이 로그에 없다"))
    print()

    if failed:
        print("  🚫 A. **종료코드가 0 이 아닌 팔**")
        for c, code, b in failed:
            last = ""
            for x in reversed(b):
                if RE_MARK.match(x):
                    last = x.strip()
                    break
            print("     [exit %d]  %s" % (code, short(c)))
            if last:
                print("               -> %s" % last[:110])
        print()

    if odd:
        print("  ⚠️ B. **종료코드는 0 인데 오류 표지가 있는 팔** (exit 0 인 것도 있다)")
        for c, hits in odd:
            print("     %s" % short(c))
            for h in hits[:2]:
                print("               -> %s" % h[:110])
        print()

    # ── 한 줄 판정 — ★두 판정을 합친다 ────────────────────────────
    ok = (not failed) and (n_contract == 0)
    print("  " + "-" * 92)
    if ok:
        print("  ✅ 판정: 실패 팔 0개 **그리고** 계측 계약 0건 — 장기 런을 시작해도 된다.")
        if odd:
            print("     ⚠️단 위 B 항목은 사람이 한 번 읽는다(종료코드로는 안 잡힌다).")
    else:
        why = []
        if failed:
            why.append("실패 팔 %d개" % len(failed))
        if n_contract:
            why.append("계측 계약 %d건" % n_contract)
        if n_contract is None:
            why.append("계약 검사 결과를 로그에서 못 찾았다")
        print("  🚫 판정: **장기 런을 시작하지 않는다** — " + " · ".join(why))
        print("     ★고치고 다시 돌린다. 실패한 팔을 남긴 채 시작한 긴 런은 통째로 버려진다.")
    print("  " + "-" * 92)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
