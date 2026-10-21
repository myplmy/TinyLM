from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import unittest
from scripts.p106b_source_cleanup import clean_text, safe, ROOT


class CleanupTests(unittest.TestCase):
    def test_balanced_tags(self):
        value, changes, warnings = clean_text("<p>사과 <b>3개</b></p>")
        self.assertIn("사과 3개", value)
        self.assertEqual(changes["balanced_presentation_tags"], 4)

    def test_math(self):
        s = "x < y 이고 y > 2이며 a != b다."
        self.assertEqual(clean_text(s)[0], s)

    def test_fenced_code_and_inline(self):
        s = "```html\n<b>x</b>\n```\n`<p>x</p>`"
        self.assertEqual(clean_text(s)[0], s)

    def test_entity_is_not_reparsed(self):
        self.assertEqual(clean_text("&lt;b&gt;x&lt;/b&gt;")[0], "&lt;b&gt;x&lt;/b&gt;")

    def test_unclosed_preserved(self):
        s = "<b>잘리지 않은 내용"
        value, _, warns = clean_text(s)
        self.assertEqual(value, s); self.assertIn("unbalanced_html_preserved", warns)

    def test_complex_preserved(self):
        s = "<script>example()</script> {{틀|이름}} {| 표 |}"
        value, _, warns = clean_text(s)
        self.assertEqual(value, s); self.assertEqual(len(warns), 2)

    def test_wiki_explicit(self):
        s = "[[사과|과일]]\n[[분류:식물]]"
        self.assertEqual(clean_text(s, "wikipedia_text")[0], "과일\n")
        self.assertEqual(clean_text(s)[0], s)

    def test_no_bad_phrase_list(self):
        s = "갑상선기능과장증과 일본어 日本語, English, 사과 사과 사과"
        self.assertEqual(clean_text(s)[0], s)

    def test_idempotence(self):
        s = "<p><b>3</b>개</p>"
        a = clean_text(s)[0]
        self.assertEqual(clean_text(a)[0], a)

    def test_protected_path(self):
        with self.assertRaises(ValueError): safe(ROOT / "datasets/TinyDataset/test")


if __name__ == "__main__":
    unittest.main()
