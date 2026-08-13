#!/usr/bin/env python3
"""문서 상대링크 검사 — 파일 개명 후 **깨진 링크가 남았는지** 본다.

## 왜 필요한가 (2026-08-13)

결과 문서는 **결론이 바뀌면 제목이 바뀐다**(`ai_dev_tool/03` §8). 개명 자체는 쉬운데
**참조를 빠뜨리기 쉽다** — 특히 `test_result/실험목록.md` 는 **같은 번호의 행이 여럿**
(041 / 041+ / 041++)이라 한 행만 고치고 나머지를 남기는 사고가 난다.

2026-08-13 실사에서 **깨진 링크 26건**이 발견됐다. 대부분 `-done` 접미사가 붙은 뒤
링크를 안 고친 것이었다. 수동으로는 못 잡는다.

## 무엇을 보는가

`docs/ test_plan/ test_result/ ai_dev_tool/ handoff/ CLAUDE.md` 안의
**상대 마크다운 링크**가 실제 파일을 가리키는지.

- ★`--fix` 를 주면 **`-done` 접미사 변형을 자동 해결**한다(같은 이름의 실제 파일을 찾는다)
- 외부 URL·앵커(`#`)·플레이스홀더(`{...}`, `...`)는 건너뛴다

⚠️ **한계**: 링크가 **존재하는 파일**을 가리키는지만 본다.
**옳은 파일**인지는 모른다.

사용:
    python scripts/check_links.py            # 검사만
    python scripts/check_links.py --fix      # -done 변형 자동 교정
    종료코드 = 깨진 링크 수
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIRS = ("docs", "test_plan", "test_result", "ai_dev_tool", "handoff")
LINK = re.compile(r"\]\(([^)#][^)]*?)\)")
SKIP = ("http://", "https://", "mailto:")


def _targets():
    out = []
    for d in TARGET_DIRS:
        out += sorted((ROOT / d).rglob("*.md"))
    cm = ROOT / "CLAUDE.md"
    if cm.exists():
        out.append(cm)
    return out


def _index():
    """파일명 → 실제 경로. `-done` 접미사를 뗀 형태로도 찾을 수 있게 넣는다."""
    idx = {}
    for d in TARGET_DIRS:
        for f in (ROOT / d).rglob("*"):
            if not f.is_file():
                continue
            idx.setdefault(f.name, f)
            stem = re.sub(r"-done(_[a-z_]+)?(\.\w+)$", r"\2", f.name)
            idx.setdefault(stem, f)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="-done 변형을 자동 교정")
    a = ap.parse_args()

    idx = _index()
    bad, legacy, fixed = [], [], 0
    for md in _targets():
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
            if (md.parent / tgt).exists():
                continue
            name = Path(tgt).name
            cand = idx.get(name)
            if cand is None:
                base = name.rsplit(".", 1)
                if len(base) == 2:
                    for k, v in idx.items():
                        if k.startswith(base[0] + "-done"):
                            cand = v
                            break
            if cand is not None and a.fix:
                rel = os.path.relpath(cand, md.parent).replace("\\", "/")
                txt = txt.replace(f"]({raw})", f"]({rel})")
                fixed += 1
            else:
                hint = f"  -> 후보: {cand.name}" if cand is not None else ""
                line = f"{md.relative_to(ROOT)}  ->  {tgt}{hint}"
                # ★`handoff/` 는 **그 시점의 기록**이다. 개명 뒤에도 고치지 않는다
                #   (ai_dev_tool/03 §8.4) — 고치면 "그때 무엇을 알았나" 가 사라진다.
                (legacy if str(md).replace("\\", "/").find("/handoff/") >= 0
                 else bad).append(line)
        if a.fix and txt != orig:
            md.write_text(txt, encoding="utf-8")

    W = 96
    print("=" * W)
    print("  문서 상대링크 검사")
    print("=" * W)
    if a.fix:
        print(f"  자동 교정 {fixed}건")
    if bad:
        print(f"\n  🚫 깨진 링크 {len(bad)}건")
        for b in bad:
            print(f"    {b}")
    else:
        print("\n  ✅ 깨진 링크 0건")
    if legacy:
        print(f"\n  [I] handoff/ 의 옛 이름 참조 {len(legacy)}건 — "
              f"**고치지 않는다**(ai_dev_tool/03 §8.4, 당시 기록)")
        for b in legacy:
            print(f"    {b}")
    print("\n  ⚠️ 존재 여부만 본다. **옳은 파일인지는 사람이 본다.**")
    print("=" * W)
    return len(bad)


if __name__ == "__main__":
    sys.exit(main())
