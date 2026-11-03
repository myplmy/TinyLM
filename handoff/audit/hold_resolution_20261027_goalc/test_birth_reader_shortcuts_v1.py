"""The short entry must preserve argv, stdout, failures, and reader pin checks."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

path = Path(__file__).with_name('prepare_birth_reader_shortcuts_v1.py')
spec = importlib.util.spec_from_file_location('reader_shortcuts', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ShortcutTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='hold_short_entry_'))
        self.reader = self.root / 'synthetic reader.py'
        self.reader.write_text('import json,sys; print(json.dumps(sys.argv[1:],ensure_ascii=False)); print("END synthetic")', encoding='utf-8')

    def wrapper(self):
        self.entry = self.root / 'short entry'
        self.entry.write_text(module.shortcut_text(sys.executable, self.reader,
            hashlib.sha256(self.reader.read_bytes()).hexdigest().upper()), encoding='utf-8')

    def call(self, *args):
        return subprocess.run(['bash', str(self.entry), *args], capture_output=True, text=True, timeout=10)

    def test_exact_arguments_and_end_are_preserved(self):
        self.wrapper()
        result = self.call('expanded_train:42', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[0]), ['--source-id', 'expanded_train:42', '--packet', '2'])
        self.assertTrue(result.stdout.endswith('END synthetic' + chr(10)))

    def test_metacharacters_are_literal_arguments(self):
        self.wrapper()
        marker = self.root / 'must_not_be_created'
        argument = '$(touch ' + str(marker) + '); echo unexpected'
        result = self.call(argument, '1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[0])[1], argument)
        self.assertFalse(marker.exists())

    def test_missing_or_extra_arguments_fail_before_reader(self):
        self.wrapper()
        for args in [(), ('one',), ('one', '2', 'extra'), ('one', '2', '--probe', 'extra')]:
            with self.subTest(args=args):
                result = self.call(*args)
                self.assertEqual(result.returncode, 64)
                self.assertEqual(result.stdout, '')

    def test_root_probe_is_forwarded_without_other_argument_changes(self):
        self.wrapper()
        result = self.call('expanded_train:42', '1', '--probe')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[0]), ['--source-id', 'expanded_train:42', '--packet', '1', '--probe'])

    def test_modified_reader_is_rejected_before_body(self):
        self.wrapper()
        with self.reader.open('a', encoding='utf-8') as stream:
            stream.write(chr(10) + 'print("CHANGED BODY")')
        result = self.call('expanded_train:42', '1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('fixed reader bytes changed', result.stderr)

    def test_reader_symlink_is_rejected(self):
        target = self.reader
        link = self.root / 'synthetic link.py'
        link.symlink_to(target)
        self.reader = link
        self.wrapper()
        result = self.call('expanded_train:42', '1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_failure_status_and_stderr_are_preserved(self):
        self.reader.write_text('import sys; print("synthetic failure",file=sys.stderr); raise SystemExit(23)', encoding='utf-8')
        self.wrapper()
        result = self.call('expanded_train:42', '1')
        self.assertEqual(result.returncode, 23)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, 'synthetic failure' + chr(10))


if __name__ == '__main__':
    unittest.main()
