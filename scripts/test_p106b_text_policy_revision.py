#!/usr/bin/env python3
"""CPU-only text provenance/turn-preservation regression."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_text_policy_revision import apply_override, apply_spans, merge_messages


class PolicyRevisionTests(unittest.TestCase):
    def test_list_becomes_source_grounded_sentence(self):
        change = {"source_span": "배우\n이범수", "action": "MOVE_TO_PROSE", "replacement": "이범수가 연기했다."}
        self.assertEqual(apply_spans("본문\n배우\n이범수", [change]), "본문\n이범수가 연기했다.")

    def test_remove_never_adds_text(self):
        with self.assertRaisesRegex(ValueError, "must not add"):
            apply_spans("참고", [{"source_span": "참고", "action": "REMOVE", "replacement": "추가"}])

    def test_remove_may_preserve_word_boundary_space(self):
        self.assertEqual(apply_spans("앞 제목 뒤", [{"source_span": " 제목 ", "action": "REMOVE", "replacement": " "}]), "앞 뒤")

    def test_ambiguous_span_rejected(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            apply_spans("참고참고", [{"source_span": "참고", "action": "REMOVE", "replacement": ""}])

    def test_empty_changes_preserve_exact_source(self):
        self.assertEqual(apply_spans("원문\n\n", []), "원문\n\n")

    def test_partial_answer_preserves_question(self):
        original = [{"role": "user", "content": "편광계란?"}, {"role": "assistant", "content": "이전"}]
        revised, partial = merge_messages(original, [{"role": "assistant", "content": "광회전을 측정하는 기기"}])
        self.assertEqual(revised[0], original[0]); self.assertTrue(partial)
        self.assertEqual(original[1]["content"], "이전")

    def test_partial_user_preserves_answer(self):
        original = [{"role": "user", "content": "이전 질문"}, {"role": "assistant", "content": "답"}]
        revised, _ = merge_messages(original, [{"role": "user", "content": "새 질문"}])
        self.assertEqual(revised[1], original[1])

    def test_ambiguous_multiturn_partial_rejected(self):
        original = [{"role": role, "content": "값"} for role in ("user", "assistant", "user", "assistant")]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            merge_messages(original, [{"role": "assistant", "content": "새 답"}])

    def test_full_multiturn_patch_preserves_roles(self):
        original = [{"role": role, "content": "값"} for role in ("user", "assistant", "user", "assistant")]
        revised, partial = merge_messages(original, original)
        self.assertEqual(revised, original); self.assertFalse(partial)

    def test_unknown_role_rejected(self):
        with self.assertRaisesRegex(ValueError, "absent"):
            merge_messages([{"role": "user", "content": "질문"}], [{"role": "system", "content": "새 값"}])

    def test_stale_manual_override_rejected(self):
        raw = {"decision": "REWRITE", "changes": [{"replacement": "실제"}]}
        with self.assertRaisesRegex(ValueError, "stale"):
            apply_override(raw, {"changes": [{"index": 0, "expected_replacement": "옛값", "replacement": ""}]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
