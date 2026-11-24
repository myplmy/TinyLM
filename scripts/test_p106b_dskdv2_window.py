"""CPU-only synthetic original-frame/global-denominator and failure contracts."""
from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from scripts import p106b_dskdv2_window as core
from scripts import p106b_dskdv2_contract as dense
from scripts.p106b_feature_window import FeatureWindow


class NativeWindowContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():
            raise RuntimeError('synthetic CPU contracts require uninitialized CUDA')

    @classmethod
    def tearDownClass(cls):
        if torch.cuda.is_initialized():
            raise RuntimeError('synthetic CPU contracts initialized CUDA')

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='tinylm-dskd-window-v1-', dir='/tmp'))
        self.arrays = [np.linspace(-.7, .8, 20, dtype=np.float32).reshape(5, 4),
                       np.linspace(.4, -.6, 28, dtype=np.float32).reshape(7, 4)]
        self.mapping = [i % 9 for i in range(11)]
        self.modes = [1 if i % 2 else 3 for i in range(11)]
        self.records = []
        indices = [([4, 0, 2], [3, 0, 4]), ([2, 6, 1, 3], [4, 1, 0, 3])]
        for row_index, (array, (teacher_indices, student_indices)) in enumerate(zip(self.arrays, indices)):
            path = self.root / ('r' + str(row_index) + '.npy')
            with path.open('xb') as stream:
                np.save(stream, array, allow_pickle=False)
            positions = []
            for ti, si in zip(teacher_indices, student_indices):
                native_id = (ti + row_index + 1) % 11
                positions.append(dict(teacher_predictor_raw_index=ti, student_predictor_raw_index=si,
                    teacher_target_raw_index=ti+1, student_target_raw_index=si+1,
                    student_target_id=(si+row_index) % 9, teacher_native_argmax=native_id,
                    mapped_student_argmax=self.mapping[native_id], mapping_mode=self.modes[native_id],
                    owner=row_index+1, lookahead_bytes=0, accepted=True))
            self.records.append(dict(row_id='r'+str(row_index), semantic_root_id='root'+str(row_index),
                split='train', feature_file=path.name,
                feature_sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                teacher_tokens=len(array), student_tokens=6, positions=positions,
                record_sha256='AB'[row_index]*64, source_row_sha256='CD'[row_index]*64))
        self.identities = {name:letter*64 for name, letter in zip(
            ('teacher_sha256', 'tokenizer_sha256', 'mapping_sha256', 'data_sha256'), 'ABCD')}

    def reader(self, records=None, batch=3):
        return FeatureWindow(self.records if records is None else records, root=self.root,
            identities=self.identities, split='train', hidden_width=4, batch_positions=batch)

    def consumer(self, reader=None, **options):
        reader = self.reader() if reader is None else reader
        settings = dict(window_sha256=reader.window_sha256, global_positions=7,
                        student_width=8, teacher_width=9, student_vocab=9, teacher_vocab=11,
                        mapping=self.mapping, mapping_modes=self.modes, chunk_positions=2)
        settings.update(options)
        return core.NativeFeatureUpdate(reader, **settings)

    def tensors(self, dtype=torch.float64):
        generator = torch.Generator(device='cpu').manual_seed(1337)
        params = [torch.randn(shape, generator=generator, dtype=dtype, requires_grad=True)
                  for shape in ((3, 2), (9, 2), (11, 4), (4, 3), (3, 4))]
        frames = {}
        bases = {}
        for row in self.records:
            base = torch.randn((8, 3), generator=generator, dtype=dtype, requires_grad=True)
            targets = torch.full((8,), -100, dtype=torch.long)
            owners = torch.zeros(8, dtype=torch.long)
            for p in row['positions']:
                targets[p['student_predictor_raw_index']] = p['student_target_id']
                owners[p['student_predictor_raw_index']] = p['owner']
            frames[row['row_id']] = core.StudentFrame(row['row_id'], row['semantic_root_id'],
                row['record_sha256'], base*1.25, targets, owners)
            bases[row['row_id']] = base
        return params, frames, bases

    def arguments(self, params):
        return dict(zip(('up', 'embedding', 'teacher_head', 't2s', 's2t'), params))

    def run_update(self, consumer, params, frames, contexts=None, provider_calls=None):
        def provider(metadata):
            if provider_calls is not None:
                provider_calls.append(metadata['row_id'])
            return frames[metadata['row_id']]
        def backward(loss, context):
            if contexts is not None:
                contexts.append(copy.deepcopy(context))
            loss.backward(retain_graph=not context['row_complete'])
        while True:
            try:
                consumer.consume_next(provider, backward, **self.arguments(params))
            except StopIteration:
                break
        return consumer.close_accounting()

    def independent(self, params, frames, rate=1.):
        sums = {key:0 for key in ('student_kd_sum', 'teacher_kd_sum', 'projector_ce_sum', 'total_sum')}
        for row, array in zip(self.records, self.arrays):
            positions = row['positions']
            hs = frames[row['row_id']].hidden[[p['student_predictor_raw_index'] for p in positions]]
            ht = torch.tensor(array[[p['teacher_predictor_raw_index'] for p in positions]], dtype=torch.float64)
            labels = torch.tensor([p['mapped_student_argmax'] for p in positions])
            terms = dense.dskd_sums(hs, ht, params[0]@params[1].T, params[2].T,
                                    params[3], params[4], labels)
            for key in sums:
                sums[key] = sums[key] + terms[key]
        return rate*sums['total_sum']/7, sums

    def test_all_dualspace_values_and_gradients_match_independent_dense_two_row_reference(self):
        params, frames, bases = self.tensors()
        wanted_loss, wanted_sums = self.independent(params, frames, rate=.3)
        args = list(bases.values()) + params
        wanted_grad = torch.autograd.grad(wanted_loss, args, allow_unused=True)
        other, other_frames, other_bases = self.tensors()
        report = self.run_update(self.consumer(kd_rate=.3), other, other_frames)
        self.assertAlmostEqual(report['normalized_loss'], float(wanted_loss.detach()), delta=1e-10)
        for key in wanted_sums:
            self.assertAlmostEqual(report['sums'][key], float(wanted_sums[key].detach()), delta=1e-10)
        for expected, actual in zip(wanted_grad, list(other_bases.values())+other):
            if expected is None:
                self.assertIsNone(actual.grad)
            else:
                torch.testing.assert_close(actual.grad, expected, atol=1e-10, rtol=1e-10)
        self.assertGreater(float(other[3].grad.norm()), 0)
        self.assertIsNone(other[2].grad)
        self.assertIsNone(other[4].grad)

    def test_one_original_frame_is_reused_across_source_batches_and_released_at_row_end(self):
        params, frames, bases = self.tensors()
        contexts, calls = [], []
        consumer = self.consumer(self.reader(batch=2))
        report = self.run_update(consumer, params, frames, contexts, calls)
        self.assertEqual(calls, ['r0', 'r1'])
        self.assertEqual([(c['row_id'], c['row_complete']) for c in contexts],
                         [('r0', False), ('r0', True), ('r1', False), ('r1', False), ('r1', True)])
        self.assertEqual((report['positions'], report['global_positions'], report['source_batches']), (7, 7, 4))
        self.assertEqual(report['maximum_chunk_positions'], 2)
        self.assertEqual(report['frame_provider_calls'], 2)
        self.assertIsNone(consumer._active_frame)
        self.assertFalse(report['full_training_checkpoint_or_resume'])
        self.assertEqual(report['optimizer_steps'], 0)

    def test_same_raw_index_in_two_rows_stays_in_distinct_original_teacher_frames(self):
        params, frames, bases = self.tensors()
        contexts, seen = [], []
        original = core.bridge.teacher_logits
        def observe(hidden, head, **kwargs):
            seen.append((tuple(hidden.shape), kwargs['width'], tuple(kwargs['indices'].tolist())))
            return original(hidden, head, **kwargs)
        with patch.object(core.bridge, 'teacher_logits', side_effect=observe):
            report = self.run_update(self.consumer(self.reader(batch=4)), params, frames, contexts)
        self.assertEqual(len(seen), 2*len(contexts))
        for index, context in enumerate(contexts):
            for observed in seen[index*2:index*2+2]:
                self.assertEqual(observed[1:], (9, context['teacher_indices']))
        self.assertEqual(report['full_teacher_frame_values'], 99)
        self.assertEqual([c['row_id'] for c in contexts], ['r0', 'r0', 'r1', 'r1', 'r1'])

    def test_all_chunk_and_batch_partitions_preserve_global_loss_and_parameter_gradients(self):
        reference_params, reference_frames, reference_bases = self.tensors()
        wanted, _ = self.independent(reference_params, reference_frames)
        expected = torch.autograd.grad(wanted, [reference_params[0], reference_params[1], reference_params[3]])
        for batch, chunk in ((1, 1), (2, 8), (4, 3), (7, 8)):
            with self.subTest(batch=batch, chunk=chunk):
                params, frames, bases = self.tensors()
                report = self.run_update(self.consumer(self.reader(batch=batch), chunk_positions=chunk), params, frames)
                self.assertAlmostEqual(report['normalized_loss'], float(wanted.detach()), delta=1e-10)
                for value, gradient in zip((params[0], params[1], params[3]), expected):
                    torch.testing.assert_close(value.grad, gradient, atol=1e-10, rtol=1e-10)

    def test_original_FP32_features_are_not_downcast_to_BF16_student_hidden(self):
        params, frames, bases = self.tensors(dtype=torch.float32)
        frames = {name:replace(frame, hidden=frame.hidden.to(torch.bfloat16)) for name, frame in frames.items()}
        original = core.bridge.native_sums
        observed = []
        def check(hs, ht, *args, **kwargs):
            observed.append((hs.dtype, ht.dtype))
            return original(hs, ht, *args, **kwargs)
        with patch.object(core.bridge, 'native_sums', side_effect=check):
            self.run_update(self.consumer(), params, frames)
        self.assertTrue(observed)
        self.assertTrue(all(value == (torch.bfloat16, torch.float32) for value in observed))

    def test_invalid_complete_denominator_identity_frame_and_output_quota_precede_feature_IO(self):
        for options in (dict(global_positions=6), dict(global_positions=True), dict(window_sha256='F'*64),
                        dict(teacher_width=6), dict(student_width=4), dict(max_teacher_frame_values=98),
                        dict(kd_rate=float('nan')), dict(kd_rate=-1), dict(chunk_positions=True)):
            reader = self.reader()
            with patch.object(reader, 'prepare', side_effect=AssertionError('preflight cannot read features')):
                with self.assertRaises(ValueError):
                    self.consumer(reader, **options)
            self.assertEqual(reader.stats['files_opened'], 0)

    def test_causal_index_mapping_acceptance_and_duplicate_positions_fail_at_window_preflight(self):
        variants = []
        for key, value in (('accepted', False), ('lookahead_bytes', 1), ('lookahead_bytes', False),
                           ('owner', True), ('mapping_mode', 2), ('mapped_student_argmax', 8),
                           ('student_target_raw_index', 1), ('teacher_target_raw_index', 0)):
            rows = copy.deepcopy(self.records)
            rows[0]['positions'][0][key] = value
            variants.append(rows)
        rows = copy.deepcopy(self.records)
        rows[0]['positions'][1] = copy.deepcopy(rows[0]['positions'][0])
        variants.append(rows)
        for rows in variants:
            reader = self.reader(records=rows)
            with patch.object(reader, 'prepare', side_effect=AssertionError('preflight cannot read features')):
                with self.assertRaises(ValueError):
                    self.consumer(reader)

    def test_wrong_student_row_identity_and_original_target_or_owner_poison_the_update(self):
        for kind in ('row', 'root', 'record', 'target', 'owner'):
            params, frames, bases = self.tensors()
            frame = frames['r0']
            if kind == 'row':frame = replace(frame, row_id='r1')
            if kind == 'root':frame = replace(frame, semantic_root_id='wrong')
            if kind == 'record':frame = replace(frame, record_sha256='F'*64)
            if kind == 'target':frame.targets[3] = 8
            if kind == 'owner':frame.owners[3] = 8
            frames['r0'] = frame
            consumer = self.consumer()
            with self.assertRaises(ValueError):
                consumer.consume_next(lambda row:frames[row['row_id']], lambda *a:self.fail('backward forbidden'),
                                      **self.arguments(params))
            with self.assertRaises(RuntimeError):consumer.close_accounting()
            with self.assertRaises(RuntimeError):consumer.reader.state_dict()

    def test_callback_failure_keeps_source_uncommitted_and_forbids_partial_update_reuse(self):
        params, frames, bases = self.tensors()
        consumer = self.consumer()
        calls = []
        def backward(loss, context):
            calls.append(context)
            if len(calls) == 2:raise RuntimeError('injected caller backward failure')
            loss.backward(retain_graph=True)
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            consumer.consume_next(lambda row:frames[row['row_id']], backward, **self.arguments(params))
        self.assertEqual(consumer.reader._offset, 0)
        self.assertIsNotNone(params[3].grad)
        with self.assertRaises(RuntimeError):consumer.close_accounting()
        with self.assertRaises(RuntimeError):consumer.reader.state_dict()
        with self.assertRaises(RuntimeError):
            consumer.consume_next(lambda row:frames[row['row_id']], backward, **self.arguments(params))

    def test_wrong_full_vocabulary_or_nonfinite_parameter_fails_before_feature_IO(self):
        for kind in ('student_vocab', 'teacher_vocab', 'nonfinite'):
            params, frames, bases = self.tensors()
            if kind == 'student_vocab':params[1] = params[1][:-1]
            if kind == 'teacher_vocab':params[2] = params[2][:-1]
            if kind == 'nonfinite':
                with torch.no_grad():params[3][0, 0] = float('nan')
            consumer = self.consumer()
            with self.assertRaises(ValueError):
                consumer.consume_next(lambda row:frames[row['row_id']], lambda *a:self.fail('backward forbidden'),
                                      **self.arguments(params))
            self.assertEqual(consumer.reader.stats['files_opened'], 0)

    def test_trainable_nonleaf_shared_head_or_projector_is_rejected_before_feature_IO(self):
        for index in (0, 1, 3):
            params, frames, bases = self.tensors()
            params[index] = params[index]*1.0
            consumer = self.consumer()
            with self.assertRaisesRegex(ValueError, 'leaf master matrices'):
                consumer.consume_next(lambda row:self.fail('provider forbidden'),
                                      lambda *a:self.fail('backward forbidden'), **self.arguments(params))
            self.assertEqual(consumer.reader.stats['files_opened'], 0)

    def test_parameters_cannot_step_or_be_replaced_between_feature_batches(self):
        for kind in ('version', 'object'):
            params, frames, bases = self.tensors()
            consumer = self.consumer(self.reader(batch=2))
            backward = lambda loss, ctx:loss.backward(retain_graph=not ctx['row_complete'])
            consumer.consume_next(lambda row:frames[row['row_id']], backward, **self.arguments(params))
            if kind == 'version':
                with torch.no_grad():params[3].add_(.01)
            else:params[3] = params[3].detach().clone().requires_grad_()
            with self.assertRaisesRegex(ValueError, 'parameter'):
                consumer.consume_next(lambda row:frames[row['row_id']], backward, **self.arguments(params))
            with self.assertRaises(RuntimeError):consumer.close_accounting()

    def test_backward_callback_cannot_change_parameters_before_accounting_closure(self):
        params, frames, bases = self.tensors()
        consumer = self.consumer()
        def bad(loss, context):
            loss.backward(retain_graph=True)
            with torch.no_grad():params[3].add_(.01)
        with self.assertRaisesRegex(ValueError, 'callback changed parameters'):
            consumer.consume_next(lambda row:frames[row['row_id']], bad, **self.arguments(params))
        with self.assertRaises(RuntimeError):consumer.close_accounting()

    def test_changed_student_frame_is_rejected_when_a_row_crosses_batch_boundaries(self):
        params, frames, bases = self.tensors()
        consumer = self.consumer(self.reader(batch=2))
        backward = lambda loss, ctx:loss.backward(retain_graph=not ctx['row_complete'])
        consumer.consume_next(lambda row:frames[row['row_id']], backward, **self.arguments(params))
        frames['r0'].owners[3] = 9
        with self.assertRaisesRegex(ValueError, 'row frame changed'):
            consumer.consume_next(lambda row:frames[row['row_id']], backward, **self.arguments(params))

    def test_source_cursor_alone_cannot_resume_partial_training_gradients(self):
        reader = self.reader()
        reader.prepare();reader.finish()
        saved = reader.state_dict()
        other = self.reader()
        other.load_state_dict(saved)
        with self.assertRaisesRegex(ValueError, 'cursor alone cannot restore gradients'):
            self.consumer(other)

    def test_modified_prepared_metadata_is_rejected_before_any_backward(self):
        params, frames, bases = self.tensors()
        reader = self.reader()
        consumer = self.consumer(reader)
        original = reader.prepare
        def bad():
            value = original()
            positions = copy.deepcopy(value.positions)
            positions[0]['student_target_id'] = 8
            return replace(value, positions=positions)
        with patch.object(reader, 'prepare', side_effect=bad):
            with self.assertRaisesRegex(ValueError, 'batch differs'):
                consumer.consume_next(lambda row:self.fail('provider forbidden'),
                                      lambda *a:self.fail('backward forbidden'), **self.arguments(params))

    def test_incomplete_accounting_cannot_be_closed_or_marked_as_full_resume(self):
        consumer = self.consumer()
        with self.assertRaises(RuntimeError):consumer.close_accounting()
        params, frames, bases = self.tensors()
        report = self.run_update(consumer, params, frames)
        self.assertFalse(report['full_training_checkpoint_or_resume'])
        self.assertIn('NOT_MODEL_OPTIMIZER_OR_RNG', report['source_state']['resume_scope'])
        with self.assertRaises(RuntimeError):
            consumer.consume_next(lambda *a:None, lambda *a:None, **self.arguments(params))


if __name__ == '__main__':
    unittest.main()
