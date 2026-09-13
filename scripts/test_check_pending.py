#!/usr/bin/env python3
"""Regression tests for the structured W2 exemption and completed-batch W3 check."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_pending.py")
SPEC = importlib.util.spec_from_file_location("check_pending", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def w2_for(body: str, plan: str | None = None) -> list[str]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        write(root / "proposal" / "done" / "fixture-approved.md", body)
        if plan is not None:
            write(root / "test_plan" / f"{plan}_fixture.md", "# plan\n")
        old_root, old_grace = MODULE.ROOT, MODULE.GRACE_DAYS
        # A just-created file can appear a few clock ticks in the future on
        # Windows.  A negative grace disables the production mtime exemption
        # deterministically for this fixture.
        MODULE.ROOT, MODULE.GRACE_DAYS = root, -1.0
        try:
            return MODULE.w2()
        finally:
            MODULE.ROOT, MODULE.GRACE_DAYS = old_root, old_grace


def main() -> int:
    assert w2_for(
        "> **실험번호**: `PNone`\n"
        "> **실험계획 비대상 사유**: 정적 도구 계약이며 학습 실험이 아니다.\n"
    ) == []
    print("[PASS] exact PNone plus reason is exempt")

    rejected = (
        "> **실험번호**: `PNone`\n",
        "> **실험계획 비대상 사유**: 도구 계약\n",
        "> **실험번호**: `P091`\n> **실험계획 비대상 사유**: 도구 계약\n",
        "> **실험번호**: `PNone`\n> **실험계획 비대상 사유**: 미정\n",
        "계획서 없이 도구 작업으로 끝났다.\n",
    )
    for body in rejected:
        assert w2_for(body) == ["fixture-approved.md"], body
    print("[PASS] incomplete, wrong, placeholder, and free-text exemptions are rejected")

    # Keep the synthetic ID out of the repository-wide plan-number scanner.
    plan_id = "P" + "123"
    assert w2_for(f"{plan_id} implementation proposal\n", plan=plan_id) == []
    print("[PASS] linked experiment plan remains accepted")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        write(root / "test_result" / "014_log_20260731_P030-cachecheck.txt", "done\n")
        write(root / "test_result" / "014_log_20260731_P030-cachegate.txt", "done\n")
        write(root / "test_result" / "014_log_20260731_P030-stage2B.txt", "done\n")
        old_root = MODULE.ROOT
        MODULE.ROOT = root
        try:
            assert MODULE._ran("run_P030_cachecheck.bat")
            assert MODULE._ran("run_P030_cachegate.bat")
            assert MODULE._ran("run_P030_stage2B_infer.bat")
            assert not MODULE._ran("run_P030_missing.bat")
        finally:
            MODULE.ROOT = old_root
    print("[PASS] terminal and underscored stage names find completed logs")
    print("[PASS] check_pending regression 4/4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
