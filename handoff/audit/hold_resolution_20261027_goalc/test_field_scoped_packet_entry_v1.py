"""Protection and role checks must precede every packet-reader invocation."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

path = Path(__file__).with_name('field_scoped_packet_entry_v1.py')
spec = importlib.util.spec_from_file_location('field_entry_tested', path)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class FieldEntryTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='hold_field_entry_'))
        self.contract = dict(restricted_ids=['expanded_train:7'], restricted_hashes=['B' * 64])
        self.registry = dict(role='role_a', page=5, allowed_packet_directory='synthetic',
                             sources={'expanded_train:42': [dict(path='synthetic/42_0001.txt', sha256='C' * 64)]},
                             source_metadata={'expanded_train:42': dict(role='role_a', original_sha256='A' * 64)})
        self.calls = []
        self.refresh()

    def write(self, name, value):
        path = self.root / name
        data = json.dumps(value).encode()
        path.write_bytes(data)
        return dict(path=name, sha256=entry.hashlib.sha256(data).hexdigest().upper())

    def refresh(self):
        contract_pin = self.write('contract.json', self.contract)
        self.registry_pin = self.write('registry.json', self.registry)
        self.config_pin = self.write('config.json', dict(schema='FIELD_SCOPED_SHORT_ENTRY_V1',
            contract=contract_pin, roles={'role_a': {'5': self.registry_pin}}))

    def spy(self, *args):
        self.calls.append(args)
        return dict(text='synthetic body', source_id=args[3], packet=args[4], piece=args[5])

    def read(self, role='role_a', page=5, ident='expanded_train:42', packet=1, piece=1):
        return entry.read_assigned(self.root, self.config_pin, role, page, ident, packet, piece, self.spy)

    def test_exact_assignment_passes_unchanged_reader_arguments(self):
        row = self.read(packet=2, piece=3)
        self.assertEqual(row['text'], 'synthetic body')
        self.assertEqual(self.calls, [(self.root / 'registry.json', self.registry_pin['sha256'],
                                      self.root, 'expanded_train:42', 2, 3)])

    def test_restricted_id_fails_before_registry_or_helper(self):
        (self.root / 'registry.json').write_bytes(b'not even a readable registry')
        with self.assertRaisesRegex(ValueError, 'restricted source ID'):
            self.read(ident='expanded_train:7')
        self.assertEqual(self.calls, [])

    def test_same_restricted_hash_under_unrestricted_alias_fails_before_helper(self):
        self.registry['source_metadata']['expanded_train:42']['original_sha256'] = 'B' * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'restricted original SHA'):
            self.read()
        self.assertEqual(self.calls, [])

    def test_other_role_page_or_source_cannot_borrow_assignment(self):
        for update in [dict(role='role_b'), dict(page=6), dict(ident='expanded_train:43')]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.read(**update)
        self.assertEqual(self.calls, [])

    def test_changed_registry_or_config_fails_before_helper(self):
        for name in ('registry.json', 'config.json'):
            self.refresh()
            (self.root / name).write_bytes(b'changed metadata')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'pinned metadata bytes changed'):
                self.read()
        self.assertEqual(self.calls, [])

    def test_registry_or_source_role_mismatch_fails_before_helper(self):
        self.registry['role'] = 'role_b'
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'registry role/page changed'):
            self.read()
        self.registry['role'] = 'role_a'
        self.registry['source_metadata']['expanded_train:42']['role'] = 'role_b'
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'source role changed'):
            self.read()
        self.assertEqual(self.calls, [])

    def test_symlink_metadata_is_rejected(self):
        path = self.root / 'config_link.json'
        path.symlink_to(self.root / 'config.json')
        self.config_pin = dict(self.config_pin, path=path.name)
        with self.assertRaisesRegex(ValueError, 'metadata left trusted root'):
            self.read()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
