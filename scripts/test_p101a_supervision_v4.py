"""Synthetic/encode-mock consumer regressions; no actual model/CP/GPU/assets."""
from __future__ import annotations
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p101a_supervision_v4 as v
from scripts import diag_p101a_sft_mtp as engine
from scripts import diag_p101a_clean_bilingual as clean
from scripts import diag_p101a_clean_eval as ev
from scripts import check_p101a_clean_cost as checker
from scripts import p101a_supervision_repair as producer
from scripts.p106b_shards import ShardWriter
from tinylm.train import mtp_sft as core
import torch
REAL_CONTRACT_RECORDS = v.contract_records
REAL_PREPARED = v.prepared
REAL_STUDY = v.study
REAL_ENGINE_INFO = engine.info
REAL_MODULES = v.modules

NOW = datetime(2026, 10, 22, 0, tzinfo=timezone.utc)


class Tok:
    def get_vocab_size(self): return 32768
    def token_to_id(self, text): return {'<|im_end|>': 4, '<|im_start|>': 3, '<eos>': 2}.get(text, 0)


class ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='p101a_v4_mock_')))
        for obj in (v, engine): self.stack.enter_context(patch.object(obj, 'ROOT', self.root))
        self.stack.enter_context(patch.object(v, 'now', return_value=NOW))
        self.stack.enter_context(patch.object(torch, 'load', side_effect=AssertionError('real checkpoint forbidden')))
        self.stack.enter_context(patch.object(torch.nn.Module, '__init__', side_effect=AssertionError('model construction forbidden')))
        self.stack.enter_context(patch.object(v.os, 'getpid', return_value=99999))
        self.stack.enter_context(patch.object(v.os, 'getpgrp', return_value=99999))
        self.stack.enter_context(redirect_stdout(io.StringIO())); self.stack.enter_context(redirect_stderr(io.StringIO()))
        with patch.object(v, 'sources', return_value={'mock-source': 'A' * 64}):
            self.study = REAL_STUDY()
        self.stack.enter_context(patch.object(v, 'study', side_effect=lambda: copy.deepcopy(self.study)))
        self.stack.enter_context(patch.object(v, 'sources', return_value=self.study['code_sha256']))
        self.m = (engine, clean, checker, ev, producer)
        self.stack.enter_context(patch.object(v, 'modules', return_value=self.m))
        self.records = {'train': [core.Record([1, 2], [9, 4], [2, 2])],
                        'val': [core.Record([3, 4], [8, 4], [1, 1])]}
        self.summary = dict(records_sha256=v.encoded_fingerprint(self.records),
            totals={'val': {'horizons': {'1': 2977, '2': 1000, '3': 500, '4': 200}}},
            expected_cost=dict(updates=32, actual_processed_x_tokens=10000, assistant_targets=1000),
            expected_mtp_active_epoch_targets=[{'1': 552153, '2': 500000, '3': 490000, '4': 480000} for _ in range(4)])
        self.contract = dict(status='CPU_V4_CONSUMER_CONTRACT_COMPLETE_NOT_MODEL_QUALITY',
            study=self.study, study_sha256=v.sha(self.study), encoded=self.summary)
        self.put(v.CONTRACT, self.contract)
        self.report = dict(counts=copy.deepcopy(v.COUNTS), manifests={'train': {'rows': 22528}, 'val': {'rows': 512}})
        self.prepared = self.stack.enter_context(patch.object(v, 'prepared', return_value=(self.report, {})))
        self.encode = self.stack.enter_context(patch.object(v, 'contract_records', side_effect=lambda _m: (self.records, copy.deepcopy(self.summary))))
        def original_info(a):
            with patch.object(engine.data, 'digest', return_value='A' * 64): return REAL_ENGINE_INFO(a)
        self.stack.enter_context(patch.object(engine, 'info', side_effect=original_info))
        self.factory = self.stack.enter_context(patch.object(engine, 'optimizers', side_effect=lambda _: (
            SimpleNamespace(param_groups=[{'lr': 1e-4, 'weight_decay': .1}]),
            SimpleNamespace(param_groups=[{'lr': 4e-4, 'weight_decay': 0}]))))
        self.train = self.stack.enter_context(patch.object(engine, 'train_arm', side_effect=self.fake_train))
        self.stack.enter_context(patch.object(engine, 'checkpoint', side_effect=lambda tag, arm: self.root / 'synthetic_checkpoint_bytes' / (tag + '_' + arm + '.mock')))
        tok = 'data_cache/mock_tokenizer'; self.put(tok, b'SYNTHETIC_NOT_A_TOKENIZER')
        self.stack.enter_context(patch.object(engine.data, 'TOKENIZER', v.path(tok)))
        self.stack.enter_context(patch.object(engine.data, 'TOK_SHA', v.digest(tok)))
        self.real_stream = engine.data.stream_rows
        self.val_row = dict(meta=dict(language='en', source='explicit_public_context_qa', kind='night_natural_qa'),
            messages=[dict(role='user', content=[dict(type='text', text='mock question')]),
                      dict(role='assistant', content=[dict(type='text', text='ok')])])
        self.val_rows = [self.val_row] * 512
        self.stack.enter_context(patch.object(engine.data, 'stream_rows', side_effect=lambda directory, manifest:
            iter(self.val_rows) if directory == v.path(v.CORPUS) else self.real_stream(directory, manifest)))
        self.eval = self.stack.enter_context(patch.object(ev, 'execute', side_effect=self.fake_eval))
        self.authority = dict(schema=v.AUTH_SCHEMA, tag=v.TAG, allow_experimental_gpu=True,
            allowed_arms=list(v.ARMS), allowed_modes=['calibrate', 'train', 'evaluate'],
            consumer_signature_sha256=v.sha(self.study), cpu_contract_sha256=v.digest(v.CONTRACT),
            corpus_report_sha256=v.REPORT_SHA, supervision_audit_sha256=v.AUDIT_SHA,
            max_worker_seconds=1200, max_family_seconds=144000, prior_spend_scope='APPROVED_PRE_V4_FAMILY_ONLY',
            prior_spent_seconds=1000., expires_at=v.HARD_STOP.isoformat(),
            prior_spend_receipts=[dict(path='handoff/audit/mock_prior_spend.json', sha256='', seconds_field='seconds')],
            v3_pair_receipts=[])
        self.put('handoff/audit/mock_prior_spend.json', {'seconds': 1000.})
        self.authority['prior_spend_receipts'][0]['sha256'] = v.digest('handoff/audit/mock_prior_spend.json')
        for arm in ('scratch_ntp', 'scratch_mtp'):
            name = 'test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/' + arm + '/report.json'
            self.put(name, dict(arm=arm, status='SFT_MTP_TRAINED_EVAL_PENDING', checkpoint_saved=True,
                corpus_sha256=v.V3_SHA, updates=704, actual_processed_x_tokens=21621776,
                assistant_targets=2210436, initial_core_sha256='same-original-scratch'))
            self.authority['v3_pair_receipts'].append(dict(path=name, sha256=v.digest(name)))
        self.auth_name = 'handoff/audit/mock_v4_authority.json'
        self.put(self.auth_name, self.authority)

    def put(self, relative, value):
        p = v.path(relative); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as f: f.write(value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode())

    def args(self, mode='calibrate', arm='parent_ntp'):
        return SimpleNamespace(mode=mode, arm=arm, initializer='parent', tag=v.TAG, max_wall_sec=1200,
            authorization=self.auth_name, authorization_sha256=v.digest(self.auth_name), execute=True, worker=True)

    def fake_train(self, a, corpus, evidence, metadata, calibrate=False):
        self.assertEqual(corpus, v.path(v.CORPUS)); self.assertEqual(evidence, v.path(v.BASE))
        report = engine.corpus_report(corpus)
        self.assertIs(engine.encoded(corpus, report, Tok()), self.records)
        adam, muon = engine.optimizers('NO_MODEL')
        self.assertEqual((adam.param_groups[0]['lr'], muon.param_groups[0]['lr']), (5e-5, 2e-4))
        self.assertEqual((adam.param_groups[0]['weight_decay'], muon.param_groups[0]['weight_decay']), (.1, 0))
        result = dict(metadata, arm=a.arm, expected_full_updates=704, model_loading='MEASURED',
            meaningful_training='RESOURCE_ONLY' if calibrate else 'EXPERIMENTAL_PSEUDO_SFT',
            initializer='SCRATCH_NO_WEIGHT_INIT' if a.arm.startswith('scratch_') else 'PINNED_PARENT_WEIGHT_ONLY',
            initial_core_sha256='PARENT' if a.arm.startswith('parent') else 'SCRATCH')
        if calibrate:
            result.update(self.summary['expected_cost'], status='COST_CALIBRATION_COMPLETE', checkpoint_saved=False,
                update_seconds=[1.] * 32, whole_wall_sec=33.)
        else:
            cp = str(engine.checkpoint(v.TAG, a.arm).relative_to(self.root)); self.put(cp, b'SYNTHETIC_NO_TENSORS')
            horizons = ('1', '2', '3', '4') if a.arm.endswith('_mtp') else ('1',)
            val = {h: dict(ce=1., targets=self.summary['totals']['val']['horizons'][h]) for h in horizons}
            history = []
            for epoch in range(4):
                h = copy.deepcopy(self.summary['expected_mtp_active_epoch_targets'][epoch]) if a.arm.endswith('_mtp') else {'1': 552153, '2': 0, '3': 0, '4': 0}
                history.append(dict(epoch=epoch + 1, updates=176 * (epoch + 1), processed_x_tokens=5405444,
                    assistant_targets=552153, active_head_target_counts=h, val=copy.deepcopy(val)))
            result.update(status='SFT_MTP_TRAINED_EVAL_PENDING', checkpoint_saved=True, updates=704,
                actual_processed_x_tokens=21621776, assistant_targets=2208612, history=history,
                checkpoint=cp, checkpoint_sha256=v.digest(cp),
                initial_val=copy.deepcopy(val),
                initial_native_ce={'val_sha256': 'same'}, final_native_ce={'val_sha256': 'same'})
        engine.write(engine.report_path(evidence, a.arm, calibrate), result)
        return 0

    def fake_eval(self, a):
        self.assertEqual(a.family, v.TAG)
        _, _, split, _, output, info = ev.prerequisites(a.family, a.arm)
        self.assertEqual(split, 'val'); self.assertEqual(info['family'], 'mtp')
        writer = ShardWriter(output, 'first_answers')
        for i, row in enumerate(self.val_rows):
            writer.append(dict(index=i, source=row, answer='ok', grading=ev.score(row, 'ok', True),
                               generation=dict(finish_reason='STOP_SEQUENCE', generated_tokens=1)))
        manifest = writer.close(lineage=info)
        review = 'review_request/20261021_' + v.TAG + '_' + a.arm + '_실제첫답.md'
        self.put(review, b'SYNTHETIC_READABLE_REVIEW')
        engine.write(output / 'report.json', dict(info, status='FIRST_ANSWER_COLLECTION_COMPLETE', returncode=0,
            counts=dict(total=512, primary_correct=512, extraction_failed=0, ended=512), raw_manifest=manifest,
            first_answer_only=True, training_feedback=0, checkpoint_writes=0, readable_review=review))
        return 0

    def finish(self, arm, through='train'):
        for mode in ('calibrate', 'train', 'evaluate'):
            self.assertEqual(v.gpu_worker(self.args(mode, arm), self.m), 0)
            if mode == through: return

    def test_fresh_authority_binds_data_contract_source_prior_spend_and_both_finished_v3_arms(self):
        auth, c, remaining = v.checked_authority(self.args())
        self.assertEqual(auth['prior_spent_seconds'], 1000.); self.assertEqual(c, self.contract)
        self.assertGreater(remaining, 1200)

    def test_wrong_or_expired_approval_and_missing_or_mixed_v3_pair_block_before_model(self):
        for serial, (field, value) in enumerate((('consumer_signature_sha256', 'bad'), ('cpu_contract_sha256', 'bad'),
                             ('corpus_report_sha256', 'bad'), ('prior_spent_seconds', 0),
                             ('expires_at', NOW.isoformat()), ('expires_at', (v.HARD_STOP + timedelta(seconds=1)).isoformat()),
                             ('v3_pair_receipts', []), ('max_family_seconds', 144001),
                             ('allowed_arms', ['scratch_ntp']), ('allowed_modes', ['evaluate']))):
            bad = copy.deepcopy(self.authority); bad[field] = value
            name = 'handoff/audit/bad_' + field + str(serial) + '.json'; self.put(name, bad)
            a = self.args(); a.authorization = name; a.authorization_sha256 = v.digest(name)
            with self.subTest(field=field):
                with self.assertRaises((v.Hold, ValueError)): v.checked_authority(a)
        self.train.assert_not_called(); self.eval.assert_not_called()

    def test_cost32_delegation_and_factory_lr_are_real_callbacks_and_restored(self):
        old = engine.corpus_report, engine.encoded, engine.optimizers, engine.write, engine.train_arm
        self.assertEqual(v.gpu_worker(self.args(), self.m), 0)
        receipt, report, _ = v.closed('calibrate', 'parent_ntp')
        self.assertEqual(report['updates'], 32); self.assertEqual(report['full_updates'], 704)
        self.assertIn('NO_QUALITY_ADOPTION', receipt['status'])
        self.assertEqual((engine.corpus_report, engine.encoded, engine.optimizers, engine.write, engine.train_arm), old)
        self.factory.assert_called_once()

    def test_train_without_closed_same_arm_cost_is_blocked_before_model(self):
        with self.assertRaises((ValueError, FileNotFoundError)): v.gpu_worker(self.args('train'), self.m)
        self.train.assert_not_called()

    def test_full704_and_four_epochs_targets_are_verified_before_and_after_save(self):
        self.finish('parent_ntp')
        _, result, _ = v.closed('train', 'parent_ntp')
        self.assertEqual((result['updates'], result['assistant_targets']), (704, 2208612))
        self.assertEqual(v.read(v.activity_name('train', 'parent_ntp'))['complete'], True)
        self.assertGreater(v.spent(self.authority), 1000.)

    def test_no_short_epoch_or_step_cli_path(self):
        with self.assertRaises(SystemExit): v.main(['--mode', 'train', '--epochs', '1', '--execute'])
        with self.assertRaises(SystemExit): v.main(['--mode', 'train', '--steps', '32', '--execute'])

    def test_wrong_main_targets_or_active_horizon_cannot_be_saved_as_complete(self):
        self.finish('parent_mtp')
        _, good, _ = v.closed('train', 'parent_mtp'); a = self.args('train', 'parent_mtp')
        for key, value in (('updates', 703), ('assistant_targets', 2210436), ('actual_processed_x_tokens', 1)):
            bad = copy.deepcopy(good); bad[key] = value
            with self.assertRaises(ValueError): v.validate_training(bad, a, self.m, self.contract)
        bad = copy.deepcopy(good); bad['history'][-1]['active_head_target_counts']['2'] += 1
        with self.assertRaises(ValueError): v.validate_training(bad, a, self.m, self.contract)

    def test_initializer_dev_and_native_drift_are_not_hidden_by_completed_status(self):
        self.finish('parent_mtp')
        _, good, _ = v.closed('train', 'parent_mtp'); a = self.args('train', 'parent_mtp')
        mutations = [lambda x: x.update(initializer='SCRATCH_NO_WEIGHT_INIT'),
                     lambda x: x.update(initial_core_sha256='wrong-parent'),
                     lambda x: x['initial_val']['1'].update(targets=2978),
                     lambda x: x['final_native_ce'].update(val_sha256='different-native')]
        for mutate in mutations:
            bad = copy.deepcopy(good); mutate(bad)
            with self.assertRaises(ValueError): v.validate_training(bad, a, self.m, self.contract)

    def test_wrong_pinned_v4_report_never_falls_back_to_hf_partial_or_old_data(self):
        def wrong(name):
            self.assertEqual(name, v.CORPUS + '/report.json')
            return '0' * 64
        with patch.object(v, 'digest', side_effect=wrong):
            with self.assertRaisesRegex(ValueError, 'exact completed data_cache V4'):
                REAL_PREPARED(self.m)
        self.encode.assert_not_called(); self.train.assert_not_called()

    def test_stale_cpu_contract_is_a_prerequisite_hold_not_model_quality_pass(self):
        bad = copy.deepcopy(self.contract); bad['study_sha256'] = 'bad'
        with patch.object(v, 'read', return_value=bad):
            with self.assertRaises(v.Hold): v.load_contract()
        self.train.assert_not_called(); self.eval.assert_not_called()

    def test_cpu_contract_source_change_does_not_write_any_completion(self):
        target = v.BASE + '/cpu_contract_mutation_case/report.json'
        changed = copy.deepcopy(self.study); changed['code_sha256']['new-code'] = 'bad'
        with patch.object(v, 'CONTRACT', target), patch.object(v, 'study', side_effect=[self.study, changed]):
            with self.assertRaisesRegex(v.Hold, 'changed during CPU contract'):
                v.cpu_contract(self.m)
        self.assertFalse(v.path(target).exists())

    def test_imported_module_origin_and_complete_code_coverage_are_checked(self):
        names = ('diag_p101a_sft_mtp', 'diag_p101a_clean_bilingual', 'check_p101a_clean_cost',
                 'diag_p101a_clean_eval', 'p101a_supervision_repair')
        fake = {name: SimpleNamespace(__file__=str(self.root / 'scripts' / (name + '.py'))) for name in names}
        fake[names[0]].data = SimpleNamespace(__file__=str(self.root / 'scripts/p101a_sft_mtp_data.py'))
        fake[names[0]].CODE = ('scripts/mock_original_dependency.py',)
        self.put('scripts/diag_p101a_sft_mtp.py', b"CODE = ('scripts/mock_original_dependency.py',)\n")
        self.stack.enter_context(patch.object(v, 'PINS', dict(v.PINS,
            **{'scripts/diag_p101a_sft_mtp.py': v.digest('scripts/diag_p101a_sft_mtp.py')})))
        importer = lambda name: fake[name.removeprefix('scripts.')]
        with patch.object(v.importlib, 'import_module', side_effect=importer), \
             patch.object(v, 'sources', return_value={'scripts/mock_original_dependency.py': 'A' * 64}):
            self.assertEqual(REAL_MODULES()[0], fake[names[0]])
            original = fake[names[0]].__file__; fake[names[0]].__file__ = '/tmp/foreign_same_name.py'
            with self.assertRaisesRegex(ValueError, 'not the pinned source'): REAL_MODULES()
            fake[names[0]].__file__ = original
            fake[names[0]].data.__file__ = '/tmp/foreign_data.py'
            with self.assertRaisesRegex(ValueError, 'complete original engine.CODE'): REAL_MODULES()
        fake[names[0]].data.__file__ = str(self.root / 'scripts/p101a_sft_mtp_data.py')
        with patch.object(v.importlib, 'import_module', side_effect=importer), patch.object(v, 'sources', return_value={}):
            with self.assertRaisesRegex(ValueError, 'complete original engine.CODE'): REAL_MODULES()

    def test_runtime_encoder_does_not_fall_back_and_mutation_is_detected(self):
        a = self.args()
        with v.training_scope(a, self.m, self.contract, self.records):
            with self.assertRaises(ValueError): engine.corpus_report(self.root / 'HF' / 'old')
            self.records['train'][0].y[0] += 1
            with self.assertRaises(ValueError): engine.encoded(v.path(v.CORPUS), self.report, Tok())

    def test_stage_exception_writes_failed_activity_no_completion_and_blocks_followup(self):
        self.train.side_effect = RuntimeError('synthetic implementation failure')
        self.assertEqual(v.gpu_worker(self.args(), self.m), 9)
        self.assertFalse(v.read(v.activity_name('calibrate', 'parent_ntp'))['complete'])
        self.assertFalse(v.path(v.receipt_name('calibrate', 'parent_ntp')).exists())
        with self.assertRaises((ValueError, FileNotFoundError)): v.spent(self.authority)

    def test_post_save_record_mutation_cannot_emit_consumer_completion(self):
        def mutate(*args, **kwargs):
            rc = self.fake_train(*args, **kwargs)
            self.records['train'][0].y[0] += 1
            return rc
        self.train.side_effect = mutate
        self.assertEqual(v.gpu_worker(self.args(), self.m), 8)
        self.assertTrue(v.path(v.BASE + '/calibrate_parent_ntp/report.json').exists())
        self.assertFalse(v.path(v.receipt_name('calibrate', 'parent_ntp')).exists())
        self.assertFalse(v.read(v.activity_name('calibrate', 'parent_ntp'))['complete'])

    def test_whole_budget_does_not_reset_prior_spend(self):
        with patch.object(v, 'spent', return_value=143000.):
            with self.assertRaises(v.Hold): v.gpu_worker(self.args(), self.m)
        self.train.assert_not_called()

    def test_evaluation_uses_v4_student_selector_all512_raw_and_restores_preconditions(self):
        old = ev.prerequisites
        self.finish('parent_ntp', 'evaluate')
        receipt, result, _ = v.closed('evaluate', 'parent_ntp')
        self.assertEqual(result['counts']['total'], 512)
        self.assertEqual(result['family'], 'mtp'); self.assertEqual(result['output_selector'], v.TAG)
        self.assertIn(v.TAG, result['readable_review']); self.assertEqual(len(receipt['artifacts']), 2)
        self.assertIs(ev.prerequisites, old)

    def test_checkpoint_byte_replacement_is_rejected_before_evaluation_backend(self):
        self.finish('parent_ntp')
        name = str(engine.checkpoint(v.TAG, 'parent_ntp').relative_to(self.root))
        with patch.object(v, 'digest', wraps=v.digest) as hashed:
            original = hashed._mock_wraps
            hashed.side_effect = lambda p: '0' * 64 if p == name else original(p)
            with self.assertRaises(ValueError): v.evaluate(self.args('evaluate'), self.m, self.contract)
        self.eval.assert_not_called()

    def test_closed_raw_or_review_mutation_is_not_promoted_to_pair_pass(self):
        self.finish('parent_ntp', 'evaluate')
        receipt, _, _ = v.closed('evaluate', 'parent_ntp')
        name = next(iter(receipt['artifacts']))
        with patch.object(v, 'digest', wraps=v.digest) as hashed:
            original = hashed._mock_wraps; hashed.side_effect = lambda p: '0' * 64 if p == name else original(p)
            with self.assertRaises(ValueError): v.closed('evaluate', 'parent_ntp')

    def test_pair_readback_requires_both_students_and_evaluations_and_reports_two_of_four(self):
        self.finish('parent_ntp', 'evaluate')
        with self.assertRaises((ValueError, FileNotFoundError)): v.pair_readback(self.args('pair-readback'))
        self.finish('parent_mtp', 'evaluate')
        value = v.pair_readback(self.args('pair-readback'))
        self.assertEqual((value['selected_complete'], value['original_total']), (2, 4))
        self.assertEqual(value['pending_training_arms'], ['scratch_ntp', 'scratch_mtp'])
        self.assertIn('NOT_RUN', value['original_four_arm_compare']); self.assertEqual(engine.ARMS, v.ARMS)

    def contract_fixture(self, ignore_mask=False):
        filler = copy.deepcopy(self.val_row)
        filler['meta']['supervised_assistant_turns'] = [1]
        rows = [filler] * 22526; raw = {}; audit = {'repairs': []}
        for spec, width in zip(producer.REPAIRS, (189, 858)):
            row = dict(meta=dict(source='oasst', source_id=spec['source_id'], language='en',
                                supervised_assistant_turns=[2]), messages=[
                dict(role='user', content=[dict(type='text', text='mock first')]),
                dict(role='assistant', content=[dict(type='text', text='mock first response')]),
                dict(role='user', content=[dict(type='text', text='mock clarification')]),
                dict(role='assistant', content=[dict(type='text', text='mock correction')])])
            first, second = spec['expected_first_targets'], spec['expected_second_targets']
            gap = width - first - second
            record = core.Record(list(range(width)), [9] * (first - 1) + [4] + [-100] * gap + [8] * (second - 1) + [4],
                                 [1] * first + [0] * gap + [2] * second)
            raw[spec['source_id']] = record; rows.append(row)
            after = core.Record(record.x, [y if owner == 2 else -100 for y, owner in zip(record.y, record.segments)],
                                [owner if owner == 2 else 0 for owner in record.segments])
            audit['repairs'].append(dict(source_id=spec['source_id'],
                messages_sha256=engine.data.conversation_identity(row), after_turn_h1_to_h4=producer.turn_audit(after)))
        datasets = {'train': rows, 'val': self.val_rows}
        manifests = {split: {'split': split} for split in datasets}
        def encode(row, *_args, **_kwargs):
            return copy.deepcopy(raw.get(row['meta'].get('source_id'), core.Record([1, 2], [7, 4], [1, 1])))
        masses = {}
        with patch.object(core, 'encode_record', side_effect=encode):
            for split, source in datasets.items():
                mass = producer.new_mass()
                for row in source: producer.add_mass(mass, row, clean.masked_record(row, Tok()))
                masses[split] = producer.plain_mass(mass)
        report = {'manifests': manifests, 'after_mass': masses}
        fake_tokenizers = SimpleNamespace(Tokenizer=SimpleNamespace(from_file=lambda _: Tok()), __version__='SYNTHETIC_TOKENIZER')
        with patch.dict(sys.modules, {'tokenizers': fake_tokenizers}), \
             patch.object(v, 'prepared', return_value=(report, audit)), \
             patch.object(core, 'encode_record', side_effect=encode), \
             patch.object(engine.data, 'stream_rows', side_effect=lambda _directory, manifest: iter(datasets[manifest['split']])):
            if ignore_mask:
                with patch.object(clean, 'encoded', side_effect=lambda _c, _r, _t: {s: [encode(row) for row in source] for s, source in datasets.items()}):
                    return REAL_CONTRACT_RECORDS(self.m)
            return REAL_CONTRACT_RECORDS(self.m)

    def test_real_encoder_callback_and_horizon_schedule_on_only_synthetic_rows(self):
        records, summary = self.contract_fixture()
        self.assertEqual((len(records['train']), len(records['val'])), (22528, 512))
        self.assertEqual(len(summary['repairs']), 2)
        for record in records['train'][-2:]:
            self.assertNotIn(1, record.segments)
            self.assertEqual([y for y, owner in zip(record.y, record.segments) if owner == 2][-1], 4)
        self.assertLess(summary['expected_mtp_active_epoch_targets'][-1]['2'], summary['expected_mtp_active_epoch_targets'][0]['2'])
        self.assertEqual(summary['expected_cost']['updates'], 32)
        self.assertEqual(summary['records_sha256'], v.encoded_fingerprint(records))

    def test_real_contract_rejects_generic_encode_that_ignores_allowlist(self):
        with self.assertRaisesRegex(ValueError, 'ignored repaired'):
            self.contract_fixture(ignore_mask=True)


