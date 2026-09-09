#!/usr/bin/env python3
"""A09: LR 복제 제거 뒤 기존 gate 이름을 유지하는 정적 계약 검사.
수치의 정답성은 tests/report_20260909/test_a09_lrm.py에서 별도로 검사한다.
"""
from __future__ import annotations
import ast
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent


def main():
    diag = ast.parse((ROOT / "scripts/diag_lrm_values.py").read_text(encoding="utf-8"))
    helper = ast.parse((ROOT / "tinylm/eval/lrm_diagnostics.py").read_text(encoding="utf-8"))
    failures = []
    if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_lr_factor"
           for n in ast.walk(diag)):
        failures.append("diagnostic에 LR schedule 복제가 다시 생김")
    if not any(isinstance(n, ast.Attribute) and n.attr == "mlp_lrm_wd" for n in ast.walk(diag)):
        failures.append("실제 cfg의 LRM WD를 읽는 경로 없음")
    if not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "history_floor" for n in ast.walk(diag)):
        failures.append("applied LR history를 쓰는 호출 없음")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "history_floor" for n in ast.walk(helper)):
        failures.append("history_floor 정본 없음")
    for failure in failures:
        print(failure)
    if not failures:
        print("LR 복제 없음, cfg WD/history 호출 연결 확인. 수치/품질 검증은 별도.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
