"""Synthetic CPU tests: real corpus, learned weights and GPU entrypoints blocked."""
from __future__ import annotations
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_cpt_unique32k as d
from scripts.p106b_shards import ShardWriter


def courses():
    rec = NS(x_tokens=10, targets=2, x=[7] * 10, y=[-100] * 8 + [9, 4], segments=[0] * 8 + [1, 1])
    natural = [[rec, rec] for _ in range(8192)]; replay = [rec] * 4096
    return [(natural, replay)] * 4


def groups_receipt():
    return [dict(optimizer='adamw', group=0, lr=5e-5, weight_decay=.1, tensors=1,
                 parameters=24, state_entries_before_updates=0),
            dict(optimizer='muon', group=0, lr=2e-4, weight_decay=0., tensors=1,
                 parameters=20, state_entries_before_updates=0)]


def json_fixture(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + '\n', encoding='utf-8')


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stub(d.foundation, 'load_foundation_parent', Mock(side_effect=AssertionError('real parent load forbidden')))
        self.stub(d.original_driver, 'read_source', Mock(side_effect=AssertionError('real source read forbidden')))
        self.stub(d.previous, 'deadline', Mock(side_effect=AssertionError('old deadline forbidden')))
        self.stub(d.other, 'budget', Mock(side_effect=AssertionError('old budget forbidden')))
        self.stub(d.foundation.runtime, 'load_runtime', Mock(side_effect=AssertionError('real model construction forbidden')))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('interactive input forbidden')))
        import torch
        self.stack.enter_context(patch('torch.load', side_effect=AssertionError('learned weights forbidden')))
        self.stack.enter_context(patch('torch.save', side_effect=AssertionError('checkpoint writing forbidden')))

    def stub(self, target, name, value):
        return self.stack.enter_context(patch.object(target, name, value))

    def temp_paths(self):
        temp = TemporaryDirectory(prefix='cpt_unique32k_cpu_'); self.addCleanup(temp.cleanup)
        root = Path(temp.name); self.stub(d, 'ROOT', root)
        self.stub(d, 'LOCAL', root / 'local'); self.stub(d, 'CORPUS', root / 'local/corpus')
        self.stub(d, 'EVIDENCE', root / 'evidence'); self.stub(d, 'INITIALIZER', root / 'native.pt')
        return root


