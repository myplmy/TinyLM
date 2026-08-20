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

# ★★2026-08-20 신설 — **G3 부모 계보 패턴 보호**
#
#   왜: 2026-08-20 에 `m100_ko-en_300M_denseb_best.pt` 가 TSV 에서 `delete` 로 판정됐고
#   사용자가 손으로 고쳤다. 원인은 **규칙을 "역할" 이 아니라 "이름" 에 걸었기 때문**이다 —
#   *"`_best` 는 하향 편향이라 판정에 안 쓴다(결과 015)"* 는 **비교용 산출물**에 대해서는
#   옳지만, **부모/교사 계보**에는 적용되면 안 된다. `dense_best` 는 이미 한 번 사라졌고
#   `denseb_best` 는 그 재생성본의 유일한 best 다. **지우면 재학습 말고는 복구가 없다.**
#
#   그래서 이름 하나를 더 적는 대신 **계보 전체를 정규식으로** 지킨다.
#   `dense`·`denseb`·`densec`… 어느 재생성본이 생겨도 자동으로 걸린다.
PROTECTED_RE = [
    (r"^m100_ko-en_300M_dense[a-z]*(_best)?\.pt$",
     "★부모 dense 계보(재생성본 포함). dense_best 가 이미 한 번 사라졌다 — 재학습 외 복구 불가"),
]


def derived_protection():
    """★★G1 — **다른 런이 부모/교사로 쓴 체크포인트**를 로그에서 뽑아 자동 보호한다.

    손으로 적은 목록은 늙는다(함정 18). `runs/logs/*.json` 의 `init_from_src`·`kd_teacher`
    는 **그 런이 실제로 무엇을 읽었는지의 기록**이므로, 여기 이름이 있으면
    **그 파일을 지우는 순간 그 런이 재현 불가능**해진다. `_best` 형제도 함께 지킨다.
    """
    import json as _json
    logs = ROOT / "runs" / "logs"
    out = {}
    if not logs.exists():
        return out
    for p in logs.glob("*.json"):
        try:
            d = _json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        for k in ("init_from_src", "kd_teacher"):
            v = d.get(k)
            if not v:
                continue
            name = Path(str(v)).name
            why = f"★{p.stem} 이 이것을 {k} 로 읽었다 — 지우면 그 런이 재현 불가"
            out.setdefault(name, why)
            if name.endswith(".pt") and not name.endswith("_best.pt"):
                out.setdefault(name[:-3] + "_best.pt", why + " (best 형제)")
    return out


TSV = ROOT / "checkpoints.tsv"


def parse_tsv():
    """★2026-08-19 — 판정 정본을 **TSV** 로 옮겼다(사용자 지시, `experiments.tsv` 와 같은 구조).

    왜: 마크다운 표는 **사람이 읽으라고** 있는 것이고 파서가 서식에 끌려다닌다.
    그리고 `keep` 의 **이유(어느 실험이 쓰는가)** 를 적을 자리가 없었다 —
    그게 없으면 다음 세션이 *"왜 남겼는지"* 를 모르고 지운다.

    ⚠️**여기 없는 파일은 후보가 아니다**(화이트리스트). 새 체크포인트의 기본은 `hold` 다.
    """
    out = {}
    if not TSV.exists():
        return out
    for ln in TSV.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        c = ln.split("\t")
        if len(c) < 3 or c[0] == "verdict":
            continue
        v = c[0].strip()
        if v not in ("keep", "hold", "delete"):
            continue
        try:
            mb = float(c[2])
        except ValueError:
            mb = 0.0
        out[c[1].strip()] = (mb, v)
    return out


def parse_doc():
    """판정 표를 읽어 {파일명: (MB, 판정)} 로 돌려준다.

    ★**TSV 가 있으면 그것이 정본**이다(`parse_tsv`). 이 함수는 구 문서 호환용으로 남는다.
    """
    tsv = parse_tsv()
    if tsv:
        return tsv
    if not DOC.exists():
        raise SystemExit(f"[STOP] 판정 정본이 없다: {TSV.name} 도 {DOC.name} 도. 안 지운다.")
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

    # ★보호 집합을 **세 경로에서** 모은다. 손목록 하나만 두면 늙는다(함정 18).
    guard = dict(PROTECTED)                      # G0 손목록
    for n, why in derived_protection().items():  # G1 로그에서 파생
        guard.setdefault(n, why)
    for name in list(doc):                       # G3 계보 정규식
        for pat, why in PROTECTED_RE:
            if re.match(pat, name):
                guard.setdefault(name, why)

    # ★★G2 — **판정 일관성**: 본체가 `hold`(미판정)인데 `_best` 만 `delete` 면 막는다.
    #   `hold` 는 *"사람이 아직 판정 안 했다"* 는 뜻이다. 본체가 미판정이면 그 best 도 미판정이다.
    #   ★이것이 denseb_best 사고를 **이름을 몰라도** 잡는 규칙이다.
    inconsistent = []
    for name, (_, v) in doc.items():
        if v != "delete" or not name.endswith("_best.pt"):
            continue
        base = name[:-len("_best.pt")] + ".pt"
        bv = doc.get(base, (0, None))[1]
        if bv == "hold":
            inconsistent.append((name, base))
            guard.setdefault(name, f"★판정 불일치 — 본체 {base} 가 hold(미판정)인데 best 만 delete 다")

    plan, blocked, gone, unlisted = [], [], [], []
    for name, (_, v) in doc.items():
        if v != "delete":
            continue
        if name in guard:
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
            print(f"    {n}\n      -> {guard[n]}")
    if inconsistent:
        print(f"\n  🚫★★판정 불일치 {len(inconsistent)}건 — **TSV 를 고쳐야 한다.**")
        for n, base in inconsistent:
            print(f"    {n}  (본체 {base} = hold)")
        print("    → 본체가 미판정이면 best 도 미판정이다. **한 런의 판정은 한 번에 정한다.**")
        print("    → 2026-08-20 denseb_best 사고의 재발 방지 규칙(G2)이다.")
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
