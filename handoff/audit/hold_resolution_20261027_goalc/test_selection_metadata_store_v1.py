"""Storage integrity regressions; only disposable, small metadata fixtures."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import io
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import selection_metadata_store_v1 as store


class SelectionStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix='hold-selection-storage-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.storage = store.SelectionStore(self.directory)
        self.path = self.directory / 'ROOT_AUTHORED_SELECTIONS_V1.json'
        self.document = {'status': 'TEST_METADATA', 'rows': [
            {'id': 'expanded_train:' + str(i), 'reason': '한글\r\nλ ' + str(i)}
            for i in range(513)], 'source_ids': 513,
            'cache_admitted': False, 'goal_complete': False}

    def write(self):
        receipt = self.storage.write(self.path, self.document, force_sharded=True)
        header = json.loads(self.path.read_bytes())
        return receipt, header

    def alter_header(self, header):
        self.path.write_bytes(store.encode(header))

    def test_inline_remains_native_json(self):
        receipt = self.storage.write(self.path, self.document)
        self.assertEqual(receipt['storage'], 'INLINE')
        self.assertEqual(json.loads(self.path.read_bytes()), self.document)
        self.assertEqual(self.storage.read(self.path, receipt['sha256']), self.document)

    def test_round_trip_preserves_order_unicode_and_crlf(self):
        receipt, _ = self.write()
        restored = self.storage.read(self.path, receipt['sha256'])
        self.assertEqual(restored, self.document)
        self.assertEqual(list(restored), list(self.document))
        self.assertEqual(store.encode(restored), store.encode(self.document))

    def test_independent_concatenation_matches_native_json(self):
        _, header = self.write()
        rows = []
        for pin in header['row_shards']:
            rows += json.loads((self.directory / pin['path']).read_bytes())
        independent = {key: rows if key == 'rows' else header['native_metadata'][key]
                       for key in header['native_key_order']}
        self.assertEqual(independent, self.document)
        self.assertEqual(store.digest(store.encode(independent)), header['logical_json_sha256'])

    def test_append_reuses_complete_earlier_row_group(self):
        first, header = self.write()
        next_document = deepcopy(self.document)
        next_document['rows'].append({'id': 'expanded_train:513', 'reason': '추가'})
        next_document['source_ids'] += 1
        second = self.storage.write(self.directory / 'ROOT_AUTHORED_SELECTIONS_V2.json',
                                    next_document, force_sharded=True)
        self.assertEqual(first['created_shards'], 2)
        self.assertEqual(second['reused_shards'], 1)
        self.assertEqual(second['created_shards'], 1)
        self.assertEqual(second['created_shard_bytes'],
                         len(store.encode(next_document['rows'][512:])))

    def test_bound_loads_and_json_load_preserve_physical_sha(self):
        receipt, _ = self.write()
        physical = self.path.read_bytes()
        with store.bound_selection_loads([(self.path, receipt['sha256'])], directory=self.directory):
            self.assertEqual(json.loads(physical), self.document)
            self.assertEqual(json.load(io.StringIO(physical.decode())), self.document)
            self.assertEqual(store.digest(self.path.read_bytes()), receipt['sha256'])
        self.assertEqual(json.loads(physical)[store.FORMAT_KEY], store.FORMAT)

    def test_bound_results_are_independent_objects(self):
        receipt, _ = self.write()
        with store.bound_selection_loads([(self.path, receipt['sha256'])], directory=self.directory):
            first = json.loads(self.path.read_bytes())
            first['rows'][0]['reason'] = 'changed only in caller'
            self.assertEqual(json.loads(self.path.read_bytes()), self.document)

    def test_unbound_manifest_rejected(self):
        self.write()
        with store.bound_selection_loads([], directory=self.directory):
            with self.assertRaisesRegex(ValueError, 'not explicitly SHA bound'):
                json.loads(self.path.read_bytes())

    def test_wrong_manifest_sha_rejected_before_binding(self):
        self.write()
        with self.assertRaisesRegex(ValueError, 'SHA differs'):
            with store.bound_selection_loads([(self.path, '0' * 64)], directory=self.directory):
                self.fail('must not enter')

    def test_ordinary_json_and_quoted_marker_are_unchanged(self):
        data = {'example': store.FORMAT_KEY, 'rows': 'quoted example', 'text': '한글'}
        with store.bound_selection_loads([], directory=self.directory):
            self.assertEqual(json.loads(store.encode(data)), data)
            self.assertEqual(json.loads('12'), 12)

    def test_decoder_hook_for_bound_manifest_is_rejected(self):
        receipt, _ = self.write()
        with store.bound_selection_loads([(self.path, receipt['sha256'])], directory=self.directory):
            with self.assertRaisesRegex(ValueError, 'custom decoder'):
                json.loads(self.path.read_bytes(), object_hook=lambda value: value)

    def test_missing_shard_rejected(self):
        _, header = self.write()
        (self.directory / header['row_shards'][0]['path']).unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.storage.read(self.path)

    def test_corrupt_shard_rejected(self):
        _, header = self.write()
        shard = self.directory / header['row_shards'][0]['path']
        raw = shard.read_bytes()
        shard.write_bytes(raw.replace(b'TRAIN', b'train') if b'TRAIN' in raw else b' ' + raw[1:])
        with self.assertRaisesRegex(ValueError, 'SHA differs'):
            self.storage.read(self.path)

    def test_reordered_shards_rejected(self):
        _, header = self.write()
        header['row_shards'].reverse()
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'logical JSON SHA differs'):
            self.storage.read(self.path)

    def test_missing_ordered_shard_rejected(self):
        _, header = self.write()
        header['row_shards'].pop()
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'source count differs'):
            self.storage.read(self.path)

    def test_path_traversal_rejected(self):
        _, header = self.write()
        header['row_shards'][0]['path'] = '../outside.json'
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'content addressed'):
            self.storage.read(self.path)

    def test_absolute_shard_path_rejected(self):
        _, header = self.write()
        header['row_shards'][0]['path'] = str(self.directory / header['row_shards'][0]['path'])
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'content addressed'):
            self.storage.read(self.path)

    def test_shard_symlink_rejected(self):
        _, header = self.write()
        shard = self.directory / header['row_shards'][0]['path']
        target = self.directory / 'test-target.json'
        shard.rename(target)
        shard.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.storage.read(self.path)

    def test_shard_directory_symlink_rejected(self):
        _, _ = self.write()
        directory = self.directory / store.SHARD_DIRECTORY
        moved = self.directory / 'test-moved'
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.storage.read(self.path)

    def test_manifest_symlink_rejected(self):
        _, _ = self.write()
        moved = self.directory / 'test-manifest.json'
        self.path.rename(moved)
        self.path.symlink_to(moved)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.storage.read(self.path)

    def test_wrong_row_count_rejected(self):
        _, header = self.write()
        header['row_shards'][0]['rows'] -= 1
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'shard rows differ'):
            self.storage.read(self.path)

    def test_wrong_byte_count_rejected(self):
        _, header = self.write()
        header['row_shards'][0]['bytes'] -= 1
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'length differs'):
            self.storage.read(self.path)

    def test_wrong_logical_hash_rejected(self):
        _, header = self.write()
        header['logical_json_sha256'] = '0' * 64
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'logical JSON SHA differs'):
            self.storage.read(self.path)

    def test_wrong_logical_length_rejected(self):
        _, header = self.write()
        header['logical_json_bytes'] += 1
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'logical JSON length differs'):
            self.storage.read(self.path)

    def test_wrong_logical_name_rejected(self):
        _, header = self.write()
        header['logical_name'] = 'ROOT_AUTHORED_SELECTIONS_V2.json'
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'filename differs'):
            self.storage.read(self.path)

    def test_duplicate_native_id_rejected_without_writes(self):
        self.document['rows'][-1]['id'] = self.document['rows'][0]['id']
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.write()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_no_overwrite_of_selection(self):
        _, _ = self.write()
        prior = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'overwrite forbidden'):
            self.storage.write(self.path, self.document, force_sharded=True)
        self.assertEqual(self.path.read_bytes(), prior)

    def test_bad_existing_content_address_rejected_without_manifest(self):
        _, header = self.write()
        shard = self.directory / header['row_shards'][0]['path']
        shard.write_bytes(b'corrupted fixture')
        next_path = self.directory / 'ROOT_AUTHORED_SELECTIONS_V2.json'
        with self.assertRaises(ValueError):
            self.storage.write(next_path, self.document, force_sharded=True)
        self.assertFalse(next_path.exists())

    def test_unknown_format_rejected(self):
        _, header = self.write()
        header[store.FORMAT_KEY] = 'UNKNOWN'
        self.alter_header(header)
        with self.assertRaisesRegex(ValueError, 'unknown selection storage'):
            self.storage.read(self.path)

    def test_empty_selection_round_trip(self):
        self.document['rows'] = []
        self.document['source_ids'] = 0
        receipt, header = self.write()
        self.assertEqual(header['row_shards'], [])
        self.assertEqual(receipt['created_shard_bytes'], 0)
        self.assertEqual(self.storage.read(self.path), self.document)

    def test_row_that_cannot_fit_rejected_before_writes(self):
        with patch.object(store, 'SHARD_LIMIT', 20):
            with self.assertRaisesRegex(ValueError, 'single metadata row'):
                self.storage.write(self.path, self.document, force_sharded=True)
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
