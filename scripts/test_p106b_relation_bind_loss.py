"""Small synthetic CPU tensors only; no real model, weights or source assets."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F
from tinylm.train.mtp_sft import Record
from scripts import p106b_relation_bind_loss as m


def record(prefix=2, content=(2, 3), tail=2, eot=4):
    ids = [1] * prefix + list(content) + [eot] + [1] * tail
    labels = [-100] * prefix + list(content) + [eot] + [-100] * tail
    y = labels[1:]
    return Record(ids[:-1], y, [int(v != -100) for v in y])


class IdentityHead:
    def _head_logits(self, value): return value


class LinearHead:
    def __init__(self): self.weight = torch.randn(3, 7, requires_grad=True)
    def _head_logits(self, value): return value @ self.weight


class SequenceTests(unittest.TestCase):
    def setUp(self): torch.manual_seed(20261017)

    def test_shifted_content_eot_and_lengths_match_manual_predictions(self):
        records = [record(2, (2, 3)), record(5, (3,))]
        hidden = torch.randn(2, 11, 7, requires_grad=True)
        content, eot, counts = m.sequence_terms(IdentityHead(), hidden, records, 4, False)
        self.assertEqual(counts, [2, 1])
        for i, rec in enumerate(records):
            positions = [j for j, target in enumerate(rec.y) if target != -100]
            targets = torch.tensor([rec.y[j] for j in positions])
            expected = hidden[i, positions].log_softmax(-1)[torch.arange(len(positions)), targets]
            self.assertTrue(torch.allclose(content[i], expected[:-1].sum()))
            self.assertTrue(torch.allclose(eot[i], expected[-1]))
        self.assertTrue(torch.allclose(m.content_means(content, counts), content / torch.tensor([2, 1])))

    def test_only_supervised_predictors_receive_direct_hidden_gradient(self):
        rec = record(4, (2, 3), tail=3)
        hidden = torch.randn(1, 16, 7, requires_grad=True)
        content, eot, _ = m.sequence_terms(IdentityHead(), hidden, [rec], 4, False)
        (-content.sum() - eot.sum()).backward()
        supervised = {j for j, target in enumerate(rec.y) if target != -100}
        for j in range(hidden.shape[1]):
            self.assertEqual(bool(hidden.grad[0, j].ne(0).any()), j in supervised)

    def test_eot_has_ce_gradient_but_no_content_or_contrast_gradient(self):
        records = [record(content=(2,)), record(content=(3,))]
        hidden = torch.randn(2, 9, 7, requires_grad=True)
        content, eot, counts = m.sequence_terms(IdentityHead(), hidden, records, 4, False)
        means = m.content_means(content, counts)
        loss = m.row_contrast_sum(m.score_matrix(means, means.flip(0)))
        loss.backward()
        for i, rec in enumerate(records):
            end = [j for j, target in enumerate(rec.y) if target != -100][-1]
            self.assertEqual(float(hidden.grad[i, end].abs().sum()), 0.)
        hidden.grad = None
        content, eot, _ = m.sequence_terms(IdentityHead(), hidden, records, 4, False)
        (-content.sum() - eot.sum()).backward()
        for i, rec in enumerate(records):
            end = [j for j, target in enumerate(rec.y) if target != -100][-1]
            self.assertGreater(float(hidden.grad[i, end].abs().sum()), 0.)

    def test_padding_and_prompt_logits_do_not_change_selected_scores(self):
        rec = record(3)
        hidden = torch.randn(1, 14, 7)
        altered = hidden.clone()
        for j in range(14):
            if j >= len(rec.y) or rec.y[j] == -100:
                altered[0, j] = torch.arange(7) * 1000.
        left = m.sequence_terms(IdentityHead(), hidden, [rec], 4, False)
        right = m.sequence_terms(IdentityHead(), altered, [rec], 4, False)
        self.assertTrue(torch.equal(left[0], right[0])); self.assertTrue(torch.equal(left[1], right[1]))

    def test_checkpoint_matches_values_and_gradients_for_different_lengths(self):
        head = LinearHead(); hidden = torch.randn(4, 13, 3, requires_grad=True)
        records = [record(1, (2,)), record(4, (3, 2, 3)), record(3, (3, 2)), record(6, (2,))]
        first = m.sequence_terms(head, hidden, records, 4, False)
        (-first[0].sum() - first[1].sum()).backward()
        gh, gw = hidden.grad.clone(), head.weight.grad.clone()
        hidden.grad = None; head.weight.grad = None
        second = m.sequence_terms(head, hidden, records, 4, True)
        (-second[0].sum() - second[1].sum()).backward()
        self.assertEqual(first[2], second[2])
        self.assertTrue(torch.equal(first[0], second[0])); self.assertTrue(torch.equal(first[1], second[1]))
        self.assertTrue(torch.allclose(hidden.grad, gh, atol=1e-6))
        self.assertTrue(torch.allclose(head.weight.grad, gw, atol=1e-6))

    def test_invalid_shift_hole_multiturn_and_missing_eot_are_refused(self):
        variants = []
        for kind in ('shift', 'hole', 'multiturn', 'eot', 'early_eot', 'prompt_segment'):
            rec = record(3, (2, 3, 2)); positions = [j for j, target in enumerate(rec.y) if target != -100]
            if kind == 'shift': rec.x[positions[0] + 1] = 6
            elif kind == 'hole': rec.y[positions[1]] = -100; rec.segments[positions[1]] = 0
            elif kind == 'multiturn': rec.segments[positions[-1]] = 2
            elif kind == 'eot': rec.y[positions[-1]] = 3
            elif kind == 'early_eot': rec.y[positions[0]] = 4
            else: rec.segments[0] = 1
            variants.append(rec)
        for rec in variants:
            with self.assertRaises(ValueError): m.sequence_terms(IdentityHead(), torch.zeros(1, 14, 7), [rec], 4)

    def test_bad_hidden_head_and_token_counts_are_refused(self):
        for hidden in (torch.zeros(2, 9, 7), torch.zeros(1, 1, 7), torch.zeros(1, 9, dtype=torch.long)):
            with self.assertRaises(ValueError): m.sequence_terms(IdentityHead(), hidden, [record()], 4)
        with self.assertRaises(ValueError):
            m.sequence_terms(IdentityHead(), torch.full((1, 9, 7), float('nan')), [record()], 4)
        with self.assertRaises(ValueError): m.sequence_terms(IdentityHead(), torch.zeros(1, 9, 3), [record()], 4)
        for counts in ([0], [True], [1, 2]):
            with self.assertRaises(ValueError): m.content_means(torch.tensor([-1.]), counts)


class RankingTests(unittest.TestCase):
    def test_interleaved_matrix_preserves_both_question_answer_maps(self):
        positive = torch.tensor([-1., -2., -3., -4.], requires_grad=True)
        crossed = torch.tensor([-10., -20., -30., -40.], requires_grad=True)
        matrix = m.score_matrix(positive, crossed)
        self.assertEqual(matrix.tolist(), [[[-1., -10.], [-20., -2.]], [[-3., -30.], [-40., -4.]]])
        m.row_contrast_sum(matrix).backward()
        self.assertTrue(bool(positive.grad.lt(0).all())); self.assertTrue(bool(crossed.grad.gt(0).all()))

    def test_positive_column_gaps_do_not_hide_wrong_first_row(self):
        scores = torch.tensor([[[-4., -1.], [-12., -.5]]], requires_grad=True)
        self.assertTrue(bool((scores[0].diag() - scores[0].flip(0).diag()).gt(0).all()))
        value = m.row_contrast_sum(scores)
        self.assertTrue(bool(value > 3.))
        value.backward()
        self.assertLess(float(scores.grad[0, 0, 0]), -.9)
        self.assertGreater(float(scores.grad[0, 0, 1]), .9)

    def test_shared_content_prefix_cancels_without_token_negative_mask(self):
        shared = torch.tensor([-.2, -.3], requires_grad=True)
        right = torch.tensor([-1., -2.], requires_grad=True)
        wrong = torch.tensor([-3., -4.], requires_grad=True)
        positive = m.content_means(shared + right, [2, 2])
        crossed = m.content_means(shared + wrong, [2, 2])
        m.row_contrast_sum(m.score_matrix(positive, crossed)).backward()
        self.assertTrue(torch.equal(shared.grad, torch.zeros_like(shared)))
        self.assertTrue(bool(right.grad.lt(0).all())); self.assertTrue(bool(wrong.grad.gt(0).all()))

    def test_unequal_lengths_do_not_claim_shared_prefix_cancellation(self):
        shared = torch.tensor([-.2, -.3], requires_grad=True)
        positive = m.content_means(shared + torch.tensor([-1., -2.]), [2, 2])
        crossed = m.content_means(shared + torch.tensor([-3., -4.]), [3, 3])
        m.row_contrast_sum(m.score_matrix(positive, crossed)).backward()
        self.assertTrue(bool(shared.grad.ne(0).all()))

    def test_joint_question_answer_permutation_preserves_loss(self):
        scores = torch.tensor([[[-1., -3.], [-4., -2.]], [[-2., -1.], [-3., -4.]]])
        self.assertTrue(torch.allclose(m.row_contrast_sum(scores), m.row_contrast_sum(scores.flip(1).flip(2))))

    def test_invalid_pairs_temperature_margin_and_nonfinite_scores_refused(self):
        with self.assertRaises(ValueError): m.score_matrix(torch.zeros(3), torch.zeros(3))
        with self.assertRaises(ValueError): m.score_matrix(torch.zeros(2), torch.zeros(4))
        for temperature, margin in ((0., 0.), (True, 0.), (1., -1.), (float('inf'), 0.)):
            with self.assertRaises(ValueError): m.row_contrast_sum(torch.zeros(1, 2, 2), temperature, margin)
        for scores in (torch.zeros(0, 2, 2), torch.zeros(2, 2), torch.full((1, 2, 2), float('nan'))):
            with self.assertRaises(ValueError): m.row_contrast_sum(scores)


class NormalizationTests(unittest.TestCase):
    def test_zero_lambda_is_exact_ce_gradient_with_zero_cross_gradient(self):
        positive = torch.tensor([-1., -2.], requires_grad=True)
        crossed = torch.tensor([-3., -4.], requires_grad=True)
        ce = -positive.sum()
        rank = m.row_contrast_sum(m.score_matrix(positive, crossed))
        loss = m.normalized_loss(ce, 5, rank, 2, 0.)
        self.assertTrue(torch.equal(loss, ce / 5)); loss.backward()
        self.assertTrue(torch.equal(positive.grad, torch.full_like(positive, -.2)))
        self.assertTrue(torch.equal(crossed.grad, torch.zeros_like(crossed)))

    def test_micro_partition_matches_whole_update_value_and_gradient(self):
        weight = torch.tensor(.7, requires_grad=True)
        counts = [i % 4 + 1 for i in range(16)]
        relation_counts = [2 if i % 3 == 0 else 0 for i in range(16)]
        ce_terms = [(weight - i / 10).square() * count for i, count in enumerate(counts)]
        relation_terms = [F.softplus(weight - i / 5) * count for i, count in enumerate(relation_counts)]
        whole = m.normalized_loss(sum(ce_terms), sum(counts), sum(relation_terms), sum(relation_counts), .1)
        expected_gradient = torch.autograd.grad(whole, weight, retain_graph=True)[0]
        partitioned = sum(m.normalized_loss(ce, sum(counts), rel, sum(relation_counts), .1)
                          for ce, rel in zip(ce_terms, relation_terms))
        actual_gradient = torch.autograd.grad(partitioned, weight)[0]
        self.assertTrue(torch.allclose(whole, partitioned, atol=1e-7))
        self.assertTrue(torch.allclose(expected_gradient, actual_gradient, atol=1e-7))

    def test_zero_relation_lane_keeps_safe_zero_graph(self):
        ce = torch.tensor(5., requires_grad=True); relation = torch.tensor(0., requires_grad=True)
        m.normalized_loss(ce, 5, relation, 0, .1).backward()
        self.assertAlmostEqual(float(ce.grad), .2, places=7); self.assertEqual(float(relation.grad), 0.)
        with self.assertRaises(ValueError): m.normalized_loss(ce, 5, torch.tensor(1.), 0, 0.)

    def test_invalid_denominators_weight_and_scalar_are_refused(self):
        for targets, questions, weight in ((0, 2, .1), (True, 2, .1), (2, -1, .1), (2, 2, .05), (2, 2, True)):
            with self.assertRaises(ValueError): m.normalized_loss(torch.tensor(1.), targets, torch.tensor(1.), questions, weight)
        with self.assertRaises(ValueError): m.normalized_loss(torch.tensor([1.]), 2, torch.tensor(1.), 2, .1)


class ScheduleTests(unittest.TestCase):
    def test_actual_full_schedule_counts_and_positive_micro_shapes(self):
        groups = m.schedule(8192, 2048, 4096, 0)
        self.assertEqual(len(groups), 192)
        counts = Counter(); seen = {kind: [] for kind in ('natural', 'relation', 'replay')}
        for group in groups:
            self.assertEqual(len(group), 16)
            for micro in group:
                expected = 8 if micro.kind == 'replay' else 4
                self.assertEqual(len(micro.indices), expected)
                counts[micro.kind] += 1; seen[micro.kind].extend(micro.indices)
        self.assertEqual(counts, {'natural': 2048, 'relation': 512, 'replay': 512})
        for kind, count in (('natural', 8192), ('relation', 2048), ('replay', 4096)):
            self.assertEqual(sorted(seen[kind]), list(range(count)))

    def test_deterministic_seed_epoch_and_legacy_zero_relation_schedule(self):
        from scripts.p106b_night_learning import schedule as old_schedule
        first = m.schedule(32, 16, 32, 0)
        self.assertEqual(first, m.schedule(32, 16, 32, 0))
        self.assertNotEqual(first, m.schedule(32, 16, 32, 1))
        self.assertNotEqual(first, m.schedule(32, 16, 32, 0, 2024))
        legacy = old_schedule(8192, 4096, 0)
        actual = m.schedule(8192, 0, 4096, 0)
        self.assertEqual([[(v.kind, v.indices) for v in g] for g in actual],
                         [[(v.kind, v.indices) for v in g] for g in legacy])

    def test_partial_empty_and_noninteger_schedule_refused(self):
        for values in ((3, 4, 8, 0), (4, 3, 8, 0), (4, 4, 7, 0), (4, 4, 8, 0),
                       (0, 0, 0, 0), (32, 16, 32, -1), (True, 16, 32, 0)):
            with self.assertRaises(ValueError): m.schedule(*values)

    def test_direct_isolated_script_import_is_safe(self):
        path = ROOT / 'scripts/p106b_relation_bind_loss.py'
        result = subprocess.run([sys.executable, '-B', '-I', str(path)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__': unittest.main()