class EquivalenceTests(Guarded):
    def test_exact_ast_and_text_after_explicit_allowed_edits(self):
        proof = d.core_equivalence()
        self.assertEqual(set(proof), {'checkpoint', 'completed', 'save', 'run'})
        self.assertTrue(all(v['ast_equal_after_declared_edits'] and v['character_equal_after_declared_edits'] for v in proof.values()))
        self.assertEqual(len(proof['run']['allowed_substitutions']), 7)
        self.assertTrue(all(e['occurrences'] == 1 for v in proof.values() for e in v['allowed_substitutions']))

    def test_math_optimizer_order_lr_schedule_and_selection_mutations_rejected(self):
        source = Path(d.__file__).read_text(encoding='utf-8')
        edits = (('loss = values[0] / denom', 'loss = values[0] / (denom + 1)'),
                 ('loss_native = sums[1] / 8192', 'loss_native = sums[1] / 8191'),
                 ('adam.step(); muon.step()', 'muon.step(); adam.step()'),
                 ("group['lr'] *= .5", "group['lr'] *= .4"),
                 ('method.schedule(len(natural), len(replay), quarter)', 'method.schedule(len(natural), len(replay), 0)'),
                 ("entry['dev']['ce'] < best_ce", "entry['dev']['ce'] <= best_ce"),
                 ("foundation.load_foundation_parent('cpt_qa')", "foundation.load_foundation_parent('base_qa')"))
        for old, new in edits:
            self.assertIn(old, source)
            with self.subTest(edit=old), self.assertRaises(ValueError):
                # Last occurrence is in run; earlier occurrence may be allowlist/prepare.
                at = source.rfind(old)
                changed = source[:at] + source[at:].replace(old, new, 1)
                d.core_equivalence(candidate_source=changed)

    def test_comment_only_change_is_not_hidden_by_ast_equality(self):
        source = Path(d.__file__).read_text(encoding='utf-8')
        needle = 'adam.step(); muon.step(); steps += 1'
        with self.assertRaises(ValueError):
            d.core_equivalence(candidate_source=source.replace(needle, needle + '  # changed science segment'))

    def test_initializer_saved_metadata_is_native_and_qa_completed_path_is_not_used(self):
        self.assertEqual(d.INITIALIZER, d.foundation.checkpoint('native'))
        self.assertNotEqual(d.INITIALIZER, d.foundation.checkpoint('cpt_qa'))
        self.assertEqual(d.INITIALIZER_SHA, 'D6ECF7127A719A08ED396B39A51285DD9F20568880F21049DF56149E01A53A11')
        self.assertNotEqual(d.INITIAL_CORE, d.SOURCE_INITIAL_CORE)
        proof = dict(initial_core_sha256=d.INITIAL_CORE)
        d.verify_initializer(d.INITIAL_CORE, d.INITIALIZER, d.INITIALIZER_SHA, proof)
        for values in ((d.SOURCE_INITIAL_CORE, d.INITIALIZER, d.INITIALIZER_SHA, proof),
                       (d.INITIAL_CORE, d.foundation.checkpoint('cpt_qa'), d.INITIALIZER_SHA, proof),
                       (d.INITIAL_CORE, d.INITIALIZER, 'X' * 64, proof)):
            with self.assertRaises(ValueError): d.verify_initializer(*values)

    def test_info_current_authority_and_future_entry_eval_code_are_explicit(self):
        info = d.info()
        self.assertEqual(info['deadline_utc'], '2026-10-20T08:00:00+00:00')
        self.assertEqual(info['training_stop_utc'], '2026-10-20T06:30:00+00:00')
        self.assertEqual(d.AUTHORITY_END, d.END)
        self.assertNotIn('budget_only_revision', info)
        self.assertNotIn('weight_decay', info)
        self.assertIn('historical_gpu_stop_utc', info['original_driver_info'])
        for path in ('scripts/p106b_cpt_unique32k_entry.py', 'scripts/test_p106b_cpt_unique32k_entry.py',
                     'scripts/diag_p106b_cpt_unique32k_eval.py', 'scripts/test_p106b_cpt_unique32k_eval.py'):
            self.assertIn(path, d.CODE)


class CourseAndOptimizerTests(Guarded):
    def test_same640_whole_update_courses_exposure_and_native_order(self):
        values = courses(); plan = d.course_plan(values)
        self.assertEqual(len(plan['updates']), 640)
        self.assertEqual(plan['updates'][-1], dict(updates=640, logical_quarter=4, natural_epoch=1,
            x=819200, assistant_targets=163840, native_x=5242880))
        self.assertEqual(plan['totals']['padded_slots'], 83886080)
        self.assertEqual(plan['totals']['pairs_seen'], 32768)
        self.assertEqual([s['updates'] for s in plan['schedules']], [160] * 4)
        self.assertEqual(len({s['schedule_sha256'] for s in plan['schedules']}), 4)
        self.assertEqual(plan, d.course_plan(values))

    def test_missing_quarter_or_wrong_micro_population_refused(self):
        with self.assertRaises(ValueError): d.course_plan(courses()[:-1])
        values = courses(); values[0] = (values[0][0][:-1], values[0][1])
        with self.assertRaises(ValueError): d.course_plan(values)

    def test_actual_embedding_wd_is_preserved_and_groups_are_read_only(self):
        import torch
        embedding = torch.nn.Parameter(torch.zeros(8, 3)); matrix = torch.nn.Parameter(torch.zeros(4, 5))
        adam = NS(state={}, param_groups=[dict(params=[embedding], lr=5e-5, weight_decay=.1)])
        muon = NS(state={}, param_groups=[dict(params=[matrix], lr=2e-4, weight_decay=0.)])
        before = [(g['lr'], g['weight_decay']) for opt in (adam, muon) for g in opt.param_groups]
        receipts = d.optimizer_receipt(adam, muon)
        self.assertEqual(receipts, groups_receipt())
        self.assertEqual(before, [(g['lr'], g['weight_decay']) for opt in (adam, muon) for g in opt.param_groups])
        d.verify_optimizer_receipt(receipts)
        adam.state['existing'] = {}
        with self.assertRaises(ValueError): d.optimizer_receipt(adam, muon)

    def test_missing_nonfinite_or_nonfresh_receipt_refused(self):
        for values in (None, [], [groups_receipt()[0]], [dict(r, state_entries_before_updates=1) for r in groups_receipt()],
                       [dict(r, lr=float('nan')) for r in groups_receipt()]):
            with self.assertRaises(ValueError): d.verify_optimizer_receipt(values)


