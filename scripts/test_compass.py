"""Synthetic Markdown only: no model, dataset, real result writes or GPU."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compass


class CompassHeadings(unittest.TestCase):
    def test_shell_archive_comment_is_not_depth_evidence(self):
        text = '# Actual result\n```bash\n# cap1800s, old d18 comment\n```\n## SFT first answers\n'
        self.assertEqual(compass.markdown_headings(text), ['# Actual result', '## SFT first answers'])

    def test_real_axis_heading_after_code_remains_visible(self):
        heads = compass.markdown_headings('```bash\n# ignored\n```\n## d18 depth actual\n')
        self.assertEqual(heads, ['## d18 depth actual'])
        self.assertEqual(compass.newest_mentioning({101: (None, heads)}, ('d18',)), 101)

    def test_tilde_fence_and_indented_open_close(self):
        self.assertEqual(compass.markdown_headings('   ~~~text\n## d18\n  ~~~~  \n  ### Real\n'), ['### Real'])

    def test_shorter_inner_backticks_do_not_close_outer_four(self):
        text = '````text\n```bash\n# d18\n```\n## still code\n````\n# Actual\n'
        self.assertEqual(compass.markdown_headings(text), ['# Actual'])

    def test_other_fence_character_does_not_close(self):
        self.assertEqual(compass.markdown_headings('~~~\n```\n## code\n~~~\n## Real\n'), ['## Real'])

    def test_unclosed_code_is_not_promoted_to_heading(self):
        self.assertEqual(compass.markdown_headings('# Before\n```bash\n## d18\n'), ['# Before'])

    def test_heading_requires_whitespace_and_at_most_six_hashes(self):
        text = '#!/usr/bin/env bash\n#not-title\n####### not heading\n# Title\n###### Last\n'
        self.assertEqual(compass.markdown_headings(text), ['# Title', '###### Last'])

    def test_four_space_indented_text_is_not_atx_heading_or_fence(self):
        self.assertEqual(compass.markdown_headings('    # d18\n    ```\n## Real\n'), ['## Real'])

    def test_backtick_in_info_string_is_not_fence(self):
        self.assertEqual(compass.markdown_headings('```invalid`info\n## Real\n'), ['## Real'])

    def test_closing_fence_with_info_is_not_close(self):
        self.assertEqual(compass.markdown_headings('```\n```info\n## code\n```\n## Real\n'), ['## Real'])

    def test_real_result_reader_retains_numbers_and_axis_rule(self):
        with tempfile.TemporaryDirectory(prefix='compass_markdown_synthetic_') as folder:
            path = Path(folder)
            (path / '100_example.md').write_text('# d18 actual\n', encoding='utf-8')
            (path / '101_example.md').write_text('# SFT\n```bash\n# cap1800s\n```\n', encoding='utf-8')
            with patch.object(compass, 'RESULTS', path):
                docs = compass.result_docs()
            self.assertEqual(compass.newest_mentioning(docs, ('d18',)), 100)
            self.assertEqual(compass.newest_mentioning(docs, ('SFT',)), 101)


if __name__ == '__main__':
    unittest.main()
