#!/usr/bin/env python3
"""Meaning-sensitive CPU regressions for the whole-pool inventory."""
from array import array
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106b_corpus_cleanup import propose, segments, open_fence, language_bucket


class TextProtection(unittest.TestCase):
    def test_negative_condition_numbers_survive_empty_tail(self):
        text="광회전은 20 °C에서 관찰되지 않을 수 있다.\n조건 A이면 2018년 3월 2일 자료를 쓴다.\n외부 링크\n각주\n"
        candidate,removed,_,risk=propose(text)
        self.assertEqual(candidate,"광회전은 20 °C에서 관찰되지 않을 수 있다.\n조건 A이면 2018년 3월 2일 자료를 쓴다.\n")
        self.assertEqual(len(removed),2)
        self.assertFalse(risk)

    def test_unclosed_code_not_truncated(self):
        text="예제:\n```text\nReferences\n"
        candidate,removed,_,risk=propose(text)
        self.assertEqual(candidate,text)
        self.assertFalse(removed)
        self.assertIn("OPEN_CODE_FENCE_CONTEXT",risk)

    def test_code_html_and_headings_are_not_noise(self):
        text="예제:\n```html\n<div>각주</div>\nReferences\n```\n"
        candidate,removed,_,risk=propose(text)
        self.assertEqual(candidate,text)
        self.assertEqual(removed,[])
        self.assertEqual(risk,[])

    def test_academic_reference_is_preserved_for_context(self):
        text="진화 가설은 확정되지 않았다.\n참고 문헌\nSmith, 2011, pp. 12–14.\n"
        candidate,_,_,risk=propose(text)
        self.assertEqual(candidate,text)
        self.assertIn("APPENDIX_OR_NAVIGATION_CONTEXT",risk)

    def test_repetition_is_held_without_deletion(self):
        text="그는 ‘돌아오라’고 말했다.\n그는 ‘돌아오라’고 말했다.\n"
        candidate,_,_,risk=propose(text)
        self.assertEqual(candidate,text)
        self.assertIn("REPETITION_CONTEXT",risk)

    def test_historical_transcription_not_regex_stripped(self):
        text="Darwin wrote: <del>not known</del>. The editor notes an uncertainty."
        candidate,_,_,risk=propose(text)
        self.assertEqual(candidate,text)
        self.assertIn("MARKUP_OR_SCHOLARLY_TRANSCRIPTION_CONTEXT",risk)

    def test_broken_table_not_filled(self):
        text="2012–13 대회 설명\n{| class=wikitable\n| colspan=4 |\n|}\n"
        candidate,_,_,risk=propose(text)
        self.assertEqual(candidate,text)
        self.assertIn("BROKEN_WIKI_OR_TABLE_CONTEXT",risk)

    def test_retail_information_not_deleted_by_ui_detector(self):
        text="The guide covers 978 species.\nSKU: 1234\nAdd to cart\n"
        candidate,_,_,risk=propose(text)
        self.assertEqual(candidate,text)
        self.assertIn("COMMERCIAL_OR_COOKIE_UI_CONTEXT",risk)

    def test_language_bucket_is_only_observed_character_presence(self):
        self.assertEqual(language_bucket("日本語 English"),"NO_HANGUL")
        self.assertEqual(language_bucket("광회전 English"),"HAS_HANGUL")

    def test_fence_closing_requires_no_trailing_code(self):
        self.assertTrue(open_fence("```python\nx=1\n```not a closer"))
        self.assertFalse(open_fence("~~~~text\nx\n~~~~"))


class IntervalAccounting(unittest.TestCase):
    def test_eos_and_incomplete_tail_account_for_every_id(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_intervals_") as folder:
            path=Path(folder)/"input.bin"
            path.write_bytes(array("H",[7,8,2,9,2,10,11]).tobytes())
            rows=list(segments(path))
            self.assertEqual([(r[1],r[2],r[5]) for r in rows],[(0,3,True),(3,5,True),(5,7,False)])
            self.assertEqual(b"".join(r[3] for r in rows),path.read_bytes())

    def test_resume_at_completed_unit_boundary_has_no_overlap(self):
        with tempfile.TemporaryDirectory(prefix="cleanup_resume_") as folder:
            path=Path(folder)/"input.bin"
            path.write_bytes(array("H",[7,2,8,2,9,2]).tobytes())
            first=list(segments(path,limit=1))
            rest=list(segments(path,start=first[-1][2],ordinal=1))
            self.assertEqual([r[0] for r in first+rest],[0,1,2])
            self.assertEqual(b"".join(r[3] for r in first+rest),path.read_bytes())


if __name__=="__main__":
    unittest.main()