class SourceTests(Guarded):
    @classmethod
    def setUpClass(cls):
        cls.values = courses(); cls.plan = d.course_plan(cls.values)

    def source_fixture(self):
        root = self.temp_paths(); self.store = {}
        self.stub(d.original_driver, 'CORPUS', root / 'old/corpus')
        self.stub(d.original_driver, 'EVIDENCE', root / 'old_evidence')
        old = dict(status='DIVERSITY_CPU_FROZEN', code_sha256={'old': 'CODE'},
            initial_core_sha256=d.SOURCE_INITIAL_CORE, padding=[0, 4], source_rewritten=False,
            actual_exposure=dict(rows=81920, x_tokens=819200, assistant_targets=163840),
            schedules=deepcopy(self.plan['schedules']), original_cpu_sha256='ORIGINAL_CPU',
            original_manifests={'train': {'rows': 32768}}, inventory={'unique': 32768}, same_replay_sha256='REPLAY')
        self.expanded = dict(train=[dict(root='train')], dev=[dict(root='dev')], test=[dict(root='test')])
        self.tok = NS(to_str=lambda: 'synthetic-tokenizer')
        self.qa_original = dict(native_train_offsets=[0, 1025])
        loader = Mock(return_value=(old, self.expanded, self.tok, self.values, self.qa_original))
        self.stub(d.original_driver, 'read_source', loader)
        self.stub(d.original_driver, 'info', lambda: dict(code_sha256={'old': 'CODE'}))
        self.stub(d, 'course_plan', lambda values: deepcopy(self.plan))
        self.stub(d, 'native_source', lambda: dict(initial_core_sha256=d.INITIAL_CORE, initializer_sha256=d.INITIALIZER_SHA))
        self.stub(d, 'core_equivalence', lambda: {'run': {'verified': True}})
        self.stub(d, 'info', lambda: dict(code_complete=True, code_sha256={'new': 'CODE'}, tag=d.TAG))
        self.stub(d.qa.data, 'digest', lambda path: 'DIGEST')
        self.stub(d, 'required', lambda path: deepcopy(self.store[Path(path)]))
        self.stub(d.qa, 'write', lambda path, value: self.store.__setitem__(Path(path), deepcopy(value)))
        return old, loader

    def install_prepared(self):
        self.source_fixture(); binding, *_ = d.source_snapshot()
        report = dict(d.info(), **binding, status='DIVERSITY_CPU_FROZEN', initial_core_sha256=d.INITIAL_CORE,
            initializer=str(d.INITIALIZER.relative_to(d.ROOT)), initializer_sha256=d.INITIALIZER_SHA,
            actual_parent_loaded_cpu=True, cuda_initialized=False, padding=[0, 4], actual_padded_shape=[8, 1024],
            first160_actual_x_y_equal=True, model_forward=False, checkpoints_written=0, optimizer_updates=0,
            source_corpus=str(d.original_driver.CORPUS.relative_to(d.ROOT)), source_rewritten=False)
        self.store[d.CORPUS / 'report.json'] = report
        self.store[d.EVIDENCE / 'cpu_contract.json'] = deepcopy(report)
        return report

    def test_source_returns_same_unmodified_courses_and_separate_initial_provenance(self):
        proof = self.install_prepared(); result = d.read_source()
        self.assertIs(result[1], self.expanded); self.assertIs(result[2], self.tok); self.assertIs(result[3], self.values)
        self.assertIs(result[4], self.qa_original)
        self.assertEqual(result[0]['source_initial_core_sha256'], d.SOURCE_INITIAL_CORE)
        self.assertEqual(result[0]['initial_core_sha256'], d.INITIAL_CORE)
        self.assertEqual(result[0], proof)
        d.foundation.load_foundation_parent.assert_not_called()

    def test_native_source_code_courses_padding_and_initializer_mutations_refused(self):
        proof = self.install_prepared()
        for key, value in dict(source_initial_core_sha256=d.INITIAL_CORE, initial_core_sha256=d.SOURCE_INITIAL_CORE,
                initializer_sha256='OTHER', initializer='qa_completed.pt', code_sha256={}, schedules=[],
                actual_exposure={}, source_split_sha256={}, padding=[0, 5], actual_padded_shape=[1, 1024],
                source_rewritten=True, optimizer_updates=1).items():
            changed = deepcopy(proof); changed[key] = value
            self.store[d.CORPUS / 'report.json'] = changed
            self.store[d.EVIDENCE / 'cpu_contract.json'] = deepcopy(changed)
            with self.subTest(field=key), self.assertRaises(ValueError): d.read_source()

    def test_public_and_local_cpu_contract_must_agree(self):
        self.install_prepared(); self.store[d.EVIDENCE / 'cpu_contract.json']['model_forward'] = True
        with self.assertRaises(ValueError): d.read_source()

    def test_cpu_prepare_uses_native_loader_padding_only_without_forward(self):
        self.source_fixture()
        from tinylm.train import mtp_sft as core
        model = NS(forward=Mock()); torch = NS(cuda=NS(is_initialized=lambda: False))
        loader = Mock(return_value=(torch, model, None, self.tok, d.INITIAL_CORE, d.INITIALIZER, d.INITIALIZER_SHA))
        self.stub(d.foundation, 'load_foundation_parent', loader)
        shape = NS(shape=(8, 1024)); pad = self.stub(core, 'pad_records', Mock(return_value=(shape, shape, shape)))
        self.stub(d.previous, 'special_ids', lambda tok: (0, 4, '<pad>'))
        self.stub(d, 'authority', lambda **kwargs: 10000.)
        with redirect_stdout(io.StringIO()): self.assertEqual(d.prepare(), 0)
        loader.assert_called_once_with('cpt_qa'); model.forward.assert_not_called()
        self.assertEqual(pad.call_args.kwargs, dict(fixed_width=1024, batch_size=8))
        self.assertEqual(len(self.store), 2)
        self.assertEqual(self.store[d.CORPUS / 'report.json']['source_initial_core_sha256'], d.SOURCE_INITIAL_CORE)

    def test_incomplete_driver_entry_eval_code_blocks_prepare_before_source(self):
        self.temp_paths(); self.stub(d, 'info', lambda: dict(code_complete=False))
        self.stub(d, 'authority', lambda **kwargs: 10000.)
        with self.assertRaises(d.PrerequisitePending): d.prepare()
        d.original_driver.read_source.assert_not_called(); d.foundation.load_foundation_parent.assert_not_called()


