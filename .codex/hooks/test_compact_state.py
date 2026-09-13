#!/usr/bin/env python3
"""Mock tests for staged TinyLM compact-state hooks (M0-M3)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().with_name("compact_state.py")
SPEC = importlib.util.spec_from_file_location("tinylm_compact_state", HOOK_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {HOOK_PATH}")
HOOK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HOOK
SPEC.loader.exec_module(HOOK)

SENTINELS = {
    "현재 지시·허용목록": "ALLOW_ONLY_DOCS_81F2",
    "보호·NOT_RUN 경계": "DATASET_NEVER_READ_C0A7",
    "열린 WIP·미완료 상태": "WIP_EXACT_2B_RUN_941D",
    "수행 변경·검증": "STATIC_ONLY_53AE",
    "막힘·승인·미확인": "APPROVAL_PENDING_70C1",
    "사용자 소유 실행": "USER_GPU_PROCESS_14B9",
    "폐기·정정 주장": "OLD_PASS_FORBIDDEN_8D30",
    "다음 행동·선결": "NEXT_AFTER_USER_E2E_6F44",
}
SENTINEL_CAPSULE = "\n".join(f"| {key} | {value} |" for key, value in SENTINELS.items())


def event(name: str, **fields: str) -> dict[str, str]:
    return {"hook_event_name": name, **fields}


class CompactStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.handoff = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_wip(self, name: str = "WIP_20990101_작업원장.md") -> Path:
        path = self.handoff / name
        path.write_text("fixture", encoding="utf-8")
        return path

    def reader(self, path: Path) -> str:
        return SENTINEL_CAPSULE

    def test_m0_all_eight_sentinels_and_retired_claim_are_preserved(self) -> None:
        self.add_wip()
        response = HOOK.evaluate_event(
            event("SessionStart", source="compact"),
            handoff_dir=self.handoff,
            capsule_reader=self.reader,
        )
        context = response["hookSpecificOutput"]["additionalContext"]
        for field, marker in SENTINELS.items():
            with self.subTest(field=field):
                self.assertIn(field, context)
                self.assertIn(marker, context)
        self.assertIn("제안→승인", context)
        self.assertIn("NOT_RUN→PASS", context)

    def test_m2_precompact_accepts_valid_manual_and_auto_capsules(self) -> None:
        self.add_wip()
        for trigger in ("manual", "auto"):
            with self.subTest(trigger=trigger):
                response = HOOK.evaluate_event(
                    event("PreCompact", trigger=trigger),
                    handoff_dir=self.handoff,
                    capsule_reader=self.reader,
                )
                self.assertTrue(response["continue"])

    def test_m2_stale_capsule_stops_before_compaction(self) -> None:
        self.add_wip()

        def stale(path: Path) -> str:
            raise ValueError("STALE_CAPSULE")

        response = HOOK.evaluate_event(
            event("PreCompact", trigger="auto"),
            handoff_dir=self.handoff,
            capsule_reader=stale,
        )
        self.assertFalse(response["continue"])
        self.assertIn("STALE_CAPSULE", response["stopReason"])

    def test_ambiguous_open_wips_stop_both_paths(self) -> None:
        self.add_wip("WIP_20990101_작업원장.md")
        self.add_wip("WIP_20990101a_작업원장.md")
        for payload in (
            event("PreCompact", trigger="manual"),
            event("SessionStart", source="compact"),
        ):
            with self.subTest(payload=payload):
                response = HOOK.evaluate_event(
                    payload,
                    handoff_dir=self.handoff,
                    capsule_reader=self.reader,
                )
                self.assertFalse(response["continue"])
                self.assertIn("count is 2", response["stopReason"])

    def test_no_open_wip_is_explicit_after_compact(self) -> None:
        response = HOOK.evaluate_event(
            event("SessionStart", source="compact"),
            handoff_dir=self.handoff,
            capsule_reader=self.reader,
        )
        context = response["hookSpecificOutput"]["additionalContext"]
        self.assertIn("열린 WIP 없음", context)

    def test_nonmatching_events_are_ignored(self) -> None:
        self.assertIsNone(HOOK.evaluate_event(event("SessionStart", source="startup")))
        self.assertIsNone(HOOK.evaluate_event(event("PreCompact", trigger="other")))
        self.assertIsNone(HOOK.evaluate_event(event("PostCompact", trigger="auto")))


class CompactStateProcessTests(unittest.TestCase):
    def test_malformed_json_is_silent(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(HOOK_PATH)],
            input="{broken",
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")

    def test_current_repository_state_is_valid_static_evidence(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(HOOK_PATH)],
            input=json.dumps(event("SessionStart", source="compact")),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[TinyLM compact recovery v1]", context)
        if HOOK._open_wips():
            self.assertIn("Compact 상태 캡슐 (v1)", context)
            for field in SENTINELS:
                self.assertIn(field, context)
        else:
            self.assertIn("열린 WIP 없음", context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
