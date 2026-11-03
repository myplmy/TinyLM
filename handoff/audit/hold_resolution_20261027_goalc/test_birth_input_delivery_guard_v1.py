"""Behavioural CPU tests; synthetic fixtures are preserved in /tmp."""
from pathlib import Path
import copy
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).with_name('birth_input_delivery_guard_v1.py')
SPEC = importlib.util.spec_from_file_location('delivery_guard_test_target', MODULE)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
MODULE_SHA = guard.sha(MODULE.read_bytes())


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='hold_input_delivery_v1_'))
        self.role = 'role_a'
        self.ident = 'synthetic:1'
        self.parts = [b'ORIGINAL fixture\nEND_ORIGINAL\n',
                      b'CANDIDATE fixture\nEND_CANDIDATE\nFULL_DIFF\nEND_FULL_DIFF\n']
        self.row = dict(id=self.ident, role=self.role,
                        original={'sha256': 'A' * 64}, candidate={'sha256': 'B' * 64},
                        reading_parts=[dict(path=f'packet_{n}.txt', sha256=guard.sha(p))
                                       for n, p in enumerate(self.parts, 1)])
        self.contract = dict(restricted_ids=['protected:1'], restricted_hashes=['F' * 64])
        self.manifest = dict(rows=[self.row])
        for n, payload in enumerate(self.parts, 1):
            (self.root / f'packet_{n}.txt').write_bytes(payload)
        self.config = dict(schema='BIRTH_INPUT_DELIVERY_CONFIG_V1', cohort='synthetic_cohort',
                           contract=self.save('contract.json', self.contract),
                           manifest=self.save('manifest.json', self.manifest), roles={self.role: dict(
                               reader=self.save('reader.py', 'synthetic fixed reader'),
                               registry=self.save('registry.json', {'synthetic': True}),
                               event_directory='events/role_a')})
        for suffix in ('review_inputs', 'root_probes'):
            (self.root / 'events/role_a' / suffix).mkdir(parents=True)
        self.config_pin = self.save('config.json', self.config)
        self.calls = []

    def save(self, name, data):
        payload = (json.dumps(data) + chr(10)).encode('utf-8')
        path = self.root / name
        path.write_bytes(payload)
        return dict(path=name, sha256=guard.sha(payload))

    def envelope(self, number):
        part = self.row['reading_parts'][number - 1]
        header = dict(source_id=self.ident, packet=number, packets=2,
                      sha256=part['sha256'], path=part['path'],
                      total_characters=len(self.parts[number - 1].decode()),
                      packet_complete=True, source_packet_sequence_complete=number == 2)
        return (b'APPROVED_COMPLETE_PACKET ' + json.dumps(header).encode() + b'\n' +
                self.parts[number - 1] + b'\nEND_APPROVED_COMPLETE_PACKET\n')

    def runner(self, argv, **kwargs):
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, self.envelope(int(argv[-1])), b'')

    def emit(self, packet=1, **kwargs):
        return guard.emit(self.root, self.config_pin, MODULE_SHA, self.role, self.ident,
                          packet, stdout=kwargs.pop('stdout', io.BytesIO()),
                          runner=kwargs.pop('runner', self.runner), clock=lambda: 1000, **kwargs)

    def gate(self, events, review_time=1500):
        return guard.gate_source(self.config, self.contract, {self.ident: self.row},
                                 self.role, self.ident, self.config_pin['sha256'],
                                 MODULE_SHA, review_time, events)

    def test_successful_complete_emissions_before_review(self):
        output = io.BytesIO()
        self.emit(1, stdout=output)
        self.emit(2, stdout=output)
        events, pins = guard.load_events(self.root, self.config, self.role)
        self.assertEqual(output.getvalue(), self.envelope(1) + self.envelope(2))
        self.assertEqual(self.gate(events)['status'], 'INPUT_DELIVERED_BEFORE_REVIEW')
        self.assertEqual(len(events), 2)
        self.assertEqual(len(pins), 1)
        self.assertFalse(any('fixture' in json.dumps(e) for e in events))

    def test_missing_packet_blocks(self):
        self.assertEqual(self.gate([self.emit(1)])['missing_packets'], [2])

    def test_late_packet_blocks_even_with_all_packets(self):
        self.assertEqual(self.gate([self.emit(1), self.emit(2)], 999)['late_packets'], [1, 2])

    def test_root_probes_are_separate_and_cannot_pass(self):
        event = self.emit(1, probe=True)
        self.assertEqual(self.gate([event, self.emit(2)])['missing_packets'], [1])
        self.assertEqual(len(guard.load_events(self.root, self.config, self.role)[0]), 1)
        self.assertTrue(list((self.root / 'events/role_a/root_probes').glob('*.jsonl')))

    def test_each_exact_binding_is_required(self):
        event = self.emit(1)
        second = self.emit(2)
        for name in guard.PIN_FIELDS:
            changed = dict(event)
            changed[name] = 99 if isinstance(event[name], int) else 'DIFFERENT'
            with self.subTest(name=name):
                self.assertEqual(self.gate([changed, second])['missing_packets'], [1])

    def test_restricted_id_blocks_before_child_or_output(self):
        self.ident = 'protected:1'
        output = io.BytesIO()
        with self.assertRaisesRegex(ValueError, 'restricted source ID'):
            self.emit(stdout=output)
        self.assertEqual(self.calls, [])
        self.assertEqual(output.getvalue(), b'')

    def test_restricted_hash_under_different_id_blocks_before_child(self):
        self.row['original']['sha256'] = 'F' * 64
        self.config['manifest'] = self.save('manifest.json', self.manifest)
        self.config_pin = self.save('config.json', self.config)
        with self.assertRaisesRegex(ValueError, 'restricted original source hash'):
            self.emit()
        self.assertEqual(self.calls, [])

    def test_other_role_blocks_before_child(self):
        self.row['role'] = 'role_b'
        self.config['manifest'] = self.save('manifest.json', self.manifest)
        self.config_pin = self.save('config.json', self.config)
        with self.assertRaisesRegex(ValueError, 'different role assignment'):
            self.emit()
        self.assertEqual(self.calls, [])

    def test_changed_metadata_or_reader_blocks(self):
        for label in ('registry', 'reader'):
            with self.subTest(label=label):
                path = self.root / self.config['roles'][self.role][label]['path']
                before = path.read_bytes()
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'root-pinned'):
                    self.emit()
                self.assertEqual(self.calls, [])
                path.write_bytes(before)

    def test_bad_child_envelope_never_emits_or_logs(self):
        for data in (b'wrong prefix', self.envelope(1)[:-1],
                     self.envelope(1).replace(b'ORIGINAL fixture', b'CHANGED fixture'),
                     self.envelope(2)):
            with self.subTest(data=data[:40]):
                output = io.BytesIO()
                run = lambda *a, **k: subprocess.CompletedProcess([], 0, data, b'')
                with self.assertRaises(ValueError):
                    self.emit(stdout=output, runner=run)
                self.assertEqual(output.getvalue(), b'')
        self.assertEqual(guard.load_events(self.root, self.config, self.role)[0], [])

    def test_failed_child_never_emits(self):
        output = io.BytesIO()
        run = lambda *a, **k: subprocess.CompletedProcess([], 3, b'untrusted output', b'failed')
        with self.assertRaisesRegex(ValueError, 'fixed packet reader failed'):
            self.emit(stdout=output, runner=run)
        self.assertEqual(output.getvalue(), b'')
        self.assertEqual(guard.load_events(self.root, self.config, self.role)[0], [])

    def test_failed_stdout_flush_does_not_log(self):
        class Broken(io.BytesIO):
            def flush(self):
                raise BrokenPipeError('synthetic pipe closed')
        with self.assertRaises(BrokenPipeError):
            self.emit(stdout=Broken())
        self.assertEqual(guard.load_events(self.root, self.config, self.role)[0], [])

    def test_short_stdout_write_does_not_log(self):
        class Short(io.BytesIO):
            def write(self, data):
                return len(data) - 1
        with self.assertRaisesRegex(ValueError, 'partial packet stdout write'):
            self.emit(stdout=Short())
        self.assertEqual(guard.load_events(self.root, self.config, self.role)[0], [])

    def test_log_rotation_preserves_all_events(self):
        event = self.emit(1)
        # A new isolated purpose directory avoids changing existing production limits.
        config = copy.deepcopy(self.config)
        config['roles'][self.role]['event_directory'] = 'rotation/role_a'
        directory = self.root / 'rotation/role_a/review_inputs'
        directory.mkdir(parents=True)
        for _ in range(5):
            guard.append_event(self.root, config, event, limit=1800)
        events, pins = guard.load_events(self.root, config, self.role)
        self.assertEqual(len(events), 5)
        self.assertGreater(len(pins), 1)
        self.assertTrue(all(p['bytes'] <= 1800 for p in pins))

    def test_corrupt_event_is_not_silently_ignored(self):
        self.emit(1)
        path = next((self.root / 'events/role_a/review_inputs').glob('*.jsonl'))
        path.write_bytes(path.read_bytes().replace(b'REVIEW_INPUT', b'WRONG_PURPOSE'))
        with self.assertRaisesRegex(ValueError, 'event hash or schema changed'):
            guard.load_events(self.root, self.config, self.role)

    def test_symlink_registry_rejected_before_reader(self):
        alias = self.root / 'registry_alias.json'
        alias.symlink_to(self.root / 'registry.json')
        self.config['roles'][self.role]['registry']['path'] = alias.name
        self.config_pin = self.save('config.json', self.config)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.emit()
        self.assertEqual(self.calls, [])

    def test_review_timestamp_requires_exact_snapshot_bytes(self):
        pin = self.save('review.md', 'actual saved review')
        stamp = guard.review_timestamp(self.root, pin)
        self.assertEqual(stamp, (self.root / 'review.md').stat().st_mtime_ns)
        (self.root / 'review.md').write_text('changed newer review', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'review bytes differ'):
            guard.review_timestamp(self.root, pin)


if __name__ == '__main__':
    unittest.main()
