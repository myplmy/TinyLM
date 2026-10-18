"""Small CPU tensor/schedule contracts; no model, learned weights or source IO."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F
from tinylm.train.mtp_sft import Record
from scripts import p106b_relation_bind_loss as original
from scripts import p106b_subject_role_loss as m


def record(content=(2,), prefix=2, tail=2, eot=8):
    ids = [1] * prefix + list(content) + [eot] + [1] * tail
    labels = [-100] * prefix + list(content) + [eot] + [-100] * tail
    y = labels[1:]
    return Record(ids[:-1], y, [int(value != -100) for value in y])


def bundle_records():
    candidates = ((2,), (3, 4), (5, 2, 3), (6,))
    positive = [record(candidates[q], prefix=q + 2) for q in range(4)]
    crossed = [record(candidates[a], prefix=q + 2)
               for q in range(4) for a in range(4) if a != q]
    return positive, crossed


class IdentityHead:
    """Plain tensor identity fixture, not a learned model or output module."""
    def _head_logits(self, hidden):
        return hidden


class LinearHead:
    """Thirty random CPU scalars, no architecture, assets or module instance."""
    def __init__(self, generator):
        self.weight = torch.randn(3, 10, generator=generator, requires_grad=True)

    def _head_logits(self, hidden):
        return hidden @ self.weight


class TensorTests(unittest.TestCase):
    def setUp(self):
        self.gen = torch.Generator(device='cpu').manual_seed(20261020)

    def scores(self, n=2):
        return torch.randn(n, 4, 4, generator=self.gen, requires_grad=True)

    def test_frozen_public_sequence_and_normalization_helpers_are_reused(self):
        self.assertIs(m.sequence_terms, original.sequence_terms)
        self.assertIs(m.content_means, original.content_means)
        self.assertIs(m.normalized_loss, original.normalized_loss)
        self.assertEqual(m.WEIGHTS, dict(CE=0., ROLE_ONLY=.1, ALL_AXES=.1))

    def test_diag4_cross12_order_is_exact_for_two_full_graphs(self):
        positive = torch.arange(8, dtype=torch.float32, requires_grad=True)
        crossed = torch.arange(24, dtype=torch.float32, requires_grad=True)
        matrix = m.score_matrix(positive, crossed)
        self.assertEqual(matrix.shape, (2, 4, 4))
        for graph in range(2):
            at = 12 * graph
            for q in range(4):
                for a in range(4):
                    value = 4 * graph + q if q == a else at + 3 * q + (a if a < q else a - 1)
                    self.assertEqual(float(matrix[graph, q, a].detach()), value)
        matrix.sum().backward()
        self.assertTrue(torch.equal(positive.grad, torch.ones_like(positive)))
        self.assertTrue(torch.equal(crossed.grad, torch.ones_like(crossed)))

    def test_partial_empty_wrong_shape_dtype_and_nonfinite_vectors_refused(self):
        bad = ((torch.zeros(0), torch.zeros(0)), (torch.zeros(3), torch.zeros(9)),
               (torch.zeros(4), torch.zeros(11)), (torch.zeros(4), torch.zeros(24)),
               (torch.zeros(1, 4), torch.zeros(12)), (torch.zeros(4, dtype=torch.long), torch.zeros(12)),
               (torch.zeros(4, dtype=torch.float64), torch.zeros(12)),
               (torch.full((4,), float('nan')), torch.zeros(12)),
               (torch.zeros(4), torch.full((12,), float('inf'))))
        for positive, crossed in bad:
            with self.subTest(shapes=(positive.shape, crossed.shape)), self.assertRaises(ValueError):
                m.score_matrix(positive, crossed)

    def test_canonical_masks_select_exactly_zero_one_or_three_negatives(self):
        for mode, count in (('CE', 0), ('ROLE_ONLY', 1), ('ALL_AXES', 3)):
            mask = m.negative_mask(mode)
            self.assertEqual(mask.dtype, torch.bool)
            self.assertEqual(mask.sum(-1).tolist(), [count] * 4)
            self.assertFalse(bool(mask.diagonal().any()))
        role = m.negative_mask('ROLE_ONLY')
        self.assertEqual(role.nonzero().tolist(), [[0, 1], [1, 0], [2, 3], [3, 2]])
        for mode in ('ce', 'SUBJECT_ONLY', None, True, []):
            with self.assertRaises(ValueError): m.negative_mask(mode)
            with self.assertRaises(ValueError): m.row_contrast_sum(self.scores(), mode)

    def test_diagonal_integer_or_wrong_shape_masks_are_never_valid_negatives(self):
        masks = (torch.eye(4, dtype=torch.bool), torch.ones(4, 4, dtype=torch.bool),
                 torch.zeros(4, 4), torch.zeros(4, 4, dtype=torch.long),
                 torch.zeros(1, 4, 4, dtype=torch.bool), torch.zeros(4, dtype=torch.bool), None)
        for mask in masks:
            with self.assertRaises(ValueError): m.masked_row_contrast_sum(self.scores(), mask)

    def test_each_row_averages_its_valid_negatives_before_question_normalization(self):
        scores = self.scores()
        for mode in ('ROLE_ONLY', 'ALL_AXES'):
            expected = scores.new_zeros(())
            for graph in range(2):
                for q in range(4):
                    negative = [q ^ 1] if mode == 'ROLE_ONLY' else [a for a in range(4) if a != q]
                    expected = expected + sum(F.softplus(scores[graph, q, a] - scores[graph, q, q])
                                              for a in negative) / len(negative)
            actual = m.row_contrast_sum(scores, mode)
            self.assertTrue(torch.allclose(actual, expected, atol=1e-6))
        zeros = torch.zeros(2, 4, 4, requires_grad=True)
        # Three negatives are averaged: both modes have the same eight question losses.
        self.assertAlmostEqual(float(m.row_contrast_sum(zeros, 'ROLE_ONLY').detach()), 8 * __import__('math').log(2), places=6)
        self.assertTrue(torch.equal(m.row_contrast_sum(zeros, 'ROLE_ONLY'), m.row_contrast_sum(zeros, 'ALL_AXES')))

    def test_role_only_counterexample_ignores_subject_but_all_axes_penalizes_tie(self):
        scores = torch.tensor([[[0. if q % 2 == a % 2 else -40. for a in range(4)]
                                for q in range(4)]], requires_grad=True)
        role = m.row_contrast_sum(scores, 'ROLE_ONLY')
        all_axes = m.row_contrast_sum(scores, 'ALL_AXES')
        self.assertLess(float(role.detach()), 1e-12)
        self.assertAlmostEqual(float(all_axes.detach()), 4 * __import__('math').log(2) / 3, places=6)
        role_grad = torch.autograd.grad(role, scores, retain_graph=True)[0]
        all_grad = torch.autograd.grad(all_axes, scores)[0]
        self.assertEqual(float(role_grad[0, 0, 2]), 0.)
        self.assertGreater(float(all_grad[0, 0, 2]), .16)
        self.assertLess(float(all_grad[0, 0, 0]), -.16)

    def test_gold_is_pushed_up_and_each_selected_crossed_answer_down(self):
        scores = self.scores()
        m.row_contrast_sum(scores, 'ALL_AXES').backward()
        diagonal = torch.eye(4, dtype=torch.bool)
        self.assertTrue(bool(scores.grad[:, diagonal].lt(0).all()))
        self.assertTrue(bool(scores.grad[:, ~diagonal].gt(0).all()))

    def test_unused_edges_keep_zero_gradients_and_ce_keeps_entire_graph(self):
        scores = self.scores()
        m.row_contrast_sum(scores, 'ROLE_ONLY').backward()
        selected = m.negative_mask('ROLE_ONLY') | torch.eye(4, dtype=torch.bool)
        self.assertTrue(torch.equal(scores.grad[:, ~selected], torch.zeros_like(scores.grad[:, ~selected])))
        scores.grad = None
        value = m.row_contrast_sum(scores, 'CE')
        self.assertEqual(float(value.detach()), 0.)
        value.backward()
        self.assertIsNotNone(scores.grad)
        self.assertTrue(torch.equal(scores.grad, torch.zeros_like(scores)))

    def test_zero_edge_rows_are_safe_and_do_not_gain_softplus_mass(self):
        scores = self.scores(1)
        mask = torch.zeros(4, 4, dtype=torch.bool)
        mask[0, 1] = True
        value = m.masked_row_contrast_sum(scores, mask)
        expected = F.softplus(scores[0, 0, 1] - scores[0, 0, 0])
        self.assertTrue(torch.equal(value, expected))
        value.backward()
        self.assertTrue(torch.equal(scores.grad[:, 1:], torch.zeros_like(scores.grad[:, 1:])))
        ce = torch.tensor(5., requires_grad=True)
        zero = torch.tensor(0., requires_grad=True)
        m.normalized_loss(ce, 5, zero, 0, .1).backward()
        self.assertAlmostEqual(float(ce.grad), .2, places=7)
        self.assertEqual(float(zero.grad), 0.)
        with self.assertRaises(ValueError): m.normalized_loss(ce, 5, torch.tensor(1.), 0, .1)

    def test_joint_permutation_preserves_all_axes_and_transformed_role_mask(self):
        scores = self.scores(); order = torch.tensor([0, 2, 1, 3])
        permuted = scores[:, order][:, :, order]
        self.assertTrue(torch.allclose(m.row_contrast_sum(scores), m.row_contrast_sum(permuted), atol=1e-6))
        mask = m.negative_mask('ROLE_ONLY')
        self.assertTrue(torch.allclose(m.masked_row_contrast_sum(scores, mask),
            m.masked_row_contrast_sum(permuted, mask[order][:, order]), atol=1e-6))
        # The default XOR mask retains meaning only under a pair-preserving permutation.
        subject_swap = torch.tensor([2, 3, 0, 1])
        self.assertTrue(torch.allclose(m.row_contrast_sum(scores, 'ROLE_ONLY'),
            m.row_contrast_sum(scores[:, subject_swap][:, :, subject_swap], 'ROLE_ONLY'), atol=1e-6))

    def test_bad_scores_parameters_and_even_unused_nan_are_refused(self):
        for value in (torch.zeros(0, 4, 4), torch.zeros(4, 4), torch.zeros(1, 2, 2),
                      torch.zeros(1, 4, 4, dtype=torch.long), torch.full((1, 4, 4), float('nan'))):
            with self.assertRaises(ValueError): m.row_contrast_sum(value, 'CE')
        for temperature, margin in ((0., 0.), (True, 0.), (float('inf'), 0.), (1., -1.), (1., float('nan'))):
            with self.assertRaises(ValueError): m.row_contrast_sum(self.scores(), 'ALL_AXES', temperature, margin)
        with self.assertRaises(ValueError): m.normalized_loss(torch.tensor(float('nan')), 4, torch.tensor(0.), 4, .1)
        with self.assertRaises(ValueError): m.normalized_loss(torch.tensor(1.), 0, torch.tensor(0.), 4, .1)
        with self.assertRaises(ValueError): m.normalized_loss(torch.tensor(1.), 4, torch.tensor(0.), 4, .05)

    def test_variable_length_candidates_use_own_content_counts(self):
        positive, crossed = bundle_records()
        p = torch.randn(4, 16, 10, generator=self.gen, requires_grad=True)
        c = torch.randn(12, 16, 10, generator=self.gen, requires_grad=True)
        ps, pe, pn = m.sequence_terms(IdentityHead(), p, positive, 8, False)
        cs, ce, cn = m.sequence_terms(IdentityHead(), c, crossed, 8, False)
        self.assertEqual(pn, [1, 2, 3, 1])
        self.assertEqual(cn, [2, 3, 1, 1, 3, 1, 1, 2, 1, 1, 2, 3])
        matrix = m.score_matrix(m.content_means(ps, pn), m.content_means(cs, cn))
        for q in range(4):
            self.assertTrue(torch.equal(matrix[0, q, q], ps[q] / pn[q]))
        self.assertEqual(pe.shape, (4,)); self.assertEqual(ce.shape, (12,))

    def test_relation_gradient_excludes_content_eot_prompt_and_padding_correctly(self):
        positive, crossed = bundle_records()
        p = torch.randn(4, 16, 10, generator=self.gen, requires_grad=True)
        c = torch.randn(12, 16, 10, generator=self.gen, requires_grad=True)
        ps, pe, pn = m.sequence_terms(IdentityHead(), p, positive, 8, False)
        cs, _, cn = m.sequence_terms(IdentityHead(), c, crossed, 8, False)
        matrix = m.score_matrix(m.content_means(ps, pn), m.content_means(cs, cn))
        m.row_contrast_sum(matrix).backward(retain_graph=True)
        for hidden, records in ((p, positive), (c, crossed)):
            for row, rec in enumerate(records):
                content = [i for i, target in enumerate(rec.y) if target != -100][:-1]
                for i in range(hidden.shape[1]):
                    self.assertEqual(bool(hidden.grad[row, i].ne(0).any()), i in content)
        p.grad = None
        (-(ps + pe).sum()).backward()
        for row, rec in enumerate(positive):
            eot = [i for i, target in enumerate(rec.y) if target != -100][-1]
            self.assertGreater(float(p.grad[row, eot].abs().sum()), 0.)

    def test_ce_comparator_has_exact_same_positive_and_head_gradients(self):
        positive, crossed = bundle_records(); positive *= 2; crossed *= 2
        p = torch.randn(8, 16, 3, generator=self.gen, requires_grad=True)
        c = torch.randn(24, 16, 3, generator=self.gen, requires_grad=True)
        head = LinearHead(self.gen)
        ps, pe, pn = m.sequence_terms(head, p, positive, 8, True)
        cs, ce, cn = m.sequence_terms(head, c, crossed, 8, True)
        correct = -(ps + pe).sum(); words = sum(rec.targets for rec in positive)
        expected = torch.autograd.grad(correct / words, (head.weight, p), retain_graph=True)
        matrix = m.score_matrix(m.content_means(ps, pn), m.content_means(cs, cn))
        ranking = m.row_contrast_sum(matrix, 'CE') + ce.sum() * 0.
        total = m.normalized_loss(correct, words, ranking, 8, m.WEIGHTS['CE'])
        self.assertTrue(torch.equal(total, correct / words))
        actual = torch.autograd.grad(total, (head.weight, p, c))
        self.assertTrue(torch.equal(expected[0], actual[0]))
        self.assertTrue(torch.equal(expected[1], actual[1]))
        self.assertTrue(torch.equal(actual[2], torch.zeros_like(c)))

    def test_full_micro_partition_has_same_whole_update_value_and_gradient(self):
        for mode in m.MODES:
            weight = torch.tensor(.7, requires_grad=True)
            ce = [(weight - i / 10).square() * (i % 4 + 1) for i in range(16)]
            questions = [8 if i % 3 == 0 else 0 for i in range(16)]
            scores = [weight * torch.arange(32, dtype=torch.float32).reshape(2, 4, 4) / (i + 4)
                      for i in range(16)]
            relation = [m.row_contrast_sum(s, mode) if n else ce[i] * 0.
                        for i, (s, n) in enumerate(zip(scores, questions))]
            whole = m.normalized_loss(sum(ce), 40, sum(relation), sum(questions), m.WEIGHTS[mode])
            expected = torch.autograd.grad(whole, weight, retain_graph=True)[0]
            partitioned = sum(m.normalized_loss(c, 40, r, sum(questions), m.WEIGHTS[mode])
                              for c, r in zip(ce, relation))
            actual = torch.autograd.grad(partitioned, weight)[0]
            self.assertTrue(torch.allclose(whole, partitioned, atol=1e-6))
            self.assertTrue(torch.allclose(expected, actual, atol=1e-6))

    def test_pure_derived_data_layout_masks_and_physical_cross_chunks_agree(self):
        # New-component integration only: synthetic source facts and a character
        # tokenizer fixture, never a frozen corpus or actual tokenizer asset.
        from scripts import p106b_subject_role_data as derived
        from scripts.test_p106b_subject_role_data import CharTokenizer
        parents = derived.original.generate(dict(train=8, dev=8, test=8))['train']
        bundles = [derived.derive_bundle(parent) for parent in parents[:2]]
        positive, crossed = derived.encode_micro(bundles, CharTokenizer())
        self.assertEqual((len(positive), len(crossed)), (8, 24))
        self.assertEqual([len(chunk) for chunk in derived.cross_micro_batches(crossed)], [8, 8, 8])
        masks = derived.negative_masks()
        for mode in ('ROLE_ONLY', 'ALL_AXES'):
            self.assertEqual(m.negative_mask(mode).tolist(), masks[mode + '4'])
        layout = derived.candidate_layout()
        self.assertEqual(list(layout['positive']), [(q, q) for q in range(4)])
        self.assertEqual(list(layout['crossed']), [(q, a) for q in range(4) for a in range(4) if a != q])
        matrix = m.score_matrix(torch.arange(8, dtype=torch.float32),
                                100 + torch.arange(24, dtype=torch.float32))
        for graph in range(2):
            for index, (q, a) in enumerate(layout['crossed']):
                targets = [y for y in crossed[12 * graph + index].y if y != -100]
                expected = [y for y in positive[4 * graph + a].y if y != -100]
                self.assertEqual(targets, expected)
                self.assertEqual(float(matrix[graph, q, a]), 100 + 12 * graph + index)


class ScheduleTests(unittest.TestCase):
    def test_full_four_passes_are896_updates_with_exact_unique_exposure(self):
        fingerprints = []
        for epoch in range(4):
            groups = m.schedule(8192, 2048, 4096, epoch)
            self.assertEqual(len(groups), 224)
            seen = {kind: [] for kind in ('natural', 'relation', 'replay')}
            count = Counter(); rows = 0
            for group in groups:
                self.assertEqual(len(group), 16)
                batch_rows = 0
                for micro in group:
                    width = dict(natural=4, relation=2, replay=8)[micro.kind]
                    self.assertEqual(len(micro.indices), width)
                    seen[micro.kind].extend(micro.indices); count[micro.kind] += 1
                    batch_rows += width * dict(natural=2, relation=4, replay=1)[micro.kind]
                self.assertEqual(batch_rows, 128); rows += batch_rows
            self.assertEqual(rows, 28672)
            self.assertEqual(count, dict(natural=2048, relation=1024, replay=512))
            for kind, size in (('natural', 8192), ('relation', 2048), ('replay', 4096)):
                self.assertEqual(sorted(seen[kind]), list(range(size)))
            fingerprints.append(tuple((x.kind, x.indices) for g in groups for x in g))
        self.assertEqual(4 * len(groups), 896)
        self.assertEqual(len(set(fingerprints)), 4)

    def test_all_modes_receive_identical_seeded_schedule_and_no_input_mutation(self):
        first = m.schedule(16, 8, 64, 0)
        self.assertEqual(len(first), 1)
        for mode in m.MODES:
            self.assertEqual(first, m.schedule(16, 8, 64, 0))
        self.assertNotEqual(first, m.schedule(16, 8, 64, 1))
        self.assertNotEqual(first, m.schedule(16, 8, 64, 0, seed=2))
        self.assertEqual(m.schedule(0, 0, 128, 0)[0][0].kind, 'replay')

    def test_unknown_partial_noninteger_or_empty_counts_are_not_filled(self):
        bad = ((None, 8, 64, 0), (15, 8, 64, 0), (16, 7, 64, 0), (16, 8, 63, 0),
               (4, 2, 8, 0), (0, 0, 0, 0), (16, 8, 64, -1), (True, 8, 64, 0))
        for values in bad:
            with self.assertRaises(ValueError): m.schedule(*values)
        with self.assertRaises(ValueError): m.schedule(16, 8, 64, 0, seed=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
