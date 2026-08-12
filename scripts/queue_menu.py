#!/usr/bin/env python3
"""`run_queue.bat` 의 두뇌 — **배치 목록을 하드코딩에서 메타데이터로 옮긴다.** GPU 0.

## 왜 있나 (사용자 지시 2026-08-11)

> *"run_queue.bat 가 하드코딩되어있기보다 ... 실험용 배치파일의 메타데이터를 가진 텍스트 파일을
>  확인해서 사용자가 원하는 순서대로 queue 를 설정할 수 있는 구조로 개선했으면 좋겠음.
>  claude 가 실험계획 배치파일을 작성하고 메타데이터만 갱신하면 사용자는 하드코딩 되지 않은
>  run_queue.bat 를 자유롭게 활용가능할 것으로 보임."*

종전 `run_queue.bat` 은 메뉴와 `:RESOLVE` 의 `if` 사슬에 **파일명을 박아** 두었다.
실험이 끝나 `-done` 이 붙거나 새 배치가 생기면 **배치 파일을 고쳐야** 했다.

**이제 진실의 원천은 `experiments.tsv` 하나다.**

## 왜 파이썬인가 — cmd 로는 불가능하다

이 저장소는 `.bat` 에서 **`%` 를 금지**한다(lint 규칙 3). 그래서 **`for /f` 로 파일을 읽을 수 없다**
(`for %%a in ...` 이 `%` 를 쓴다). 목록을 읽어 분배하는 일은 **파이썬이 해야 한다.**

## 세 가지 모드

    --list              메뉴를 찍는다. 디스크에 있고 `-done` 이 아닌 배치만
    --build "0 1 3"     선택을 검증하고 `runs/_queue_plan.bat` 을 **생성**한다
    --audit             표 ↔ 디스크 불일치를 잡는다(양방향). 종료코드 = 문제 수

`--build` 가 만드는 파일은 `call ...` + `if errorlevel 1 echo [WARN] ... - continuing` 뿐이다
— **`ai_dev_tool/03` §6 규칙 2 를 기계가 지킨다**(사람이 잊을 여지가 없다).

⚠️ **생성 파일은 `runs/` 에 둔다**(gitignore). 최상위에 두면 `lint_bat.py` 가 검사 대상으로 오인하고
   `-done` 판정 대상으로도 보인다.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "experiments.tsv"
PLAN = ROOT / "runs" / "_queue_plan.bat"

COLS = ["prio", "plan", "batch", "gpu", "hours", "alone", "watch", "note"]
GPU_LABEL = {"Y": "학습", "D": "진단", "N": "없음"}


def load():
    """TSV 를 읽어 (행 목록, 경고 목록) 을 돌려준다."""
    if not TSV.exists():
        raise SystemExit(f"[STOP] {TSV.name} 이 없다. 메타데이터가 없으면 큐를 만들 수 없다.")
    rows, warn = [], []
    for ln, raw in enumerate(TSV.read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        f = raw.split("\t")
        f = [x.strip() for x in f]
        if f[0] == "prio":                 # 헤더
            continue
        if len(f) < len(COLS):
            warn.append(f"L{ln} 열이 {len(f)}개다(필요 {len(COLS)}). TAB 구분인지 확인: {s[:50]}")
            continue
        r = dict(zip(COLS, f[:len(COLS)]))
        try:
            r["prio_n"] = int(r["prio"])
        except ValueError:
            warn.append(f"L{ln} prio 가 정수가 아니다: {r['prio']!r}")
            r["prio_n"] = 999
        try:
            r["hours_n"] = float(r["hours"])
        except ValueError:
            r["hours_n"] = 0.0
        r["line"] = ln
        p = ROOT / r["batch"]
        r["exists"] = p.exists()
        # `-done` 은 파일명이 바뀌므로 원본이 없을 때만 확인한다
        stem = r["batch"][:-4] if r["batch"].endswith(".bat") else r["batch"]
        r["done"] = any(Path(g).exists() for g in glob.glob(str(ROOT / (stem + "-done*.bat"))))
        rows.append(r)
    rows.sort(key=lambda x: (x["prio_n"], x["line"]))
    return rows, warn


def available(rows):
    """메뉴에 올릴 것 = 디스크에 있고 `-done` 이 아닌 것."""
    return [r for r in rows if r["exists"]]


def cmd_list(rows, warn):
    W = 100
    print("=" * W)
    print("  TinyLM 실험 큐 — 메타데이터: experiments.tsv")
    print("=" * W)
    av = available(rows)
    if not av:
        print("  실행 가능한 배치가 없다. experiments.tsv 와 최상위 .bat 을 확인할 것.")
    else:
        print(f"  {'id':>3}  {'계획':<7}{'배치':<40}{'GPU':<5}{'시간':>6}  비고")
        print("  " + "-" * (W - 4))
        for i, r in enumerate(av):
            flag = []
            if r["alone"].upper() == "Y":
                flag.append("단독")
            if r["watch"].upper() == "Y":
                flag.append("★감시")
            h = f"{r['hours_n']:.1f}h" if r["hours_n"] >= 1 else f"{r['hours_n']*60:.0f}분"
            print(f"  {i:>3}  {r['plan']:<7}{r['batch']:<40}"
                  f"{GPU_LABEL.get(r['gpu'].upper(), r['gpu']):<5}{h:>6}  "
                  f"{('[' + '·'.join(flag) + '] ') if flag else ''}{r['note']}")
        print("  " + "-" * (W - 4))
        tot = sum(r["hours_n"] for r in av)
        print(f"  전부 돌리면 약 {tot:.1f}시간")
    # 표에는 있는데 디스크에 없는 것 = 완료됐거나 아직 안 만든 것
    miss = [r for r in rows if not r["exists"]]
    if miss:
        print()
        print("  메뉴에 없는 항목(디스크에 파일이 없다):")
        for r in miss:
            why = "완료(-done)" if r["done"] else "★배치 미작성"
            print(f"    {r['plan']:<7}{r['batch']:<40}{why}  — {r['note']}")
    for w in warn:
        print(f"  [경고] {w}")
    print()
    print("  입력: 돌릴 id 를 한 줄에 공백으로. 예)  0 1     / 그냥 ENTER 면 취소")
    print("=" * W)
    return 0


def cmd_build(rows, pick: str):
    av = available(rows)
    ids = [t for t in pick.replace(",", " ").split() if t]
    if not ids:
        print("[queue] 입력이 없다. 취소.")
        return 2
    chosen, bad = [], []
    for t in ids:
        if not t.isdigit() or int(t) >= len(av):
            bad.append(t)
            continue
        chosen.append(av[int(t)])
    for t in bad:
        print(f"[queue] [SKIP] 알 수 없는 id: {t}")
    if not chosen:
        print("[queue] 유효한 id 가 없다. 취소.")
        return 2

    print()
    print("=" * 100)
    print("  실행 계획")
    print("=" * 100)
    tot = 0.0
    for n, r in enumerate(chosen, 1):
        h = f"{r['hours_n']:.1f}h" if r["hours_n"] >= 1 else f"{r['hours_n']*60:.0f}분"
        tag = []
        if r["alone"].upper() == "Y":
            tag.append("단독 실행 — 다른 GPU 작업 금지")
        if r["watch"].upper() == "Y":
            tag.append("★앞부분을 눈으로 확인할 것")
        print(f"  {n}. {r['batch']}   ({r['plan']}, {h})")
        print(f"     {r['note']}")
        for x in tag:
            print(f"     ⚠️ {x}")
        tot += r["hours_n"]
    print("  " + "-" * 96)
    print(f"  합계 약 {tot:.1f}시간")
    if any(r["batch"] == "run_smoke_check.bat" for r in chosen):
        if chosen[0]["batch"] != "run_smoke_check.bat":
            print("  ⚠️ 스모크가 첫 번째가 아니다. 코드를 고쳤다면 맨 앞에 두는 것이 맞다.")
    else:
        print("  ⚠️ 스모크(id 0)가 없다. **코드를 고쳤다면 반드시 넣을 것**(2026-07-31 사고).")
    print("=" * 100)

    PLAN.parent.mkdir(parents=True, exist_ok=True)
    L = ["@echo off",
         "REM ===== queue_menu.py 가 생성한 파일. 손으로 고치지 말 것. =====",
         "REM ai_dev_tool/03 section 6: 큐는 call 만 한다. 이 파일이 그 규칙을 기계로 지킨다.",
         ""]
    for r in chosen:
        b = r["batch"]
        L += [f"echo.",
              f"echo =================================================================",
              f"echo [queue] starting {b}",
              f"time /t",
              f"echo =================================================================",
              f"call {b}"]
        if b == "run_smoke_check.bat":
            # ★스모크만 큐를 멈춘다 — 깨진 트리에 시간을 태우지 않는다
            L += ["if errorlevel 1 goto QSMOKEBAD"]
        else:
            L += [f"if errorlevel 1 echo [WARN] {b} returned an error - continuing"]
        L += [f"echo [queue] {b} done", "time /t", ""]
    L += ["exit /b 0", "", ":QSMOKEBAD",
          "echo.",
          "echo [STOP] smoke check failed. Nothing else was run.",
          "echo   Read the [VERIFY] lines in smoketest_logs and fix before queuing again.",
          "exit /b 3", ""]
    PLAN.write_bytes(("\r\n".join(L)).encode("ascii", errors="replace"))
    print(f"[queue] 계획 파일 생성: {PLAN.relative_to(ROOT)}  ({len(chosen)}개)")
    return 0


def cmd_audit(rows, warn):
    """표 ↔ 디스크 양방향 대조. **메타데이터 갱신을 잊는 것이 이 구조의 유일한 실패 모드다.**"""
    W = 100
    print("=" * W)
    print("  experiments.tsv 감사 — 표와 디스크가 일치하는가")
    print("=" * W)
    listed = {r["batch"] for r in rows}
    on_disk = {os.path.basename(p) for p in glob.glob(str(ROOT / "run_*.bat"))}
    # ★스케줄러 자신은 실험이 아니다 — 표에 넣으면 자기를 call 하게 된다
    SELF = {"run_queue.bat"}
    live = {b for b in on_disk if "-done" not in b} - SELF
    err = 0

    only_disk = sorted(live - listed)
    if only_disk:
        err += len(only_disk)
        print("  ★표에 없는 배치(메타데이터 누락 — Claude 가 추가해야 한다):")
        for b in only_disk:
            print(f"    {b}")
    only_tsv = sorted(r["batch"] for r in rows if not r["exists"] and not r["done"])
    if only_tsv:
        print("  표에만 있는 배치(아직 안 만들었거나 이름이 바뀌었다 — 오류는 아니다):")
        for b in only_tsv:
            print(f"    {b}")
    done = sorted(r["batch"] for r in rows if r["done"])
    if done:
        print("  완료(-done)로 판정돼 메뉴에서 빠진 것:")
        for b in done:
            print(f"    {b}")
    for w in warn:
        err += 1
        print(f"  [형식 오류] {w}")
    print("  " + "-" * (W - 4))
    print(f"  총 문제 {err}건" + ("" if err else " — 통과"))
    print("  ⚠️ 이 감사는 **표와 파일의 존재**만 본다. 우선순위가 옳은지, note 가 정확한지는 보증하지 않는다.")
    print("=" * W)
    return err


def main():
    ap = argparse.ArgumentParser(description="run_queue.bat 의 메타데이터 기반 두뇌")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--build", metavar="IDS")
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()
    rows, warn = load()
    if a.audit:
        return cmd_audit(rows, warn)
    if a.build is not None:
        return cmd_build(rows, a.build)
    return cmd_list(rows, warn)


if __name__ == "__main__":
    sys.exit(main())
