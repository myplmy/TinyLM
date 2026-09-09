"""Explicit, non-overwriting artifacts and provenance for reference evaluations."""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.metadata
import json
import math
import platform
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_default(value):
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    if callable(value):
        return f"{value.__module__}:{value.__qualname__}"
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      default=json_default, allow_nan=False)


def digest(value):
    return hashlib.sha256(json_text(value).encode("utf-8")).hexdigest()


def json_write(path, value):
    """Fail rather than overwriting an earlier result."""
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2,
                                default=json_default, allow_nan=False) + "\n")


def jsonl_write(path, records):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json_text(record) + "\n")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def fresh_dir(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def versions(*names):
    result = {"python": platform.python_version(), "platform": platform.platform()}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def source_tree(root):
    """Hash task/scorer code too: a version string alone does not detect local edits."""
    root = Path(root).resolve()
    entries = {}
    for path in sorted(root.rglob("*")):
        tracked = path.suffix in {".py", ".yaml", ".yml", ".json", ".jsonl", ".txt",
                                  ".csv", ".tsv", ".toml", ".cfg", ".jinja", ".j2", ".js", ".java"}
        tracked = tracked or path.name.endswith((".json.gz", ".jsonl.gz"))
        if path.is_file() and tracked:
            if "__pycache__" not in path.parts:
                entries[path.relative_to(root).as_posix()] = sha256_file(path)
    if not entries:
        raise ValueError(f"No source/data files found: {root}")
    return {"root": str(root), "files": entries, "sha256": digest(entries)}


def finite_json(value):
    """Keep unavailable upstream estimates explicit; do not emit nonstandard NaN JSON."""
    if isinstance(value, dict):
        return {str(k): finite_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(v) for v in value]
    if hasattr(value, "tolist"):
        return finite_json(value.tolist())
    if hasattr(value, "item"):
        return finite_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
