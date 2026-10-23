#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_native_format_candidate import transform


class FormatTests(unittest.TestCase):
    def test_empty_heading_chain_only(self):
        text, removed, _, _ = transform("본문\n각주\n외부 링크\n")
        self.assertEqual(text, "본문\n")
        self.assertEqual(len(removed), 2)

    def test_reference_content_and_outline_preserved(self):
        source = "본문\n참고 문헌\n저자 (2020). 제목.\n선수 및 지도자\n홍길동\n"
        text, _, review, _ = transform(source)
        self.assertEqual(text, source)
        self.assertIn("structured_list_relation_needs_source_reading", review)

    def test_code_and_html_are_not_semantically_rewritten(self):
        source = "HTML 예: <p>Hello</p>\n```\n각주\n```\n"
        self.assertEqual(transform(source)[0], source)

    def test_empty_result_retains_original(self):
        source = "외부 링크\n"
        self.assertEqual(transform(source)[0], source)
        self.assertIn("empty_after_proposal_original_retained", transform(source)[2])

    def test_heading_in_inline_code_preserved(self):
        self.assertEqual(transform("문장\n`참고 문헌`\n")[0], "문장\n`참고 문헌`\n")


if __name__ == "__main__":
    unittest.main()
