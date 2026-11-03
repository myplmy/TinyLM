"""The short field call keeps literal argv, role binding and the fixed module."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

path = Path(__file__).with_name('prepare_field_short_readers_v1.py')
spec = importlib.util.spec_from_file_location('field_shortcut_builder_tested', path)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class FieldShortcutTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='hold_field_shortcut_'))
        self.old_root, self.old_python = builder.ROOT, builder.PYTHON
        builder.ROOT, builder.PYTHON = self.root, Path(sys.executable)
        self.module = self.root / 'synthetic module.py'
        self.module.write_text('import json,sys\ndef cli(root,role,config):\n print(json.dumps(dict(role=role,argv=sys.argv[1:],config=config)))\n', encoding='utf-8')
        self.module_pin = dict(path=self.module.name, sha256=hashlib.sha256(self.module.read_bytes()).hexdigest().upper())
        self.config_pin = dict(path='synthetic config.json', sha256='A' * 64)
        self.wrapper = self.root / 'short field entry'
        self.wrapper.write_text(builder.launcher('bound_role_a', self.config_pin, self.module_pin), encoding='utf-8')

    def tearDown(self):
        builder.ROOT, builder.PYTHON = self.old_root, self.old_python

    def call(self, *args):
        return subprocess.run(['bash', str(self.wrapper), *args], capture_output=True, text=True, timeout=10)

    def test_role_page_id_packet_and_optional_piece_are_exact(self):
        for args, piece in [(('5', 'expanded_train:42', '2'), '1'), (('6', 'expanded_train:43', '3', '2'), '2')]:
            result = self.call(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(value['role'], 'bound_role_a')
            self.assertEqual(value['argv'], ['--page', args[0], '--source-id', args[1], '--packet', args[2], '--piece', piece])
            self.assertEqual(value['config'], self.config_pin)

    def test_shell_metacharacters_remain_literal(self):
        marker = self.root / 'must_not_be_created'
        argument = '$(touch ' + str(marker) + '); unexpected'
        result = self.call('5', argument, '1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['argv'][3], argument)
        self.assertFalse(marker.exists())

    def test_invalid_argument_count_or_modified_module_never_emits_body(self):
        for args in [(), ('5',), ('5', 'id'), ('5', 'id', '1', '1', 'extra')]:
            result = self.call(*args)
            self.assertEqual(result.returncode, 64)
            self.assertEqual(result.stdout, '')
        with self.module.open('a') as stream:
            stream.write(chr(10) + 'print("changed body")')
        result = self.call('5', 'expanded_train:42', '1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
