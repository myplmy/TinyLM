"""CPU synthetic/mocked preparation only; never open real assets or a model."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p101a_supervision_repair as r
from scripts import p106b_shards
from tinylm.train import mtp_sft as core
import torch


def line(row):
    return (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def synthetic_row(name, source='oasst', language='en', two=True):
    meta = dict(source=source, source_id=name, language=language, canonical_version=1)
    if source == 'explicit_public_context_qa':
        meta.update(kind='night_natural_qa', supervised_assistant_turns=[1])
    messages = [dict(role='user', content=[dict(type='text', text='question-' + name)]),
                dict(role='assistant', content=[dict(type='text', text='first-' + name)])]
    if two:
        messages.extend([dict(role='user', content=[dict(type='text', text='correction-' + name)]),
                         dict(role='assistant', content=[dict(type='text', text='second-' + name)])])
    return dict(messages=messages, meta=meta, tools=[])


LENGTHS = {'first-192': 3, 'second-192': 2, 'first-198': 4, 'second-198': 5,
           'first-natural': 3, 'first-other': 2, 'first-val': 4}


def encoded_synthetic(row, _tok, context=1024):
    """Fake token IDs only. Production masking and horizon counting stay real."""
    labels, owners = [], []
    owner = 0
    for message in row['messages']:
        if message['role'] != 'assistant':
            labels.extend([-100, -100]); owners.extend([0, 0])
            continue
        owner += 1
        n = LENGTHS[message['content'][0]['text']]
        labels.extend([100 + owner] * (n - 1) + [4]); owners.extend([owner] * n)
    return core.Record(list(range(len(labels))), labels, owners)


class SyntheticPreparation(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='p101a_repair_mock_')))
        self.stack.enter_context(patch.object(r, 'ROOT', self.root))
        self.stack.enter_context(patch.object(r.cleanup, 'ROOT', self.root))
        self.stack.enter_context(patch.object(r, 'CODE', (r.SOURCE_CONTROLLER,)))
        self.stack.enter_context(patch.object(core, 'encode_record', side_effect=encoded_synthetic))
        self.tokenizer = self.stack.enter_context(patch.object(r, 'load_tokenizer', return_value=object()))
        self.stack.enter_context(patch.object(torch, 'load', side_effect=AssertionError('checkpoint forbidden')))
        self.stack.enter_context(patch.object(torch.nn.Module, '__init__', side_effect=AssertionError('model forbidden')))
        self.stack.enter_context(redirect_stdout(io.StringIO()))
        self.a, self.b = synthetic_row('192'), synthetic_row('198')
        self.a['meta']['source_id'] = r.REPAIRS[0]['source_id']
        self.b['meta']['source_id'] = r.REPAIRS[1]['source_id']
        other = synthetic_row('other', source='aya', language='ko', two=False)
        natural = synthetic_row('natural', source='explicit_public_context_qa', language='ko', two=False)
        val = synthetic_row('val', source='explicit_public_context_qa', language='en', two=False)
        self.rows = dict(train=[natural, other, self.a, self.b], val=[val])
        self.public_rows = [self.a, other, self.b]
        self.put(r.SOURCE_CONTROLLER, b'original-controller-fixture\n')
        self.put(r.TOKENIZER, b'NOT_A_REAL_TOKENIZER\n')
        self.put(r.PUBLIC, b''.join(line(row) for row in self.public_rows))
        self.stack.enter_context(patch.object(r, 'TOKENIZER_SHA', r.digest(r.path(r.TOKENIZER))))
        self.stack.enter_context(patch.object(r, 'PUBLIC_SHA', r.digest(r.path(r.PUBLIC))))
        specs = copy.deepcopy(r.REPAIRS)
        for spec, index, first, second in zip(specs, (0, 2), (3, 4), (2, 5)):
            spec.update(source_index=index, canonical_line_sha256=hashlib.sha256(line(self.public_rows[index])).hexdigest().upper(),
                        expected_first_targets=first, expected_second_targets=second)
        self.stack.enter_context(patch.object(r, 'REPAIRS', specs))
        self.make_source()

    def put(self, relative, data):
        target = r.path(relative); target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)

    def make_source(self):
        counts, manifests = {}, {}
        for split, rows in self.rows.items():
            writer = p106b_shards.ShardWriter(r.path(r.SOURCE), split, limit=19_999_999)
            counts[split] = dict(rows=len(rows), x_tokens=0, assistant_targets=0)
            for row in rows:
                writer.append(row); record = r.masked_record(row, None)
                counts[split]['x_tokens'] += record.x_tokens
                counts[split]['assistant_targets'] += record.targets
            manifests[split] = writer.close(lineage=dict(mock_only=True))
        self.source_report = dict(schema='P101A_SFT_MTP_CORPUS_V1',
            preparation_schema='P101A_CLEAN_BILINGUAL_PREPARATION_V3', status='CORPUS_READY', family='mtp',
            tag=r.SOURCE_TAG, epochs=4, learning_updates=4, counts=counts, manifests=manifests,
            tokenizer_sha256=r.TOKENIZER_SHA, actual_unique_train_x_tokens=counts['train']['x_tokens'],
            target_processed_x_tokens=4 * counts['train']['x_tokens'],
            sources=dict(public_train_sha256=r.PUBLIC_SHA),
            code_sha256={r.SOURCE_CONTROLLER: r.digest(r.path(r.SOURCE_CONTROLLER))},
            supervised_wrong_turns='HISTORICAL_OVERBROAD_CLAIM_NOT_TO_INHERIT')
        r.write_json(r.SOURCE + '/report.json', self.source_report)
        self.stack.enter_context(patch.object(r, 'SOURCE_COUNTS', counts))
        self.stack.enter_context(patch.object(r, 'UPDATES', 4))
        self.stack.enter_context(patch.object(r, 'SOURCE_REPORT_SHA', r.digest(r.path(r.SOURCE + '/report.json'))))
        self.originals = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def unchanged(self):
        self.assertTrue(all(p.read_bytes() == raw for p, raw in self.originals.items()))

    def prepared(self):
        result = r.prepare(r.CANDIDATE_OUTPUT); self.unchanged()
        return result

    def test_only_two_metadata_fields_change_and_full_split_order_bytes_are_recounted(self):
        result = self.prepared()
        self.assertEqual(result['equivalence_audit']['compared_rows_by_split'], {'train': 4, 'val': 1})
        self.assertEqual(result['equivalence_audit']['metadata_changed_rows'], 2)
        self.assertEqual(result['equivalence_audit']['messages_changed'], 0)
        self.assertEqual(result['counts']['train']['rows'], 4)
        self.assertEqual(result['learning_updates'], 4)
        after = [entry[1] for entry in r.stream(r.CANDIDATE_OUTPUT, result['manifests']['train'])]
        self.assertEqual([row['messages'] for row in after], [row['messages'] for row in self.rows['train']])
        self.assertEqual(after[:2], self.rows['train'][:2])
        for actual, original in zip(after[2:], self.rows['train'][2:]):
            self.assertEqual(actual['meta'].pop('supervised_assistant_turns'), [2])
            self.assertEqual(actual, original)

    def test_original_actual_x_and_val_are_identical_only_expected_targets_drop(self):
        result = self.prepared()
        self.assertEqual(result['counts']['train']['x_tokens'], self.source_report['counts']['train']['x_tokens'])
        self.assertEqual(result['target_processed_x_tokens'], 4 * result['actual_unique_train_x_tokens'])
        self.assertEqual(result['counts']['val'], self.source_report['counts']['val'])
        self.assertEqual(result['counts']['train']['assistant_targets'], self.source_report['counts']['train']['assistant_targets'] - 7)

    def test_before_after_turn_horizons_eot_and_removal_meaning_are_recorded(self):
        result = self.prepared()
        audit = r.read_json(r.CANDIDATE_OUTPUT + '/supervision_audit.json')
        self.assertEqual(r.digest(r.path(r.CANDIDATE_OUTPUT + '/supervision_audit.json')), result['supervision_audit']['sha256'])
        for repair, first, second in zip(audit['repairs'], (3, 4), (2, 5)):
            self.assertEqual(repair['before_turn_h1_to_h4']['1']['1'], first)
            self.assertEqual(repair['after_turn_h1_to_h4'], {'2': repair['before_turn_h1_to_h4']['2']})
            self.assertEqual(repair['after_turn_h1_to_h4']['2']['1'], second)
            self.assertIn('NOT a count of factually incorrect tokens', repair['removal_interpretation'])
            self.assertEqual(repair['canonical_line_hash_unit'], 'RAW_UTF8_JSONL_LINE_INCLUDING_LF')
        candidate, _ = r.repaired_row(self.a, 'train', {self.a['meta']['source_id']: self.a})
        record = r.masked_record(candidate, None)
        self.assertEqual([y for y, owner in zip(record.y, record.segments) if owner == 2][-1], 4)
        self.assertNotIn(1, record.segments)

    def test_language_and_source_family_token_mass_is_not_replaced_with_row_ratios(self):
        result = self.prepared(); before = result['before_mass']['train']; after = result['after_mass']['train']
        self.assertEqual(before['by_language']['en']['rows'], 2)
        self.assertEqual(before['by_language']['ko']['rows'], 2)
        self.assertNotEqual(before['by_language']['en']['assistant_targets'], before['by_language']['ko']['assistant_targets'])
        self.assertEqual(before['by_language']['en']['assistant_targets'] - after['by_language']['en']['assistant_targets'], 7)
        self.assertEqual(before['by_language']['ko'], after['by_language']['ko'])
        self.assertEqual(set(after['by_source_family']), {'natural_context_qa', 'public_general:aya', 'public_general:oasst'})
        for mass in (before, after):
            for grouping in ('by_language', 'by_source_family', 'by_language_and_source_family'):
                for metric in ('rows', 'x_tokens', 'assistant_targets'):
                    self.assertEqual(sum(values[metric] for values in mass[grouping].values()), mass['total'][metric])

    def test_prepared_status_never_claims_training_admission_consumer_or_universal_truth(self):
        result = self.prepared()
        self.assertEqual(result['status'], 'SUPERVISION_REPAIR_PREPARED_NOT_ADMITTED')
        self.assertEqual(result['training_admission'], 'NOT_ADMITTED')
        self.assertIn('NOT_IMPLEMENTED', result['versioned_consumer_integration'])
        self.assertFalse(result['formal_train_ready'])
        self.assertNotIn('supervised_wrong_turns', result)
        self.assertIn('REST_NOT_EXHAUSTIVELY_REVIEWED', result['semantic_quality'])
        self.assertEqual((result['original_writes'], result['model_constructions'], result['checkpoint_loads'], result['gpu_calls']), (0, 0, 0, 0))

    def test_output_is_write_once_and_collision_is_rejected_before_reading_assets(self):
        self.prepared()
        with patch.object(r, 'load_inputs', side_effect=AssertionError('must reject before input reads')):
            with self.assertRaises(FileExistsError): r.prepare(r.CANDIDATE_OUTPUT)
        self.unchanged()

    def test_other_protected_and_parent_outputs_are_refused(self):
        for output in (r.SOURCE, 'data_cache', '../escape', '/tmp/escape', 'datasets/TinyDataset/x'):
            with self.subTest(output=output):
                with self.assertRaises(ValueError): r.prepare(output)
        for relative in ('../escape', '/tmp/escape', 'datasets/TinyDataset/x', 'x\\y'):
            with self.assertRaises(ValueError): r.path(relative)

    def test_wrong_canonical_line_hash_or_source_id_fails_before_output_creation(self):
        for field, value in (('canonical_line_sha256', '0' * 64), ('source_id', 'not-the-reviewed-source')):
            specs = copy.deepcopy(r.REPAIRS); specs[0][field] = value
            with patch.object(r, 'REPAIRS', specs):
                with self.assertRaises(ValueError): r.prepare(r.CANDIDATE_OUTPUT)
            self.assertFalse(r.path(r.CANDIDATE_OUTPUT).exists())
        self.unchanged()

    def test_changed_canonical_file_or_source_report_pin_is_not_silently_accepted(self):
        for name in ('SOURCE_REPORT_SHA', 'PUBLIC_SHA', 'TOKENIZER_SHA'):
            with patch.object(r, name, '0' * 64):
                with self.assertRaises(ValueError): r.prepare(r.CANDIDATE_OUTPUT)
            self.assertFalse(r.path(r.CANDIDATE_OUTPUT).exists())

    def test_changed_messages_or_metadata_target_in_val_and_prealready_masked_are_refused(self):
        canonical = {self.a['meta']['source_id']: self.a}
        with self.assertRaises(ValueError): r.repaired_row(self.a, 'val', canonical)
        for mutate in ('messages', 'meta'):
            bad = copy.deepcopy(self.a)
            if mutate == 'messages': bad['messages'][1]['content'][0]['text'] += ' changed'
            else: bad['meta']['supervised_assistant_turns'] = [1]
            with self.assertRaises(ValueError): r.repaired_row(bad, 'train', canonical)

    def test_x_label_owner_second_turn_and_denominator_drift_are_refused(self):
        before = encoded_synthetic(self.a, None); candidate, _ = r.repaired_row(self.a, 'train', {self.a['meta']['source_id']: self.a})
        after = r.masked_record(candidate, None); spec = r.REPAIRS[0]
        r.audit_repair(before, after, spec)
        bad = copy.deepcopy(after); bad.x[0] += 1
        with self.assertRaises(ValueError): r.audit_repair(before, bad, spec)
        bad = copy.deepcopy(after); i = bad.segments.index(2); bad.y[i] += 1
        with self.assertRaises(ValueError): r.audit_repair(before, bad, spec)
        bad = copy.deepcopy(after); i = before.segments.index(1); bad.y[i] = 4; bad.segments[i] = 1
        with self.assertRaises(ValueError): r.audit_repair(before, bad, spec)
        bad_spec = dict(spec, expected_first_targets=spec['expected_first_targets'] + 1)
        with self.assertRaises(ValueError): r.audit_repair(before, after, bad_spec)

    def test_full_readback_detects_messages_order_or_unapproved_metadata_mutations(self):
        result = self.prepared(); _, _, canonical = r.load_inputs()
        original_stream = r.stream
        for damage in ('messages', 'metadata', 'order', 'raw_bytes'):
            def altered(directory, manifest):
                rows = list(original_stream(directory, manifest))
                if directory == r.CANDIDATE_OUTPUT and manifest is result['manifests']['train']:
                    if damage == 'order': rows[0], rows[1] = rows[1], rows[0]
                    else:
                        entry = list(rows[0]); entry[1] = copy.deepcopy(entry[1])
                        if damage == 'messages': entry[1]['messages'][0]['content'][0]['text'] += ' changed'
                        elif damage == 'metadata': entry[1]['meta']['unapproved'] = True
                        else: entry[2] = entry[2][:-1] + b' \n'
                        rows[0] = tuple(entry)
                yield from rows
            with patch.object(r, 'stream', side_effect=altered):
                with self.assertRaises(ValueError): r.verify_copy(r.CANDIDATE_OUTPUT, result['manifests'], self.source_report, canonical)
        self.unchanged()

    def test_late_verification_failure_keeps_original_and_partial_candidate_no_completion_report(self):
        with patch.object(r, 'verify_copy', side_effect=ValueError('synthetic readback failure')):
            with self.assertRaises(ValueError): r.prepare(r.CANDIDATE_OUTPUT)
        self.assertTrue(r.path(r.CANDIDATE_OUTPUT).exists())
        self.assertFalse(r.path(r.CANDIDATE_OUTPUT + '/report.json').exists())
        self.unchanged()
        with self.assertRaises(FileExistsError): r.prepare(r.CANDIDATE_OUTPUT)

    def test_unknown_source_family_cannot_be_silently_grouped_as_public(self):
        with self.assertRaises(ValueError): r.source_family(synthetic_row('unknown', source='unreviewed-new-source'))

    def test_all_actual_frozen_source_families_are_kept_distinct(self):
        pairs = [('project_authored_query_specific_evidence', 'evidence_recovery'),
                 ('code_graph_factory', 'fictional_relation_fields'),
                 *[('p106b_context_code_fixture', kind) for kind in ('arithmetic', 'boolean', 'json', 'update')],
                 *[('PROJECT_AUTHORED_CODE', kind) for kind in ('binding_color', 'binding_department')]]
        names = []
        for source, kind in pairs:
            row = synthetic_row('fixture', source=source)
            row['meta']['kind'] = kind
            names.append(r.source_family(row))
        self.assertEqual(len(set(names)), 8)
        with self.assertRaises(ValueError):
            r.source_family({'meta': {'source': 'unknown', 'kind': 'night_natural_qa'}})

    def test_role_bridge_source_family_remains_separate_from_public_and_natural(self):
        row = synthetic_row('replay', source='project_authored_role_bridge')
        row['meta']['kind'] = 'role_bridge'
        self.assertEqual(r.source_family(row), 'role_replay')

    def missing_or_duplicate(self, duplicate):
        loaded = r.load_inputs(); real_stream = r.stream
        entries = list(real_stream(r.SOURCE, loaded[0]['manifests']['train']))
        replacement = list(copy.deepcopy(entries[2] if duplicate else entries[1])); replacement[0] = 3
        entries[3] = tuple(replacement)
        counts = copy.deepcopy(r.SOURCE_COUNTS)
        records = [r.masked_record(entry[1], None) for entry in entries]
        counts['train'] = dict(rows=len(entries), x_tokens=sum(x.x_tokens for x in records),
                               assistant_targets=sum(x.targets for x in records))
        def altered(directory, manifest):
            if directory == r.SOURCE and manifest is loaded[0]['manifests']['train']:
                yield from entries
            else:
                yield from real_stream(directory, manifest)
        with patch.object(r, 'load_inputs', return_value=loaded), patch.object(r, 'SOURCE_COUNTS', counts), \
             patch.object(r, 'stream', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'two first-response removals only'):
                r.prepare(r.CANDIDATE_OUTPUT)
        self.assertFalse(r.path(r.CANDIDATE_OUTPUT + '/report.json').exists())
        self.unchanged()

    def test_missing_second_reviewed_source_is_not_reported_as_complete(self):
        self.missing_or_duplicate(False)

    def test_duplicate_reviewed_source_is_not_counted_as_the_two_distinct_repairs(self):
        self.missing_or_duplicate(True)

    def test_source_snapshot_change_after_copy_prevents_completion_report(self):
        real_hashes = r.hashes
        def changed(names):
            result = real_hashes(names)
            if isinstance(names, dict): result[next(iter(result))] = '0' * 64
            return result
        with patch.object(r, 'hashes', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed during preparation'): r.prepare(r.CANDIDATE_OUTPUT)
        self.assertFalse(r.path(r.CANDIDATE_OUTPUT + '/report.json').exists())
        self.unchanged()

    def test_code_snapshot_change_after_copy_prevents_completion_report(self):
        real_hashes = r.hashes; code_calls = 0
        def changed(names):
            nonlocal code_calls
            result = real_hashes(names)
            if names is r.CODE:
                code_calls += 1
                if code_calls == 2: result[next(iter(result))] = '0' * 64
            return result
        with patch.object(r, 'hashes', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed during preparation'): r.prepare(r.CANDIDATE_OUTPUT)
        self.assertFalse(r.path(r.CANDIDATE_OUTPUT + '/report.json').exists())
        self.unchanged()

    def test_linked_new_output_parent_is_rejected_before_asset_reads(self):
        target = r.path(r.CANDIDATE_OUTPUT).parent
        target.symlink_to(self.root, target_is_directory=True)
        with patch.object(r, 'load_inputs', side_effect=AssertionError('linked output must fail first')):
            with self.assertRaises(ValueError): r.prepare(r.CANDIDATE_OUTPUT)
        self.unchanged()


class StaticOnlyTests(unittest.TestCase):
    def test_fresh_stdlib_process_check_only_does_not_import_torch_or_read_assets(self):
        code = ("import sys; from scripts import p101a_supervision_repair as r; "
                "assert 'torch' not in sys.modules; "
                "assert r.main(['--check-only']) == 0; assert 'torch' not in sys.modules")
        result = subprocess.run(['/usr/bin/python3', '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"asset_reads": 0', result.stdout)
        self.assertIn('"training_admission": "NOT_ADMITTED"', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
