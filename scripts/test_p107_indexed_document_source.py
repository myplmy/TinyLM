"""Preserved synthetic files and tiny CPU source/trainer controls only."""
from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from tinylm.train import indexed_document_source as module
from tinylm.train import document_input as legacy
from tinylm.train.document_source import ExplicitDocumentSource
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer, CONSUME_SCALED_GROUP
from tinylm.train.hybrid_session import HybridTrainingSession
from scripts.p107_scaled_optimizer_group import ScaledOptimizerGroup, ScaleConfig
from scripts import test_p107_adaptive_training as old

FIXTURE_ROOTS = []
CREATED_FILES = []
MEASUREMENTS = []


def rows_for(lengths=(3, 24, 25, 26, 29, 55)):
    return [dict(source_id='cpu-doc-'+str(i), token_ids=[35+(i+j)%29 for j in range(n)],
        language='synthetic', source_sha256='A'*64) for i, n in enumerate(lengths)]


class Fixture:
    """Every fixture is new and retained; no cleanup, unlink or overwrite."""
    def __init__(self, rows=None, *, manifest_edit=None, admitted=False,
                 evidence_edit=None, raw_edit=None):
        self.root = Path(tempfile.mkdtemp(prefix='p107_indexed_cpu_'))
        FIXTURE_ROOTS.append(str(self.root))
        (self.root/'inputs').mkdir()
        self.rows = copy.deepcopy(rows_for() if rows is None else rows)
        if admitted:
            for row in self.rows:
                row['language'] = 'ko'
        self.paths = []
        shards = []
        cut = max(1, len(self.rows)//2)
        for group in (self.rows[:cut], self.rows[cut:]):
            if not group:
                continue
            raw = b''.join(json.dumps(row, sort_keys=True).encode()+b'\n' for row in group)
            if raw_edit is not None:
                raw = raw_edit(raw)
            path = self.put('docs_'+str(len(shards))+'.jsonl', raw)
            self.paths.append(path)
            shards.append(dict(file=self.ref(path), documents=len(group), tokens=sum(len(row['token_ids']) for row in group)))
        admission = dict(status='TECHNICAL_FIXTURE_ONLY', authority_ref='NEW_SYNTHETIC_CPU_FIXTURE_ONLY',
            training_authorized=False, evidence=None)
        purpose = 'SYNTHETIC_TECHNICAL'
        if admitted:
            purpose = 'TRAIN_ADMITTED'
            admission.update(status='TRAIN_APPROVED', training_authorized=True)
            evidence = dict(schema=legacy.ADMISSION_SCHEMA, split='train', approved_for_training=True,
                authority_ref=admission['authority_ref'], tokenizer_sha256='C'*64,
                shards_sha256=legacy.canonical_sha(shards))
            if evidence_edit is not None:
                evidence_edit(evidence)
            admission['evidence'] = self.ref(self.put('admission.json', json.dumps(evidence).encode()))
        self.manifest = dict(schema=legacy.SCHEMA, purpose=purpose, split='train',
            tokenizer=dict(sha256='C'*64, vocab_size=64), admission=admission, shards=shards)
        if manifest_edit is not None:
            manifest_edit(self.manifest)
        self.manifest_ref = self.ref(self.put('manifest.json', json.dumps(self.manifest).encode()))

    def put(self, name, raw):
        path = self.root/'inputs'/name
        with path.open('xb') as stream:
            stream.write(raw)
        CREATED_FILES.append(dict(path=str(path), bytes=len(raw), sha256=legacy.sha256(raw)))
        return path

    def ref(self, path):
        raw = path.read_bytes()
        return dict(path=path.relative_to(self.root).as_posix(), bytes=len(raw), sha256=legacy.sha256(raw))

    def load(self, **kwargs):
        return module.load_indexed_document_input(self.root, self.manifest_ref,
            allowed_root='inputs', tokenizer_sha256='C'*64, vocab_size=64, **kwargs)

    def resident(self, *, batch=2, length=24, micros=4, seed=19):
        return ExplicitDocumentSource([torch.tensor(row['token_ids'], dtype=torch.long, device='cpu') for row in self.rows],
            [row['source_id'] for row in self.rows], batch=batch, length=length, micros=micros, vocab=64, seed=seed)


def source(data, **kwargs):
    options = dict(batch=2, length=24, micros=4, vocab=64, seed=19)
    options.update(kwargs)
    return data.as_source(**options)


def trainer(data_source, mode='adaptive', scaled=False):
    random.seed(211);np.random.seed(307);torch.manual_seed(1337)
    if not scaled:
        return old.make(mode, source=data_source)
    model = old.ToyAttention()
    parameters = list(model.parameters())
    matrix = [model.head.weight]
    rest = [p for p in parameters if p is not model.head.weight]
    optimizers = [torch.optim.SGD(matrix, lr=.01, momentum=.9), torch.optim.AdamW(rest, lr=.001)]
    config = PolicyConfig(64, .5, .2, 2, 'keep', 23, 34, 13, 'A'*64, 'B'*64)
    def factory():
        return ScaledOptimizerGroup(parameters, optimizers, run_signature='C'*64,
            expected_backwards=4, config=ScaleConfig(init_scale=64., growth_interval=2))
    return AdaptiveMNTPTrainer(model, optimizers, data_source, policy_config=config, mode=mode,
        masked_micros=2, signature='C'*64, collect_ids=old.predictions,
        scaled_group_factory=factory, overflow_policy=CONSUME_SCALED_GROUP)


class IndexedSourceTests(unittest.TestCase):
    assert_tree = old.TrainingBoundaryTests.assert_tree

    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():
            raise RuntimeError('CPU source suite requires uninitialized CUDA')

    @classmethod
    def tearDownClass(cls):
        if torch.cuda.is_initialized():
            raise RuntimeError('CPU source suite initialized CUDA')

    def test_exact_resident_draws_padding_crop_order_and_rng(self):
        fixture = Fixture();data = fixture.load()
        resident = fixture.resident(batch=3)
        current = source(data, batch=3)
        self.assertEqual(resident.corpus_sha256, data.contract['corpus_sha256'])
        self.assertEqual(resident.source_ids, data.source_ids)
        padded = False
        for _ in range(20):
            a, b = resident.next_update(), current.next_update()
            self.assert_tree(a, b)
            self.assertTrue(torch.equal(resident.rng.get_state(), current.rng.get_state()))
            padded |= any(bool((docs == -1).any()) for _, docs in b)
        self.assertTrue(padded)
        self.assertEqual(current.cursor, 20)
        self.assertEqual(current.record_reads, 240)
        self.assertEqual(current.contract['sampling'], resident.contract['sampling'])
        MEASUREMENTS.append(dict(scope='RESIDENT_EXACT_DRAW_CONTROL', input_groups=20,
            micros=4, batch=3, seq=24, sampled_rows=240, compared_input_positions=5760,
            actual_language_tokens=0, exact_tensors_and_RNG=True))

    def test_fresh_reopen_source_resume_reproduces_following_draws(self):
        fixture = Fixture();current = source(fixture.load())
        for _ in range(3):current.next_update()
        saved = current.state_dict()
        expected = [current.next_update() for _ in range(3)]
        wanted = current.state_dict()
        resumed = source(fixture.load());resumed.load_state_dict(saved)
        self.assert_tree(expected, [resumed.next_update() for _ in range(3)])
        self.assert_tree(wanted, resumed.state_dict())
        self.assertFalse(hasattr(resumed, 'documents'))

    def test_one_million_token_payload_is_not_retained_in_the_index(self):
        fixture = Fixture(rows_for([4096]*256));data = fixture.load()
        c = data.contract
        self.assertEqual(c['tokens'], 1_048_576)
        self.assertEqual(c['duplicate_token_documents'], 227)
        self.assertEqual(c['retained_document_token_values'], 0)
        self.assertEqual(c['max_document_tokens'], 4096)
        self.assertLess(c['max_raw_record_bytes'], c['file_bytes']//100)
        self.assertLess(c['serialized_record_metadata_bytes'], c['file_bytes']//10)
        self.assertTrue(all(type(record.tokens) is int for record in data.records))
        current = source(data, micros=2, length=16);current.next_update()
        self.assertEqual(current.record_reads, 4)
        self.assertEqual(current.max_decoded_document_tokens, 4096)
        self.assertLess(current.requested_record_bytes, c['file_bytes']//10)
        detached = data.contract;detached['tokens'] = 0
        self.assertEqual(data.contract['tokens'], 1_048_576)
        MEASUREMENTS.append(dict(scope='SYNTHETIC_PAYLOAD_AND_INDEX_NOT_RSS', **c,
            sample_record_reads=current.record_reads, sample_requested_record_bytes=current.requested_record_bytes,
            sample_max_decoded_document_tokens=current.max_decoded_document_tokens,
            retained_fixture=str(fixture.root), actual_language_tokens=0, actual_75M_run=False))

    def test_declared_budgets_stop_before_row_parsing_and_hard_profile_stays_bounded(self):
        fixture = Fixture()
        for limits in (module.IndexLimits(total_tokens=1), module.IndexLimits(total_bytes=1),
                       module.IndexLimits(documents=1), module.IndexLimits(shards=1)):
            with self.subTest(limits=limits), patch.object(module, '_row', side_effect=AssertionError('row parsed')):
                with self.assertRaises(ValueError):fixture.load(limits=limits)
        self.assertEqual(module.IndexLimits().total_tokens, 16_000_000)
        self.assertEqual(module.IndexLimits(total_tokens=75_000_000, total_bytes=1_280_000_000).total_tokens, 75_000_000)
        for values in (dict(total_tokens=75_000_001), dict(total_bytes=1_280_000_001),
                       dict(documents=True), dict(record_bytes=0), dict(shards=65)):
            with self.subTest(values=values), self.assertRaises(ValueError):module.IndexLimits(**values)

    def test_actual_metadata_and_record_budgets_reject_without_silent_drops(self):
        fixture = Fixture()
        for limits in (module.IndexLimits(metadata_bytes=1), module.IndexLimits(record_bytes=8)):
            with self.subTest(limits=limits), self.assertRaises(ValueError):fixture.load(limits=limits)
        for field in ('documents', 'tokens'):
            def change(m, field=field):m['shards'][0][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):Fixture(manifest_edit=change).load()
        def duplicate(m):m['shards'] *= 2
        with self.assertRaises(ValueError):Fixture(manifest_edit=duplicate).load()

    def test_manifest_split_tokenizer_purpose_and_fixture_admission_strict(self):
        changes = [lambda m:m.update(split='test'), lambda m:m.update(purpose='UNKNOWN'),
            lambda m:m['tokenizer'].update(vocab_size=64.0), lambda m:m['tokenizer'].update(sha256='D'*64),
            lambda m:m['admission'].update(training_authorized=True),
            lambda m:m['admission'].update(status='TRAIN_APPROVED'),
            lambda m:m['admission'].update(evidence={})]
        for index, change in enumerate(changes):
            with self.subTest(case=index), self.assertRaises(ValueError):Fixture(manifest_edit=change).load()

    def test_declared_train_admission_requires_explicit_caller_and_exact_evidence(self):
        fixture = Fixture(admitted=True)
        with self.assertRaises(ValueError):fixture.load()
        data = fixture.load(allow_admitted=True)
        self.assertEqual(data.contract['admission_status'], 'TRAIN_APPROVED')
        self.assertEqual(data.contract['semantic_rights_leakage_review'], 'NOT_PERFORMED_BY_THIS_BYTE_CONTRACT')
        for change in (lambda e:e.update(approved_for_training=1),
                       lambda e:e.update(shards_sha256='D'*64), lambda e:e.update(authority_ref='OTHER')):
            with self.assertRaises(ValueError):Fixture(admitted=True, evidence_edit=change).load(allow_admitted=True)
        self.assertEqual(len(data.metadata_files), 2)

    def test_exact_rows_ids_language_tokens_lengths_and_JSON_fields(self):
        changes = [lambda r:r[0].update(source_id=''), lambda r:r[0].update(language='xx'),
            lambda r:r[0].update(source_sha256='A'*63), lambda r:r[1].update(source_id=r[0]['source_id'])]
        for change in changes:
            rows = rows_for();change(rows)
            with self.assertRaises(ValueError):Fixture(rows).load()
        for bad in (13, True, 35.0, -1, 64):
            rows = rows_for();rows[0]['token_ids'][1] = bad
            with self.subTest(token=bad), self.assertRaises(ValueError):Fixture(rows).load()
        for n in (2, 65_537):
            with self.subTest(length=n), self.assertRaises(ValueError):Fixture(rows_for([n])).load()
        for edit in (lambda raw:b'\n'+raw,
                     lambda raw:raw.replace(b'"language": "synthetic"', b'"language": "synthetic", "language": "synthetic"', 1)):
            with self.assertRaises(ValueError):Fixture(raw_edit=edit).load()

    def test_protected_root_and_paths_fail_before_any_filesystem_query(self):
        cases = [(Path('/home/uranus/tinyLM'), 'datasets/TinyDataset/a.json', 'inputs'),
            (Path('/home/uranus/tinyLM/datasets'), 'TinyDataset/a.json', 'TinyDataset'),
            (Path('/home/uranus/tinyLM/datasets/TinyDataset'), 'inputs/a.json', 'inputs'),
            (Path('/tmp'), '.agents/a.json', 'inputs'), (Path('/tmp'), '../escape', 'inputs')]
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('unexpected filesystem query')):
            for root, name, allowed in cases:
                ref = dict(path=name, bytes=1, sha256='A'*64)
                with self.subTest(root=str(root), path=name), self.assertRaises(ValueError):
                    module.load_indexed_document_input(root, ref, allowed_root=allowed,
                        tokenizer_sha256='C'*64, vocab_size=64)

    def test_symlink_and_file_identity_then_selected_row_hash_guards(self):
        fixture = Fixture();data = fixture.load()
        shard = data.shards[0]
        original = fixture.root/shard.path
        link = fixture.root/'inputs/linked.jsonl';link.symlink_to(original)
        linked = replace(shard, path='inputs/linked.jsonl')
        bad = replace(data, shards=(linked, *data.shards[1:]))
        with self.assertRaises(ValueError):bad.read_tokens(0)
        raw = original.read_bytes().replace(b'35', b'36', 1)
        changed = fixture.put('changed_copy.jsonl', raw)
        changed_ref = replace(shard, path=changed.relative_to(fixture.root).as_posix())
        bad = replace(data, shards=(changed_ref, *data.shards[1:]))
        with self.assertRaises(ValueError):bad.read_tokens(0)
        with patch.object(module, '_stamp', return_value=shard.stamp):
            with self.assertRaisesRegex(ValueError, 'row SHA'):bad.read_tokens(0)
        self.assertEqual(legacy.sha256(original.read_bytes()), shard.sha256)

    def test_failed_partial_draw_restores_source_rng_cursor_then_retries_exactly(self):
        fixture = Fixture();data = fixture.load();current = source(data)
        before = current.state_dict()
        original = module.IndexedDocumentInput.read_tokens
        calls = []
        def fail_second(obj, index):
            calls.append(index)
            if len(calls) == 2:raise OSError('simulated selected-file interruption')
            return original(obj, index)
        with patch.object(module.IndexedDocumentInput, 'read_tokens', fail_second):
            with self.assertRaises(OSError):current.next_update()
        self.assertFalse(current.active)
        self.assert_tree(before, current.state_dict())
        reference = source(data)
        self.assert_tree(reference.next_update(), current.next_update())
        self.assert_tree(reference.state_dict(), current.state_dict())
        self.assertEqual(current.record_reads, 9)

    def test_source_state_schema_shape_seed_and_rng_validation_precedes_mutation(self):
        fixture = Fixture();data = fixture.load();current = source(data)
        current.next_update();saved = current.state_dict()
        variants = [fixture.resident().state_dict()]
        for key, value in (('cursor', True), ('cursor', -1), ('signature', 'D'*64),
                           ('rng', torch.ones(3)), ('rng', torch.ones(1, dtype=torch.uint8))):
            wrong = copy.deepcopy(saved);wrong[key] = value;variants.append(wrong)
        for wrong in variants:
            with self.assertRaises((ValueError, RuntimeError)):current.load_state_dict(wrong)
            self.assert_tree(saved, current.state_dict())
        with self.assertRaises(ValueError):source(data, seed=20).load_state_dict(saved)
        with patch.object(module.IndexedDocumentInput, 'validate_files', side_effect=ValueError('changed input')):
            with self.assertRaises(ValueError):current.load_state_dict(saved)
        self.assert_tree(saved, current.state_dict())
        for options in (dict(batch=True), dict(length=1), dict(vocab=65), dict(pad_id=35)):
            with self.assertRaises(ValueError):source(data, **options)

    def test_three_tiny_trainer_modes_match_resident_model_optimizer_policy_rng_and_loss(self):
        fixture = Fixture();data = fixture.load()
        for mode in ('uniform', 'observe', 'adaptive'):
            resident = trainer(fixture.resident(), mode)
            wanted_rows = [resident.update() for _ in range(3)]
            wanted = resident.state_dict()
            current = trainer(source(data), mode)
            rows = [current.update() for _ in range(3)]
            actual = current.state_dict()
            for a, b in zip(wanted_rows, rows):
                for key in ('loss', 'causal_targets', 'masked_targets'):
                    self.assert_tree(a[key], b[key])
                self.assert_tree(a.get('policy_commit'), b.get('policy_commit'))
            for key in ('model', 'optimizers', 'policy', 'rng', 'uniform_rng', 'cursor'):
                self.assert_tree(wanted[key], actual[key])
            self.assert_tree(wanted['source']['rng'], actual['source']['rng'])
            self.assertEqual(wanted['source']['cursor'], actual['source']['cursor'])

    def test_scaled_overflow_consumes_indexed_source_then_fresh_full_CPU_resume_is_exact(self):
        fixture = Fixture();data = fixture.load()
        current = HybridTrainingSession(trainer(source(data), scaled=True), total_updates=5,
            warmup_updates=1, schedule='cosine')
        hook = current.trainer.model.head.weight.register_hook(lambda g:g*float('inf'))
        try:skipped = current.update()
        finally:hook.remove()
        self.assertFalse(skipped['optimizer_applied'])
        self.assertEqual((current.cursor, current.trainer.source.cursor, current.trainer.scaled_group.steps), (1, 1, 0))
        saved = current.state_dict()
        rows = [current.update() for _ in range(2)];wanted = current.state_dict()
        resumed = HybridTrainingSession(trainer(source(fixture.load()), scaled=True), total_updates=5,
            warmup_updates=1, schedule='cosine')
        resumed.load_state_dict(saved)
        actual = [resumed.update() for _ in range(2)]
        for a, b in zip(rows, actual):
            for key in ('loss', 'causal_targets', 'masked_targets', 'schedule_lrs', 'scaled_optimizer_group'):
                self.assert_tree(a[key], b[key])
        self.assert_tree(wanted, resumed.state_dict())
        self.assertEqual((resumed.cursor, resumed.trainer.scaled_group.steps, resumed.trainer.scaled_group.skips), (3, 2, 1))

    def test_source_outputs_stay_CPU_under_a_meta_default_device(self):
        fixture = Fixture();data = fixture.load()
        reference = fixture.resident().next_update()
        with torch.device('meta'):
            current = source(data)
            actual = current.next_update()
        self.assert_tree(reference, actual)
        self.assertTrue(all(tokens.device.type == docs.device.type == 'cpu' for tokens, docs in actual))


if __name__ == '__main__':
    unittest.main()
