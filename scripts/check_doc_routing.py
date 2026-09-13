#!/usr/bin/env python3
"""Validate explicitly named changed documents against project routing."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / ".agents" / "project.json"
PROTECTED = "datasets/TinyDataset/"


def parse_pair(raw: str, label: str) -> tuple[str, str]:
    if "=" not in raw:
        raise ValueError(f"{label} must be KEY=VALUE")
    left, right = raw.split("=", 1)
    if not left.strip() or not right.strip():
        raise ValueError(f"{label} needs non-empty KEY and VALUE")
    return left.strip(), right.strip()


def normalize(raw: str) -> str:
    path = Path(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe repository path: {raw}")
    value = path.as_posix()
    if value == PROTECTED.rstrip("/") or value.startswith(PROTECTED):
        raise ValueError(f"protected dataset path rejected: {raw}")
    return value


def validate(documents: list[str], explicit: dict[str, str], *, root: Path = ROOT) -> list[str]:
    data = json.loads((root / ".agents" / "project.json").read_text(encoding="utf-8"))
    routes = data["documentRouting"]
    errors: list[str] = []
    checked_paths: set[str] = set()
    for raw in documents:
        try:
            kind, path_raw = parse_pair(raw, "--document")
            path = normalize(path_raw)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        checked_paths.add(path)
        if kind not in routes:
            errors.append(f"unknown document kind {kind!r}")
            continue
        target = root / path
        if not target.is_file():
            errors.append(f"changed document does not exist: {path}")
            continue
        default = str(routes[kind]["defaultDir"]).rstrip("/") + "/"
        in_default = path.startswith(default)
        authority = explicit.get(path, "").strip()
        if not in_default and not authority:
            errors.append(f"{kind} document is outside {default} without exact-path authority: {path}")
        prefix = str(routes[kind].get("temporaryPrefix", ""))
        if prefix and target.name.lower().startswith(prefix.lower()) and not authority:
            errors.append(f"temporary prefix requires exact-path authority: {path}")
    unused = sorted(set(explicit) - checked_paths)
    if unused:
        errors.append(f"unused exact-path authorities: {', '.join(unused)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", action="append", required=True, help="KIND=repository/relative/path.md")
    parser.add_argument("--explicit-path", action="append", default=[], help="PATH=exact user authority")
    args = parser.parse_args(argv)
    explicit: dict[str, str] = {}
    try:
        for raw in args.explicit_path:
            path, authority = parse_pair(raw, "--explicit-path")
            path = normalize(path)
            if path in explicit:
                raise ValueError(f"duplicate --explicit-path: {path}")
            explicit[path] = authority
        errors = validate(args.document, explicit)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL {type(exc).__name__}: {exc}")
        return 2
    for error in errors:
        print(f"FAIL {error}")
    print(f"RESULT {'FAIL' if errors else 'PASS'} documents={len(args.document)} errors={len(errors)} STRUCTURAL_ONLY")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
