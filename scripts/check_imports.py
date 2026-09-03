#!/usr/bin/env python3
"""★★**저장소 모듈의 `from A import B` 에서 B 가 A 에 정말 있는가** — torch 없이 `ast` 로만.

## 왜 이 게이트가 생겼나 (2026-09-03, 실제 사고)

`scripts/check_return_probs.py:41` 이 **`from tinylm.model.transformer import TMT`** 였다.
그런데 그 모듈의 클래스는 **`TiedMLPTransformer` 하나뿐**이고, `TMT` 라는 이름은
**저장소 어디에도 없었다**(별칭이 삭제된 게 아니라 **존재한 적이 없다**).

★**그 파일은 2026-08-31 에 신설돼 오늘까지 한 번도 import 에 성공하지 못했다.**
그동안 **정적 게이트 22종이 매번 전부 통과했다** — 아무도 import 문을 안 봤기 때문이다.

| 기존 게이트 | 보는 것 | 왜 못 잡았나 |
|---|---|---|
| `check_attrs` | `cfg.X` 오타 | **import 문을 안 본다** |
| `check_call_kwargs` | 호출의 키워드·위치인자 | 대상 함수를 **못 찾으면 건너뛴다** — 없는 이름은 그냥 미해결 |
| `check_smoke` / `check_smoke_fields` | 런 json 의 필드 계약 | **런이 시작조차 못 한 경우**를 안 본다 |

★**함정 37 계열의 새 얼굴**이다. 종전 표현이 *"필드가 기록된다 ≠ 그 경로가 실행된다"* 였다면,
이번은 ★**"파일이 있다 ≠ 그 파일이 import 된다"**.

## 🚫이 게이트가 하지 않는 것

- **import 를 실행하지 않는다.** 소스를 `ast` 로 파싱할 뿐이라 torch·GPU 가 0 이다.
- **외부 패키지를 안 본다.** 대상 모듈이 저장소 안에 **파일로 있을 때만** 검사한다
  (`torch`·`datasets`·`transformers` 는 건너뛴다 — 버전마다 달라 오탐이 된다).
- **이름이 있다 ≠ 그 이름이 옳다.** 같은 이름의 다른 물건일 수 있다.

사용법
    python scripts/check_imports.py            # 전수
    python scripts/check_imports.py --verbose  # 건너뛴 것까지
종료코드 0 = 통과 / 1 = 없는 이름을 import 한다
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ★저장소 안의 모듈만 본다. 최상위 이름이 이 둘 중 하나여야 검사 대상이다.
PKG_ROOTS = ("tinylm", "scripts")

SCAN = ["tinylm/**/*.py", "scripts/*.py", "run100m.py"]


# ────────────────────────────────────────────────────────────────────────────
def parse(path):
    try:
        return ast.parse(io.open(path, encoding="utf-8").read(), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as e:
        return e


def resolve(mod: str):
    """'tinylm.model.transformer' → 저장소 파일 경로. 없으면 None(=외부 패키지)."""
    if not mod:
        return None
    parts = mod.split(".")
    if parts[0] not in PKG_ROOTS:
        return None
    base = ROOT.joinpath(*parts)
    if (base / "__init__.py").exists():          # 패키지
        return base / "__init__.py"
    if base.with_suffix(".py").exists():         # 모듈
        return base.with_suffix(".py")
    return None


def _bind(node, out):
    """한 문(statement)이 **모듈 최상위에 심는 이름**을 모은다."""
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        out.add(node.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            for n in ast.walk(t):
                if isinstance(n, ast.Name):
                    out.add(n.id)
    elif isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            out.add(node.target.id)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            if a.name == "*":
                out.add("*")                      # ★해결 불가 표시
            else:
                out.add(a.asname or a.name.split(".")[0])


def exported(tree, path):
    """대상 모듈이 **밖에서 볼 수 있는 이름**의 집합.

    ⚠️`if TYPE_CHECKING:` · `try/except ImportError:` 안의 정의도 최상위에 심긴다 —
    그래서 If/Try/With 의 본문까지 **재귀로** 훑는다. 🚫함수 **안**은 안 훑는다.
    """
    names = set()

    def walk_body(body):
        for st in body:
            _bind(st, names)
            if isinstance(st, (ast.If, ast.Try, ast.With, ast.AsyncWith)):
                for attr in ("body", "orelse", "finalbody"):
                    walk_body(getattr(st, attr, []) or [])
                for h in getattr(st, "handlers", []) or []:
                    walk_body(h.body)

    walk_body(tree.body)

    # ★패키지면 하위 모듈·하위 패키지도 import 가능한 이름이다
    if path.name == "__init__.py":
        for p in path.parent.iterdir():
            if p.suffix == ".py" and p.name != "__init__.py":
                names.add(p.stem)
            elif p.is_dir() and (p / "__init__.py").exists():
                names.add(p.name)
    return names


# ────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    print("=" * 96)
    print("  check_imports — 저장소 모듈의 `from A import B` 에서 B 가 A 에 있는가 (ast 전용)")
    print("=" * 96)

    files = []
    for pat in SCAN:
        files += sorted(ROOT.glob(pat))
    files = [f for f in files if f.is_file()]

    cache = {}
    errs, skipped, checked = [], [], 0

    for f in files:
        tree = parse(f)
        if not isinstance(tree, ast.Module):
            errs.append((f, 0, f"파일을 파싱하지 못했다 — {tree}"))
            continue

        for node in ast.walk(tree):
            # ── ① from A import B ────────────────────────────────────
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level:                    # 상대 import
                    here = f.parent
                    for _ in range(node.level - 1):
                        here = here.parent
                    rel = here.relative_to(ROOT).as_posix().replace("/", ".")
                    mod = f"{rel}.{mod}" if mod else rel
                tgt = resolve(mod)
                if tgt is None:
                    continue                      # 외부 패키지 — 안 본다
                if tgt not in cache:
                    t2 = parse(tgt)
                    cache[tgt] = (exported(t2, tgt)
                                  if isinstance(t2, ast.Module) else {"*"})
                names = cache[tgt]
                if "*" in names:                  # `import *` 가 있으면 판정 불가
                    skipped.append((f, node.lineno, f"{mod} 에 `import *` 가 있어 판정 불가"))
                    continue
                for al in node.names:
                    if al.name == "*":
                        continue
                    checked += 1
                    if al.name not in names:
                        errs.append((
                            f, node.lineno,
                            f"`from {mod} import {al.name}` — ★**{al.name} 이 그 모듈에 없다**"
                            f"  [있는 이름 예: {', '.join(sorted(n for n in names if not n.startswith('_'))[:4])}]"))

            # ── ② import A.B.C ──────────────────────────────────────
            elif isinstance(node, ast.Import):
                for al in node.names:
                    if al.name.split(".")[0] not in PKG_ROOTS:
                        continue
                    checked += 1
                    if resolve(al.name) is None:
                        errs.append((f, node.lineno,
                                     f"`import {al.name}` — ★**그 모듈 파일이 저장소에 없다**"))

    print(f"  ① 파일 {len(files)}개 · 저장소 모듈 참조 {checked}건 검사")
    if a.verbose and skipped:
        print(f"  ② 판정 불가 {len(skipped)}건 (`import *`)")
        for f, ln, m in skipped:
            print(f"       {f.relative_to(ROOT).as_posix()}:{ln}  {m}")

    print()
    if errs:
        print(f"  🚫 없는 이름을 import 한다 — **{len(errs)}건**")
        for f, ln, m in errs:
            print(f"    {f.relative_to(ROOT).as_posix()}:{ln}  {m}")
        print()
        print("  ★이 게이트는 **이름의 존재**만 본다 — 그 이름이 옳은 물건인지는 사람이 본다.")
        return 1

    print("  ✅ 저장소 안에서 해결되는 import 는 전부 실재하는 이름이다.")
    print("  🚫외부 패키지(torch·datasets·transformers)는 **일부러 안 본다** — 버전마다 달라 오탐이 된다.")
    print("  ⚠️정적은 *'이름이 있는가'*, 동적(`run_smoke_check.bat`)은 *'그 경로가 도는가'* 를 본다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
