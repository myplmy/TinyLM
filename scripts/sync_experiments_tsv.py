#!/usr/bin/env python3
"""★`experiments.tsv` ↔ 디스크 동기화 + **`-done` 배치 삭제 가능 판정**. GPU 0.

## 왜 이 도구가 생겼나 (2026-08-21 사용자 지시)

두 가지가 사람 손에 남아 있었고 둘 다 사고를 냈다:

1. ★**`-done` 삭제 가능 판정을 "이번 세션에 돌린 배치" 에만 했다.**
   그래서 디스크에 남아 있던 `run_P062_stage0b_paired_repeat-done.bat` 과
   `run_P060_stageA2_sdpa_backends-done.bat` 이 **두 세션 연속 보고에서 빠졌다.**
   → ★**이제 디스크의 `-done` 을 **전수** 본다.** 범위를 기억에 맡기지 않는다.

2. ★**사용자가 `-done` 을 지우면 `experiments.tsv` 에 행이 남는다.**
   `queue_menu.py --audit` 가 잡긴 하지만 **고치는 것은 손이었고**,
   손으로 고치다 **엉뚱한 행을 지우면 큐가 깨진다.**
   → ★**이 도구가 행을 "삭제" 하지 않고 **완료 주석 블록으로 이동**한다.** 되돌릴 수 있다.

## 삭제 가능 3조건 (`CLAUDE.md` 폴더정리 절)

    ① 실험 완료           -> 파일명이 `-done`
    ② ★재현 명령이 결과문서 §재현 명령에 **문자열 일치**로 보존
    ③ 재실행 예정 없음     -> **사람이 판단한다.** 이 도구는 ①②만 본다

★**②를 문자열로 대조하는 이유**: 011 §0.5-7 이 `--tag dense --docstats` 를 빠뜨린 채
"보존됨" 이라 적혀 있었고, 그대로 지웠으면 **원래 명령이 소실**될 뻔했다.

사용법
    python scripts/sync_experiments_tsv.py               # 보고만 (아무것도 안 고친다)
    python scripts/sync_experiments_tsv.py --apply       # TSV 고아 행을 주석으로 이동
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "experiments.tsv"
RESULT = ROOT / "test_result"
MARK = "# ⏸ 배치 미작성(선결 있음 — 계획서에 설계만):"


def banner(s, ch="="):
    print("\n" + ch * 100)
    print(f"  {s}")
    print(ch * 100)


def norm(s):
    """캐럿 줄바꿈·연속공백·대소문자·경로 구분자를 지운 비교용 정규형."""
    s = s.replace("^\n", " ").replace("^\r\n", " ")
    s = s.replace("\\", "/").replace("\r", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def batch_commands(p):
    """배치에서 **실제로 실행되는 명령**만 뽑는다(`--note` 줄은 제외)."""
    out = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        t = ln.strip()
        if not t.lower().startswith("python "):
            continue
        if "--note" in t and " -- " not in t:
            continue                       # 제목만 찍는 줄
        if " -- " in t:                    # runlog 경유 -> 뒤쪽이 진짜 명령
            t = t.split(" -- ", 1)[1]
        out.append(t)
    return out


def result_corpus():
    buf = []
    for p in sorted(RESULT.glob("*.md")):
        try:
            buf.append(norm(p.read_text(encoding="utf-8")))
        except Exception:                                       # noqa: BLE001
            pass
    return "\n".join(buf)


def report_done(corpus):
    """디스크의 `-done` **전수**에 대해 ①② 를 판정한다."""
    dones = sorted(ROOT.glob("run_*-done.bat"))
    banner(f"`-done` 배치 전수 판정 — 디스크에 {len(dones)}건")
    if not dones:
        print("  없다.")
        return []
    ok = []
    for p in dones:
        cmds = batch_commands(p)
        miss = [c for c in cmds if norm(c) not in corpus]
        if not cmds:
            print(f"\n  ⚠️ {p.name}\n      실행 명령을 못 찾았다 — **사람이 본다**")
            continue
        if miss:
            print(f"\n  🚫 {p.name}   [보류]")
            print(f"      명령 {len(cmds)}개 중 {len(miss)}개가 결과문서에 없다:")
            for c in miss[:3]:
                print(f"        {c[:110]}")
            print("      → ★**지우면 이 명령이 소실된다.** 결과문서 §재현 명령을 먼저 채운다")
        else:
            print(f"\n  ✅ {p.name}   [삭제 가능]  (명령 {len(cmds)}개 전부 결과문서에 보존)")
            ok.append(p.name)
    print("\n  ⚠️ ③'재실행 예정 없음' 은 **사람이 판단한다.** 이 도구는 ①②만 본다.")
    return ok


def report_orphans(apply_):
    """TSV 에는 있는데 디스크에 없는 배치 행 → 주석 블록으로 **이동**."""
    lines = TSV.read_text(encoding="utf-8").splitlines()
    orphans, keep = [], []
    for ln in lines:
        if not ln.strip() or ln.lstrip().startswith("#"):
            keep.append(ln)
            continue
        c = ln.split("\t")
        if len(c) < 3:
            keep.append(ln)
            continue
        batch = c[2].strip()
        if not batch.endswith(".bat"):
            keep.append(ln)
            continue
        stem = batch[:-4]
        if (ROOT / batch).exists() or (ROOT / f"{stem}-done.bat").exists():
            keep.append(ln)
        else:
            orphans.append((ln, batch, c))

    banner(f"TSV 고아 행 — 표에는 있는데 디스크에 없는 배치 {len(orphans)}건")
    if not orphans:
        print("  없다. 표와 디스크가 일치한다.")
        return 0
    for _ln, batch, c in orphans:
        print(f"  {batch}   (plan {c[1].strip()}, {c[4].strip()}h)")
    if not apply_:
        print("\n  [보고만] `--apply` 를 붙이면 **주석 블록으로 이동**한다(삭제가 아니다).")
        return 0

    # ★삭제가 아니라 이동 — 되돌릴 수 있게 원문을 그대로 주석으로 옮긴다
    note = ["#", "# ★사용자가 -done 을 삭제해 표에서 옮긴 행 (sync_experiments_tsv.py --apply):"]
    for ln, batch, _c in orphans:
        note.append(f"#   {ln}")
    out = keep[:]
    if MARK in "\n".join(out):
        i = next(i for i, l in enumerate(out) if l.startswith(MARK[:20]))
        out = out[:i] + note + [""] + out[i:]
    else:
        out += [""] + note
    TSV.write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print(f"\n  ✅ {len(orphans)}행을 주석으로 이동했다. **지우지 않았다** — 원문이 `#` 뒤에 남아 있다.")
    print("  ⚠️ 이동 후 `python scripts/queue_menu.py --audit` 로 확인하세요.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="experiments.tsv 동기화 + -done 삭제 판정")
    ap.add_argument("--apply", action="store_true", help="고아 행을 주석 블록으로 이동")
    a = ap.parse_args()

    banner("experiments.tsv 동기화 — 범위를 기억에 맡기지 않는다", "#")
    corpus = result_corpus()
    ok = report_done(corpus)
    report_orphans(a.apply)

    print(f"\n{'=' * 100}")
    print(f"  삭제 가능 후보 {len(ok)}건: {' '.join(ok) if ok else '(없음)'}")
    print("  ★삭제는 **사용자가** 한다. 이 도구도, AI 도 파일을 지우지 않는다.")
    print("  ★삭제한 뒤에는 `--apply` 로 표를 정리하고 `queue_menu.py --ids` 를 다시 돌린다.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
