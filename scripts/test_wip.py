#!/usr/bin/env python3
"""Isolated regression tests for scripts/wip.py; no repository WIP is changed."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().with_name("wip.py")
# The environment audit runs this suite with Python -I, which excludes the
# script directory from sys.path. wip.close() imports its sibling gate modules.
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("tinylm_wip_v2", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
WIP = importlib.util.module_from_spec(SPEC)
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

    def invalid_id_ledger(self) -> Path:
        """Reproduce the old --add defect only in an isolated temporary file."""
        path = self.create()
        WIP.add_item(path, "3B", "추가 원문 | 보존", "다음 단계 | 보존")
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("| **3B** |", "| **3AB** |", 1), encoding="utf-8")
        return path

    def test_add_rejects_unsupported_ids_before_any_write(self) -> None:
        path = self.create()
        before = path.read_bytes()
        for item_id in ("3AB", "", "3-A", "3 B", "3가", "3|B", "3B\n"):
            with self.subTest(item_id=item_id):
                with self.assertRaisesRegex(ValueError, "invalid item id"):
                    WIP.add_item(path, item_id, "원문", "다음 단계")
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(path.with_name(path.name + ".lock").exists())

    def test_create_rejects_unsupported_ids_without_artifacts(self) -> None:
        for raw in ("3AB=지시", "3-A=지시", "3가=지시", "=지시"):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "invalid"):
                    WIP.create_ledger([raw], "prev", "docs", "GPU 금지", "없음", "없음")
                self.assertEqual(list(self.handoff.iterdir()), [])

    def test_parse_and_close_refuse_unrecognized_progress_rows(self) -> None:
        path = self.create()
        for item in ("1", "2A"):
            WIP.set_state(path, item, WIP.RUN, "착수", None, "다음 단계")
            WIP.set_state(path, item, WIP.DONE, "완료", "산출물", None)
        valid = path.read_text(encoding="utf-8")
        for replacement in ("| **3AB** |", "| 3B |", "| **3가** |", "| **1** ", "**1** |"):
            with self.subTest(replacement=replacement):
                malformed = valid.replace("| **1** |", replacement, 1)
                path.write_text(malformed, encoding="utf-8")
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, "invalid item id|malformed progress row"):
                    WIP.parse_table(malformed)
                with self.assertRaisesRegex(ValueError, "invalid item id|malformed progress row"):
                    WIP.close(path)
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(path.with_name(path.stem + "-done.md").exists())

    def test_parse_rejects_bad_separator_and_accepts_indented_rows(self) -> None:
        path = self.create()
        valid = path.read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "separator is malformed"):
            WIP.parse_table(valid.replace("| --- | --- | --- | --- | --- | --- |",
                                          "| --- | --- |", 1))
        indented = valid.replace("| **1** |", "    | **1** |", 1)
        self.assertEqual([row[1] for row in WIP.parse_table(indented).rows], ["1", "2A"])

    def test_id_repair_preserves_directive_status_and_history(self) -> None:
        path = self.invalid_id_ledger()
        before = path.read_text(encoding="utf-8")
        before_line = next(line for line in before.splitlines() if line.startswith("| **3AB** |"))
        WIP.override_field(path, "3AB", "#", "3AB", "3B", "지원하지 않는 ID 복구",
                           "사용자 2026-10-06 두 파일 수리 승인", False)
        after = path.read_text(encoding="utf-8")
        table = WIP.parse_table(after)
        self.assertEqual(len(table.rows), 3)
        repaired_line = after.splitlines()[table.rows[-1][0]]
        self.assertEqual(repaired_line, before_line.replace("**3AB**", "**3B**", 1))
        self.assertEqual(table.rows[-1][2][1:], WIP._markdown_cells(before_line)[1:])
        self.assertIn("- **사용자 지시**: 3건(아래 표가 정본)", after)
        log_before = before.split(WIP.LOG_HEADING, 1)[1].split(WIP.AUDIT_HEADING, 1)[0]
        self.assertIn(log_before.rstrip(), after)
        audit_body = after.split(WIP.AUDIT_HEADING, 1)[1].split(WIP.CAPSULE_HEADING, 1)[0]
        record = json.loads(audit_body.split("```json", 1)[1].split("```", 1)[0])
        self.assertEqual(record["operation"], "repair unsupported item id (compare-and-set)")
        self.assertEqual(record["before"], "3AB")
        self.assertEqual(record["after"], "3B")
        self.assertEqual(record["before_sha256"], WIP._sha_text("3AB"))
        self.assertEqual(record["after_sha256"], WIP._sha_text("3B"))
        self.assertEqual(record["before_file_sha256"], WIP._sha_text(before))
        self.assertEqual(record["before_row_sha256"], WIP._sha_text(before_line))
        self.assertEqual(record["after_row_sha256"], WIP._sha_text(repaired_line))
        self.assertIn("두 파일 수리 승인", record["approval_ref"])
        capsule = WIP.capsule_text(path)
        self.assertIn("사용자 지시 3건", capsule)
        self.assertIn("3B:⏳대기", capsule)
        WIP.set_state(path, "3B", WIP.RUN, "복구 후 착수", None, "검증")
        WIP.set_state(path, "3B", WIP.DONE, "완료", "산출물", None)

    def test_id_repair_rejects_stale_collision_and_invalid_after(self) -> None:
        path = self.invalid_id_ledger()
        before = path.read_bytes()
        for item_id, expected, after, message in (
            ("3AB", "다른 값", "3B", "STALE_BEFORE"),
            ("3AB", "3AB", "2A", "duplicate item id"),
            ("3AB", "3AB", "3AC", "invalid item id"),
            ("1", "1", "5", "unsupported item id"),
            ("9ZZ", "9ZZ", "9Z", "exactly once"),
        ):
            with self.subTest(item_id=item_id, after=after):
                with self.assertRaisesRegex(ValueError, message):
                    WIP.override_field(path, item_id, "#", expected, after, "사유", "승인", False)
                self.assertEqual(path.read_bytes(), before)

    def test_id_repair_does_not_bypass_other_malformed_rows(self) -> None:
        path = self.invalid_id_ledger()
        text = path.read_text(encoding="utf-8")
        for malformed, message in (
            (text.replace("| **1** |", "| **1ZZ** |", 1), "invalid item id"),
            (text.replace("| **2A** |", "| **3AB** |", 1), "exactly once"),
            (text.replace("| **3AB** |", "| **3AB** | extra |", 1), "cells"),
        ):
            with self.subTest(message=message):
                path.write_text(malformed, encoding="utf-8")
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, message):
                    WIP.override_field(path, "3AB", "#", "3AB", "3B", "사유", "승인", False)
                self.assertEqual(path.read_bytes(), before)

    def test_id_repair_requires_approval_and_refuses_completed_file(self) -> None:
        path = self.invalid_id_ledger()
        before = path.read_bytes()
        for reason, approval in (("", "승인"), ("사유", "")):
            with self.subTest(reason=reason, approval=approval):
                with self.assertRaisesRegex(ValueError, "required"):
                    WIP.override_field(path, "3AB", "#", "3AB", "3B", reason, approval, False)
                self.assertEqual(path.read_bytes(), before)
        completed = path.with_name(path.stem + "-done.md")
        path.rename(completed)
        with self.assertRaisesRegex(ValueError, "immutable"):
            WIP.override_field(completed, "3AB", "#", "3AB", "3B", "사유", "승인", False)
        self.assertEqual(completed.read_bytes(), before)

    def test_repaired_row_must_finish_before_close(self) -> None:
        path = self.invalid_id_ledger()
        WIP.override_field(path, "3AB", "#", "3AB", "3B", "사유", "승인", False)
        for item_id in ("1", "2A"):
            WIP.set_state(path, item_id, WIP.RUN, "착수", None, "완료 처리")
            WIP.set_state(path, item_id, WIP.DONE, "완료", "산출물", None)
        with self.assertRaisesRegex(ValueError, "미완료 항목 1개: 3B"):
            WIP.close(path)
        WIP.set_state(path, "3B", WIP.RUN, "착수", None, "완료 처리")
        WIP.set_state(path, "3B", WIP.DONE, "완료", "산출물", None)
        audit = self.root / "audit-repaired.json"
        audit.write_text(json.dumps({
            "schema": "TINYLM_STATIC_AUDIT_V1", "profile": "codex-safe",
            "wip": {"path": path.relative_to(self.root).as_posix(),
                    "sha256": WIP._sha_bytes(path.read_bytes()), "session_id": None},
            "counts": {"errors": 0, "actionable_warnings": 0},
        }), encoding="utf-8")
        self.assertTrue(WIP.close(path, audit).is_file())

    def test_existing_override_cli_repairs_id_without_new_flags(self) -> None:
        path = self.invalid_id_ledger()
        argv = ["wip.py", "--override", "--file", str(path), "--item", "3AB",
                "--field", "#", "--expect-before", "3AB", "--set-after", "3B",
                "--reason", "ID 복구", "--approval-ref", "사용자 승인"]
        output = io.StringIO()
        with patch.object(sys, "argv", argv), redirect_stdout(output):
            self.assertEqual(WIP.main(), 0)
        self.assertIn("OVERRIDE_OK item=3AB field=#", output.getvalue())
        self.assertEqual(len(WIP.parse_table(path.read_text(encoding="utf-8")).rows), 3)
        self.assertIn("3B:⏳대기", WIP.capsule_text(path))

    def test_add_updates_instruction_count_and_sync_repairs_old_header(self) -> None:
        path = self.create()
        WIP.add_item(path, "3", "추가 지시", "GPT가 다음 검사")
        current = path.read_text(encoding="utf-8")
        self.assertIn("- **사용자 지시**: 3건(아래 표가 정본)", current)
        path.write_text(current.replace("- **사용자 지시**: 3건(아래 표가 정본)",
                                        "- **사용자 지시**: 2건(아래 표가 정본)"),
                        encoding="utf-8")
        WIP.sync_instruction_count(path, "기존 --add의 메타 수 미갱신", "사용자 지시")
        repaired = path.read_text(encoding="utf-8")
        self.assertIn("- **사용자 지시**: 3건(아래 표가 정본)", repaired)
        self.assertIn('"operation": "sync displayed instruction count with v2 table"',
                      repaired)
        self.assertIn("상황판 SHA-256", WIP.capsule_text(path))
        with self.assertRaisesRegex(ValueError, "already current"):
            WIP.sync_instruction_count(path, "중복", "사용자 지시")


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

    def test_capsule_includes_bounded_running_progress(self) -> None:
        path = self.create()
        WIP.set_state(path, "1", WIP.RUN, "진행 근거 " + "가" * 400, "중간 산출물", "다음 검사")
        capsule = WIP.capsule_text(path)
        self.assertIn("1:진행 진행 근거", capsule)
        self.assertIn("산출물=중간 산출물", capsule)
        self.assertIn("…", capsule)

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
        with self.assertRaisesRegex(ValueError, "미완료 항목"):
            WIP.close(path)
        for item in ("1", "2A"):
            WIP.set_state(path, item, WIP.RUN, "착수", None, "완료 처리")
            WIP.set_state(path, item, WIP.DONE, "완료", "없음", None)
        with self.assertRaisesRegex(ValueError, "requires --static-audit"):
            WIP.close(path)
        audit = self.root / "audit.json"
        audit.write_text(
            json.dumps({
                "schema": "TINYLM_STATIC_AUDIT_V1",
                "profile": "codex-safe",
                "wip": {
                    "path": path.relative_to(self.root).as_posix(),
                    "sha256": WIP._sha_bytes(path.read_bytes()),
                    "session_id": None,
                },
                "counts": {"errors": 0, "actionable_warnings": 0},
            }),
            encoding="utf-8",
        )
        target = WIP.close(path, audit)
        self.assertFalse(path.exists())
        self.assertTrue(target.exists())

    def test_result_document_close_requires_exact_result_only_manifest(self) -> None:
        path = WIP.create_ledger(
            ["1=사용자가 지정한 실험 로그를 결과문서에 반영한다"],
            "handoff/prev_HANDOFF.md", "test_result only", "GPU 금지",
            "사용자 실행", "없음", session_id="fixture-session",
        )
        WIP.set_state(path, "1", WIP.RUN, "원본 판독", None, "결과문서 기록")
        WIP.set_state(path, "1", WIP.DONE, "기록 완료", "test_result/101_test.md", None)
        static = self.root / "audit-static.json"
        static.write_text(json.dumps({
            "schema": "TINYLM_STATIC_AUDIT_V1", "profile": "codex-safe",
            "wip": {"path": path.relative_to(self.root).as_posix(),
                    "sha256": WIP._sha_bytes(path.read_bytes()),
                    "session_id": "fixture-session"},
            "counts": {"errors": 0, "actionable_warnings": 0},
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "requires --result-closure"):
            WIP.close(path, static)
        result_dir = self.root / "test_result"
        result_dir.mkdir()
        log = result_dir / "101_log_20260927_fixture.txt"
        doc = result_dir / "101_fixture.md"
        log.write_text("raw", encoding="utf-8")
        doc.write_text("## 1. Fixture" + chr(10) + log.name, encoding="utf-8")
        audit_dir = self.handoff / "audit"
        audit_dir.mkdir()
        manifest = audit_dir / "fixture_RESULT_CLOSURE.json"
        data = {"schema": "TINYLM_RESULT_CLOSURE_V1",
                "session_id": "fixture-session",
                "wip": path.with_name(path.stem + "-done.md").relative_to(self.root).as_posix(),
                "input_logs": ["test_result/" + log.name],
                "mappings": [{"log": "test_result/" + log.name,
                              "result": "test_result/" + doc.name,
                              "section": "## 1. Fixture", "status": "RECORDED"}]}
        manifest.write_text(json.dumps(dict(data, session_id="other")), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "session id differs"):
            WIP.close(path, static, result_closure=manifest)
        manifest.write_text(json.dumps(dict(data, mappings=[])), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "result closure failed"):
            WIP.close(path, static, result_closure=manifest)
        manifest.write_text(json.dumps(data), encoding="utf-8")
        target = WIP.close(path, static, result_closure=manifest)
        self.assertTrue(target.is_file())

    def test_queue_handoff_close_requires_frontier_gate(self) -> None:
        path = WIP.create_ledger(
            ["1=다음 권장 실험 순서와 세션 핸드오프 작성"],
            "handoff/prev_HANDOFF.md", "docs", "GPU 금지", "사용자 실행", "없음",
        )
        WIP.set_state(path, "1", WIP.RUN, "큐 감사", None, "완료 처리")
        WIP.set_state(path, "1", WIP.DONE, "완료", "handoff/next_HANDOFF.md", None)
        audit = self.root / "audit-queue.json"
        audit.write_text(json.dumps({
            "schema": "TINYLM_STATIC_AUDIT_V1", "profile": "codex-safe",
            "wip": {"path": path.relative_to(self.root).as_posix(),
                    "sha256": WIP._sha_bytes(path.read_bytes()), "session_id": None},
            "counts": {"errors": 0, "actionable_warnings": 0},
        }), encoding="utf-8")
        handoff = self.handoff / "202609251234_HANDOFF.md"
        handoff.write_text("- **이전**: [prev](prev_HANDOFF.md)" + chr(10)
                           + path.name + chr(10) + "## 7. 다음 권장 실험 순서" + chr(10),
                           encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "requires --handoff"):
            WIP.close(path, audit)
        with self.assertRaisesRegex(ValueError, "frontier queue gate failed"):
            WIP.close(path, audit, handoff)
        self.assertTrue(path.exists())
        valid_handoff = handoff.read_text(encoding="utf-8")
        handoff.write_text(valid_handoff.replace("prev_HANDOFF.md", "foreign_HANDOFF.md"),
                           encoding="utf-8")
        with patch("frontier_queue_gate.verify_handoff", return_value=[]):
            with self.assertRaisesRegex(ValueError, "previous-chain"):
                WIP.close(path, audit, handoff)
        handoff.write_text(valid_handoff.replace(path.name, "foreign_WIP.md"), encoding="utf-8")
        with patch("frontier_queue_gate.verify_handoff", return_value=[]):
            with self.assertRaisesRegex(ValueError, "exact WIP"):
                WIP.close(path, audit, handoff)
        handoff.write_text(valid_handoff, encoding="utf-8")
        with patch("frontier_queue_gate.verify_handoff", return_value=[]):
            with self.assertRaisesRegex(ValueError, "semantic triage"):
                WIP.close(path, audit, handoff)
        with patch("frontier_queue_gate.verify_handoff", return_value=[]), patch(
            "frontier_semantic_gate.verify_handoff", return_value=[]
        ):
            target = WIP.close(path, audit, handoff)
        self.assertTrue(target.exists())

    def test_previous_chain_accepts_intervening_handoff_and_rejects_cycle(self) -> None:
        original = self.handoff / "prev_HANDOFF.md"
        intervening = self.handoff / "middle_HANDOFF.md"
        latest = self.handoff / "latest_HANDOFF.md"
        original.write_text("- **이전**: [none](none_HANDOFF.md)\n", encoding="utf-8")
        intervening.write_text("- **이전**: [prev](prev_HANDOFF.md)\n", encoding="utf-8")
        latest.write_text("- **이전**: [middle](middle_HANDOFF.md)\n", encoding="utf-8")
        self.assertTrue(WIP._handoff_previous_chain_contains(latest, original.name))
        intervening.write_text("- **이전**: [latest](latest_HANDOFF.md)\n", encoding="utf-8")
        self.assertFalse(WIP._handoff_previous_chain_contains(latest, original.name))
        intervening.write_text("- **이전**: [escape](../prev_HANDOFF.md)\n", encoding="utf-8")
        self.assertFalse(WIP._handoff_previous_chain_contains(latest, original.name))



    def test_blocked_remains_incomplete_and_cannot_close(self) -> None:
        path = self.create()
        WIP.set_state(path, "1", WIP.BLOCK, "외부 증거 미도착", None,
                      "GPT가 로그를 판독한다")
        WIP.set_state(path, "2A", WIP.RUN, "착수", None, "완료 처리")
        WIP.set_state(path, "2A", WIP.DONE, "완료", "없음", None)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(WIP.show(path), 1)
        self.assertIn("미완료 1개 (대기·진행 0, 막힘 1) · 완료 1개",
                      output.getvalue())
        with self.assertRaisesRegex(ValueError, "미완료 항목 1개: 1"):
            WIP.close(path)
        self.assertTrue(path.exists())


    def test_static_audit_session_id_accepts_markdown_metadata(self) -> None:
        path = self.create()
        WIP.bind_session(path, "thread-owner", "소유 확인", "사용자 승인")
        for item in ("1", "2A"):
            WIP.set_state(path, item, WIP.RUN, "착수", None, "완료 처리")
            WIP.set_state(path, item, WIP.DONE, "완료", "없음", None)
        audit = self.root / "audit-session.json"
        audit.write_text(
            json.dumps({
                "schema": "TINYLM_STATIC_AUDIT_V1", "profile": "codex-safe",
                "wip": {
                    "path": path.relative_to(self.root).as_posix(),
                    "sha256": WIP._sha_bytes(path.read_bytes()),
                    "session_id": "thread-owner",
                },
                "counts": {"errors": 0, "actionable_warnings": 0},
            }), encoding="utf-8",
        )
        target = WIP.close(path, audit)
        self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
