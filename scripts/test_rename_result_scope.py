#!/usr/bin/env python3
"""Codex text tools must not enumerate forbidden environment sources."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


def _load(name: str):
    module_path = Path(__file__).resolve().with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"{name}_scope_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RENAME = _load("rename_result")
CONTROL = _load("check_control_chars")
LINKS = _load("check_links")


def _relative(paths, root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in paths if path is not None}


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_name:
        root = Path(temp_name)
        (root / "CLAUDE.md").write_text("forbidden", encoding="utf-8")
        (root / "README.md").write_text("shared", encoding="utf-8")
        (root / "AGENTS.md").write_text("shared", encoding="utf-8")
        (root / ".claude").mkdir()
        (root / ".claude" / "hidden.md").write_text("forbidden", encoding="utf-8")
        (root / "datasets" / "TinyDataset").mkdir(parents=True)
        (root / "datasets" / "TinyDataset" / "secret.md").write_text(
            "forbidden", encoding="utf-8"
        )
        (root / "docs").mkdir()
        (root / "docs" / "visible.md").write_text("shared", encoding="utf-8")
        (root / "ai_dev_tool" / "Codex").mkdir(parents=True)
        (root / "ai_dev_tool" / "00_rules.md").write_text("forbidden", encoding="utf-8")
        (root / "ai_dev_tool" / "Codex" / "00_rules.md").write_text("allowed", encoding="utf-8")

        old_roots = (RENAME.ROOT, CONTROL.ROOT, LINKS.ROOT, LINKS.PROTECTED_ROOT)
        RENAME.ROOT = root
        CONTROL.ROOT = root
        LINKS.ROOT = root
        LINKS.PROTECTED_ROOT = root / "datasets" / "TinyDataset"
        try:
            rename_found = _relative(RENAME._targets(), root)
            control_found = _relative(CONTROL._targets(), root)
            link_found = _relative(LINKS._targets(), root)
            link_found.update(_relative(LINKS._index().values(), root))
        finally:
            RENAME.ROOT, CONTROL.ROOT, LINKS.ROOT, LINKS.PROTECTED_ROOT = old_roots

    assert "README.md" in rename_found
    assert "AGENTS.md" in control_found
    assert "docs/visible.md" in link_found
    for found in (rename_found, control_found, link_found):
        assert "ai_dev_tool/Codex/00_rules.md" in found
        assert "CLAUDE.md" not in found
        assert ".claude/hidden.md" not in found
        assert "ai_dev_tool/00_rules.md" not in found
        assert "datasets/TinyDataset/secret.md" not in found
    print("[PASS] Codex text tool scopes exclude forbidden environment sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