class EntryTests(unittest.TestCase):
    def test_source_manifest_contains_every_actual_original_engine_code_path(self):
        self.assertEqual(v.engine_code(), engine.CODE)
        self.assertTrue(set(engine.CODE) <= set(v.sources()))

    def test_train_and_evaluate_require_explicit_whole_worker_cap_before_modules(self):
        with patch.object(v, 'modules', side_effect=AssertionError('must reject before runtime imports')), redirect_stderr(io.StringIO()):
            self.assertEqual(v.main(['--mode', 'train', '--execute']), 8)
            self.assertEqual(v.main(['--mode', 'evaluate', '--execute']), 8)

    def test_cold_stdlib_check_only_imports_no_torch_and_opens_no_assets(self):
        code = ("import sys; from scripts import diag_p101a_supervision_v4 as v; "
                "assert 'torch' not in sys.modules; assert v.main(['--mode','check-only']) == 0; "
                "assert 'torch' not in sys.modules")
        p = subprocess.run(['/usr/bin/python3', '-B', '-X', 'utf8', '-c', code], cwd=ROOT,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr); self.assertIn('"asset_reads": 0', p.stdout)

    def test_child_reenters_own_adapter_and_timeout_only_signals_owned_group(self):
        process = Mock(pid=424242); process.wait.side_effect = [subprocess.TimeoutExpired('mock', 1200), 0]
        with patch.object(v.subprocess, 'Popen', return_value=process) as launch, patch.object(v.os, 'killpg') as kill:
            self.assertEqual(v.launch(['--mode', 'train', '--execute'], 1200), 130)
        argv = launch.call_args.args[0]
        self.assertEqual(argv[4], str(ROOT / v.SCRIPT)); self.assertEqual(argv[-1], '--worker')
        self.assertTrue(launch.call_args.kwargs['start_new_session']); kill.assert_called_once_with(424242, signal.SIGTERM)

    def test_protected_paths_and_linked_outputs_are_not_allowed(self):
        for p in ('../escape', '/absolute', 'datasets/TinyDataset/x', '.claude/x', 'a\\b'):
            with self.assertRaises(ValueError): v.path(p)


if __name__ == '__main__': unittest.main(verbosity=2)
