#!/usr/bin/env python3
"""Isolated regression tests for scripts/wip.py; no repository WIP is changed."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().with_name("wip.py")
SPEC = importlib.util.spec_from_file_location("tinylm_wip_v2", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
WIP = importlib.util.module_from_spec(SPEC)
import sys
sys.modules[SPEC.name] = WIP
SPEC.loader.exec_module(WIP)


class WipV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.handoff = self.root / "handoff"
        self.handoff.mkdir()
        self.old_root, self.old_handoff = WIP.ROOT, WIP.HANDOFF
        WIP.ROOT, WIP.HANDOFF = self.root, self.handoff

    def tearDown(self) -> None:
        WIP.ROOT, WIP.HANDOFF = self.old_root, self.old_handoff
        self.temp.cleanup()

    def create(self) -> Path:
        return WIP.create_ledger(
            ["1=첫 지시", "2A=파이프 | 포함 지시"],
            "handoff/prev_HANDOFF.md",
            "docs와 scripts",
            "GPU·삭제 금지",
            "실행 중인 사용자 프로세스 없음",
            "낡은 PASS 주장을 되살리지 않음",
        )

    def test_new_state_history_and_capsule(self) -> None:
        path = self.create()
        WIP.set_state(path, "1", WIP.RUN, "착수 | 검증", None, "검사 실행")
        WIP.set_state(path, "1", WIP.DONE, "완료", "docs/a.md", None)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("<br>", text)
        self.assertIn(r"착수 \| 검증", text)
        self.assertIn("**1번 착수**", text)
        self.assertIn("**1번 완료**", text)
        self.assertIn("| **1** | 첫 지시 | ✅**완료** | 완료 | docs/a.md | — |", text)
        self.assertIn("상황판 SHA-256", WIP.capsule_text(path))

    def test_concurrent_creation_is_explicit_audited_and_unambiguous(self) -> None:
        first = self.create()
        with self.assertRaisesRegex(ValueError, "open WIP already exists"):
            self.create()
        with self.assertRaisesRegex(ValueError, "concurrent-reason"):
            WIP.create_ledger(
                ["3=둘째 지시"], "prev", "docs", "GPU 금지", "없음", "없음",
                allow_concurrent=True, session_id="thread-2",
            )
        second = WIP.create_ledger(
            ["3=둘째 지시"], "prev", "docs", "GPU 금지", "없음", "없음",
            allow_concurrent=True,
            concurrent_reason="사용자 승인 2026-09-13",
            session_id="thread-2",
        )
        self.assertNotEqual(first, second)
        text = second.read_text(encoding="utf-8")
        self.assertIn("**Codex 세션 ID**: `thread-2`", text)
        self.assertIn("**동시 WIP 생성 승인**: 사용자 승인 2026-09-13", text)
        self.assertIn(first.name, text)
        with self.assertRaisesRegex(ValueError, "--file 필수"):
            WIP.resolve_ledger(None)
        self.assertEqual(WIP.resolve_ledger(str(second)), second.resolve())

    def test_new_ledger_skips_open_and_closed_name_slots(self) -> None:
        self.create()
        day = WIP.dt.datetime.now().strftime("%Y%m%d")
        closed_b = self.handoff / f"WIP_{day}b_작업원장-done.md"
        closed_b.write_text("historic", encoding="utf-8")
        created = WIP.create_ledger(
            ["3=셋째 지시"], "prev", "docs", "GPU 금지", "없음", "없음",
            allow_concurrent=True,
            concurrent_reason="사용자 승인",
            session_id="thread-3",
        )
        self.assertEqual(created.name, f"WIP_{day}c_작업원장.md")
        self.assertEqual(closed_b.read_text(encoding="utf-8"), "historic")

    def test_repair_name_collision_is_audited_and_preserves_closed_file(self) -> None:
        self.create()
        second = WIP.create_ledger(
            ["3=교정 지시"], "prev", "docs", "GPU 금지", "없음", "없음",
            allow_concurrent=True,
            concurrent_reason="사용자 승인",
            session_id="thread-3",
        )
        closed = second.with_name(second.stem + "-done.md")
        closed.write_text("historic", encoding="utf-8")
        repaired = WIP.repair_name_collision(second, "이름 충돌 교정", "사용자 승인")
        self.assertFalse(second.exists())
        self.assertTrue(repaired.exists())
        self.assertEqual(closed.read_text(encoding="utf-8"), "historic")
        text = repaired.read_text(encoding="utf-8")
        self.assertIn('"operation": "repair open-ledger close-target name collision"', text)
        self.assertIn(repaired.name, WIP.capsule_text(repaired))

    def test_bind_session_is_explicit_audited_and_one_way(self) -> None:
        path = self.create()
        WIP.bind_session(path, "thread-owner", "기존 원장 소유 확인", "사용자 승인")
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count("**Codex 세션 ID**"), 1)
        self.assertIn("**Codex 세션 ID**: `thread-owner`", text)
        self.assertIn(
            '"operation": "bind previously unbound open ledger to owning Codex session"',
            text,
        )
        with self.assertRaisesRegex(ValueError, "already has"):
            WIP.bind_session(path, "thread-other", "재결합", "사용자 승인")

    def test_bind_session_rejects_completed_or_unsafe_session_id(self) -> None:
        path = self.create()
        with self.assertRaisesRegex(ValueError, "nonempty safe"):
            WIP.bind_session(path, "bad id", "사유", "사용자 승인")
        completed = path.with_name(path.stem + "-done.md")
        path.rename(completed)
        with self.assertRaisesRegex(ValueError, "immutable"):
            WIP.bind_session(completed, "thread-owner", "사유", "사용자 승인")

    def test_done_requires_start_and_legacy_is_read_only(self) -> None:
        path = self.create()
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "--done requires|invalid transition"):
            WIP.set_state(path, "1", WIP.DONE, "성급한 완료", None, None)
        self.assertEqual(before, path.read_bytes())

        legacy = self.handoff / "WIP_20200101_작업원장.md"
        legacy.write_text(
            "# WIP\n\n## 1. 진행 상황판\n\n"
            "| # | 지시 | 상태 | 작업 내용 | 산출물 |\n"
            "|---|---|---|---|---|\n"
            "| **1** | 옛 지시 | ⏳대기 | — | — |\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "LEGACY_READ_ONLY"):
            WIP.set_state(legacy, "1", WIP.RUN, "착수", None, "다음")

    def test_override_is_compare_and_set_and_audited(self) -> None:
        path = self.create()
        with self.assertRaisesRegex(ValueError, "STALE_BEFORE"):
            WIP.override_field(path, "1", "작업 내용", "틀린 값", "새 값", "사유", "승인", False)
        WIP.override_field(path, "1", "작업 내용", "—", "교정값", "표현 교정", "사용자 지시 2026-09-13", False)
        text = path.read_text(encoding="utf-8")
        self.assertIn('"before_sha256"', text)
        self.assertIn('"after_sha256"', text)
        self.assertIn('"approval_ref": "사용자 지시 2026-09-13"', text)
        self.assertIn('"cli_contract"', text)
        self.assertIn("| **1** | 첫 지시 | ⏳대기 | 교정값 | — |", text)

    def test_existing_lock_is_not_removed_by_failed_writer(self) -> None:
        path = self.create()
        lock = path.with_name(path.name + ".lock")
        lock.write_text("other writer", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            WIP.set_state(path, "1", WIP.RUN, "착수", None, "다음")
        self.assertEqual(lock.read_text(encoding="utf-8"), "other writer")

    def test_migrate_only_open_legacy_and_records_approval(self) -> None:
        legacy = self.handoff / "WIP_20200101_작업원장.md"
        legacy.write_text(
            "# WIP\n\n## 1. 진행 상황판\n\n"
            "| # | 사용자 지시 | 상태 | 작업 내용 | 산출물 |\n"
            "|---|---|---|---|---|\n"
            "| **2A** | 옛 지시 | ⏳대기 | — | — |\n"
            "\n## 3. 작업 로그 (append-only)\n\n- 착수\n",
            encoding="utf-8",
        )
        WIP.migrate_v2(legacy, "사용자 승인 D/E", "없음", "없음")
        text = legacy.read_text(encoding="utf-8")
        self.assertIn("| # | 사용자 지시 | 상태 | 작업 내용 | 산출물 | 이어받을 지점 |", text)
        self.assertIn('"approval_ref": "사용자 승인 D/E"', text)
        self.assertIn("Compact 상태 캡슐", WIP.capsule_text(legacy))

    def test_close_refuses_open_then_renames_completed(self) -> None:
        path = self.create()
        with self.assertRaisesRegex(ValueError, "열린 항목"):
            WIP.close(path)
        for item in ("1", "2A"):
            WIP.set_state(path, item, WIP.RUN, "착수", None, "완료 처리")
            WIP.set_state(path, item, WIP.DONE, "완료", "없음", None)
        target = WIP.close(path)
        self.assertFalse(path.exists())
        self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
