#!/usr/bin/env python3
"""문서 상대링크 검사 — 파일 개명 후 **깨진 링크가 남았는지** 본다.

## 왜 필요한가 (2026-08-13)

결과 문서는 **결론이 바뀌면 제목이 바뀐다**(`ai_dev_tool/Codex/02_핸드오프_규약.md`). 개명 자체는 쉬운데
**참조를 빠뜨리기 쉽다** — 특히 `test_result/실험목록.md` 는 **같은 번호의 행이 여럿**
(041 / 041+ / 041++)이라 한 행만 고치고 나머지를 남기는 사고가 난다.

2026-08-13 실사에서 **깨진 링크 26건**이 발견됐다. 대부분 `-done` 접미사가 붙은 뒤
링크를 안 고친 것이었다. 수동으로는 못 잡는다.

## 무엇을 보는가

`docs/ test_plan/ test_result/ ai_dev_tool/Codex/ handoff/` 안의
**상대 마크다운 링크**가 실제 파일을 가리키는지.

- ★`--fix` 를 주면 **상태 접미사 변형을 자동 해결**한다(같은 이름의 유일한 실제 파일을 찾는다)
- ★`--fix-handoff-renames` 는 사용자가 과거 링크 목적지의 단순 개명 치환을 명시적으로
  승인한 경우에만 쓴다. 기본값은 역사 기록을 보존한다.
- 외부 URL·앵커(`#`)·플레이스홀더(`{...}`, `...`)는 건너뛴다
- 보호 데이터 링크는 경로 문자열만 검사 대상에 남기고 대상 파일 존재 여부는 읽지 않는다
- 봉인된 계획 사본은 `link_snapshot_origins.tsv`에 기록한 지문 및 원래 위치로 검사한다
- 봉인된 사본에 있는 예전 작업원장 경로는 정식 `-done` 종결 파일을 확인한다

⚠️ **한계**: 링크가 **존재하는 파일**을 가리키는지만 본다.
**옳은 파일**인지는 모른다.

사용:
    python scripts/check_links.py            # 검사만
    python scripts/check_links.py --fix      # 상태 접미사 변형 자동 교정
    python scripts/check_links.py --fix-handoff-renames  # 명시 승인된 역사 링크 목적지만 교정
    종료코드 = 오류가 있으면 1, 없으면 0. 자세한 건수는 출력으로 확인한다.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIRS = ("docs", "test_plan", "test_result", "ai_dev_tool/Codex", "handoff")
LINK = re.compile(r"\]\(([^)#][^)]*?)\)")
SKIP = ("http://", "https://", "mailto:")
PROTECTED_ROOT = ROOT / "datasets" / "TinyDataset"
SNAPSHOT_INDEX = ROOT / "scripts" / "link_snapshot_origins.tsv"


def _snapshot_origins() -> dict[Path, tuple[str, Path]]:
    origins = {}
    with SNAPSHOT_INDEX.open(encoding="utf-8", newline="") as source:
        rows = csv.DictReader(source, delimiter="\t")
        for row in rows:
            copy, origin = (PurePosixPath(row[key]) for key in ("snapshot", "origin"))
            digest = row["sha256"]
            if (copy.parts[:2] != ("test_result", "evidence")
                    or origin.parts[:1] != ("test_plan",)
                    or ".." in copy.parts or ".." in origin.parts
                    or copy.suffix != ".md" or origin.suffix != ".md"
                    or ROOT / copy in origins or not re.fullmatch(r"[a-f0-9]{64}", digest)):
                raise ValueError(f"invalid snapshot origin row: {row}")
            origins[ROOT / copy] = (digest, ROOT / origin)
    return origins


def _matches_snapshot(data: bytes, digest: str) -> bool:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == digest


def _closed_archive_wip(origin: Path, target: str) -> bool:
    """Recognize the in-place WIP rename for a link in a sealed plan copy."""
    path = Path(os.path.abspath(origin.parent / target))
    if (path.parent != ROOT / "handoff"
            or not re.fullmatch(r"WIP_\d{8}[a-z]?_작업원장\.md", path.name)):
        return False
    closed = path.with_name(path.stem + "-done.md")
    return not closed.is_symlink() and closed.is_file()


def _targets():
    out = []
    for d in TARGET_DIRS:
        out += sorted((ROOT / d).rglob("*.md"))
    return out


# ★상태 접미사 정본 — `proposal/README.md` §2 와 Codex 02 규약이 쓰는 것.
#   🚫목록을 두 곳에 두지 않는다(함정 18).
STATUS_SUFFIXES = (
    "approved-on-going",
    "done",
    "approved",
    "rejected",
    "conditional",
    "superseded",
    "absorbed",
    "완료",
)


# ★★2026-09-08(2차) — **색인 범위는 검사 범위보다 넓다.**
#   🚫`proposal/` 이 색인에 없어서 `-approved` 후보를 **하나도 못 찾았다** —
#   접미사 목록을 넓혀도 그 폴더를 안 보면 소용이 없다(초판이 자동교정 0건이었던 이유).
#   ⚠️검사 범위(`TARGET_DIRS`)는 안 넓힌다 — 넓히면 새 경고가 쏟아지고
#   **아무도 안 읽는 경고는 미탐과 같다**(2026-09-06 사용자 지시).
INDEX_DIRS = TARGET_DIRS + ("proposal", "review_request")


def _record_candidate(index: dict[str, Path | None], key: str, path: Path) -> None:
    """Keep only unique filename candidates; ambiguous names must not be auto-fixed."""
    if key not in index:
        index[key] = path
    elif index[key] != path:
        index[key] = None


def _index():
    """파일명 → 실제 경로. `-done` 접미사를 뗀 형태로도 찾을 수 있게 넣는다."""
    idx = {}
    for d in INDEX_DIRS:
        for f in (ROOT / d).rglob("*"):
            if not f.is_file():
                continue
            _record_candidate(idx, f.name, f)
            stem = re.sub(r"-done(_[a-z_]+)?(\.\w+)$", r"\2", f.name)
            _record_candidate(idx, stem, f)
    return idx


def _status_candidate(index: dict[str, Path | None], name: str) -> Path | None:
    candidate = index.get(name)
    if candidate is not None:
        return candidate
    base = name.rsplit(".", 1)
    if len(base) != 2:
        return None
    for suffix in STATUS_SUFFIXES:
        for separator in ("-", "_"):
            candidate = index.get(f"{base[0]}{separator}{suffix}.{base[1]}")
            if candidate is not None:
                return candidate
    return None


def _is_protected_target(source: Path, target: str) -> bool:
    """Classify a link lexically without touching the protected data tree."""
    normalized = target.replace("\\", "/")
    windows_repo = re.match(r"^[A-Za-z]:/TinyLM/(.*)$", normalized, re.IGNORECASE)
    if windows_repo:
        candidate = Path(os.path.abspath(ROOT / windows_repo.group(1)))
    elif re.match(r"^[A-Za-z]:/", normalized):
        return False
    else:
        candidate = Path(os.path.abspath(source.parent / normalized))
    try:
        candidate.relative_to(PROTECTED_ROOT)
        return True
    except ValueError:
        return False


def _write_requested(fix: bool, fix_handoff_renames: bool) -> bool:
    """Both explicit repair modes must persist their own scoped rewrites."""
    return fix or fix_handoff_renames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="비-handoff 상태 접미사 변형을 자동 교정")
    ap.add_argument(
        "--fix-handoff-renames",
        action="store_true",
        help="명시 승인된 경우 handoff의 유일한 상태 개명 후보만 교정",
    )
    a = ap.parse_args()

    idx = _index()
    try:
        origins = _snapshot_origins()
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"[E] 계획 사본 원본표: {error}")
        return 1
    bad, legacy, snapshot_errors = [], [], []
    fixed = protected_skipped = archived_links = archived_wip_links = 0
    for md in _targets():
        origin = md
        if md in origins:
            digest, origin = origins[md]
            if md.is_symlink() or origin.is_symlink() or not origin.is_file():
                snapshot_errors.append(f"{md.relative_to(ROOT)}  ->  원래 계획 경로 또는 사본 유형 불일치")
                continue
            data = md.read_bytes()
            if not _matches_snapshot(data, digest):
                snapshot_errors.append(f"{md.relative_to(ROOT)}  ->  봉인 지문 불일치")
                continue
            txt = data.decode("utf-8", errors="replace")
        else:
            txt = md.read_text(encoding="utf-8", errors="replace")
        orig = txt
        for m in list(LINK.finditer(txt)):
            raw = m.group(1)
            tgt = raw.split("#")[0].strip()
            if not tgt or tgt.startswith(SKIP) or "{" in tgt or "..." in tgt:
                continue
            # ★확장자가 없으면 링크가 아니다 — `](self.ln2(x)` 같은 **코드 조각**이
            #   마크다운 링크처럼 보이는 경우다. 초판이 이걸 2건 오탐했다.
            if not re.search(r"\.(md|txt|py|bat|json|png|pdf|tsv|csv)$", tgt):
                continue
            if _is_protected_target(origin, tgt) or _is_protected_target(md, tgt):
                protected_skipped += 1
                continue
            if (md.parent / tgt).exists():
                continue
            if origin != md and (origin.parent / tgt).exists():
                archived_links += 1
                continue
            if origin != md and _closed_archive_wip(origin, tgt):
                archived_wip_links += 1
                continue
            name = Path(tgt).name
            cand = _status_candidate(idx, name)
            # ★`handoff/` 는 **그 시점의 기록**이다. 개명 뒤에도 고치지 않는다
            #   (Codex 02 핸드오프 규약) — 고치면 "그때 무엇을 알았나" 가 사라진다.
            # 🚫★2026-09-08(2차) — 종전에는 이 규칙이 **보고에만** 걸려 있고
            #   `--fix` 는 handoff 도 고쳤다. 색인에 `proposal/` 을 넣자마자
            #   **과거 핸드오프 9개가 한 번에 고쳐졌다**(되돌렸다).
            #   ★인쇄가 *"고치지 않는다"* 라고 말하는데 동작이 고치는 것 = 함정 38.
            is_handoff = str(md).replace("\\", "/").find("/handoff/") >= 0
            should_fix = origin == md and cand is not None and (
                (a.fix and not is_handoff) or (a.fix_handoff_renames and is_handoff)
            )
            if should_fix:
                rel = os.path.relpath(cand, md.parent).replace("\\", "/")
                txt = txt.replace(f"]({raw})", f"]({rel})")
                fixed += 1
            else:
                hint = f"  -> 후보: {cand.name}" if cand is not None else ""
                line = f"{md.relative_to(ROOT)}  ->  {tgt}{hint}"
                (legacy if is_handoff else bad).append(line)
        if _write_requested(a.fix, a.fix_handoff_renames) and txt != orig:
            md.write_text(txt, encoding="utf-8")

    W = 96
    print("=" * W)
    print("  문서 상대링크 검사")
    print("=" * W)
    if a.fix:
        print(f"  자동 교정 {fixed}건")
    elif a.fix_handoff_renames:
        print(f"  handoff 단순 개명 교정 {fixed}건")
    if bad:
        print(f"\n  🚫 깨진 링크 {len(bad)}건")
        for b in bad:
            print(f"    {b}")
    else:
        print("\n  ✅ 깨진 링크 0건")
    if legacy:
        print(f"\n  [I] handoff/ 의 옛 이름 참조 {len(legacy)}건 — "
              f"**고치지 않는다**(Codex 02 핸드오프 규약, 당시 기록)")
        for b in legacy:
            print(f"    {b}")
    if archived_links:
        print(f"\n  [I] 봉인된 계획 사본의 원래 위치에서 확인한 링크 {archived_links}건")
    if archived_wip_links:
        print(f"  [I] 봉인된 계획 사본에서 종결 원장으로 확인한 링크 {archived_wip_links}건")
    for error in snapshot_errors:
        print(f"  [E] {error}")
    if protected_skipped:
        print(f"\n  [I] 보호 데이터 대상 존재 확인 생략 {protected_skipped}건")
    print("\n  ⚠️ 존재 여부만 본다. **옳은 파일인지는 사람이 본다.**")
    print("=" * W)
    return int(bool(bad or snapshot_errors))


if __name__ == "__main__":
    sys.exit(main())
