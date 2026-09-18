#!/usr/bin/env python3
"""Regression tests for the result-document ownership gate."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_doc_ownership.py")
SPEC = importlib.util.spec_from_file_location("check_doc_ownership", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_fixture(documents: dict[str, str]):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name, text in documents.items():
            write(root / "test_result" / name, text)
        old_root = MODULE.ROOT
        MODULE.ROOT = root
        try:
            return MODULE.check()
        finally:
            MODULE.ROOT = old_root


def main() -> int:
    shared_table = "\n".join(
        f"| standard_field_{index} | N/A | N/A | 학습하지 않은 진단의 공통 재현조건 |"
        for index in range(1, 8)
    )
    errors, warnings, infos = run_fixture({
        "001_first.md": "# 결과 001 — 첫 진단\n\n첫 문서만의 서로 다른 서술 근거가 충분히 길게 들어간다.\n" + shared_table,
        "002_second.md": "# 실험 002 — 둘째 진단\n\n둘째 문서만의 별도 판정 근거가 충분히 길게 들어간다.\n" + shared_table,
    })
    assert errors == [] and warnings == [] and infos == [], (errors, warnings, infos)
    print("[PASS] shared reproducibility tables are not body-copy evidence")

    copied = "\n".join(
        f"복사된 서술 본문 {index}번째 줄은 귀속 검출 길이를 넘기도록 작성한다."
        for index in range(1, 7)
    )
    errors, warnings, _ = run_fixture({
        "001_first.md": "# 001 — 첫 문서\n" + copied,
        "002_second.md": "# 002 — 둘째 문서\n" + copied,
    })
    assert any("[E2]" in error for error in errors), errors
    assert warnings == [], warnings
    print("[PASS] six copied narrative lines remain an E2 error")

    errors, _, _ = run_fixture({"003_wrong.md": "# 결과 004 — 잘못된 소유 번호\n"})
    assert any("[E3]" in error for error in errors), errors
    print("[PASS] mismatched result number remains an E3 error")

    first, second = next(iter(MODULE.ALLOW))
    errors, warnings, infos = run_fixture({
        first: "# 003 — 허용된 첫 문서\n" + copied,
        second: "# 051 — 허용된 둘째 문서\n" + copied,
    })
    assert errors == [] and warnings == [] and len(infos) == 1, (errors, warnings, infos)
    print("[PASS] reviewed allowlist entries are informational, not warning debt")
    print("[PASS] document ownership regression 4/4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
