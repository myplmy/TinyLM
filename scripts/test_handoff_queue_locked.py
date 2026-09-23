#!/usr/bin/env python3
"""Queue-locked handoff inheritance uses only previous Markdown, never registry."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import handoff_queue


class LockedInheritanceTests(unittest.TestCase):
    def test_locked_mode_never_loads_live_inventory(self):
        original = handoff_queue._load_registry
        handoff_queue._load_registry = lambda: (_ for _ in ()).throw(
            AssertionError("registry must not be opened")
        )
        try:
            with tempfile.TemporaryDirectory() as directory:
                previous = Path(directory) / "previous.md"
                previous.write_text(
                    "## 7. 다음 권장 실험 순서" + chr(10) +
                    "| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |" + chr(10) +
                    "|---:|---:|---|---|---:|---:|---|---|---|---|" + chr(10) +
                    "| 1 | 3 | P000 Stage0 | " + chr(96) + "run_P000_Stage0.sh" + chr(96) +
                    " | 1.5 | 1.5 | PRESENT | REVALIDATE | 현재 큐 잠금 | 역사 이유 |" + chr(10) +
                    "| 2 | — | P001 완료 | " + chr(96) + "run_P001-done.sh" + chr(96) +
                    " | 0.2 | 1.7 | DONE | DONE | 없음 | 완료 |" + chr(10),
                    encoding="utf-8",
                )
                rows = handoff_queue.inherited_rows_locked(previous)
        finally:
            handoff_queue._load_registry = original
        self.assertEqual(len(rows), 1)
        self.assertIn("| UNVERIFIED | REVALIDATE |", rows[0])
        self.assertIn("| 1.5 | 1.5 |", rows[0])
        self.assertIn("run_P000_Stage0.sh", rows[0])
        self.assertNotIn("run_P001-done.sh", rows[0])


if __name__ == "__main__":
    unittest.main()
