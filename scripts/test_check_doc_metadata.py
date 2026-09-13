#!/usr/bin/env python3
"""Regression tests for check_doc_metadata.py (stdlib only)."""
from __future__ import annotations

import datetime as dt
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_doc_metadata.py")
SPEC = importlib.util.spec_from_file_location("check_doc_metadata", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


POLICY = """record_type\tname\trequired_date_fields\trequired_fields\tgit_policy\tmtime_policy\tleft\tright\tequal_fields\treason
type\tlive\tlatest_update\ttype\tgit_not_older_than\toptional\t\t\t\tlive
type\tdraft\tauthored\ttype,status\tnone\tignore\t\t\t\tdraft
type\tsnapshot\tauthored|as_of\ttype\tnone\tignore\t\t\t\tsnapshot
pair\tpair\t\t\t\t\tai_dev_tool/00_WORKING_RULES.md\tai_dev_tool/00_작업규약_한글판.md\tdate\tmirror
"""

FIXTURE_GIT_DATE = "2026-09-13T12:00:00+0900"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    # The fixture metadata is pinned to 2026-09-13.  Without a pinned commit
    # date, the nominally "normal" case starts failing merely because the test
    # is run on the next day; that tests the wall clock, not stale metadata.
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = FIXTURE_GIT_DATE
    env["GIT_COMMITTER_DATE"] = FIXTURE_GIT_DATE
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", env=env
    )
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)


def make_repo() -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    policy = root / "docs" / "doc_metadata_policy.tsv"
    write(policy, POLICY)
    metadata = "> **Last updated**: 2026-09-13 · **Document type**: live\n"
    write(root / "ai_dev_tool" / "00_WORKING_RULES.md", "# EN\n\n" + metadata)
    write(root / "ai_dev_tool" / "00_작업규약_한글판.md", "# KO\n\n" + metadata)
    write(
        root / "ai_dev_tool" / "draft.md",
        "# Draft\n\n> **작성일**: 2026-09-12 · **문서 유형**: draft · **상태**: 검토 중\n",
    )
    write(
        root / "ai_dev_tool" / "snapshot.md",
        "# Snapshot\n\n> **기준일**: 2026-09-11 · **문서 유형**: snapshot\n",
    )
    write(root / "ai_dev_tool" / "Codex" / "README.md", "# Codex\n\n" + metadata)
    git(root, "init")
    git(root, "add", "ai_dev_tool", "docs")
    git(root, "-c", "user.name=metadata-test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")
    return temporary, root, policy


def run_case(name: str, action, expected_fragment: str | None = None) -> None:
    temporary, root, policy = make_repo()
    try:
        action(root)
        errors, warnings, findings = MODULE.validate(
            root,
            policy,
            scope="all",
            today=dt.date(2026, 9, 13),
            as_of=dt.date(2026, 9, 13),
            mtime_mode="off",
        )
        if expected_fragment is None:
            assert not errors, errors
            assert len(findings) == 5
        else:
            assert any(expected_fragment in error for error in errors), (name, errors)
        print(f"[PASS] {name}")
    finally:
        temporary.cleanup()


def main() -> int:
    run_case("normal", lambda root: None)
    run_case(
        "new file is auto-discovered",
        lambda root: write(root / "ai_dev_tool" / "new.md", "# Missing metadata\n"),
        "missing document type",
    )
    run_case(
        "pair date mismatch",
        lambda root: write(
            root / "ai_dev_tool" / "00_작업규약_한글판.md",
            "# KO\n\n> **최신 갱신일자**: 2026-09-12 · **문서 유형**: live\n",
        ),
        "date differs",
    )
    run_case(
        "dirty live requires as-of date",
        lambda root: write(
            root / "ai_dev_tool" / "00_WORKING_RULES.md",
            "# changed\n\n> **Last updated**: 2026-09-12 · **Document type**: live\n",
        ),
        "before --as-of",
    )

    temporary, root, policy = make_repo()
    try:
        path = root / "ai_dev_tool" / "00_WORKING_RULES.md"
        old = dt.datetime(2026, 9, 10, 12, 0).timestamp()
        os.utime(path, (old, old))
        errors, warnings, _ = MODULE.validate(
            root, policy, scope="all", today=dt.date(2026, 9, 13), mtime_mode="warn"
        )
        assert not errors and warnings
        errors, _, _ = MODULE.validate(
            root, policy, scope="all", today=dt.date(2026, 9, 13), mtime_mode="strict"
        )
        assert any("local mtime" in error for error in errors)
        print("[PASS] mtime warn and strict")
    finally:
        temporary.cleanup()
    temporary, root, policy = make_repo()
    try:
        write(root / "ai_dev_tool" / "legacy-broken.md", "# Missing metadata\n")
        errors, warnings, findings = MODULE.validate(
            root, policy, today=dt.date(2026, 9, 13), mtime_mode="off"
        )
        assert not errors and not warnings, errors
        assert [finding.path for finding in findings] == ["ai_dev_tool/Codex/README.md"]
        print("[PASS] default Codex scope excludes legacy Claude documents")
    finally:
        temporary.cleanup()

    print("[PASS] check_doc_metadata 6/6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
