#!/usr/bin/env python3
"""Check an explicit changed-path list against a file-level authorization list.

This tool deliberately does not infer user permission from Git history and does
not scan the repository.  Callers provide every path changed by the just-finished
patch group and every authorized literal path or ``directory/**`` prefix.
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
ENVIRONMENT_PREFIXES = (".agents/", ".codex/")
ENVIRONMENT_FILES = {
    "scripts/wip.py",
    "scripts/new_handoff.py",
    "scripts/handoff_queue.py",
    "scripts/check_change_scope.py",
}
PROTECTED_PREFIX = "datasets/TinyDataset/"


@dataclass(frozen=True)
class Authorization:
    pattern: str
    authority: str


def normalize(raw: str) -> str:
    text = raw.strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    if not text or text.startswith("/") or ".." in PurePosixPath(text).parts:
        raise ValueError(f"path must be repository-relative: {raw!r}")
    return text


def parse_authorization(raw: str) -> Authorization:
    if "=" not in raw:
        raise ValueError("--allow must be PATH=AUTHORITY")
    pattern, authority = raw.split("=", 1)
    pattern = normalize(pattern)
    if not authority.strip():
        raise ValueError(f"authorization has no authority text: {raw!r}")
    if any(token in pattern for token in ("?", "[", "]")):
        raise ValueError("only a literal path or a trailing /** prefix is allowed")
    if "*" in pattern and not pattern.endswith("/**"):
        raise ValueError("wildcards are allowed only as a trailing /** prefix")
    return Authorization(pattern, authority.strip())


def matches(path: str, authorization: Authorization) -> bool:
    pattern = authorization.pattern
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def is_environment_path(path: str) -> bool:
    return path in ENVIRONMENT_FILES or path.startswith(ENVIRONMENT_PREFIXES)


def audit(
    changed: list[str],
    allowed: list[Authorization],
    *,
    environment_approval: str | None,
) -> list[str]:
    errors: list[str] = []
    if not changed:
        return ["no --changed paths were supplied"]
    for path in changed:
        if path == PROTECTED_PREFIX.rstrip("/") or path.startswith(PROTECTED_PREFIX):
            errors.append(f"protected dataset path is never accepted by this checker: {path}")
            continue
        matches_for_path = [entry for entry in allowed if matches(path, entry)]
        if not matches_for_path:
            errors.append(f"changed path is outside the authorization list: {path}")
            continue
        if is_environment_path(path) and not environment_approval:
            errors.append(f"environment behavior path lacks --environment-approval: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="explicit patch-group authorization checker")
    parser.add_argument("--allow", action="append", default=[], metavar="PATH=AUTHORITY")
    parser.add_argument("--changed", action="append", default=[], metavar="PATH")
    parser.add_argument(
        "--environment-approval",
        help="exact user approval reference required for .agents/.codex/workflow files",
    )
    args = parser.parse_args()
    try:
        allowed = [parse_authorization(raw) for raw in args.allow]
        changed = [normalize(raw) for raw in args.changed]
        errors = audit(changed, allowed, environment_approval=args.environment_approval)
    except ValueError as exc:
        print(f"SCOPE_ERROR ValueError: {exc}", file=sys.stderr)
        return 2
    for path in changed:
        hits = [entry for entry in allowed if matches(path, entry)]
        authority = "; ".join(entry.authority for entry in hits) or "NONE"
        print(f"PATH {path} | authority={authority}")
    for error in errors:
        print(f"FAIL {error}")
    print(f"SUMMARY changed={len(changed)} allowed_rules={len(allowed)} errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
