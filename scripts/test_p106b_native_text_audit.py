#!/usr/bin/env python3
"""Offline audit regression; no model, GPU, or original corpus mutation."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import (plain_content, signals, tail_proposal,
                                            validate_deletion, validate_variant_conversation)
from scripts.p106b_source_cleanup import sha


class TextAuditTests(unittest.TestCase):
    def test_plain_headings_are_seen(self):
        counts, heads = signals("본문\n\n참고 문헌\n책1\n외부 링크\nhttps://example.test/a\n")
        self.assertEqual(counts["standalone_heading_lines"], 2)
        self.assertEqual(heads["참고 문헌"], 1)
        self.assertEqual(counts["url_occurrences"], 1)

    def test_inline_heading_word_is_not_a_page_heading(self):
        counts, _ = signals("참고 문헌은 주장에 대한 근거를 밝히는 목록이다.")
        self.assertNotIn("standalone_heading_lines", counts)

    def test_code_html_math_preserved(self):
        text = "```html\n<div>References</div>\n```\n`www.example.test`\nx < y\n"
        counts, _ = signals(text)
        self.assertNotIn("html_tag_occurrences", counts)
        self.assertNotIn("url_occurrences", counts)
        self.assertEqual(tail_proposal(text), (text, []))

    def test_empty_final_heading_proposal_only(self):
        result, spans = tail_proposal("본문\n\n같이 보기\n")
        self.assertEqual(result, "본문\n\n")
        self.assertEqual(spans[0]["text"], "같이 보기\n")

    def test_nonempty_references_and_lists_are_retained(self):
        text = "약품분류\nA10 당뇨\n참고 문헌\nKim 2020\nLee 2022\n"
        self.assertEqual(tail_proposal(text), (text, []))

    def test_final_heading_inside_code_is_not_removed(self):
        text = "```\nReferences\n```"
        self.assertEqual(tail_proposal(text), (text, []))

    def test_repeat_signal_is_not_a_delete_action(self):
        text = "동일한 문장입니다.\n동일한 문장입니다."
        self.assertEqual(signals(text)[0]["within_doc_repeated_line_extras"], 1)
        self.assertEqual(tail_proposal(text), (text, []))

    def test_explicit_categories_and_html(self):
        counts, _ = signals("분류: 사람\n<p>본문</p>\n")
        self.assertEqual(counts["explicit_category_lines"], 1)
        self.assertEqual(counts["html_tag_occurrences"], 2)

    def source(self, text):
        return {"text": text, "sha256": sha(text)}

    def test_exact_deletion(self):
        original = "본문\n외부 링크\nURL"
        row = dict(decision="EXTRACT_APPENDIX", cleaned_text="본문", removed_spans=[{"text": "\n외부 링크\nURL"}])
        self.assertEqual(validate_deletion(self.source(original), row), "본문")

    def test_undeclared_rewrite_rejected(self):
        row = dict(decision="EXTRACT_APPENDIX", cleaned_text="새본문", removed_spans=[{"text": "\n꼬리"}])
        with self.assertRaisesRegex(ValueError, "beyond"):
            validate_deletion(self.source("본문\n꼬리"), row)

    def test_keep_with_deletion_rejected(self):
        row = dict(decision="KEEP", cleaned_text="본문", removed_spans=[{"text": "꼬리"}])
        with self.assertRaisesRegex(ValueError, "KEEP"):
            validate_deletion(self.source("꼬리본문"), row)

    def test_hash_and_ambiguous_span_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA"):
            validate_deletion({"text": "본문", "sha256": "wrong"}, {"cleaned_text": "본문"})
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            validate_deletion(self.source("가나가나본문"), dict(decision="EXTRACT_APPENDIX", cleaned_text="가나본문", removed_spans=[{"text": "가나"}]))

    def test_text_blocks_preserved(self):
        self.assertEqual(plain_content([{"type": "text", "text": "앞"}, {"type": "text", "text": "뒤"}]), "앞뒤")

    def test_nontext_block_not_silently_stringified(self):
        with self.assertRaisesRegex(ValueError, "non-text"):
            plain_content([{"type": "image", "url": "unresolved"}])

    def test_four_turns_remain_four(self):
        messages = [{"role": r, "content": "원문"} for r in ("user", "assistant", "user", "assistant")]
        translated = [{"role": r, "content": "번역"} for r in ("user", "assistant", "user", "assistant")]
        self.assertEqual(validate_variant_conversation(messages, {"messages": translated}), translated)

    def test_four_turn_collapse_rejected(self):
        messages = [{"role": r, "content": "원문"} for r in ("user", "assistant", "user", "assistant")]
        with self.assertRaisesRegex(ValueError, "collapsed"):
            validate_variant_conversation(messages, {"question": "합친 질문", "answer": "합친 답"})

    def test_two_turn_translation_and_wrong_roles(self):
        original = [{"role": "user", "content": "Q"}, {"role": "assistant", "content": "A"}]
        self.assertEqual(len(validate_variant_conversation(original, {"question": "질문", "answer": "답"})), 2)
        with self.assertRaisesRegex(ValueError, "roles"):
            validate_variant_conversation(original, {"messages": list(reversed(original))})


if __name__ == "__main__":
    unittest.main(verbosity=2)
