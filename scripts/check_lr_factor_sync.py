#!/usr/bin/env python3
"""★정적 게이트 — **LR factor 정본·호환 wrapper·복제가 같은 계약인가.**(torch 0 · GPU 0)

## 왜 이 게이트가 생겼나 (2026-09-05)

`scripts/diag_lrm_values.py` 가 **순수 weight-decay 바닥**을 계산하려면 LR 스케줄이 필요하다.
정본은 `tinylm/train/anneal_schedule.py::lr_factor`다. 학습기는 기존 하위 도구 호환을 위해
`trainer.py::_lr_factor` 이름을 wrapper로 남기고, 진단 도구는 torch 없이 돌기 위해 수식을 복제한다.

🚫★**복제는 함정 18 이다** — *"적용 대상 집합을 두 곳에서 정의"*. 이 저장소는 그 실수로
평가가 죽은 적이 있다(`config.REPEAT_MODES`). 복제를 남기려면 **기계 대조**가 함께 있어야 한다.

## 무엇을 검사하나

정본 `lr_factor`와 진단 복제 `_lr_factor`의 **소스를 `ast` 로 떼어내** 각각 컴파일하고,
**표준 조건 격자 전부**에서 값을 비교한다. `1e-12` 를 넘는 차이가 하나라도 있으면 에러.
`trainer.py::_lr_factor`가 같은 인자를 정본 `lr_factor`로 그대로 전달하는지도 AST로 검사한다.

    sched   : cosine · wsd · stable · decay
    steps   : 250 · 2289 · 4578 · 9156
    decay_frac : 0.1 · 0.2 · 0.3
    s       : 각 steps 를 균등 분할한 40점 + 경계(0, warm-1, warm, steps-1)

🚫**"두 함수가 글자까지 같은가" 를 보지 않는다** — 주석·이름은 달라도 되고,
**값이 갈리는 것만** 사고다.

사용:  python scripts/check_lr_factor_sync.py
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = [
    ("tinylm/train/anneal_schedule.py", "lr_factor", "정본"),
    ("scripts/diag_lrm_values.py", "_lr_factor", "복제"),
]
TOL = 1e-12


def extract(rel: str, function_name: str):
    """파일에서 순수 함수 정의 하나만 떼어내 컴파일한다."""
    p = ROOT / rel
    if not p.is_file():
        return None, f"파일이 없다: {rel}"
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            mod = ast.Module(body=[node], type_ignores=[])
            ast.fix_missing_locations(mod)
            ns = {"math": math}
            exec(compile(mod, rel, "exec"), ns)          # noqa: S102 — 우리 저장소 파일만
            return ns[function_name], None
    return None, f"{rel} 에 `def {function_name}` 이 없다"


def check_trainer_wrapper() -> str | None:
    """Ensure the legacy trainer name is a transparent call to the canonical function."""
    rel = "tinylm/train/trainer.py"
    path = ROOT / rel
    if not path.is_file():
        return f"파일이 없다: {rel}"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        (node for node in tree.body
         if isinstance(node, ast.FunctionDef) and node.name == "_lr_factor"),
        None,
    )
    if function is None:
        return f"{rel} 에 `def _lr_factor` 가 없다"
    expected = ["s", "warm", "steps", "sched", "decay_frac"]
    body = function.body
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return "trainer._lr_factor가 단일 return wrapper가 아니다"
    call = body[0].value
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        return "trainer._lr_factor가 직접 함수 호출을 반환하지 않는다"
    actual = [arg.id for arg in call.args if isinstance(arg, ast.Name)]
    if call.func.id != "lr_factor" or actual != expected or len(call.args) != len(expected):
        return (
            "trainer._lr_factor가 정본 lr_factor에 다섯 인자를 그대로 전달하지 않는다: "
            f"callee={call.func.id!r} args={actual!r}"
        )
    if call.keywords:
        return "trainer._lr_factor wrapper에 예상하지 않은 keyword 인자가 있다"
    return None


def main() -> int:
    fns, fails = [], []
    wrapper_error = check_trainer_wrapper()
    if wrapper_error:
        fails.append(f"★{wrapper_error}")
    for rel, function_name, role in SRC:
        f, err = extract(rel, function_name)
        if err:
            fails.append(f"★{err}")
        else:
            fns.append((rel, function_name, role, f))

    if len(fns) < 2:
        for m in fails:
            print(f"  🚫 {m}")
        print("  🚫★**두 정의를 다 못 찾아 대조하지 못했다** — R19: 잰 것이 0 이면 통과가 아니다.")
        return 1

    if fails:
        for message in fails:
            print(f"  🚫 {message}")
        return 1

    (r0, n0, _, f0), (r1, n1, _, f1) = fns[0], fns[1]
    n_cmp, worst, worst_at = 0, 0.0, None
    for sched in ("cosine", "wsd", "stable", "decay"):
        for steps in (250, 2289, 4578, 9156):
            warm = 0 if sched == "decay" else max(5, min(steps // 10, 100))
            pts = sorted({0, max(warm - 1, 0), warm, steps - 1}
                         | {round(i * (steps - 1) / 39) for i in range(40)})
            for decay_frac in (0.1, 0.2, 0.3):
                for s in pts:
                    a = f0(s, warm, steps, sched, decay_frac)
                    b = f1(s, warm, steps, sched, decay_frac)
                    n_cmp += 1
                    d = abs(a - b)
                    if d > worst:
                        worst, worst_at = d, (sched, steps, decay_frac, s, a, b)

    print("=" * 96)
    print(f"  LR factor 동기 검사 — {r0}::{n0} (정본) vs {r1}::{n1} (복제)")
    print("=" * 96)
    print(f"  비교 {n_cmp:,}점 · 최대 차 {worst:.3e} (허용 {TOL:.0e})")
    print("  trainer.py::_lr_factor → lr_factor 투명 wrapper 계약 PASS")
    if worst > TOL:
        sc, st, df, s, a, b = worst_at
        print(f"  🚫★**두 함수가 다른 값을 낸다** — sched={sc} steps={st} "
              f"decay_frac={df} s={s}: 정본 {a!r} vs 복제 {b!r}")
        print("     ★복제를 정본에 맞춘다. 🚫반대로 하지 않는다(정본은 학습이 실제로 쓰는 쪽이다).")
        return 1
    print("  ✅ 두 정의가 격자 전 점에서 일치한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
