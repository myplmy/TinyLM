#!/usr/bin/env python3
"""Result-only raw-log backlink closure for an explicit user/WIP input set.

The manifest lists input_logs independently of mappings. This checker never
discovers logs, reads their contents, or scans reviews. It validates exact
log basenames in the declared result section and verifies file existence.
Do not run it on a user's live queue until the queue lock is lifted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "TINYLM_RESULT_CLOSURE_V1"
RESULT_SCOPE = "test_result"


def _scoped_path(raw, suffix):
    if not isinstance(raw, str) or not raw or chr(92) in raw:
        raise ValueError("path must be a non-empty POSIX relative string")
    posix = PurePosixPath(raw)
    if posix.is_absolute() or ".." in posix.parts or posix.parts[0] != RESULT_SCOPE:
        raise ValueError("path must stay inside test_result")
    if str(posix) != raw:
        raise ValueError("path must be normalized")
    if posix.suffix != suffix:
        raise ValueError(f"path needs suffix {suffix}")
    if len(posix.parts) != 2:
        raise ValueError("only exact top-level test_result files are allowed")
    return raw


def _section_body(document, heading):
    if not isinstance(heading, str) or not heading.startswith("#"):
        raise ValueError("section must be an exact Markdown heading")
    lines = document.splitlines()
    hits = [i for i, line in enumerate(lines) if line == heading]
    if len(hits) != 1:
        raise ValueError(f"section heading count={len(hits)} for {heading!r}")
    start = hits[0]
    level = len(heading) - len(heading.lstrip("#"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if not line.startswith("#"):
            continue
        other = len(line) - len(line.lstrip("#"))
        if other <= level and line[other:other + 1] == " ":
            end = i
            break
    return chr(10).join(lines[start:end])


def _contains_exact_basename(text, basename):
    pos = text.find(basename)
    while pos >= 0:
        before = text[pos - 1] if pos else ""
        after_pos = pos + len(basename)
        after = text[after_pos] if after_pos < len(text) else ""
        token_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
        if (not before or before not in token_chars) and (not after or after not in token_chars):
            return True
        pos = text.find(basename, pos + 1)
    return False


def validate_manifest(manifest, *, read_result, log_exists):
    """Pure validation with injected I/O, allowing no-file synthetic fixtures."""
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest must be object"]
    forbidden = ("review", "consumer")
    if any(any(word in str(key).lower() for word in forbidden) for key in manifest):
        errors.append("review/consumer fields are outside the approved result-only scope")
    if manifest.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    if not manifest.get("session_id") or not manifest.get("wip"):
        errors.append("session_id and wip are required")
    inputs = manifest.get("input_logs")
    mappings = manifest.get("mappings")
    if not isinstance(inputs, list) or not inputs:
        return errors + ["input_logs must be a non-empty independent list"]
    if not isinstance(mappings, list) or not mappings:
        return errors + ["mappings must be a non-empty list"]
    valid_inputs = []
    for raw in inputs:
        try:
            valid_inputs.append(_scoped_path(raw, ".txt"))
        except ValueError as exc:
            errors.append(f"input {raw!r}: {exc}")
    if len(valid_inputs) != len(set(valid_inputs)):
        errors.append("input_logs contains duplicate paths")
    input_set = set(valid_inputs)
    mapped = []
    for index, row in enumerate(mappings):
        if not isinstance(row, dict):
            errors.append(f"mapping[{index}] is not an object")
            continue
        if any(any(word in str(key).lower() for word in forbidden) for key in row):
            errors.append(f"mapping[{index}] contains review/consumer field")
        raw = row.get("log")
        try:
            log = _scoped_path(raw, ".txt")
        except ValueError as exc:
            errors.append(f"mapping[{index}] log: {exc}")
            continue
        mapped.append(log)
        if log not in input_set:
            errors.append(f"mapping[{index}] log was not independently declared")
        if not log_exists(log):
            errors.append(f"mapping[{index}] log file does not exist: {log}")
        status = row.get("status", "RECORDED")
        if status == "EXEMPT":
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                errors.append(f"mapping[{index}] exemption requires a reason")
            continue
        if status != "RECORDED":
            errors.append(f"mapping[{index}] unknown status {status!r}")
            continue
        try:
            result = _scoped_path(row.get("result"), ".md")
            body = _section_body(read_result(result), row.get("section"))
            if not _contains_exact_basename(body, PurePosixPath(log).name):
                errors.append(f"mapping[{index}] exact raw-log basename absent from section")
        except (ValueError, FileNotFoundError, OSError) as exc:
            errors.append(f"mapping[{index}] result/section: {exc}")
    if len(mapped) != len(set(mapped)):
        errors.append("mappings contains duplicate log paths")
    if set(mapped) != input_set:
        errors.append(f"input/mapping coverage differs: missing={sorted(input_set - set(mapped))}"
                      f" extra={sorted(set(mapped) - input_set)}")
    return errors


def self_test():
    log = "test_result/001_log_20260923_fixture.txt"
    doc = "test_result/001_fixture.md"
    base = {"schema": SCHEMA, "session_id": "fixture",
            "wip": "handoff/WIP_fixture.md", "input_logs": [log],
            "mappings": [{"log": log, "result": doc,
                          "section": "## 1. Fixture", "status": "RECORDED"}]}
    reader = lambda path: "## 1. Fixture" + chr(10) + "source: " + Path(log).name
    exists = lambda path: path == log
    assert validate_manifest(base, read_result=reader, log_exists=exists) == []
    missing = dict(base, input_logs=[log, "test_result/002_log_20260923_fixture.txt"])
    assert validate_manifest(missing, read_result=reader, log_exists=exists)
    assert validate_manifest(base, read_result=lambda path: "## 1. Fixture" + chr(10) + "summary only",
                             log_exists=exists)
    outside = dict(base, review_disposition="UPDATED")
    assert any("review" in e for e in validate_manifest(outside, read_result=reader, log_exists=exists))
    print("[PASS] result-only closure fixtures: valid, missing input, missing backlink, review scope")


def _safe_existing(raw):
    scope = ROOT / RESULT_SCOPE
    target = ROOT / raw
    if scope.is_symlink() or target.is_symlink():
        raise ValueError("symlink is not allowed in result closure")
    if not target.resolve().is_relative_to(scope.resolve()):
        raise ValueError("result closure path escapes test_result")
    return target


def _existing_log(raw):
    try:
        return _safe_existing(raw).is_file()
    except (ValueError, OSError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.manifest is None:
        parser.error("--manifest is required unless --self-test")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = validate_manifest(
        manifest,
        read_result=lambda path: _safe_existing(path).read_text(encoding="utf-8"),
        log_exists=_existing_log,
    )
    for error in errors:
        print(f"[FAIL] {error}")
    print(f"SUMMARY result_closure_errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
