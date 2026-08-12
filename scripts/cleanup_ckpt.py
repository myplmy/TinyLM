#!/usr/bin/env python3
"""체크포인트 정리 — **판정 목록 문서를 진실의 원천으로 삼아** 삭제한다. GPU 0.

## 왜 배치에 파일명을 박지 않았나

**함정 18: "적용 대상 집합을 두 곳에서 정의"** — 결과 016 §13·§14 가 같은 실수를 2회 냈다.
삭제 목록을 `.bat` 에 68줄 박아 두면 문서와 배치가 **따로 늙는다.** 문서에서 판정을 바꿔도
배치는 옛 목록을 지운다. 그래서 **집합은 한 곳에서만 정한다** —
`docs/20260813_체크포인트_정리목록.md` 의 표가 정본이고 이 스크립트는 그것을 읽는다.

(배치에서 `for /f` 로 파일을 읽을 수 없다는 사정도 있다 — 이 저장소는 `.bat` 에서
`%` 를 금지한다(lint 규칙 3). 목록을 읽어 분배하는 일은 파이썬이 해야 한다.)

## 안전장치 넷

1. **기본은 dry-run.** `--yes` 없이는 한 파일도 지우지 않는다.
2. **화이트리스트 방식.** 문서에서 `삭제 가능` 으로 판정된 것만 후보다.
   `보존`·`보류`·목록에 없는 파일은 **건드릴 수 없다**(오탈자로 지워지는 경로가 없다).
3. **정본 보호 하드코딩.** 부모/교사와 `--kd-best` 대상은 목록이 뭐라 하든 거부한다.
   ★2026-08-14 에 `m100_ko-en_300M_dense_best.pt` 가 실수로 지워졌다. 그 재발을 막는 줄이다.
4. **삭제 전 존재 확인 + 사후 대조.** 지운 개수·바이트를 세어 계획과 맞는지 본다.

사용:
    python scripts/cleanup_ckpt.py              # 계획만 인쇄(아무것도 안 지운다)
    python scripts/cleanup_ckpt.py --yes        # 실제 삭제
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "20260813_체크포인트_정리목록.md"
CKPT = ROOT / "runs" / "ckpt"

# ★목록이 뭐라 하든 절대 지우지 않는다. 이유를 함께 적는다.
PROTECTED = {
    "m100_ko-en_300M_dense.pt":
        "정본 부모/KD 교사 — 이 저장소의 거의 모든 tied 런이 여기서 초기화됐다",
    "m100_ko-en_300M_dense_best.pt":
        "--kd-best 대상. ★2026-08-14 실수 삭제된 파일 — 복구되면 다시 지키기 위해 남긴다",
    "m100_ko-en_300M_tied.pt":
        "정본 tied 기준선(태그 없음)",
}


def parse_doc():
    """판정 표를 읽어 {파일명: (MB, 판정)} 로 돌려준다."""
    if not DOC.exists():
        raise SystemExit(f"[STOP] 판정 문서가 없다: {DOC.name}. 집합의 정본이 없으면 안 지운다.")
    out = {}
    for f, mb, verdict in re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([\d.]+)\s*\|\s*(.+?)\s*\|",
                                     DOC.read_text(encoding="utf-8"), re.M):
        if "삭제 가능" in verdict:
            v = "delete"
        elif "보존" in verdict:
            v = "keep"
        elif "보류" in verdict:
            v = "hold"
        else:
            v = "?"
        out[f] = (float(mb), v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="실제로 지운다(없으면 dry-run)")
    a = ap.parse_args()

    doc = parse_doc()
    if not CKPT.exists():
        raise SystemExit(f"[STOP] {CKPT} 가 없다.")
    disk = {p.name: p.stat().st_size for p in CKPT.glob("*.pt")}

    plan, blocked, gone, unlisted = [], [], [], []
    for name, (_, v) in doc.items():
        if v != "delete":
            continue
        if name in PROTECTED:
            blocked.append(name)
        elif name in disk:
            plan.append(name)
        else:
            gone.append(name)
    for name in disk:
        if name not in doc:
            unlisted.append(name)

    W = 78
    print("=" * W)
    print("  체크포인트 정리 — 판정 정본:", DOC.name)
    print("=" * W)
    print(f"  디스크    {len(disk):>4}개  {sum(disk.values())/2**30:8.1f} GB")
    print(f"  삭제 대상 {len(plan):>4}개  {sum(disk[n] for n in plan)/2**30:8.1f} GB")
    print(f"  이미 없음 {len(gone):>4}개  (앞선 정리에서 지워진 것)")
    keep_n = sum(1 for _, (_, v) in doc.items() if v == "keep")
    hold_n = sum(1 for _, (_, v) in doc.items() if v == "hold")
    print(f"  보존      {keep_n:>4}개 / 보류 {hold_n}개  — 후보에 들어가지 않는다")
    if blocked:
        print(f"\n  ★보호 규칙이 막은 것 {len(blocked)}개(목록이 삭제라 해도 안 지운다):")
        for n in blocked:
            print(f"    {n}\n      -> {PROTECTED[n]}")
    if unlisted:
        print(f"\n  ⚠️ 목록에 없는 디스크 파일 {len(unlisted)}개 — **판정되지 않았으므로 안 건드린다.**")
        for n in sorted(unlisted)[:20]:
            print(f"    {n}")
        print("    → 새 런이 생겼다면 정리 문서에 행을 추가할 것(양방향 대조가 이 구조의 요점이다).")

    if not plan:
        print("\n  지울 것이 없다.")
        return 0

    print(f"\n  {'MB':>7}  파일")
    print("  " + "-" * (W - 4))
    for n in sorted(plan, key=lambda x: -disk[x]):
        print(f"  {disk[n]/2**20:7.0f}  {n}")
    print("  " + "-" * (W - 4))
    print(f"  합계 {sum(disk[n] for n in plan)/2**30:.1f} GB / {len(plan)}개")

    if not a.yes:
        print("\n  [DRY-RUN] 아무것도 지우지 않았다. 실제로 지우려면 --yes 를 붙인다.")
        return 0

    print("\n  삭제 중...")
    ok, fail, freed = 0, 0, 0
    for n in plan:
        p = CKPT / n
        sz = disk[n]
        try:
            p.unlink()
            ok += 1
            freed += sz
        except Exception as e:
            fail += 1
            print(f"    [실패] {n}: {type(e).__name__}: {e}")
    print(f"\n  삭제 {ok}개 / 실패 {fail}개 / 회수 {freed/2**30:.1f} GB")
    left = sum(p.stat().st_size for p in CKPT.glob("*.pt"))
    print(f"  남은 체크포인트 {len(list(CKPT.glob('*.pt')))}개  {left/2**30:.1f} GB")
    if fail:
        print("  ⚠️ 실패분은 파일이 열려 있을 수 있다(학습이 도는 중인지 확인).")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