class CostBudgetAndCompletionTests(Guarded):
    def cost_fixture(self):
        root = self.temp_paths(); values = courses(); total, updates = d.original_driver._first8(values)
        proof = dict(cost8_expected=total, cost8_updates=updates, initial_core_sha256=d.INITIAL_CORE)
        self.info = dict(code_sha256={'new': 'CODE'}, tag=d.TAG)
        self.stub(d, 'info', lambda: deepcopy(self.info)); self.stub(d.qa.data, 'digest', lambda path: 'CPU')
        report = dict(total, **self.info, status='DIVERSITY_COST_COMPLETE', updates=8,
            cpu_contract_sha256='CPU', initializer_sha256=d.INITIALIZER_SHA,
            initial_core_sha256=d.INITIAL_CORE, source_initial_core_sha256=d.SOURCE_INITIAL_CORE,
            actual_oom=False, checkpoint_written=False, actual_optimizer_groups=groups_receipt(),
            event_manifest=dict(rows=8, lineage=deepcopy(self.info)), step_seconds=[99.] + [2.] * 7,
            whole_seconds=115., grad_max=.6, clip_events=0)
        events = [dict(row, ce=3., grad=.6, step_seconds=report['step_seconds'][i]) for i, row in enumerate(updates)]
        self.stub(d, '_cost_events', Mock(return_value=events))
        return root, proof, report, events

    def test_cost8_worst_seven_warm_steps_and_exact_source_recount(self):
        _, proof, report, _ = self.cost_fixture()
        self.assertEqual(d.cost_forecast(report, proof), 1880.)
        self.assertEqual(report['native_x_tokens'], 65536)
        self.assertEqual(report['padded_slots'], 1048576)

    def test_base_initializer_partial_wrong_code_nonfinite_or_oom_cost_refused(self):
        _, proof, report, _ = self.cost_fixture()
        for change in (dict(tag='old'), dict(updates=7), dict(initializer_sha256=d.foundation.data.PARENT_SHA),
                dict(initial_core_sha256=d.SOURCE_INITIAL_CORE), dict(source_initial_core_sha256=d.INITIAL_CORE),
                dict(code_sha256={}), dict(event_manifest=dict(rows=8, lineage={})), dict(actual_oom=True),
                dict(checkpoint_written=True), dict(step_seconds=[float('nan')] + [2.] * 7),
                dict(actual_optimizer_groups=[]), dict(assistant_targets=0), dict(whole_seconds=1.),
                dict(grad_max=0.), dict(clip_events=1)):
            with self.subTest(change=change), self.assertRaises(ValueError): d.cost_forecast(dict(report, **change), proof)

    def test_cost_raw_missing_duplicate_or_changed_timing_refused(self):
        _, proof, report, events = self.cost_fixture()
        for bad in (events[:-1], [events[0]] * 8, [dict(e, x=0) for e in events],
                    [dict(e, step_seconds=3.) for e in events], [dict(e, ce=float('inf')) for e in events]):
            d._cost_events.return_value = bad
            with self.assertRaises((ValueError, d.PrerequisitePending)): d.cost_forecast(report, proof)

    def test_current_full_budget_reserves_final_dev_and_one_hour_records(self):
        _, proof, report, _ = self.cost_fixture()
        self.stub(d, 'required', lambda path: deepcopy(report))
        result = d.budget(proof, now=d.END - timedelta(hours=5))
        self.assertEqual(result['needed_seconds'], 1880 + 1800 + 3600)
        self.assertEqual(result['reserve_seconds'], 3600)
        self.assertEqual(result['cost8_already_spent_seconds'], 115.)
        self.assertTrue(result['fits'])
        d.other.budget.assert_not_called(); d.previous.deadline.assert_not_called()
        for remaining in (7280, 5400, 0):
            with self.assertRaises(d.PrerequisitePending): d.budget(proof, now=d.END - timedelta(seconds=remaining))

    def test_cost_only_budget_caps_work_and_does_not_claim_full_training(self):
        self.cost_fixture()
        reservation = d.cost_reservation(14400, now=d.END - timedelta(hours=5))
        self.assertEqual(reservation['cost_wall_seconds'], 900)
        self.assertFalse(reservation['full_training_admitted'])
        with self.assertRaises(d.PrerequisitePending): d.cost_reservation(14400, now=d.END - timedelta(seconds=6300))

    def test_authority_uses_current_absolute_dates_not_old_deadline(self):
        now = d.END - timedelta(hours=2)
        self.assertEqual(d.authority(now=now), 7200.)
        self.assertEqual(d.authority(training=True, now=now), 1800.)
        for value in (d.END, d.END + timedelta(seconds=1)):
            with self.assertRaises(d.PrerequisitePending): d.authority(now=value)
        with self.assertRaises(ValueError): d.authority(now=d.END.replace(tzinfo=None))

    def test_completed_requires_full640_events_checkpoint_and_dev_only_selection(self):
        root, _, _, _ = self.cost_fixture()
        plan = d.course_plan(courses()); expected = plan['totals']
        proof = dict(actual_exposure=dict(rows=81920, x_tokens=expected['actual_x_tokens'],
            assistant_targets=expected['assistant_targets']), initial_core_sha256=d.INITIAL_CORE, course_plan=plan)
        events = [dict(v, ce=3., grad=.6, step_seconds=2.) for v in plan['updates']]
        report = dict(self.info, status='DIVERSITY_TRAIN_COMPLETE', updates=640, cpu_contract_sha256='CPU',
            initial_core_sha256=d.INITIAL_CORE, source_initial_core_sha256=d.SOURCE_INITIAL_CORE,
            initializer_sha256=d.INITIALIZER_SHA, actual_x_tokens=expected['actual_x_tokens'],
            assistant_targets=expected['assistant_targets'], native_x_tokens=5242880, padded_slots=83886080,
            pairs_seen=32768, natural_epoch=1, logical_quarters=4, actual_oom=False, checkpoint_written=True,
            content_targets=expected['content_targets'], initializer=str(d.INITIALIZER.relative_to(root)),
            checkpoint=str(d.checkpoint().relative_to(root)), checkpoint_sha256='CPU',
            event_manifest=dict(rows=640, lineage=deepcopy(self.info)), step_seconds=[2.] * 640,
            grad_max=.6, clip_events=0, optimizer_saved=False, source_immutable=True,
            actual_optimizer_groups=groups_receipt(), history=[dict(logical_quarter=i, updates=i * 160,
                dev=dict(ce=float(i))) for i in (1, 2, 3, 4)], best_dev_quarter=1, best_dev_ce=1.,
            final_core_sha256='A' * 64, best_dev_core_sha256='B' * 64,
            best_dev_checkpoint=str(d.checkpoint(True).relative_to(root)), best_dev_checkpoint_sha256='CPU')
        self.stub(d, '_read_events', Mock(return_value=events))
        self.assertFalse(d.completed(proof))
        path = d.EVIDENCE / 'unique32k/report.json'; json_fixture(path, report)
        self.assertTrue(d.completed(proof))
        for key, value in dict(updates=639, initializer_sha256=d.foundation.data.PARENT_SHA,
                checkpoint='qa_completed.pt', best_dev_quarter=2, source_initial_core_sha256='wrong',
                history=[], grad_max=0., content_targets=1, actual_optimizer_groups=[]).items():
            changed = deepcopy(report); changed[key] = value; json_fixture(path, changed)
            with self.subTest(field=key), self.assertRaises(ValueError): d.completed(proof)


