"""New CPU numerical schedule boundaries; no real model or old checkpoint."""
from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np
import torch

from scripts import p106b_dskdv2_training as fixed
from scripts import p106b_dskdv2_scheduled_training as scheduled
from scripts import test_p106b_dskdv2_training as fixtures
from scripts.p107_scaled_optimizer_group import ScaleConfig
from tinylm.train.anneal_schedule import lr_factor

FIXTURE_BASES = []
CONTROLS = []


class ScheduledFeatureTrainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():
            raise RuntimeError('CPU schedule controls require uninitialized CUDA')

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='p106b-dskd-schedule-C-', dir='/tmp'))
        FIXTURE_BASES.append(self.root)
        torch.manual_seed(2024)
        random.seed(19)
        np.random.seed(23)
        self.fixture = fixtures.Fixture(self.root, dtype=torch.float32, dropout=.2, external_random=True)

    def fresh(self):
        return fixtures.Fixture(self.root, dtype=torch.float32, write=False, dropout=.2, external_random=True)

    def optimizers(self, fixture):
        return [fixtures.CountedMuon([fixture.model.body, fixture.model.up], lr=.01, scale_mode='rms'),
                fixtures.CountedAdamW([fixture.model.embedding], lr=.001),
                fixtures.CountedAdamW([fixture.t2s], lr=.001, weight_decay=.1)]

    def trainer(self, fixture=None, phases=(True, False, True, True), schedule=None):
        fixture = self.fixture if fixture is None else fixture
        schedule = scheduled.ConsumedGroupSchedule(len(phases), warm=1) if schedule is None else schedule
        def provider(model, row):
            if model is not fixture.model:
                raise ValueError('provider bound to another numerical student')
            return fixture.provider(row)
        return scheduled.ScheduledFeatureTrainer(fixture.model, self.optimizers(fixture),
            fixtures.UpdateSource(fixture, phases), provider, schedule=schedule,
            signature='9' * 64, up=fixture.model.up, embedding=fixture.model.embedding,
            teacher_head=fixture.teacher_head, t2s=fixture.t2s, s2t=fixture.s2t, teacher_head_identity='F' * 64,
            student_width=8, teacher_width=9, mapping=fixture.mapping, mapping_modes=fixture.modes,
            chunk_positions=2, ce_chunk=2, kd_rate=.3,
            scale_config=ScaleConfig(init_scale=128., growth_interval=2))

    def test_manual_unscaled_optimizer_reference_matches_loss_full_updates_source_and_RNG(self):
        phases = (True, False, True, True)
        plan = scheduled.ConsumedGroupSchedule(4, warm=2, sched='cosine')
        trainer = self.trainer(schedule=plan)
        initial = trainer.state_dict()
        reports = [trainer.step() for _ in phases]
        wanted = trainer.state_dict()
        reference = self.fresh()
        opts = self.optimizers(reference)
        source = fixtures.UpdateSource(reference, phases)
        reference.model.load_state_dict(initial['boundary']['model'])
        with torch.no_grad():
            reference.t2s.copy_(initial['boundary']['external_projectors']['t2s'])
            reference.s2t.copy_(initial['boundary']['external_projectors']['s2t'])
        trainer._restore_rng(initial['boundary']['rng'])
        losses = []
        for ordinal, kd in enumerate(phases):
            update = source.next_update()
            factor = lr_factor(ordinal, plan.warm, plan.steps, plan.sched, plan.decay_frac)
            active = list(range(len(opts))) if kd else [0, 1]
            for index in active:
                for group, base in zip(opts[index].param_groups, initial['policy']['base_lrs'][index]):
                    group['lr'] = base * factor
            group = reference.group(reader=kd, kd_rate=.3)
            result = group.consume(reference.provider,
                lambda loss, context: loss.backward(retain_graph=context['retain_graph']))
            parameters = reference.parameters() if kd else list(reference.model.parameters())
            torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
            for index in active:
                opts[index].step()
                opts[index].zero_grad(set_to_none=True)
            losses.append(result['normalized_total'])
            self.assertEqual(update.ordinal, ordinal)
        self.assertEqual(losses, [report['group']['normalized_total'] for report in reports])
        self.assertTrue(fixed._same(reference.model.state_dict(), wanted['boundary']['model']))
        self.assertTrue(fixed._same(reference.t2s, wanted['boundary']['external_projectors']['t2s']))
        self.assertTrue(fixed._same(reference.s2t, wanted['boundary']['external_projectors']['s2t']))
        self.assertTrue(fixed._same([opt.state_dict() for opt in opts], wanted['boundary']['optimizers']))
        self.assertTrue(fixed._same(source.state_dict(), wanted['boundary']['source']))
        self.assertTrue(fixed._same(trainer._rng(), wanted['boundary']['rng']))
        CONTROLS.append(dict(scope='TINY_FP32_MANUAL_UNSCALED_REFERENCE', groups=4, CE_rows_per_group=5,
            CE_targets_per_group=15, KD_positions_when_active=7, independent_optimizer_reference=True,
            full_updates_losses_source_three_RNGs_exact=True,
            factors=[report['lr_schedule']['factor'] for report in reports],
            actual_language_training_tokens=0))

    def test_fresh_safe_checkpoint_future_rates_losses_complete_state_cross_warmup_and_cooldown(self):
        phases = (True, False, False, True, False, True)
        plan = scheduled.ConsumedGroupSchedule(6, warm=2, sched='cosine')
        trainer = self.trainer(phases=phases, schedule=plan)
        trainer.step()
        trainer.step()
        saved = trainer.state_dict()
        path = self.root / 'new_scheduled_numerical_boundary.pt'
        with path.open('xb') as stream:
            torch.save(saved, stream)
        reports = [trainer.step() for _ in range(4)]
        expected = trainer.state_dict()
        fresh = self.trainer(self.fresh(), phases=phases, schedule=plan)
        fresh.load_state_dict(torch.load(path, weights_only=True, map_location='cpu'))
        actual = [fresh.step() for _ in range(4)]
        self.assertTrue(fixed._same(actual, reports))
        self.assertTrue(fixed._same(fresh.state_dict(), expected))
        self.assertEqual(saved['lr_schedule']['last_active_ordinals'], [1, 1, 0])
        self.assertLess(actual[-1]['lr_schedule']['factor'], .3)
        CONTROLS.append(dict(scope='FRESH_OBJECTS_SAME_PROCESS_NEW_SAFE_CHECKPOINT', resumed_at_consumed=2,
            future_groups=4, future_reports_and_complete_state_exact=True,
            checkpoint_bytes=path.stat().st_size, cross_process=False))

    def test_overflow_advances_consumed_schedule_and_restores_future_exactly(self):
        phases = (True, False, True)
        plan = scheduled.ConsumedGroupSchedule(3, sched='decay')
        trainer = self.trainer(phases=phases, schedule=plan)
        parameters = [p.detach().clone() for p in trainer.parameters]
        calls = len(fixtures.STEP_CALLS)
        hook = trainer.model.body.register_hook(lambda grad: torch.full_like(grad, float('inf')))
        try:
            report = trainer.step()
        finally:
            hook.remove()
        self.assertEqual((trainer.completed_groups, trainer.applied_groups, trainer.skipped_groups), (1, 0, 1))
        self.assertEqual(len(fixtures.STEP_CALLS), calls)
        self.assertTrue(all(torch.equal(p, value) for p, value in zip(trainer.parameters, parameters)))
        self.assertEqual(report['lr_schedule']['next_ordinal'], 1)
        self.assertEqual(report['scaled_optimizer_group']['scale_after'], 64.)
        saved = trainer.state_dict()
        expected = [trainer.step(), trainer.step()]
        final = trainer.state_dict()
        fresh = self.trainer(self.fresh(), phases=phases, schedule=plan)
        fresh.load_state_dict(saved)
        self.assertTrue(fixed._same([fresh.step(), fresh.step()], expected))
        self.assertTrue(fixed._same(fresh.state_dict(), final))
        self.assertEqual(expected[0]['lr_schedule']['consumed_ordinal'], 1)
        self.assertEqual(expected[0]['lr_schedule']['factor'], lr_factor(1, 0, 3, 'decay', .2))

    def test_two_zero_KD_groups_preserve_all_projector_state_including_previous_LR(self):
        phases = (True, False, False, True)
        trainer = self.trainer(phases=phases, schedule=scheduled.ConsumedGroupSchedule(4, sched='decay'))
        trainer.step()
        before = copy.deepcopy(trainer.optimizers[2].state_dict())
        value = trainer.t2s.detach().clone()
        for ordinal in (1, 2):
            report = trainer.step()
            self.assertEqual(report['lr_schedule']['consumed_ordinal'], ordinal)
            self.assertTrue(fixed._same(trainer.optimizers[2].state_dict(), before))
            self.assertTrue(torch.equal(value, trainer.t2s))
            self.assertEqual(trainer.state_dict()['lr_schedule']['last_active_ordinals'], [ordinal, ordinal, 0])
        trainer.step()
        self.assertLess(trainer.optimizers[2].param_groups[0]['lr'], before['param_groups'][0]['lr'])
        self.assertEqual(float(trainer.optimizers[2].state[trainer.t2s]['step']), 2.)

    def test_partial_optimizer_failure_requires_full_schedule_model_source_RNG_restore(self):
        plan = scheduled.ConsumedGroupSchedule(4, sched='decay')
        trainer = self.trainer(schedule=plan)
        trainer.step()
        saved = trainer.state_dict()
        real_step = trainer.optimizers[1].step
        def fail(*args, **kwargs):
            raise RuntimeError('injected scheduled optimizer failure')
        trainer.optimizers[1].step = fail
        with self.assertRaisesRegex(RuntimeError, 'scheduled optimizer failure'):
            trainer.step()
        trainer.optimizers[1].step = real_step
        self.assertTrue(trainer.dirty)
        with self.assertRaises(RuntimeError):
            trainer.state_dict()
        with self.assertRaises(RuntimeError):
            trainer.step()
        trainer.load_state_dict(saved)
        actual = trainer.step()
        wanted = trainer.state_dict()
        fresh = self.trainer(self.fresh(), schedule=plan)
        fresh.load_state_dict(saved)
        self.assertTrue(fixed._same(fresh.step(), actual))
        self.assertTrue(fixed._same(fresh.state_dict(), wanted))

    def test_invalid_schedule_rate_and_base_boundary_snapshots_refuse_before_live_copy(self):
        trainer = self.trainer()
        trainer.step()
        trainer.step()
        initial = trainer.state_dict()
        for field in ('policy', 'schema', 'counter', 'student', 'projector', 'rate', 'optimizer', 'other_setting', 'bool'):
            bad = copy.deepcopy(initial)
            if field == 'policy':
                bad['policy']['base_lrs'][0][0] *= 2
            elif field == 'schema':
                bad['lr_schedule']['extra'] = 0
            elif field == 'counter':
                bad['lr_schedule']['next_ordinal'] -= 1
            elif field == 'student':
                bad['lr_schedule']['last_active_ordinals'][0] = 0
            elif field == 'projector':
                bad['lr_schedule']['last_active_ordinals'][2] = 1
            elif field == 'rate':
                bad['lr_schedule']['current_lrs'][0][0] *= 2
            elif field == 'optimizer':
                bad['boundary']['optimizers'][0]['param_groups'][0]['lr'] *= 2
            elif field == 'other_setting':
                bad['boundary']['optimizers'][1]['param_groups'][0]['eps'] *= 2
            else:
                bad['lr_schedule']['last_active_ordinals'][0] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                trainer.load_state_dict(bad)
            self.assertFalse(trainer.dirty)
            self.assertTrue(fixed._same(trainer.state_dict(), initial))
        with self.assertRaises(ValueError):
            trainer.load_state_dict(initial['boundary'])

    def test_failed_restore_stays_dirty_and_complete_envelope_retry_succeeds(self):
        trainer = self.trainer()
        trainer.step()
        saved = trainer.state_dict()
        fresh = self.trainer(self.fresh())
        real_load = fresh.source.load_state_dict
        def fail(state):
            raise RuntimeError('injected scheduled source restore failure')
        fresh.source.load_state_dict = fail
        with self.assertRaisesRegex(RuntimeError, 'source restore failure'):
            fresh.load_state_dict(saved)
        self.assertTrue(fresh.dirty)
        with self.assertRaises(RuntimeError):
            fresh.step()
        fresh.source.load_state_dict = real_load
        fresh.load_state_dict(saved)
        self.assertTrue(fixed._same(fresh.state_dict(), saved))

    def test_live_LR_change_is_refused_before_source_and_valid_restore_recovers(self):
        trainer = self.trainer()
        trainer.step()
        saved = trainer.state_dict()
        trainer.optimizers[0].param_groups[0]['lr'] *= 2
        with self.assertRaisesRegex(ValueError, 'live optimizer LR'):
            trainer.step()
        self.assertEqual(trainer.source.cursor, 1)
        trainer.load_state_dict(saved)
        self.assertTrue(fixed._same(trainer.state_dict(), saved))

    def test_budget_stops_before_another_source_call_and_early_normal_EOF_is_unchanged(self):
        trainer = self.trainer(phases=(True, False, True), schedule=scheduled.ConsumedGroupSchedule(2))
        count = [0]
        next_update = trainer.source.next_update
        def next_counted():
            count[0] += 1
            return next_update()
        trainer.source.next_update = next_counted
        trainer.step()
        trainer.step()
        before = trainer.state_dict()
        with self.assertRaisesRegex(StopIteration, 'planned'):
            trainer.step()
        self.assertEqual(count[0], 2)
        self.assertTrue(fixed._same(trainer.state_dict(), before))
        early = self.trainer(self.fresh(), phases=(True,), schedule=scheduled.ConsumedGroupSchedule(3))
        early.step()
        before = early.state_dict()
        with self.assertRaises(StopIteration):
            early.step()
        self.assertFalse(early.dirty)
        self.assertTrue(fixed._same(early.state_dict(), before))

    def test_declared_profiles_use_canonical_formula_and_reject_invalid_control(self):
        for name in ('cosine', 'wsd', 'stable', 'decay'):
            plan = scheduled.ConsumedGroupSchedule(8, warm=2, sched=name, decay_frac=.5)
            self.assertEqual([plan.factor(i) for i in range(8)],
                             [lr_factor(i, 2, 8, name, .5) for i in range(8)])
            if name != 'decay':
                self.assertEqual([plan.factor(i) for i in range(2)], [.5, 1.])
        plan = scheduled.ConsumedGroupSchedule(8)
        for change in (dict(steps=0), dict(steps=True), dict(warm=8), dict(sched='cosin'),
                       dict(decay_frac=0), dict(decay_frac=float('nan'))):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(plan, **change)
        for ordinal in (-1, 8, True):
            with self.assertRaises(ValueError):
                plan.factor(ordinal)


if __name__ == '__main__':
    unittest.main()
