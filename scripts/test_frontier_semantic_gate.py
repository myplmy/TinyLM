#!/usr/bin/env python3
"""C3 semantic triage regressions on an isolated temporary repository."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from frontier_semantic_gate import marker, prepare, verify_artifact, verify_handoff


class SemanticGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("test_plan", "handoff/audit", "docs/review", "proposal"):
            (self.root / name).mkdir(parents=True)
        (self.root / "test_plan/P014_old.md").write_text(
            "# P014 old\n\n## Stage0 미실행\n\n선결: backend attribution.\n",
            encoding="utf-8",
        )
        (self.root / "test_plan/P097_new.md").write_text(
            "# P097 new\n\n## Stage1 미실행\n\n선결: source decision.\n",
            encoding="utf-8",
        )
        (self.root / "test_plan/실험계획목록.md").write_text(
            "## 1. 계획만 있고 실행 전\n\n"
            "| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |\n"
            "|---|---|---|---|\n"
            "| [P014](P014_old.md) | old | gate | 2026-09-25 |\n"
            "## 2. 진행 중\n\n"
            "| [P097](P097_new.md) | new | data | 2026-09-25 |\n"
            "## 3. 종결\n", encoding="utf-8",
        )
        (self.root / "experiments.tsv").write_text(
            "prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\n",
            encoding="utf-8",
        )
        (self.root / "handoff/COMPASS.md").write_text(
            "| quality | P014 P097 |\n", encoding="utf-8",
        )
        self.proposal = self.root / "proposal/20260925_candidate-approved-on-going.md"
        self.proposal.write_text(
            "# approved ongoing\n\n> 상태: 구현 진행 중\n", encoding="utf-8",
        )
        self.handoff = self.root / "handoff/202609251234_HANDOFF.md"
        self.handoff.write_text(
            "## 7. 다음 권장 실험 순서\n\n"
            "| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |\n"
            "|---:|---:|---|---|---:|---:|---|---|---|---|\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _prepared(self):
        path, state, created = prepare(self.root)
        self.assertTrue(created)
        self.handoff.write_text(
            self.handoff.read_text(encoding="utf-8") + marker(path, state) + chr(10),
            encoding="utf-8",
        )
        return path, state

    @staticmethod
    def _fill(path):
        data = json.loads(path.read_text(encoding="utf-8"))
        by_id = {row["plan_id"]: row for row in data["plan_reviews"]}
        by_id["P014"].update(
            value_tier="HIGH", decision="BUILD_NEXT", priority=1, review="MANUAL",
            reason="old backend plan has a useful current attribution question",
            evidence="test_plan/P014_old.md Stage0",
            next_action="implement attribution diagnostic",
        )
        by_id["P097"].update(
            value_tier="MEDIUM", decision="USER_DECISION", review="MANUAL",
            reason="new data comparison needs an explicit source choice",
            evidence="test_plan/P097_new.md Stage1",
            next_action="ask user for source revision",
        )
        data["proposal_reviews"][0].update(
            decision="IMPLEMENT_NEXT", review="MANUAL",
            reason="ongoing research proposal has an unfinished implementation gate",
            evidence="proposal/20260925_candidate-approved-on-going.md status",
            next_action="implement the first functional test",
            linked_plans=["P014"],
        )
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + chr(10),
                        encoding="utf-8")
        return data

    def test_handoff_generator_announces_unverified_semantic_triage(self):
        from new_handoff import SKELETON
        self.assertIn("FRONTIER_SEMANTIC_NOT_VERIFIED", SKELETON)

    def test_template_is_not_a_review_and_manual_old_new_coverage_passes(self):
        path, _state = self._prepared()
        self.assertTrue(any("manual decision" in x for x in verify_artifact(self.root, path)))
        self._fill(path)
        self.assertEqual(verify_artifact(self.root, path), [])
        self.assertEqual(verify_handoff(self.root, self.handoff), [])
        self.assertEqual(prepare(self.root)[0], path)

    def test_missing_plan_or_proposal_and_rank_collision_fail(self):
        path, _state = self._prepared()
        data = self._fill(path)
        data["plan_reviews"] = data["plan_reviews"][:1]
        data["proposal_reviews"] = []
        path.write_text(json.dumps(data), encoding="utf-8")
        errors = verify_artifact(self.root, path)
        self.assertTrue(any("plan IDs" in x for x in errors))
        self.assertTrue(any("proposal paths" in x for x in errors))

    def test_no_launcher_is_not_a_value_decision(self):
        path, _state = self._prepared()
        data = self._fill(path)
        row = data["plan_reviews"][0]
        row.update(decision="LOW_PRIORITY", priority=None, reason="런처 없음")
        path.write_text(json.dumps(data), encoding="utf-8")
        errors = verify_artifact(self.root, path)
        self.assertTrue(any("launcher absence" in x for x in errors))
        self.assertTrue(any("need BUILD_NEXT" in x for x in errors))

    def test_duplicate_priority_and_copied_reason_fail(self):
        path, _state = self._prepared()
        data = self._fill(path)
        first, second = data["plan_reviews"]
        second.update(
            decision="BUILD_NEXT", value_tier="HIGH", priority=1,
            reason=first["reason"],
        )
        path.write_text(json.dumps(data), encoding="utf-8")
        errors = verify_artifact(self.root, path)
        self.assertTrue(any("priorities" in error for error in errors))
        self.assertTrue(any("copied value reason" in error for error in errors))

    def test_proposal_body_change_mints_new_artifact_and_preserves_old(self):
        path, _state = self._prepared()
        self._fill(path)
        old_bytes = path.read_bytes()
        self.proposal.write_text("# approved ongoing\n\n> 상태: 새 증거\n",
                                 encoding="utf-8")
        self.assertTrue(any("stale" in x for x in verify_artifact(self.root, path)))
        new_path, _state, created = prepare(self.root)
        self.assertTrue(created)
        self.assertNotEqual(path, new_path)
        self.assertEqual(path.read_bytes(), old_bytes)

    def test_marker_must_be_inside_seven(self):
        path, state = self._prepared()
        self._fill(path)
        stamp = marker(path, state)
        body = self.handoff.read_text(encoding="utf-8").replace(stamp, "")
        self.handoff.write_text(body + "## 8. 커밋\n" + stamp + chr(10),
                                encoding="utf-8")
        self.assertIn("exactly one", verify_handoff(self.root, self.handoff)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
