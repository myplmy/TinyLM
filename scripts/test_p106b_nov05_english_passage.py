"""Typed source parsing and dual-version replay boundaries; CPU only."""
import copy
import unittest
from unittest.mock import patch

from scripts import diag_p106b_nov05_english_passage as view


def source(text):
    return dict(messages=[dict(role='user', content=text),
                          dict(role='assistant', content='old question or answer list')])


class ArticleViewTests(unittest.TestCase):
    def test_utf8_byte_slice_matches_complete_article(self):
        text = '  A cafe named caf\u00e9 serves tea.\n\n' + view.MARKERS[0] + '\n1. Old question'
        article, trace = view.article(source(text))
        self.assertEqual(article, 'A cafe named caf\u00e9 serves tea.')
        self.assertEqual(text.encode()[trace['start_byte']:trace['end_byte']].decode(), article)

    def test_original_messages_are_not_modified(self):
        row = source('The article.\n\n' + view.MARKERS[1] + '\nold questions')
        before = copy.deepcopy(row)
        view.article(row)
        self.assertEqual(row, before)

    def test_unknown_or_multiple_boundaries_fail(self):
        for text in ('An unsupported source.', 'A.\n' + view.MARKERS[0] + '\n' + view.MARKERS[1],
                     'A.\n' + view.MARKERS[0] + '\n' + view.MARKERS[0]):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    view.article(source(text))

    def test_inline_or_empty_article_fails(self):
        for text in ('An inline ' + view.MARKERS[0], view.MARKERS[0]):
            with self.assertRaises(ValueError):
                view.article(source(text))

    def test_parent_v3_and_new_view_versions_are_separate(self):
        original_version, original_replay = view.supported.VERSION, view.supported.replay
        def parent(*args, **kwargs):
            self.assertEqual(view.supported.VERSION, view.V3)
            return 'parent'
        def new(*args, **kwargs):
            self.assertEqual(view.supported.VERSION, view.VIEW)
            self.assertEqual(view.supported.replay(), 'parent')
            self.assertEqual(view.supported.VERSION, view.VIEW)
            return 'new'
        with patch.object(view, 'BASE_REPLAY', parent), patch.object(view.base, 'replay_new', new):
            self.assertEqual(view.replay_typed(None, None, None, None, None), 'new')
        self.assertEqual(view.supported.VERSION, original_version)
        self.assertIs(view.supported.replay, original_replay)

    def test_exception_restores_replay_version(self):
        original_version, original_replay = view.supported.VERSION, view.supported.replay
        with patch.object(view.base, 'replay_new', side_effect=RuntimeError('fixture')):
            with self.assertRaises(RuntimeError):
                view.replay_typed(None, None, None, None, None)
        self.assertEqual(view.supported.VERSION, original_version)
        self.assertIs(view.supported.replay, original_replay)


if __name__ == '__main__':
    unittest.main()
