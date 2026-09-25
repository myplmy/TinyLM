#!/usr/bin/env python3
"""C2 frontier/handoff coverage regressions on an isolated temporary tree."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from frontier_queue_gate import marker, prepare, verify_handoff


class FrontierQueueGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("test_plan", "handoff/audit", "docs/review"):
            (self.root / name).mkdir(parents=True)
        (self.root / "test_plan/P014_old.md").write_text(
            "# P014 old\n\n## Stage1 실행 전\n\n선결: synthetic gate.\n", encoding="utf-8")
        (self.root / "test_plan/P097_new.md").write_text(
            "# P097 new\n\n## Stage1 실행 전\n\n선결: data decision.\n", encoding="utf-8")
        (self.root / "test_plan/실험계획목록.md").write_text(
            "## 1. 계획만 있고 실행 전\n\n"
            "| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |\n"
            "|---|---|---|---|\n"
            "| [P014](P014_old.md) | old | gate | 2026-09-25 |\n"
            "| [P097](P097_new.md) | new | data | 2026-09-25 |\n"
            "## 2. 진행 중\n\n## 3. 종결\n", encoding="utf-8")
        (self.root / "experiments.tsv").write_text(
            "prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\n"
            "1\tP014\trun_P014.sh\tN\t0.1\tN\tN\told gate\n", encoding="utf-8")
        (self.root / "run_P014.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.root / "handoff/COMPASS.md").write_text("| speed | P014 P097 |\n", encoding="utf-8")
        self.handoff = self.root / "handoff/202609251234_HANDOFF.md"
        self.handoff.write_text(
            "## 7. 다음 권장 실험 순서\n\n"
            "| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |\n"
            "|---:|---:|---|---|---:|---:|---|---|---|---|\n"
            "| 1 | 0 | P014 gate | run_P014.sh | 0.1 | 0.1 | PRESENT | GATED | none | old |\n",
            encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _prepared(self):
        path, frontier, created = prepare(self.root, self.handoff)
        self.assertTrue(created)
        with self.handoff.open("a", encoding="utf-8") as stream:
            stream.write("\n" + marker(path, frontier) + "\n")
        return path, frontier

    def _accept_live(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        by_id = {row["plan_id"]: row for row in data["dispositions"]}
        by_id["P014"].update(decision="INCLUDE", review="MANUAL",
                              reason="old runnable gate selected after review")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_prepare_reuses_exact_artifact_and_requires_manual_live_decision(self):
        path, frontier = self._prepared()
        self.assertEqual(frontier["counts"]["disposition_required"], 2)
        self.assertEqual(prepare(self.root, self.handoff)[0], path)
        self.assertIn("P014: decision/reason not reviewed", verify_handoff(self.root, self.handoff))
        self._accept_live(path)
        self.assertEqual(verify_handoff(self.root, self.handoff), [])
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual({row["plan_id"] for row in data["dispositions"]}, {"P014", "P097"})
        self.assertEqual(next(row for row in data["dispositions"] if row["plan_id"] == "P097")["review"],
                         "AUTO_NO_LAUNCHER")

    def test_missing_marker_stale_source_and_missing_disposition_fail(self):
        self.assertIn("exactly one", verify_handoff(self.root, self.handoff)[0])
        path, _frontier = self._prepared()
        self._accept_live(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["dispositions"] = data["dispositions"][:1]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertTrue(any("disposition IDs" in error for error in verify_handoff(self.root, self.handoff)))
        self._accept_live(path)
        (self.root / "test_plan/P097_new.md").write_text("# P097 changed\n선결 새 항목\n", encoding="utf-8")
        self.assertTrue(any("stale" in error for error in verify_handoff(self.root, self.handoff)))

    def test_queue_hours_and_conflict_are_not_green(self):
        path, _frontier = self._prepared()
        self._accept_live(path)
        body = self.handoff.read_text(encoding="utf-8").replace(
            "run_P014.sh | 0.1 | 0.1", "run_P014.sh | 0.2 | 0.2")
        self.handoff.write_text(body, encoding="utf-8")
        self.assertTrue(any("stale" in error for error in verify_handoff(self.root, self.handoff)))
        (self.root / "test_plan/P014_old.md").write_text(
            "# P014 old\n\n> 상태: 종결\n", encoding="utf-8")
        self.assertTrue(any("conflict" in error for error in verify_handoff(self.root, self.handoff)))

    def test_marker_outside_section_seven_is_rejected(self):
        path, frontier = self._prepared()
        self._accept_live(path)
        stamp = marker(path, frontier)
        body = self.handoff.read_text(encoding="utf-8").replace(stamp, "")
        self.handoff.write_text(body + chr(10) + "## 8. 커밋 메시지" + chr(10) + stamp + chr(10),
                                encoding="utf-8")
        self.assertIn("exactly one", verify_handoff(self.root, self.handoff)[0])

    def test_wsl_shell_companion_maps_to_registered_bat(self):
        tsv = self.root / "experiments.tsv"
        tsv.write_text(tsv.read_text(encoding="utf-8").replace("run_P014.sh", "run_P014.bat"),
                       encoding="utf-8")
        (self.root / "run_P014.bat").write_text("REM fixture" + chr(10), encoding="utf-8")
        path, _frontier = self._prepared()
        self._accept_live(path)
        self.assertEqual(verify_handoff(self.root, self.handoff), [])

    def test_missing_hold_carryover_is_not_runnable_include(self):
        body = self.handoff.read_text(encoding="utf-8")
        body += ("| 2 | — | P097 future | run_P097_missing.sh | 0.0 | 0.1 | MISSING | HOLD | "
                 "implementation absent | preserve previous decision |" + chr(10))
        self.handoff.write_text(body, encoding="utf-8")
        path, _frontier = self._prepared()
        self._accept_live(path)
        self.assertEqual(verify_handoff(self.root, self.handoff), [])





if __name__ == "__main__":
    unittest.main(verbosity=2)
