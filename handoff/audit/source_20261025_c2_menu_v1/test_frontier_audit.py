#!/usr/bin/env python3
"""Old and new plan IDs must both survive frontier compilation."""
from __future__ import annotations

import tempfile
from pathlib import Path

from frontier_audit import compile_frontier


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for directory in ("test_plan", "handoff", "docs/review"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / "test_plan/P014_old.md").write_text(
            "# P014\n\n## Stage1 ⏳ 실행 전\n\n선결 없음.\n", encoding="utf-8"
        )
        (root / "test_plan/P097_new.md").write_text(
            "# P097 — 진행 중\n\n## Stage1 ✅ 완료\n\n## Stage2 ⏳ 실행 전\n", encoding="utf-8"
        )
        (root / "test_plan/실험계획목록.md").write_text(
            "## 1. 계획만 있고 실행 전\n\n| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |\n"
            "|---|---|---|---|\n| [P014](P014_old.md) | old | 실행 전 | 2026-01-01 |\n"
            "## 2. 진행 중\n\n| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |\n"
            "|---|---|---|---|\n| [P097](P097_new.md) | new | Stage2 | 2026-09-21 |\n"
            "## 3. 종결\n",
            encoding="utf-8",
        )
        (root / "experiments.tsv").write_text(
            "prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\n"
            "1\tP014\trun_P014.sh\tD\t0.1\tN\tY\told ready\n", encoding="utf-8"
        )
        (root / "run_P014.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (root / "handoff/COMPASS.md").write_text("| 속도 | P014 |\n", encoding="utf-8")
        data = compile_frontier(root)
        by_id = {row["plan_id"]: row for row in data["rows"]}
        assert set(by_id) == {"P014", "P097"}
        assert by_id["P014"]["readiness"] == "GATED"
        assert by_id["P097"]["readiness"] == "HOLD"
        assert data["set_differences"] == {"physical_without_index": [], "index_without_physical": []}
    print("[PASS] frontier preserves old P014 and new P097 with one row per physical plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
