#!/usr/bin/env python3
"""체크포인트 정리 — checkpoints.tsv delete 판정만 처리한다. GPU 0.

WSL 사용자 실행 경로는 run_cleanup_checkpoints.sh가 호출하는 --interactive다.
한 프로세스 안에서 정확한 파일/크기를 먼저 보여주고 대문자 YES를 받은 뒤
TSV, 부모 참조, inode, 크기, mtime/ctime을 재검증한다. 달라지면 삭제 0건이다.

인자 없이 실행하면 read-only 계획만 인쇄한다. --yes는 Windows BAT 호환
레거시 직접 경로여서 별도 dry-run과 동일 계획을 고정하지 못한다.
WSL에서는 직접 --yes를 사용하지 않는다.
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


def _file_identity(path: Path):
    """Fail closed on links and freeze identity, size and write timestamps."""
    import stat as _stat
    item = path.lstat()
    if not _stat.S_ISREG(item.st_mode):
        raise ValueError(f"cleanup target is not a regular file: {path}")
    return (item.st_dev, item.st_ino, item.st_size,
            item.st_mtime_ns, item.st_ctime_ns)


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--yes", action="store_true", help="구형 직접 실행 경로")
    mode.add_argument("--interactive", action="store_true",
                      help="한 프로세스에서 미리 본 정확한 파일만 YES 후 삭제")
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

    preview = {}
    registry_bytes = None
    if a.interactive:
        if not parse_tsv():
            raise SystemExit("[STOP] interactive cleanup requires populated checkpoints.tsv")
        registry_bytes = TSV.read_bytes()
        preview = {name: _file_identity(CKPT / name) for name in plan}
        if parse_doc() != doc or any(preview[name][2] != disk[name] for name in plan):
            raise SystemExit("[STOP] cleanup plan changed during preview construction")

    W = 78
    print("=" * W)
    # ★★2026-09-04 수정 — **인쇄와 정본이 갈라져 있었다**(R20 · 함정 38).
    #   2026-08-19 에 정본을 TSV 로 옮겼는데 **이 줄만 MD 이름을 찍고 있었다.**
    #   `parse_doc()` 은 `parse_tsv()` 를 먼저 부르므로 실제로 읽는 것은 TSV 다.
    #   -> **실제로 읽은 파일을 찍는다.**
    _src = TSV.name if parse_tsv() else DOC.name
    print("  체크포인트 정리 — 판정 정본:", _src)
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
        if not a.interactive:
            print()
            print("  [DRY-RUN] 아무것도 지우지 않았다. 사용자 실행은 run_cleanup_checkpoints.sh를 쓴다.")
            return 0
        if inconsistent:
            print("[STOP] 판정 불일치가 있어 삭제를 취소한다.")
            return 1
        print()
        print("위 정확한 파일만 삭제합니다. 대문자 YES 외에는 취소합니다.", flush=True)
        try:
            answer = input("delete these files? ")
        except EOFError:
            answer = ""
        if answer != "YES":
            print("[cancel] nothing was deleted.")
            return 0
        if TSV.read_bytes() != registry_bytes or parse_doc() != doc:
            print("[STOP] checkpoints.tsv 판정이 미리보기 이후 바뀌었다. 삭제 0건.")
            return 1
        new_parents = derived_protection()
        for name in plan:
            if name in new_parents or name in guard:
                print(f"[STOP] {name} 이 새 부모/보호 대상이 됐다. 삭제 0건.")
                return 1
            try:
                unchanged = _file_identity(CKPT / name) == preview[name]
            except (OSError, ValueError):
                unchanged = False
            if not unchanged:
                print(f"[STOP] {name} 파일 identity/크기/시각이 바뀌었다. 삭제 0건.")
                return 1

    print("\n  삭제 중...")
    ok, fail, freed = 0, 0, 0
    for n in plan:
        p = CKPT / n
        sz = disk[n]
        try:
            if a.interactive and _file_identity(p) != preview[n]:
                raise RuntimeError("target changed after YES; refusing this file")
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
