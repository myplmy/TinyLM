"""CPU file-admission and existing-source integration, not language quality."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import copy
import json
import tempfile
import unittest
from unittest.mock import patch

import torch
from tinylm.train import document_input as module
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer
from tinylm.train.hybrid_session import HybridTrainingSession
from scripts import test_p107_adaptive_training as old_fixture


class DocumentInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'inputs').mkdir()
        self.rows = [dict(source_id='doc-a', token_ids=list(range(35, 64)),
                          language='synthetic', source_sha256='A'*64),
                     dict(source_id='doc-b', token_ids=list(range(63, 34, -1)),
                          language='synthetic', source_sha256='B'*64)]
        self.manifest = dict(schema=module.SCHEMA, purpose='SYNTHETIC_TECHNICAL', split='train',
            tokenizer=dict(sha256='C'*64, vocab_size=64),
            admission=dict(status='TECHNICAL_FIXTURE_ONLY', authority_ref='CPU_TEST_ONLY',
                           training_authorized=False, evidence=None), shards=[])

    def ref(self, path):
        data = path.read_bytes()
        return dict(path=path.relative_to(self.root).as_posix(), bytes=len(data), sha256=module.sha256(data))

    def packet(self, rows=None):
        rows = self.rows if rows is None else rows
        raw = (chr(10).join(json.dumps(r) for r in rows)+chr(10)).encode()
        path = self.root/'inputs/docs.jsonl'; path.write_bytes(raw)
        self.manifest['shards'] = [dict(file=self.ref(path), documents=len(rows),
                                       tokens=sum(len(r['token_ids']) for r in rows))]
        return self.seal()

    def seal(self):
        path = self.root/'inputs/manifest.json'
        path.write_text(json.dumps(self.manifest), encoding='utf-8')
        return self.ref(path)

    def load(self, ref=None, **kwargs):
        return module.load_document_input(self.root, self.packet() if ref is None else ref,
            allowed_root='inputs', tokenizer_sha256='C'*64, vocab_size=64, **kwargs)

    def test_valid_input_has_exact_counts_and_detached_contract(self):
        data = self.load()
        self.assertEqual(data.source_ids, ('doc-a', 'doc-b'))
        self.assertEqual(data.contract['tokens'], 58)
        self.assertEqual(data.documents[0], tuple(range(35, 64)))
        detached = data.contract; detached['tokens'] = 0
        self.assertEqual(data.contract['tokens'], 58)
        self.assertEqual(data.contract['source_sha256_validation'], 'DECLARED_ONLY_RAW_SOURCE_NOT_READ')

    def test_protected_and_outside_paths_fail_before_stat(self):
        names = ('datasets/TinyDataset/a.json', '.agents/a.json', '../escape', '/tmp/a',
                 'other_session/a.json', 'inputs/../escape')
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('unexpected filesystem query')):
            for name in names:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    module.input_path(self.root, name, 'inputs')

    def test_root_or_ancestor_symlink_refused(self):
        (self.root/'inputs/linked').symlink_to(self.root/'inputs', target_is_directory=True)
        with self.assertRaises(ValueError):module.input_path(self.root, 'inputs/linked/a', 'inputs')
        (self.root/'inputs/file.json').symlink_to(self.root/'missing')
        with self.assertRaises(ValueError):module.input_path(self.root, 'inputs/file.json', 'inputs')

    def test_manifest_hash_and_bytes_must_match(self):
        ref = self.packet()
        for key, value in (('sha256', 'D'*64), ('bytes', ref['bytes']+1)):
            bad = dict(ref); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):self.load(bad)

    def test_manifest_size_limit_enforced_before_open(self):
        ref = self.packet();ref['bytes'] = module.MAX_META_BYTES+1
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('unexpected stat')):
            with self.assertRaises(ValueError):self.load(ref)

    def test_tokenizer_identity_and_integer_vocab(self):
        for key, value in (('sha256', 'D'*64), ('vocab_size', 64.0)):
            self.packet();self.manifest['tokenizer'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):self.load(self.seal())
            self.manifest['tokenizer'] = dict(sha256='C'*64, vocab_size=64)

    def test_non_train_split_and_unknown_purpose_refused(self):
        self.packet()
        for split in ('val', 'test', 'TRAIN'):
            self.manifest['split'] = split
            with self.subTest(split=split), self.assertRaises(ValueError):self.load(self.seal())
        self.manifest['split'] = 'train';self.manifest['purpose'] = 'UNKNOWN'
        with self.assertRaises(ValueError):self.load(self.seal())

    def test_fixture_cannot_claim_training_or_evidence(self):
        self.packet()
        for key, value in (('training_authorized', True), ('status', 'TRAIN_APPROVED'), ('evidence', {})):
            before = copy.deepcopy(self.manifest['admission'])
            self.manifest['admission'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):self.load(self.seal())
            self.manifest['admission'] = before

    def admitted(self):
        self.packet();self.manifest['purpose'] = 'TRAIN_ADMITTED'
        self.manifest['admission'].update(status='TRAIN_APPROVED', training_authorized=True)
        for row in self.rows:row['language'] = 'ko'
        self.packet()
        evidence = dict(schema=module.ADMISSION_SCHEMA, split='train', approved_for_training=True,
            authority_ref='CPU_TEST_ONLY', tokenizer_sha256='C'*64,
            shards_sha256=module.canonical_sha(self.manifest['shards']))
        p = self.root/'inputs/admission.json';p.write_text(json.dumps(evidence))
        self.manifest['admission']['evidence'] = self.ref(p)
        return self.seal(), evidence

    def test_admission_needs_explicit_caller_and_exact_bound_evidence(self):
        ref, _ = self.admitted()
        with self.assertRaises(ValueError):self.load(ref)
        data = self.load(ref, allow_admitted=True)
        self.assertEqual(data.contract['admission_status'], 'TRAIN_APPROVED')
        self.assertEqual(data.contract['semantic_rights_leakage_review'], 'NOT_PERFORMED_BY_THIS_BYTE_CONTRACT')

    def test_admission_bool_and_shard_binding_strict(self):
        for key, value in (('approved_for_training', 1), ('shards_sha256', 'D'*64)):
            _, evidence = self.admitted(); evidence[key] = value
            p = self.root/'inputs/admission.json';p.write_text(json.dumps(evidence))
            self.manifest['admission']['evidence'] = self.ref(p)
            with self.subTest(key=key), self.assertRaises(ValueError):self.load(self.seal(), allow_admitted=True)

    def test_changed_shard_refused(self):
        ref = self.packet(); p = self.root/'inputs/docs.jsonl'
        data = p.read_bytes();p.write_bytes(data.replace(b'doc-a', b'doc-x'))
        with self.assertRaises(ValueError):self.load(ref)

    def test_declared_counts_and_duplicate_shards_refused(self):
        self.packet()
        for field in ('documents', 'tokens'):
            self.manifest['shards'][0][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):self.load(self.seal())
            self.packet()
        self.manifest['shards'] *= 2
        with self.assertRaises(ValueError):self.load(self.seal())

    def test_duplicate_source_ids_refused_without_dropping_rows(self):
        rows = copy.deepcopy(self.rows);rows[1]['source_id'] = rows[0]['source_id']
        with self.assertRaises(ValueError):self.load(self.packet(rows))

    def test_invalid_tokens_mask_boolean_float_and_range(self):
        for bad in (13, True, 35.0, -1, 64):
            rows = copy.deepcopy(self.rows);rows[0]['token_ids'][3] = bad
            with self.subTest(token=bad), self.assertRaises(ValueError):self.load(self.packet(rows))

    def test_document_length_and_aggregate_caps(self):
        for values in ([35, 36], [35]*65_537):
            rows = copy.deepcopy(self.rows);rows[0]['token_ids'] = values
            with self.subTest(length=len(values)), self.assertRaises(ValueError):self.load(self.packet(rows))
        ref = self.packet()
        for name, cap in (('MAX_TOKENS', 30), ('MAX_DOCUMENTS', 1), ('MAX_TOTAL_BYTES', 10)):
            with patch.object(module, name, cap), self.subTest(name=name), self.assertRaises(ValueError):self.load(ref)

    def test_invalid_language_declared_sha_and_source_id(self):
        for key, value in (('language', 'ko'), ('source_sha256', 'a'*64), ('source_id', '')):
            rows = copy.deepcopy(self.rows);rows[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):self.load(self.packet(rows))

    def test_duplicate_json_fields_and_blank_lines_refused(self):
        self.packet()
        p = self.root/'inputs/docs.jsonl'
        for raw in (b'{"source_id":"a","source_id":"b"}'+bytes([10]), bytes([10])):
            p.write_bytes(raw)
            self.manifest['shards'][0]['file'] = self.ref(p)
            with self.subTest(raw=raw), self.assertRaises(ValueError):self.load(self.seal())

    def test_exact_duplicate_token_documents_are_reported_not_removed(self):
        rows = copy.deepcopy(self.rows);rows[1]['token_ids'] = list(rows[0]['token_ids'])
        data = self.load(self.packet(rows))
        self.assertEqual(data.contract['duplicate_token_documents'], 1)
        self.assertEqual(len(data.documents), 2)
        self.assertEqual(data.contract['dropped_documents'], 0)

    def test_reused_source_boundaries_rng_and_vocab_guard(self):
        data = self.load()
        source = data.as_source(batch=2, length=16, micros=4, vocab=64, seed=23)
        before = source.state_dict();a = source.next_update();source.load_state_dict(before);b = source.next_update()
        for (tokens, docs), (other, ids) in zip(a, b):
            self.assertTrue(torch.equal(tokens, other));self.assertTrue(torch.equal(docs, ids))
            for row in docs:self.assertEqual(len(set(row[row >= 0].tolist())), 1)
        with self.assertRaises(ValueError):data.as_source(batch=2, length=16, micros=4, vocab=65, seed=23)

    def test_existing_trainer_receives_file_input_and_exact_resume(self):
        torch.set_num_threads(1)
        data = self.load()
        def make():
            torch.manual_seed(1337)
            model = old_fixture.ToyAttention()
            source = data.as_source(batch=2, length=16, micros=4, vocab=64, seed=23)
            policy = PolicyConfig(64, .5, .2, 2, 'keep', 23, 34, 13, source.corpus_sha256, 'D'*64)
            trainer = AdaptiveMNTPTrainer(model, [torch.optim.AdamW(model.parameters(), lr=.001)],
                source, policy_config=policy, mode='adaptive', masked_micros=2, signature='E'*64,
                collect_ids=lambda logits, targets:logits.argmax(-1).cpu())
            return HybridTrainingSession(trainer, total_updates=4, warmup_updates=1, schedule='cosine')
        left = make();left.update();saved = left.state_dict();expected = left.update()
        right = make();right.load_state_dict(saved);actual = right.update()
        for key in ('loss', 'causal_targets', 'masked_targets', 'executed_input_tokens', 'schedule_lrs'):
            self.assertEqual(expected[key], actual[key])
        for key, value in left.trainer.model.state_dict().items():
            self.assertTrue(torch.equal(value, right.trainer.model.state_dict()[key]))


if __name__ == '__main__':
    unittest.main()
