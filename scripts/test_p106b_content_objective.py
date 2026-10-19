"""Synthetic CPU loss/gradient contracts; no model assets, tokenizer or GPU."""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F

from scripts import p106b_content_objective as objective
from tinylm.train import mtp_sft as core


def record(targets, owners=None):
    owners = [0 if value == -100 else 1 for value in targets] if owners is None else owners
    return core.Record([1] * len(targets), list(targets), list(owners))


def unequal_records(count=7):
    result = []
    for i in range(count):
        length = 2 + (i * 7) % 13
        targets = [-100] + [5 + (i + j) % 8 for j in range(length - 2)] + [4]
        owners = [0] + [1 + int(j >= length // 2) for j in range(length - 1)]
        if i % 9 == 0:
            targets, owners = [-100] * length, [2] * length
        elif i % 7 == 0:
            targets = [-100] * (length - 1) + [4]
        elif length > 4:
            targets[2] = -100  # C2 old wrong answer keeps a positive owner.
        result.append(record(targets, owners))
    return result


class MockHead(torch.nn.Module):
    def __init__(self):
        super().__init__()
        rng = torch.Generator().manual_seed(23)
        self.projection = torch.nn.Parameter(torch.randn(4, 6, generator=rng) / 3)
        self.vocabulary = torch.nn.Parameter(torch.randn(13, 4, generator=rng) / 3)
        self.head_positions = []

    def _head_logits(self, hidden):
        self.head_positions.append(hidden.shape[0] * hidden.shape[1])
        return F.linear(F.linear(hidden.float(), self.projection), self.vocabulary)

    def mtp_aux_logits(self, *_):
        raise AssertionError('content objective must never call an auxiliary head')


def hidden_for(rows, width):
    rng = torch.Generator().manual_seed(47)
    return torch.randn(len(rows), width, 6, generator=rng).requires_grad_()


def dense_reference(model, hidden, y, owners, policy, eot_id=4):
    """Independent dense L0/P formulas, including conversation means for P."""
    logits = model._head_logits(hidden)
    ce = F.cross_entropy(logits.reshape(-1, 13).float(), y.reshape(-1),
                         ignore_index=-100, reduction='none').reshape_as(y)
    valid = y.ne(-100) & owners.gt(0)
    content = valid & y.ne(eot_id)
    eot = valid & y.eq(eot_id)
    raw, content_sum, eot_sum = ce[valid].sum(), ce[content].sum(), ce[eot].sum()
    total = int(valid.sum())
    if policy == 'token':
        weighted = raw / total
    else:
        means = [ce[i][content[i]].mean() for i in range(y.shape[0])
                 if bool(content[i].any())]
        content_part = (int(content.sum()) / total * torch.stack(means).mean()
                        if means else hidden.sum() * 0.0)
        weighted = content_part + eot_sum / total
    return dict(weighted=weighted, raw=raw, content=content_sum, eot=eot_sum)


class WeightPlanTests(unittest.TestCase):
    def test_token_counts_weights_and_masked_owner(self):
        rows = [record([-100, 5, 4, -100], [0, 1, 1, 2]), record([6, 7, 4])]
        plan = objective.make_weights(rows)
        self.assertEqual((plan.targets, plan.content_targets, plan.eot_targets,
                          plan.content_rows, plan.row_content_counts), (5, 3, 2, 2, [1, 2]))
        self.assertEqual(plan.weights, [[0.0, .2, .2, 0.0], [.2, .2, .2]])
        self.assertEqual(plan.policy, 'token')

    def test_paper_example_preserves_content_and_each_eot_mass(self):
        rows = [record([5, 4]), record([6, 4]), record([7] * 10 + [4])]
        baseline = objective.make_weights(rows)
        plan = objective.make_weights(rows, policy='content')
        self.assertEqual(plan.row_content_counts, [1, 1, 10])
        self.assertAlmostEqual(sum(plan.weights[0][:-1]) + sum(plan.weights[1][:-1]), 8 / 15)
        self.assertAlmostEqual(sum(plan.weights[2][:-1]), 4 / 15)
        for a, b in zip(baseline.weights, plan.weights):
            self.assertEqual(a[-1], b[-1])
        self.assertAlmostEqual(sum(map(sum, plan.weights)), 1.)

    def test_multiple_turns_are_one_conversation(self):
        rows = [record([5, 4, -100, 6, 7, 4], [1, 1, 0, 2, 2, 2]), record([8, 4])]
        plan = objective.make_weights(rows, policy='content')
        self.assertEqual((plan.content_rows, plan.row_content_counts), (2, [3, 1]))
        self.assertAlmostEqual(plan.weights[0][0], 4 / (7 * 2 * 3))
        self.assertEqual(plan.weights[0][0], plan.weights[0][3])
        self.assertEqual(plan.weights[0][1], 1 / 7)

    def test_eot_only_row_stays_in_total_not_content_rows(self):
        plan = objective.make_weights([record([4, 4], [1, 2]), record([5, 6, 4])], policy='content')
        self.assertEqual((plan.targets, plan.content_rows, plan.row_content_counts), (5, 1, [0, 2]))
        self.assertEqual(plan.weights[0], [.2, .2])
        self.assertEqual(plan.weights[1], [.2, .2, .2])

    def test_eot_only_update_is_allowed(self):
        rows = [record([-100, 4], [3, 1]), record([4, 4], [1, 2])]
        for policy in ('token', 'content'):
            plan = objective.make_weights(rows, policy=policy)
            self.assertEqual((plan.content_targets, plan.content_rows, plan.targets), (0, 0, 3))
            self.assertEqual(plan.weights, [[0., 1 / 3], [1 / 3, 1 / 3]])

    def test_all_ignored_row_allowed_inside_supervised_update(self):
        plan = objective.make_weights([record([-100, -100], [1, 2]), record([5, 4])], policy='content')
        self.assertEqual(plan.weights[0], [0., 0.])
        self.assertEqual(plan.row_content_counts, [0, 1])
        self.assertEqual(plan.targets, 2)

    def test_no_supervision_rejected(self):
        for rows in ([], [record([])], [record([-100], [3])]):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, 'no supervised'):
                objective.make_weights(rows)

    def test_invalid_policy_and_eot_rejected(self):
        for kwargs in ({'policy': 'row'}, {'eot_id': -1}, {'eot_id': True}, {'eot_id': 4.}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                objective.make_weights([record([5, 4])], **kwargs)

    def test_invalid_record_lengths_labels_and_owners_rejected(self):
        rows = [core.Record([1], [5, 4], [1, 1]), record([5], [0]),
                record([-100], [-1]), record([-2], [1]), record([5.], [1]),
                record([True], [1]), record([5], [1.]), core.Record([-1], [5], [1]), object()]
        for row in rows:
            with self.subTest(row=row), self.assertRaises(ValueError):
                objective.make_weights([row])

    def test_custom_eot(self):
        plan = objective.make_weights([record([4, 5, 2])], eot_id=2, policy='content')
        self.assertEqual((plan.content_targets, plan.eot_targets), (2, 1))

    def test_tensor_selects_order_and_zero_padding(self):
        plan = objective.make_weights([record([5, 4]), record([-100, 6, 7, 4])], policy='content')
        result = objective.make_tensor(plan, [1, 0], width=6)
        self.assertEqual(result.shape, (2, 6))
        self.assertEqual(result.dtype, torch.float32)
        self.assertFalse(result.requires_grad)
        self.assertTrue(torch.equal(result[0, 4:], torch.zeros(2)))
        self.assertTrue(torch.equal(result[1, 2:], torch.zeros(4)))
        torch.testing.assert_close(result[0, :4], torch.tensor(plan.weights[1]))

    def test_invalid_tensor_request_rejected(self):
        plan = objective.make_weights([record([5, 4])])
        requests = [dict(indices=[]), dict(indices=[-1]), dict(indices=[1]),
                    dict(indices=[True]), dict(indices=[0.]), dict(indices=[0], width=1),
                    dict(indices=[0], width=0), dict(indices=[0], width=True),
                    dict(indices=[0], dtype=torch.long), dict(indices=[0], dtype=torch.complex64)]
        for kwargs in requests:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                objective.make_tensor(plan, **kwargs)
        with self.assertRaises(ValueError):
            objective.make_tensor(object(), [0])

    def test_corrupted_selected_plan_weights_rejected(self):
        for value in (float('nan'), float('inf'), -1., True):
            plan = objective.make_weights([record([5, 4])])
            plan.weights[0][0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                objective.make_tensor(plan, [0], width=2)


class ComponentTests(unittest.TestCase):
    def compare(self, rows, policy, checkpoint_heads, micros=1, chunk=5):
        width = max(len(row.x) for row in rows) + 2
        _, y, owners = core.pad_records(rows, 0, fixed_width=width)
        plan = objective.make_weights(rows, policy=policy)
        expected_model, actual_model = MockHead(), MockHead()
        expected_hidden = hidden_for(rows, width)
        actual_hidden = expected_hidden.detach().clone().requires_grad_()
        expected = dense_reference(expected_model, expected_hidden, y, owners, policy)
        expected['weighted'].backward()
        totals = {key: 0. for key in expected}
        counts = dict(targets=0, content=0, eot=0)
        micro_size = math.ceil(len(rows) / micros)
        for start in range(0, len(rows), micro_size):
            indices = list(range(start, min(start + micro_size, len(rows))))
            sums, observed = objective.components(actual_model, actual_hidden[indices], y[indices],
                owners[indices], objective.make_tensor(plan, indices, width=width),
                chunk=chunk, checkpoint_heads=checkpoint_heads)
            for key in totals:
                totals[key] += float(sums[key].detach())
            for key in counts:
                counts[key] += observed[key]
            sums['weighted'].backward()
        for key, value in expected.items():
            self.assertAlmostEqual(totals[key], float(value.detach()), delta=3e-4, msg=key)
        self.assertEqual(counts, dict(targets=plan.targets, content=plan.content_targets, eot=plan.eot_targets))
        torch.testing.assert_close(actual_hidden.grad, expected_hidden.grad, atol=3e-7, rtol=2e-5)
        for (name, actual), (_, expected_param) in zip(actual_model.named_parameters(), expected_model.named_parameters()):
            torch.testing.assert_close(actual.grad, expected_param.grad, atol=3e-7, rtol=2e-5, msg=name)
        self.assertLessEqual(max(actual_model.head_positions), chunk)

    def test_dense_loss_and_gradients_for_both_policies_and_checkpoint_modes(self):
        for policy in ('token', 'content'):
            for checkpoint_heads in (False, True):
                with self.subTest(policy=policy, checkpoint=checkpoint_heads):
                    self.compare(unequal_records(), policy, checkpoint_heads)

    def test_whole128_conversations_in16_micros_matches_dense(self):
        for policy in ('token', 'content'):
            for checkpoint_heads in (False, True):
                with self.subTest(policy=policy, checkpoint=checkpoint_heads):
                    self.compare(unequal_records(128), policy, checkpoint_heads, micros=16, chunk=11)

    def test_token_policy_matches_existing_core_loss_and_gradients(self):
        rows = unequal_records(13)
        _, y, owners = core.pad_records(rows, 0, fixed_width=16)
        plan = objective.make_weights(rows)
        for checkpoint_heads in (False, True):
            baseline, weighted = MockHead(), MockHead()
            old_hidden = hidden_for(rows, 16)
            new_hidden = old_hidden.detach().clone().requires_grad_()
            old_sums, old_counts = core.components(baseline, old_hidden, y, owners,
                horizons=(), chunk=39, checkpoint_heads=checkpoint_heads)
            old_loss = core.normalized_loss(old_sums, old_counts, {})
            new_sums, new_counts = objective.components(weighted, new_hidden, y, owners,
                objective.make_tensor(plan, range(len(rows)), width=16), chunk=39,
                checkpoint_heads=checkpoint_heads)
            torch.testing.assert_close(new_sums['weighted'], old_loss, atol=5e-7, rtol=1e-6)
            torch.testing.assert_close(new_sums['raw'], old_sums[1], atol=3e-5, rtol=1e-6)
            self.assertEqual(new_counts['targets'], old_counts[1])
            old_loss.backward(); new_sums['weighted'].backward()
            torch.testing.assert_close(new_hidden.grad, old_hidden.grad, atol=3e-7, rtol=2e-5)
            for a, b in zip(weighted.parameters(), baseline.parameters()):
                torch.testing.assert_close(a.grad, b.grad, atol=3e-7, rtol=2e-5)

    def test_eot_only_dense_and_gradient_parity(self):
        rows = [record([4]), record([-100, 4, 4], [1, 1, 2])]
        for policy in ('token', 'content'):
            self.compare(rows, policy, True, micros=2, chunk=1)

    def test_ignored_micro_returns_differentiable_fp32_zero(self):
        rows = [record([-100, -100], [1, 2]), record([5, 4])]
        plan = objective.make_weights(rows, policy='content')
        _, y, owners = core.pad_records(rows[:1], 0, fixed_width=3)
        hidden = torch.ones(1, 3, 6, dtype=torch.bfloat16, requires_grad=True)
        model = MockHead()
        sums, counts = objective.components(model, hidden, y, owners,
            objective.make_tensor(plan, [0], width=3))
        self.assertEqual(counts, dict(targets=0, content=0, eot=0))
        self.assertEqual(model.head_positions, [])
        for value in sums.values():
            self.assertEqual(value.dtype, torch.float32)
            self.assertEqual(float(value.detach()), 0.)
        sums['weighted'].backward()
        self.assertTrue(torch.equal(hidden.grad, torch.zeros_like(hidden)))

    def test_head_gradients_work_with_frozen_hidden(self):
        rows = [record([5, 4])]
        _, y, owners = core.pad_records(rows, 0)
        hidden = hidden_for(rows, 2).detach()
        model = MockHead()
        sums, _ = objective.components(model, hidden, y, owners,
            objective.make_tensor(objective.make_weights(rows), [0], width=2))
        sums['weighted'].backward()
        self.assertTrue(all(parameter.grad is not None for parameter in model.parameters()))

    def test_no_grad_mode_returns_fp32_reports(self):
        rows = [record([5, 4])]
        _, y, owners = core.pad_records(rows, 0)
        with torch.no_grad():
            sums, _ = objective.components(MockHead(), hidden_for(rows, 2), y, owners,
                objective.make_tensor(objective.make_weights(rows), [0], width=2))
        self.assertTrue(all(value.dtype == torch.float32 and not value.requires_grad for value in sums.values()))

    def test_ignored_positions_have_zero_hidden_gradient(self):
        rows = [record([-100, 5, -100, 4], [0, 1, 2, 2])]
        _, y, owners = core.pad_records(rows, 0, fixed_width=6)
        hidden = hidden_for(rows, 6)
        sums, _ = objective.components(MockHead(), hidden, y, owners,
            objective.make_tensor(objective.make_weights(rows), [0], width=6), chunk=1)
        sums['weighted'].backward()
        self.assertTrue(torch.equal(hidden.grad[0, [0, 2, 4, 5]], torch.zeros(4, 6)))
        self.assertGreater(float(hidden.grad[0, [1, 3]].abs().sum()), 0.)

    def test_raw_sums_do_not_change_with_policy(self):
        rows = unequal_records()
        _, y, owners = core.pad_records(rows, 0, fixed_width=16)
        result = []
        for policy in ('token', 'content'):
            sums, _ = objective.components(MockHead(), hidden_for(rows, 16), y, owners,
                objective.make_tensor(objective.make_weights(rows, policy=policy), range(len(rows)), width=16))
            result.append(sums)
        for key in ('raw', 'content', 'eot'):
            torch.testing.assert_close(result[0][key], result[1][key], atol=0, rtol=0)
        torch.testing.assert_close(result[0]['raw'], result[0]['content'] + result[0]['eot'])

    def test_deferred_backward_has_no_last_chunk_target_or_weight_capture(self):
        rows = unequal_records(17)
        _, y, owners = core.pad_records(rows, 0, fixed_width=17)
        model, reference = MockHead(), MockHead()
        hidden = hidden_for(rows, 17)
        dense_hidden = hidden.detach().clone().requires_grad_()
        plan = objective.make_weights(rows, policy='content')
        parts = []
        for i in range(len(rows)):
            sums, _ = objective.components(model, hidden[i:i + 1], y[i:i + 1], owners[i:i + 1],
                objective.make_tensor(plan, [i], width=17), chunk=2, checkpoint_heads=True)
            parts.append(sums['weighted'])
        sum(parts).backward()
        dense_reference(reference, dense_hidden, y, owners, 'content')['weighted'].backward()
        torch.testing.assert_close(hidden.grad, dense_hidden.grad, atol=3e-7, rtol=2e-5)
        for a, b in zip(model.parameters(), reference.parameters()):
            torch.testing.assert_close(a.grad, b.grad, atol=3e-7, rtol=2e-5)

    def test_native_term_is_separate_and_keeps_8192_denominator(self):
        rows = [record([5, 4]), record([6, 7, 8, 4])]
        _, y, owners = core.pad_records(rows, 0, fixed_width=5)
        native_gradients = []
        for policy in ('token', 'content'):
            native = torch.tensor(3., requires_grad=True)
            sums, _ = objective.components(MockHead(), hidden_for(rows, 5), y, owners,
                objective.make_tensor(objective.make_weights(rows, policy=policy), [0, 1], width=5))
            (sums['weighted'] + native.square() / 8192).backward()
            native_gradients.append(float(native.grad))
        self.assertEqual(native_gradients, [6 / 8192, 6 / 8192])

    def test_same_eot_weights_do_not_promise_same_vocabulary_row_gradient(self):
        rows = [record([5, 4]), record([6] * 7 + [4])]
        _, y, owners = core.pad_records(rows, 0)
        gradients = []
        for policy in ('token', 'content'):
            model = MockHead()
            sums, _ = objective.components(model, hidden_for(rows, y.shape[1]), y, owners,
                objective.make_tensor(objective.make_weights(rows, policy=policy), [0, 1], width=y.shape[1]))
            sums['weighted'].backward()
            gradients.append(model.vocabulary.grad[4].clone())
        self.assertFalse(torch.allclose(gradients[0], gradients[1], atol=1e-7, rtol=1e-7))

    def test_components_rejects_shape_dtype_and_chunk_errors(self):
        hidden = torch.ones(1, 2, 6)
        y = torch.tensor([[5, 4]])
        owners = torch.ones_like(y)
        weights = torch.full((1, 2), .5)
        cases = [(hidden[0], y, owners, weights, {}),
                 (hidden, y, owners[:, :1], weights, {}),
                 (hidden, y, owners, weights[:, :1], {}),
                 (hidden, y.float(), owners, weights, {}),
                 (hidden, y, owners.float(), weights, {}),
                 (hidden.long(), y, owners, weights, {}),
                 (hidden, y, owners, weights.long(), {}),
                 (hidden, y, owners, weights, dict(chunk=0)),
                 (hidden, y, owners, weights, dict(chunk=True)),
                 (hidden, y, owners, weights, dict(eot_id=-1))]
        for args in cases:
            with self.subTest(args=args[4]), self.assertRaises(ValueError):
                objective.components(MockHead(), *args[:4], **args[4])

    def test_components_rejects_supervision_and_weight_errors(self):
        hidden = torch.ones(1, 2, 6)
        y = torch.tensor([[5, 4]])
        owners = torch.ones_like(y)
        weights = torch.full((1, 2), .5)
        cases = [(y, torch.zeros_like(owners), weights),
                 (y, -owners, weights), (torch.tensor([[-2, 4]]), owners, weights),
                 (y, owners, weights.clone().requires_grad_()),
                 (y, owners, torch.tensor([[float('nan'), .5]])),
                 (y, owners, torch.tensor([[-.5, .5]])),
                 (y, owners, torch.tensor([[0., .5]])),
                 (torch.tensor([[-100, 4]]), owners, weights)]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                objective.components(MockHead(), hidden, *args)

    def test_custom_eot_components_and_fp32_bfloat16_hidden(self):
        rows = [record([4, 5, 2])]
        _, y, owners = core.pad_records(rows, 0)
        hidden = hidden_for(rows, 3).detach().bfloat16().requires_grad_()
        plan = objective.make_weights(rows, eot_id=2, policy='content')
        sums, counts = objective.components(MockHead(), hidden, y, owners,
            objective.make_tensor(plan, [0], width=3), eot_id=2, chunk=1)
        self.assertEqual(counts, dict(targets=3, content=2, eot=1))
        self.assertTrue(all(value.dtype == torch.float32 for value in sums.values()))
        sums['weighted'].backward()
        self.assertIsNotNone(hidden.grad)

    def test_computation_never_loads_assets_or_initializes_cuda(self):
        rows = [record([5, 4])]
        _, y, owners = core.pad_records(rows, 0)
        with patch('torch.load', side_effect=AssertionError('asset loading forbidden')), \
             patch('torch.cuda.init', side_effect=AssertionError('CUDA forbidden')):
            sums, _ = objective.components(MockHead(), hidden_for(rows, 2), y, owners,
                objective.make_tensor(objective.make_weights(rows), [0], width=2), chunk=1)
            sums['weighted'].backward()


if __name__ == '__main__':
    unittest.main()