class NativeTimelineTests(Guarded):
    def fixture(self):
        root = self.temp_paths(); self.store = {}; self.events = []
        self.stub(d.foundation.data, 'CORPUS', root / 'native_corpus')
        self.stub(d.foundation.data, 'EVIDENCE', root / 'native_evidence')
        self.stub(d.foundation.data, 'PARENT', root / 'original.pt')
        self.stub(d.foundation.data, 'validate_contract', lambda contract: None)
        self.stub(d.foundation, 'info', lambda: dict(code_sha256={'native': 'CODE'}))
        self.stub(d, 'required', lambda path: deepcopy(self.store[Path(path)]))
        self.stub(d.qa.data, 'digest', lambda path: d.INITIALIZER_SHA if Path(path) == d.INITIALIZER else 'DIGEST')
        report = dict(status='FOUNDATION_TRAIN_COMPLETE', tag=d.foundation.data.TAG, arm='native',
            code_sha256={'native': 'CODE'}, updates=2281, actual_x_tokens=298975232, actual_targets=298975232,
            padded_slots=298975232, native_replay_x=0, natural_pairs=0, content_targets=0,
            actual_oom=False, checkpoint_written=True, optimizer_saved=False, original_assets_preserved=True,
            initial_core_sha256=d.SOURCE_INITIAL_CORE, initializer='original.pt', initializer_sha256=d.foundation.data.PARENT_SHA,
            checkpoint='native.pt', checkpoint_sha256=d.INITIALIZER_SHA, final_core_sha256=d.INITIAL_CORE,
            contract_sha256='DIGEST', source_qa_sha256=d.foundation.data.LOCKED_QA_SHA,
            step_seconds=[2.] * 2281, grad_max=.5, clip_events=0,
            event_manifest=dict(rows=2281, concat_sha256='EVENTS', lineage=dict(tag=d.foundation.data.TAG,
                arm='native', status='FOUNDATION_TRAIN_COMPLETE')))
        self.store[d.foundation.data.EVIDENCE / 'native/report.json'] = report
        self.store[d.foundation.data.CORPUS / 'native_contract.json'] = dict(steps=2281, actual_draw_tokens=298975232)
        self.store[d.foundation.data.EVIDENCE / 'cpt_qa/report.json'] = dict(status='FOUNDATION_TRAIN_COMPLETE', arm='cpt_qa',
            updates=640, code_sha256={'native': 'CODE'}, initializer='native.pt', initializer_sha256=d.INITIALIZER_SHA,
            initial_core_sha256=d.INITIAL_CORE)
        self.events = [dict(arm='native', updates=i, epoch=1, x=i * 131072, targets=i * 131072,
                           native_replay_x=0, ce=3., grad=.5, step_seconds=2.) for i in range(1, 2282)]
        self.stub(d, '_read_events', Mock(return_value=self.events))
        return report

    def test_complete_native2281_full_timeline_and_cpt8_initializer_reference(self):
        self.fixture(); proof = d.native_source()
        self.assertEqual(proof['native_updates'], 2281)
        self.assertEqual(proof['native_actual_targets'], 298975232)
        self.assertEqual(proof['initial_core_sha256'], d.INITIAL_CORE)
        d.foundation.load_foundation_parent.assert_not_called()

    def test_native_report_qa_completed_checkpoint_oom_or_wrong_counts_refused(self):
        report = self.fixture(); baseline = deepcopy(report)
        for field, value in dict(updates=2280, actual_x_tokens=298975231, actual_oom=True,
                checkpoint='qa_completed.pt', checkpoint_sha256='wrong', final_core_sha256=d.SOURCE_INITIAL_CORE,
                initial_core_sha256=d.INITIAL_CORE, contract_sha256='wrong', code_sha256={}).items():
            report.clear(); report.update(deepcopy(baseline)); report[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): d.native_source()

    def test_native_event_source_order_gradient_and_prior_initializer_change_refused(self):
        report = self.fixture(); baseline = deepcopy(self.events)
        for change in (dict(updates=1), dict(x=1), dict(native_replay_x=8192), dict(step_seconds=3.), dict(grad=float('inf'))):
            self.events[:] = deepcopy(baseline); self.events[2].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): d.native_source()
        self.events[:] = baseline
        self.store[d.foundation.data.EVIDENCE / 'cpt_qa/report.json']['initializer_sha256'] = 'QA_COMPLETED'
        with self.assertRaises(ValueError): d.native_source()


