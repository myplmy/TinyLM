"""Meaningful regression: growing live logs must not change saved evidence."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

AUDIT = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, AUDIT / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


guard = load('birth_input_delivery_guard_v1')
archive = load('snapshot_birth_delivery_events_v1').archive_event_prefixes


class EventArchiveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='hold_event_prefix_v1_'))
        self.live = self.root / 'events_000000.jsonl'
        self.payload = (json.dumps(dict(synthetic='first verified event')) + chr(10)).encode()
        self.live.write_bytes(self.payload)
        self.pin = dict(path=self.live.name, sha256=guard.sha(self.payload), bytes=len(self.payload))
        self.target = self.root / 'view'
        self.target.mkdir()

    def test_append_after_check_and_after_archive_does_not_change_evidence(self):
        with self.live.open('ab') as stream:
            stream.write(b'{"synthetic":"later event"}\n')
        saved = archive(self.root, self.target, [self.pin], guard)[0]
        with self.live.open('ab') as stream:
            stream.write(b'{"synthetic":"still later event"}\n')
        self.assertEqual(guard.read_pin(self.root, saved), self.payload)
        self.assertEqual(saved['source_journal_prefix'], self.pin)
        self.assertNotEqual(guard.sha(self.live.read_bytes()), saved['sha256'])

    def test_changed_verified_prefix_fails_closed(self):
        self.live.write_bytes(b'X' + self.payload[1:])
        with self.assertRaisesRegex(ValueError, 'journal prefix changed'):
            archive(self.root, self.target, [self.pin], guard)
        self.assertEqual(list((self.target / 'event_archive').iterdir()), [])

    def test_shortened_prefix_fails_closed(self):
        self.live.write_bytes(self.payload[:-1])
        with self.assertRaisesRegex(ValueError, 'journal prefix changed'):
            archive(self.root, self.target, [self.pin], guard)


if __name__ == '__main__':
    unittest.main()
