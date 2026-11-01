"""정확 파일명 경로·Git 실패와 기존 미래10분 기준의 CPU 회귀."""
from datetime import datetime
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from scripts import handoff_time as target
except ModuleNotFoundError:
    import handoff_time as target


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root/'handoff/202610261536_HANDOFF.md'
        self.path.parent.mkdir()
        self.path.write_text('fixture only',encoding='utf-8')
        patch = mock.patch.object(target,'ROOT',self.root)
        patch.start();self.addCleanup(patch.stop)
        self.addCleanup(self.temp.cleanup)

    def test_similar_other_filename_is_not_followed(self):
        def history(command,**kwargs):
            old = '--follow' in command
            return SimpleNamespace(returncode=0,stdout='2026-10-26 05:19:58' if old else '2026-10-26 16:47:41')
        with mock.patch.object(target.subprocess,'run',side_effect=history) as run:
            self.assertEqual(target.audit_one(self.path)[0],'ok')
        args = run.call_args.args[0]
        self.assertIn('--no-renames',args)
        self.assertNotIn('--follow',args)
        self.assertEqual(args[-2:],['--','handoff/202610261536_HANDOFF.md'])

    def test_readded_exact_path_uses_earliest_author_time(self):
        result = SimpleNamespace(returncode=0,stdout=chr(10).join([
            '2026-10-29 10:00:00','2026-10-26 16:47:41','2026-10-27 18:00:00']))
        with mock.patch.object(target.subprocess,'run',return_value=result):
            self.assertEqual(target.first_commit(self.path),datetime(2026,10,26,16,47,41))

    def test_malformed_git_line_is_not_time_evidence(self):
        result = SimpleNamespace(returncode=0,stdout='not-a-time'+chr(10)+'2026-10-26 16:47:41')
        with mock.patch.object(target.subprocess,'run',return_value=result):
            self.assertEqual(target.first_commit(self.path),datetime(2026,10,26,16,47,41))

    def test_git_failure_is_not_a_fabricated_timestamp(self):
        with mock.patch.object(target.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')):
            self.assertIsNone(target.first_commit(self.path))

    def test_git_timeout_remains_unknown(self):
        with mock.patch.object(target.subprocess,'run',side_effect=subprocess.TimeoutExpired('git',30)):
            self.assertIsNone(target.first_commit(self.path))

    def test_uncommitted_path_uses_actual_mtime(self):
        expected = datetime(2026,10,26,15,37)
        os.utime(self.path,(expected.timestamp(),expected.timestamp()))
        with mock.patch.object(target.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='')):
            value,source = target.evidence(self.path)
        self.assertEqual(value,expected)
        self.assertIn('mtime',source)

    def test_exact_ten_minutes_allowed_but_next_second_rejected(self):
        with mock.patch.object(target,'evidence',return_value=(datetime(2026,10,26,15,26),'fixture')):
            self.assertEqual(target.audit_one(self.path)[0],'ok')
        with mock.patch.object(target,'evidence',return_value=(datetime(2026,10,26,15,25,59),'fixture')):
            self.assertEqual(target.audit_one(self.path)[0],'bad')

    def test_rounded_minute_is_not_a_statistical_error(self):
        with mock.patch.object(target,'evidence',return_value=(datetime(2026,11,1,6,59),'fixture')):
            self.assertEqual(target.audit_one(self.root/'202611010700_HANDOFF.md')[0],'ok')

    def test_outside_repository_does_not_invoke_git(self):
        with mock.patch.object(target.subprocess,'run') as run:
            self.assertIsNone(target.first_commit(self.root.parent/'outside_HANDOFF.md'))
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