class StorageAndCLITests(Guarded):
    def test_write_once_shards_manifest_mutation_missing_and_symlink_guards(self):
        root = self.temp_paths(); directory = root / 'events'
        writer = ShardWriter(directory, 'events'); writer.append(dict(updates=1))
        manifest = writer.close(lineage=dict(test=True)); report = dict(event_manifest=manifest)
        self.assertEqual(d._read_events(directory, report, 1), [dict(updates=1)])
        with self.assertRaises(d.PrerequisitePending): d._read_events(directory, report, 2)
        changed = deepcopy(report); changed['event_manifest']['shards'][0]['sha256'] = 'wrong'
        with self.assertRaises(ValueError): d._read_events(directory, changed, 1)
        with self.assertRaises(d.PrerequisitePending): d.required(root / 'missing.json')
        empty = root / 'empty.json'; empty.touch()
        with self.assertRaises(d.PrerequisitePending): d.required(empty)
        link = root / 'linked'; link.symlink_to(directory, target_is_directory=True)
        with self.assertRaises(ValueError): d.safe(link / 'event.json')
        with self.assertRaises(ValueError): d.safe(root / '..' / 'outside')

    def test_check_only_and_preflight_do_not_load_or_mutate(self):
        self.stub(d, 'info', lambda: dict(tag=d.TAG, code_complete=False))
        read = self.stub(d, 'read_source', Mock(return_value=(dict(),)))
        self.stub(d, 'authority', lambda **kwargs: 10000.)
        with redirect_stdout(io.StringIO()):
            for mode in ('prepare', 'preflight', 'cost', 'train'):
                self.assertEqual(d.main(['--mode', mode, '--check-only']), 0)
            read.assert_not_called()
            self.assertEqual(d.main(['--mode', 'preflight', '--execute']), 0)
        read.assert_called_once_with(); d.foundation.load_foundation_parent.assert_not_called()

    def test_cli_explicit_execution_bounds_and_failure_statuses(self):
        self.stub(d, 'authority', lambda **kwargs: 10000.)
        with redirect_stderr(io.StringIO()):
            for args in (['--mode', 'cost'], ['--mode', 'cost', '--execute', '--check-only'],
                         ['--mode', 'cost', '--execute', '--max-wall-sec', '0']):
                with self.assertRaises(SystemExit): d.main(args)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.stub(d, 'prepare', Mock(side_effect=d.PrerequisitePending('not run')))
            self.assertEqual(d.main(['--mode', 'prepare', '--execute']), 8)
            d.prepare.side_effect = ValueError('tool mismatch')
            self.assertEqual(d.main(['--mode', 'prepare', '--execute']), 9)
        self.assertEqual(d.failure_status(KeyboardInterrupt()), ('INTERRUPTED', 130))
        oom = type('OutOfMemoryError', (RuntimeError,), {'__module__': 'torch.cuda'})
        self.assertEqual(d.failure_status(oom('synthetic')), ('ACTUAL_RESOURCE_OOM', 8))

    def test_fresh_process_help_and_check_only_never_need_real_sources(self):
        for args in (['--help'], ['--mode', 'train', '--check-only']):
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/diag_p106b_cpt_unique32k.py'), *args],
                cwd=ROOT, stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__': unittest.main(verbosity=2)
