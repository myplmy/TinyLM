#!/usr/bin/env python3
"""Synthetic preview binding regression; never unlinks a real checkpoint."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import cleanup_ckpt as cleanup


def trial(change):
    with TemporaryDirectory(prefix="tiny-ckpt-preview-") as temp:
        root = Path(temp)
        ckpt = root / "ckpt"
        ckpt.mkdir()
        target = ckpt / "demo.pt"
        target.write_bytes(b"example")
        registry = root / "checkpoints.tsv"
        registry.write_text("delete demo.pt", encoding="utf-8")
        record = {"demo.pt": (0.1, "delete")}
        parent_calls = [0]

        def parents():
            parent_calls[0] += 1
            if change == "parent" and parent_calls[0] > 1:
                return {"demo.pt": "new parent"}
            return {}

        def answer(_prompt):
            if change == "file":
                target.write_bytes(b"replaced")
            if change == "tsv":
                registry.write_text("hold demo.pt", encoding="utf-8")
            return "NO" if change == "cancel" else "YES"

        with mock.patch.object(cleanup, "CKPT", ckpt), mock.patch.object(
            cleanup, "TSV", registry
        ), mock.patch.object(cleanup, "parse_doc", return_value=record), mock.patch.object(
            cleanup, "parse_tsv", return_value=record
        ), mock.patch.object(cleanup, "derived_protection", side_effect=parents), mock.patch(
            "builtins.input", side_effect=answer
        ), mock.patch.object(Path, "unlink", autospec=True) as unlinked, mock.patch.object(
            sys, "argv", ["cleanup_ckpt.py", "--interactive"]
        ), redirect_stdout(io.StringIO()):
            code = cleanup.main()
            return code, [call.args[0] for call in unlinked.call_args_list]


def main():
    for change in ("cancel", "file", "tsv", "parent"):
        code, targets = trial(change)
        assert not targets, (change, targets)
        assert code == (0 if change == "cancel" else 1), (change, code)
    code, targets = trial("unchanged")
    assert code == 0 and len(targets) == 1 and targets[0].name == "demo.pt"
    print("[PASS] frozen preview: cancel/change/parent block; unchanged exact target only")
    print("[NOT_RUN] real checkpoint deletion")


if __name__ == "__main__":
    main()
