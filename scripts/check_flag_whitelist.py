#!/usr/bin/env python3
"""★배치가 써도 되는 플래그인가 — **"존재" 가 아니라 "의도"** 를 본다(2026-09-04 신설).

## 왜 (승인된 제안서 `proposal/done/20260904_배치-파라미터-화이트리스트-approved.md`)

문법 검증은 이미 된다:

| 게이트 | 무엇을 보나 |
|---|---|
| `check_batch_flags` | 배치의 플래그가 **파서에 있는가** |
| `check_flag_used` | 선언만 하고 **아무도 안 읽는** 플래그가 있는가 |

🚫**그런데 파서에 있다고 배치에 써도 되는 것이 아니다.** 실재하는 셋:

| 플래그 | 파서에 | 배치에 쓰면 |
|---|---|---|
| `--drop-contaminated` | ✅있다 | 🚫**미구현**(2026-09-03 실측 — 몸통 0줄, 출력 바이트 동일) |
| `--reuse-attn-on-dup` | ✅있다 | 🚫**기각**(결과 041 §17.4 — 재귀 이득을 전부 잃는다) |
| `--repeat-kv-reuse` | ✅있다 | 🚫**기각**(결과 062 — 대가가 재귀 이득의 5.4배) |

## ★함정 18 을 구조로 피한다

🚫**표를 정본으로 두지 않는다.** 표가 소유하는 것은 **등급과 근거뿐**이고,
**플래그 목록은 파서가 소유**한다. 게이트가 **양방향**으로 대조한다:

- 파서에 있는데 표에 없다 -> **에러**(새 플래그를 넣고 등급을 안 적었다)
- 표에 있는데 파서에 없다 -> **에러**(낡은 행)

★**사용자 요구 — *"신규 파라미터 추가 시 whitelist 도 함께 수정해야 작동"* — 이 그것이다.**

## 등급 넷

| 등급 | 뜻 | `lint_bat` 이 배치에서 보면 |
|---|---|---|
| `ok` | 표준 경로 | ✅통과 |
| `exp` | 실험용(기본 off · 비트 동일) | ⚠️경고 — 계획번호를 함께 적었는지 본다 |
| `dead` | 미구현·무동작 | 🚫**에러** |
| `rejected` | 실험으로 기각됨 | 🚫**에러**(근거 결과번호를 인쇄한다) |

## 사용법

    python scripts/check_flag_whitelist.py            # 양방향 대조
    python scripts/check_flag_whitelist.py --init     # 표 초안 생성(없을 때만)
    python scripts/check_flag_whitelist.py --sync     # 추가된 플래그를 ok 로 덧붙인다(제거는 안 한다)
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

TSV = ROOT / "scripts" / "flag_whitelist.tsv"
SCAN = ["scripts/*.py", "tinylm/**/*.py", "run100m.py"]
GRADES = ("ok", "exp", "dead", "rejected")
NEEDS_EVIDENCE = ("dead", "rejected")
HDR = "flag\tgrade\tevidence\tchecked\tdeclared_in"


def parser_flags():
    """파서가 선언한 **긴 옵션**을 전부 모은다 -> {flag: [file, ...]}"""
    out = {}
    for pat in SCAN:
        for f in sorted(ROOT.glob(pat)):
            try:
                src = io.open(f, encoding="utf-8").read()
                tree = ast.parse(src)
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            rel = f.relative_to(ROOT).as_posix()
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "add_argument"):
                    continue
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                            and arg.value.startswith("--"):
                        out.setdefault(arg.value, [])
                        if rel not in out[arg.value]:
                            out[arg.value].append(rel)
    return out


def read_tsv():
    """-> {flag: (grade, evidence, checked, declared_in)}"""
    if not TSV.is_file():
        return {}
    rows = {}
    for ln in io.open(TSV, encoding="utf-8").read().split("\n"):
        if not ln.strip() or ln.startswith("flag\t") or ln.startswith("#"):
            continue
        c = (ln.split("\t") + ["", "", "", ""])[:5]
        rows[c[0]] = tuple(c[1:5])
    return rows


def write_tsv(rows):
    lines = [HDR]
    for flag in sorted(rows):
        g, ev, ck, di = rows[flag]
        lines.append("\t".join((flag, g, ev, ck, di)))
    body = ("\n".join(lines) + "\n").encode("utf-8")
    tmp = TSV.with_suffix(".tsv.tmp")
    tmp.write_bytes(body)
    assert tmp.stat().st_size == len(body)
    tmp.replace(TSV)


def grade_of(flag):
    """표를 읽어 등급을 준다. 표가 없거나 행이 없으면 `ok` 로 본다(린터가 조용하도록)."""
    r = read_tsv().get(flag)
    return r[0] if r else "ok"


def load():
    """`lint_bat` 이 쓰는 진입점 — {flag: (grade, evidence)}"""
    return {k: (v[0], v[1]) for k, v in read_tsv().items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true", help="표가 없을 때 초안을 만든다")
    ap.add_argument("--sync", action="store_true",
                    help="파서에 새로 생긴 플래그를 `ok` 로 덧붙인다(삭제는 사람이 한다)")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    pf = parser_flags()
    if not pf:
        print("  🚫 파서에서 플래그를 하나도 못 찾았다 — 도구가 고장났다(R19).", file=sys.stderr)
        return 1

    if a.init:
        if TSV.is_file():
            print(f"  🚫 이미 있다: {TSV.name}. `--sync` 를 쓰세요.", file=sys.stderr)
            return 2
        write_tsv({f: ("ok", "", "2026-09-04", ",".join(v)) for f, v in pf.items()})
        print(f"  ✅ 초안 생성 {TSV.name} — {len(pf)}행. **등급을 손질하세요.**")
        return 0

    rows = read_tsv()
    if not rows:
        print(f"  🚫 표가 없다: {TSV.name}. `--init` 으로 만드세요.", file=sys.stderr)
        return 2

    if a.sync:
        add = {f: ("ok", "", "2026-09-04", ",".join(v)) for f, v in pf.items() if f not in rows}
        keep = {f: (rows[f][0], rows[f][1], rows[f][2], ",".join(pf[f]))
                for f in rows if f in pf}
        write_tsv({**keep, **add})
        print(f"  ✅ sync — 추가 {len(add)}개 · 유지 {len(keep)}개 · "
              f"🚫제거 후보 {len(rows) - len(keep)}개(사람이 지운다)")
        return 0

    print("=" * 96)
    print("  플래그 화이트리스트 — 파서 <-> 표 양방향 대조")
    print("=" * 96)

    err = []
    missing = sorted(set(pf) - set(rows))
    stale = sorted(set(rows) - set(pf))
    for f in missing:
        err.append(f"★**표에 없는 새 플래그**: `{f}`  ({', '.join(pf[f])}) — "
                   f"`{TSV.name}` 에 **등급을 적어야** 배치에서 쓸 수 있다")
    for f in stale:
        err.append(f"**낡은 행**: `{f}` 가 파서에 없다 — 표에서 지우세요")
    for f in sorted(set(rows) & set(pf)):
        g, ev, _ck, _di = rows[f]
        if g not in GRADES:
            err.append(f"`{f}`: 모르는 등급 `{g}` — {'/'.join(GRADES)} 중 하나")
        elif g in NEEDS_EVIDENCE and not ev.strip():
            err.append(f"`{f}`: 등급 `{g}` 인데 **근거가 비어 있다** — "
                       f"결과번호를 적으세요(안 적을 거면 `exp`)")

    cnt = {g: sum(1 for f in rows if rows[f][0] == g) for g in GRADES}
    print(f"  파서 {len(pf)}개 · 표 {len(rows)}행 — "
          + " · ".join(f"{g} {cnt.get(g, 0)}" for g in GRADES))
    for g in ("dead", "rejected"):
        for f in sorted(f for f in rows if rows[f][0] == g):
            print(f"    🚫 {g:<9} {f:<26} {rows[f][1]}")
    if a.verbose:
        for f in sorted(f for f in rows if rows[f][0] == "exp"):
            print(f"    ⚠️ exp       {f:<26} {rows[f][1]}")

    print()
    for e in err:
        print(f"  🚫 {e}")
    if err:
        print(f"\n  🚫 {len(err)}건 실패")
        print("  ★**목록은 파서가 소유하고 표는 등급만 소유한다**(함정 18) — "
              "`--sync` 가 추가만 해 준다.")
        return 1
    print("  ✅ 양방향 일치. **등급이 옳은지는 사람이 본다.**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
