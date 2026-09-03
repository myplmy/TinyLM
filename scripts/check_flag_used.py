#!/usr/bin/env python3
"""★★**선언만 하고 아무도 안 읽는 CLI 플래그**를 잡는다 — torch 없이 `ast` 로만.

## 왜 이 게이트가 생겼나 (2026-09-03, 실제 사고)

`scripts/common_bpb.py` 에 **`--drop-contaminated`** 가 있었다. 도움말은
*"P075 오염 감사에서 걸린 문서를 뺀다"* 라고 **약속**한다. 그런데 그 파일에서
`drop_contaminated` 라는 문자열은 **`add_argument` 한 줄에만** 나온다 —
★**`a.drop_contaminated` 를 읽는 코드가 0곳**이었다.

**결과**: 배치가 그 플래그를 주고 돌렸는데 **출력이 바이트 단위로 같았다**
(문서 4,000개 그대로 — 348개를 뺐다면 3,652 여야 했다). **종료코드 0.**

🚫★**기존 게이트가 왜 못 잡았나** — `check_batch_flags.py` 는
*"배치가 쓰는 플래그가 **파서에 있는가**"* 를 본다. **있다.** 그래서 통과한다.

★**함정 37 의 셋째 얼굴**이다:

| 얼굴 | 표현 | 게이트 |
|---|---|---|
| 첫째 | 필드가 기록된다 ≠ 그 경로가 **실행**된다 | `check_smoke_fields` |
| 둘째 | 파일이 있다 ≠ 그 파일이 **import** 된다 | `check_imports` |
| ★셋째 | 플래그가 파서에 있다 ≠ 그 플래그가 **무언가 한다** | ★**이 파일** |

## 🚫오탐을 피하는 규칙

- 파일이 `vars(a)` · `**vars(` · `asdict(` 를 쓰거나 **네임스페이스를 함수에 통째로 넘기면**
  플래그가 다른 곳에서 소비될 수 있다 → ★**그 파일은 건너뛴다**(정보로만 인쇄).
- `dest=` 가 명시되면 그 이름을 쓴다.
- 읽기로 인정하는 형태: `<ns>.<dest>` 속성 접근 · `getattr(<ns>, "<dest>")` ·
  문자열 `"<dest>"` 가 코드에 등장(딕셔너리 키로 쓰는 경우).

사용법
    python scripts/check_flag_used.py
종료코드 0 = 통과 / 1 = 선언만 하고 안 읽는 플래그가 있다
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ["scripts/*.py", "tinylm/**/*.py", "run100m.py"]

# ★네임스페이스를 통째로 넘기는 신호 — 있으면 그 파일은 판정하지 않는다
OPAQUE = ("vars(", "asdict(", "argparse.Namespace", "**a", "**args")


def dest_of(call: ast.Call):
    """add_argument 호출에서 dest 이름을 뽑는다. 위치 플래그·짧은 옵션만이면 None."""
    for kw in call.keywords:
        if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    best = None
    for arg in call.args:
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            return None                       # 동적 이름 — 판정하지 않는다
        s = arg.value
        if s.startswith("--"):
            best = s[2:].replace("-", "_")    # 긴 옵션이 dest 를 정한다
        elif not s.startswith("-") and best is None:
            best = s.replace("-", "_")        # 위치 인자
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    print("=" * 96)
    print("  check_flag_used — 선언만 하고 아무도 안 읽는 CLI 플래그 (ast 전용)")
    print("=" * 96)

    files = []
    for pat in SCAN:
        files += sorted(ROOT.glob(pat))

    errs, skipped, n_flag, n_file = [], [], 0, 0

    for f in files:
        if not f.is_file():
            continue
        src = io.open(f, encoding="utf-8", errors="replace").read()
        try:
            tree = ast.parse(src, filename=str(f))
        except SyntaxError:
            continue

        # ★상호배타 그룹의 이름을 모은다 — `--check` vs `--apply` 처럼
        #   **한쪽만 읽어도 다른 쪽이 의미를 갖는다**(음의 분기).
        groups = {n.targets[0].id for n in ast.walk(tree)
                  if isinstance(n, ast.Assign) and len(n.targets) == 1
                  and isinstance(n.targets[0], ast.Name)
                  and isinstance(n.value, ast.Call)
                  and isinstance(n.value.func, ast.Attribute)
                  and 'mutually_exclusive' in n.value.func.attr}

        decls = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"):
                d = dest_of(node)
                if not d:
                    continue
                # ★그룹 소속인가 (`g.add_argument(...)`)
                owner = (node.func.value.id
                         if isinstance(node.func.value, ast.Name) else None)
                # ★도움말이 스스로 '예약·미구현' 이라고 밝혔는가
                helptxt = "".join(str(k.value.value) for k in node.keywords
                                  if k.arg == "help"
                                  and isinstance(k.value, ast.Constant))
                inert = any(w in helptxt for w in ("예약", "미구현", "no-op"))
                decls.append((d, node.lineno, owner in groups, inert))
        if not decls:
            continue
        n_file += 1

        if any(sig in src for sig in OPAQUE):
            skipped.append((f, len(decls), "네임스페이스를 통째로 넘긴다"))
            continue

        # ★읽기로 인정하는 이름 집합
        read = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                read.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                read.add(node.value)
            elif isinstance(node, ast.Name):
                read.add(node.id)

        grouped_read = {d for d, _, g, _ in decls if g and d in read}
        for d, ln, in_group, inert in decls:
            n_flag += 1
            if d in read:
                continue
            if inert:                       # 도움말이 스스로 밝혔다
                skipped.append((f, 1, f"`--{d}` 는 도움말에 예약·미구현이라고 적혀 있다"))
                continue
            if in_group and grouped_read:   # 상호배타 그룹의 음의 분기
                skipped.append((f, 1, f"`--{d}` 는 상호배타 그룹 — 형제를 읽으면 의미가 선다"))
                continue
            errs.append((f, ln, d))

    print(f"  ① 파서를 가진 파일 {n_file}개 · 플래그 {n_flag}개 검사"
          + (f" · 판정 보류 {len(skipped)}개 파일" if skipped else ""))
    if a.verbose:
        for f, n, why in skipped:
            print(f"       {f.relative_to(ROOT).as_posix()}  ({n}개) — {why}")

    print()
    if errs:
        print(f"  🚫 선언만 하고 **아무도 안 읽는** 플래그 — **{len(errs)}건**")
        for f, ln, d in errs:
            print(f"    {f.relative_to(ROOT).as_posix()}:{ln}  `--{d.replace('_', '-')}` "
                  f"— ★**`a.{d}` 를 읽는 코드가 없다**. 도움말은 무언가 한다고 약속한다")
        print()
        print("  ★고치는 법 둘: **구현하거나**, 아니면 **도움말에 `미구현` 이라고 적는다.**")
        print("  🚫**조용히 두면 배치가 그 플래그를 주고 돌린다 — 종료코드 0 으로.**")
        return 1

    print("  ✅ 선언된 플래그는 전부 같은 파일 안에서 읽힌다.")
    print("  ⚠️★**'읽는다' 는 '옳게 쓴다' 가 아니다** — 값이 실제로 동작을 바꾸는지는 스모크가 본다(함정 37).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
