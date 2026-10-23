#!/usr/bin/env python3
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_native_appendix_overlay import proposal


class OverlayTests(unittest.TestCase):
    def test_reversible_appendix(self):
        original = "실제 본문과 사실을 그대로 보존합니다. " * 60 + "\n각주\n서지 원형\n외부 링크\nhttps://example.org\n"
        result = proposal(original)
        self.assertIsNotNone(result)
        self.assertEqual(result["body"] + result["appendix"], original)

    def test_body_list_not_appendix(self):
        text = "본문입니다. " * 100 + "\n선수 및 지도자\n이름: 역할\n통산기록\n3회\n"
        self.assertIsNone(proposal(text))

    def test_code_headings_are_not_footer(self):
        text = "HTML 예제 본문 " * 100 + "\n```\n각주\n외부 링크\n```\n"
        self.assertIsNone(proposal(text))

    def test_early_or_large_appendix_is_deferred(self):
        self.assertIsNone(proposal("각주\n" + "서지 " * 300 + "\n외부 링크\n"))

    def test_single_or_duplicate_heading_is_deferred(self):
        text = "본문 " * 300
        self.assertIsNone(proposal(text + "\n외부 링크\nurl"))
        self.assertIsNone(proposal(text + "\n각주\n각주\n외부 링크\nurl"))


if __name__ == "__main__":
    unittest.main()
