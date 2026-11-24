#!/usr/bin/env python3
"""Regression checks for the cross-platform document link checker."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().with_name("check_links.py")
SPEC = importlib.util.spec_from_file_location("check_links_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_protected_relative_target_is_classified_without_io() -> None:
    source = MODULE.ROOT / "ai_dev_tool" / "20260909_report" / "report.md"
    assert MODULE._is_protected_target(
        source, "../../datasets/TinyDataset/docs/example.md"
    )
    assert not MODULE._is_protected_target(source, "../../docs/example.md")


def test_status_candidate_supports_ongoing_and_absorbed() -> None:
    ongoing = Path("proposal/item-approved-on-going.md")
    absorbed = Path("docs/review/item_absorbed.md")
    index = {
        ongoing.name: ongoing,
        absorbed.name: absorbed,
    }
    assert MODULE._status_candidate(index, "item.md") == ongoing

    index = {absorbed.name: absorbed}
    assert MODULE._status_candidate(index, "item.md") == absorbed


def test_ambiguous_candidates_are_not_auto_fixable() -> None:
    index: dict[str, Path | None] = {}
    MODULE._record_candidate(index, "same.md", Path("a/same.md"))
    MODULE._record_candidate(index, "same.md", Path("b/same.md"))
    assert index["same.md"] is None
    assert MODULE._status_candidate(index, "same.md") is None


def test_each_explicit_fix_mode_requests_persistence() -> None:
    assert MODULE._write_requested(True, False)
    assert MODULE._write_requested(False, True)
    assert MODULE._write_requested(True, True)
    assert not MODULE._write_requested(False, False)


def test_archives_require_a_pinned_copy_and_existing_target() -> None:
    with TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
        root = Path(folder)
        original_plan = root / "test_plan/original.md"
        original_target = root / "docs/linked.md"
        archive = root / "test_result/evidence/run/initial_plan.md"
        registry = root / "scripts/link_snapshot_origins.tsv"
        for path in (original_plan, original_target, archive, registry):
            path.parent.mkdir(parents=True, exist_ok=True)
        content = "[linked](../docs/linked.md)\n"
        original_plan.write_text(content, encoding="utf-8")
        original_target.write_text("original target\n", encoding="utf-8")
        archive.write_bytes(content.encode("utf-8"))
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        registry.write_text("snapshot\tsha256\torigin\tevidence\n"
                            f"{archive.relative_to(root).as_posix()}\t{digest}\t"
                            "test_plan/original.md\tfixture\n", encoding="utf-8")
        with (patch.object(MODULE, "ROOT", root), patch.object(MODULE, "SNAPSHOT_INDEX", registry),
              patch("sys.argv", ["check_links.py", "--fix"])):
            assert MODULE.main() == 0
            archive.write_bytes(content.replace("linked.md", "absent.md").encode("utf-8"))
            assert MODULE.main() == 1
            assert "absent.md" in archive.read_text(encoding="utf-8")
            broken = "[absent](../docs/absent.md)\n" * 256
            original_plan.write_text(broken, encoding="utf-8")
            archive.write_bytes(content.encode("utf-8"))
            assert MODULE.main() == 1


def test_archive_resolves_only_the_exact_closed_wip_name() -> None:
    with TemporaryDirectory() as folder:
        root = Path(folder)
        handoff = root / "handoff"
        handoff.mkdir()
        closed = handoff / "WIP_20261022_작업원장-done.md"
        closed.write_text("종결된 원장\n", encoding="utf-8")
        origin = root / "test_plan/P109_plan.md"
        with patch.object(MODULE, "ROOT", root):
            assert MODULE._closed_archive_wip(origin, "../handoff/WIP_20261022_작업원장.md")
            assert not MODULE._closed_archive_wip(origin, "../handoff/WIP_20261021_작업원장.md")
            assert not MODULE._closed_archive_wip(origin, "../docs/WIP_20261022_작업원장.md")


def main() -> int:
    tests = [
        test_protected_relative_target_is_classified_without_io,
        test_status_candidate_supports_ongoing_and_absorbed,
        test_ambiguous_candidates_are_not_auto_fixable,
        test_each_explicit_fix_mode_requests_persistence,
        test_archives_require_a_pinned_copy_and_existing_target,
        test_archive_resolves_only_the_exact_closed_wip_name,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"SUMMARY {len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
