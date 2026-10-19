#!/usr/bin/env python3
"""Synthetic CPU-only span-readout contracts; no assets or learned weights IO."""
from __future__ import annotations

from dataclasses import replace
import inspect
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from scripts import p106b_span_readout as m


class FixedTokenizer:
    def __init__(self, ids, offsets):
        self.ids, self.offsets = list(ids), list(offsets)
        self.calls = []

    def encode(self, prefix):
        self.calls.append(prefix)
        return SimpleNamespace(ids=list(self.ids), offsets=list(self.offsets))


def character_bank(reference='Ab cd', *, max_tokens=1024):
    prefix = '<U>' + reference + '<Q>'
    tok = FixedTokenizer(range(len(prefix)), [(i, i + 1) for i in range(len(prefix))])
    return m.build_bank(tok, prefix, (3, 3 + len(reference)), max_tokens=max_tokens), tok


def identity_head(dim=2, rank=2):
    head = torch.nn.ModuleDict({name: torch.nn.Linear(dim, rank, bias=False)
                               for name in ('qs', 'ks', 'qe', 'ke')})
    with torch.no_grad():
        for layer in head.values():
            layer.weight.zero_()
            for i in range(min(dim, rank)):
                layer.weight[i, i] = 1.
    return head


class BankTests(unittest.TestCase):
    def test_exact_prefix_ids_offsets_and_last_query_are_preserved(self):
        bank, tok = character_bank()
        self.assertEqual(tok.calls, [bank.prefix])
        self.assertEqual(bank.ids, tuple(tok.ids))
        self.assertEqual(bank.offsets, tuple(tok.offsets))
        self.assertEqual(bank.positions, (3, 4, 5, 6, 7))
        self.assertEqual(bank.query, len(bank.ids) - 1)

    def test_reference_boundary_straddles_are_excluded_without_retokenization(self):
        prefix = 'xxABCqq'
        tok = FixedTokenizer([7, 8, 9, 10], [(0, 3), (3, 4), (4, 6), (6, 7)])
        bank = m.build_bank(tok, prefix, (2, 5))
        self.assertEqual(bank.positions, (1,))
        self.assertEqual(bank.ids, (7, 8, 9, 10))

    def test_zero_width_offsets_never_enter_source_bank(self):
        tok = FixedTokenizer([1, 2, 3, 4], [(0, 0), (1, 2), (2, 3), (0, 0)])
        bank = m.build_bank(tok, 'xABy', (1, 3))
        self.assertEqual(bank.positions, (1, 2))
        self.assertEqual(bank.query, 3)

    def test_duplicate_and_overlapping_bytelevel_offsets_remain_distinct_keys(self):
        tok = FixedTokenizer(range(6), [(0, 1), (1, 2), (1, 2), (1, 3), (2, 3), (3, 4)])
        bank = m.build_bank(tok, 'x가나Q', (1, 3))
        self.assertEqual(bank.positions, (1, 2, 3, 4))
        self.assertEqual(bank.offsets[1:4], ((1, 2), (1, 2), (1, 3)))
        out = m.select_span(bank, [0., 8., 0., 0.], [0., 0., 0., 9.])
        self.assertEqual(out.raw_text, '가나')

    def test_duplicate_entire_reference_is_rejected(self):
        tok = FixedTokenizer(range(7), [(i, i + 1) for i in range(7)])
        with self.assertRaises(ValueError):
            m.build_bank(tok, 'abcabcQ', (0, 3))

    def test_overlapping_duplicate_reference_is_rejected(self):
        tok = FixedTokenizer(range(6), [(i, i + 1) for i in range(6)])
        with self.assertRaises(ValueError):
            m.build_bank(tok, 'aaaaaQ', (0, 3))

    def test_declared_range_must_be_valid_unicode_character_range(self):
        bank, tok = character_bank('가나다')
        for bounds in ((0, 0), (-1, 2), (1, 99), (True, 2), (0., 2), (1,), '1:2'):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                m.build_bank(tok, bank.prefix, bounds)

    def test_no_empty_or_zero_width_only_source_bank(self):
        for offsets in ([(0, 4), (4, 5)], [(0, 0), (4, 5)]):
            with self.subTest(offsets=offsets), self.assertRaises(ValueError):
                m.build_bank(FixedTokenizer([1, 2], offsets), 'xABqQ', (1, 3))

    def test_source_may_not_include_query_or_future_positions(self):
        tok = FixedTokenizer([1, 2, 3], [(0, 1), (1, 2), (2, 3)])
        with self.assertRaises(ValueError):
            m.build_bank(tok, 'xAQ', (1, 3))
        bank, _ = character_bank()
        with self.assertRaises(ValueError):
            replace(bank, query=3)

    def test_token_limit_is_exact_and_invalid_limits_are_rejected(self):
        bank, tok = character_bank()
        m.build_bank(tok, bank.prefix, bank.reference_range, max_tokens=len(bank.ids))
        for limit in (len(bank.ids) - 1, 0, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                m.build_bank(tok, bank.prefix, bank.reference_range, max_tokens=limit)

    def test_bad_ids_offsets_or_order_are_rejected(self):
        bad = (([1, True, 3], [(0, 1), (1, 2), (2, 3)]),
               ([1, -1, 3], [(0, 1), (1, 2), (2, 3)]),
               ([1, 2, 3], [(0, 1), (1, 2)]),
               ([1, 2, 3], [(0, 1), (1, 99), (2, 3)]),
               ([1, 2, 3], [(0, 1), (True, 2), (2, 3)]),
               ([1, 2, 3], [(1, 2), (0, 1), (2, 3)]),
               ([1, 2, 3], [(0, 2), (1, 1, 2), (2, 3)]))
        for ids, offsets in bad:
            with self.subTest(ids=ids, offsets=offsets), self.assertRaises(ValueError):
                m.build_bank(FixedTokenizer(ids, offsets), 'ABQ', (0, 2))

    def test_non_tokenizer_or_malformed_encoding_is_rejected(self):
        for tok in (None, SimpleNamespace(encode=lambda _: object()),
                    SimpleNamespace(encode=lambda _: SimpleNamespace(ids=[1], offsets=None))):
            with self.subTest(tok=tok), self.assertRaises(ValueError):
                m.build_bank(tok, 'ABQ', (0, 2))

    def test_empty_prefix_and_empty_encoding_are_rejected(self):
        for prefix, tok in (('', FixedTokenizer([], [])), ('ABQ', FixedTokenizer([], []))):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                m.build_bank(tok, prefix, (0, 2))

    def test_bank_is_immutable_and_cannot_be_forged_with_missing_source_keys(self):
        bank, _ = character_bank()
        with self.assertRaises(AttributeError):
            bank.query = 0
        with self.assertRaises(ValueError):
            replace(bank, positions=bank.positions[:-1])
        with self.assertRaises(ValueError):
            replace(bank, positions=(True, *bank.positions[1:]))


class SelectionTests(unittest.TestCase):
    def test_independent_reverse_is_invalid_and_never_repaired(self):
        bank, _ = character_bank('ABC')
        out = m.select_span(bank, [0., 0., 4.], [9., 0., 0.])
        self.assertEqual((out.start_index, out.end_index), (2, 0))
        self.assertEqual(out.status, 'INVALID_REVERSED')
        self.assertIsNone(out.text)
        self.assertIsNone(out.raw_text)
        self.assertIsNone(out.char_range)

    def test_valid_joint_finds_global_legal_pair_not_argmax_repair(self):
        bank, _ = character_bank('ABC')
        out = m.select_span(bank, [3., 0., 4.], [9., 0., 0.], 'valid_joint')
        self.assertEqual((out.start_index, out.end_index), (0, 0))
        self.assertEqual((out.text, out.joint_score), ('A', 12.))

    def test_both_tie_policies_choose_lexicographically_first(self):
        bank, _ = character_bank('ABC')
        for policy in m.POLICIES:
            out = m.select_span(bank, [2., 2., 2.], [3., 3., 3.], policy)
            self.assertEqual((out.start_index, out.end_index), (0, 0))
        out = m.select_span(bank, [0., 1., 1.], [1., 0., 0.], 'valid_joint')
        self.assertEqual((out.start_index, out.end_index), (0, 0))

    def test_joint_algorithm_matches_exhaustive_all_pairs(self):
        rng = random.Random(20261020)
        for n in range(1, 13):
            bank, _ = character_bank(''.join(chr(0xAC00 + i) for i in range(n)))
            for _ in range(30):
                start = [rng.randrange(-4, 5) / 2 for _ in range(n)]
                end = [rng.randrange(-4, 5) / 2 for _ in range(n)]
                expected = min(((i, j) for i in range(n) for j in range(i, n)),
                               key=lambda pair: (-(start[pair[0]] + end[pair[1]]), pair))
                out = m.select_span(bank, start, end, 'valid_joint')
                self.assertEqual((out.start_index, out.end_index), expected)

    def test_joint_policy_has_no_hidden_answer_length_cap(self):
        bank, _ = character_bank(''.join(chr(0xAC00 + i) for i in range(300)))
        start, end = [0.] * 300, [0.] * 300
        start[0], end[-1] = 10., 11.
        out = m.select_span(bank, start, end, 'valid_joint')
        self.assertEqual(len(out.raw_text), 300)
        self.assertEqual((out.start_index, out.end_index), (0, 299))

    def test_english_leading_space_and_internal_layout_are_preserved(self):
        prefix = 'X Nuri  Hall.Y'
        tok = FixedTokenizer([1, 2, 3, 4, 5], [(0, 1), (1, 6), (6, 12), (12, 13), (13, 14)])
        bank = m.build_bank(tok, prefix, (1, 13))
        out = m.select_span(bank, [8., 0., 0.], [0., 9., 0.])
        self.assertEqual(out.raw_text, ' Nuri  Hall')
        self.assertEqual(out.text, 'Nuri  Hall')
        self.assertEqual(out.normalization, m.NORMALIZATION)

    def test_korean_particle_and_punctuation_spill_are_not_gold_trimmed(self):
        prefix = 'X지아는 사서.Y'
        tok = FixedTokenizer([1, 2, 3, 4], [(0, 1), (1, 4), (4, 8), (8, 9)])
        bank = m.build_bank(tok, prefix, (1, 8))
        out = m.select_span(bank, [9., 0.], [9., 0.])
        self.assertEqual(out.raw_text, '지아는')
        self.assertEqual(out.text, '지아는')
        other = m.select_span(bank, [0., 9.], [0., 9.])
        self.assertEqual(other.text, '사서.')

    def test_empty_outer_trim_result_is_preserved(self):
        bank, _ = character_bank('A B')
        out = m.select_span(bank, [0., 5., 0.], [0., 5., 0.])
        self.assertEqual(out.status, 'OK')
        self.assertEqual(out.raw_text, ' ')
        self.assertEqual(out.text, '')

    def test_score_shape_dtype_nonfinite_and_policy_are_rejected(self):
        bank, _ = character_bank('ABC')
        for values in ([1.], [1., 2., float('nan')], [1., 2., float('inf')],
                       [1., 2., True], torch.ones(1, 3), torch.ones(3, dtype=torch.long)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                m.select_span(bank, values, [0., 0., 0.])
        for policy in ('greedy', 'VALID_JOINT', None, []):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                m.select_span(bank, [0.] * 3, [0.] * 3, policy)
        with self.assertRaises(ValueError):
            m.select_span(bank, [1e308] * 3, [1e308] * 3)

    def test_no_gold_or_metadata_inference_argument_and_gold_change_invariance(self):
        bank, tok = character_bank('한영Alpha')
        hidden = torch.arange(len(bank.ids) * 2, dtype=torch.float32).reshape(-1, 2)
        head = identity_head()
        prior = m.readout(head, hidden, bank)
        outside_metadata = {'gold': 'old', 'user_answer_range': [3, 4]}
        outside_metadata.update(gold='unrelated', user_answer_range=[99, 101])
        again = m.readout(head, hidden, m.build_bank(tok, bank.prefix, bank.reference_range))
        self.assertEqual(prior, again)
        for function in (m.build_bank, m.boundary_scores, m.select_span, m.readout):
            self.assertFalse({'gold', 'answer', 'user_answer_range', 'locations', 'meta'}
                             & set(inspect.signature(function).parameters))
        with self.assertRaises(TypeError):
            m.build_bank(tok, bank.prefix, bank.reference_range, gold=outside_metadata['gold'])


class ScoreTests(unittest.TestCase):
    def test_existing_head_formula_and_last_prefix_query_match_manual_math(self):
        bank, _ = character_bank('AB')
        hidden = torch.zeros(len(bank.ids), 2, requires_grad=True)
        with torch.no_grad():
            hidden[bank.positions[0]] = torch.tensor([1., 2.])
            hidden[bank.positions[1]] = torch.tensor([3., 4.])
            hidden[bank.query] = torch.tensor([2., 1.])
        head = identity_head()
        with torch.no_grad():
            head['qe'].weight.copy_(torch.tensor([[0., 1.], [1., 0.]]))
        start, end = m.boundary_scores(head, hidden, bank)
        torch.testing.assert_close(start, torch.tensor([4., 10.]) / math.sqrt(2))
        torch.testing.assert_close(end, torch.tensor([5., 11.]) / math.sqrt(2))
        self.assertFalse(start.requires_grad)
        self.assertTrue(all(p.grad is None for p in head.parameters()))

    def test_exact_single_batch_hidden_matches_unbatched_without_state_mutation(self):
        bank, _ = character_bank()
        hidden = torch.arange(len(bank.ids) * 2, dtype=torch.float32).reshape(-1, 2)
        head = identity_head()
        before = {key: value.clone() for key, value in head.state_dict().items()}
        saved_rng = torch.random.get_rng_state().clone()
        left = m.boundary_scores(head, hidden, bank)
        right = m.boundary_scores(head, hidden.unsqueeze(0), bank)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(left, right)))
        self.assertTrue(torch.equal(saved_rng, torch.random.get_rng_state()))
        self.assertTrue(all(torch.equal(v, head.state_dict()[k]) for k, v in before.items()))

    def test_only_bank_and_query_hidden_can_affect_scores(self):
        bank, _ = character_bank()
        hidden = torch.ones(len(bank.ids), 2)
        head = identity_head()
        baseline = m.boundary_scores(head, hidden, bank)
        changed = hidden.clone()
        ignored = set(range(len(bank.ids))) - set(bank.positions) - {bank.query}
        changed[list(ignored)] = -1000.
        actual = m.boundary_scores(head, changed, bank)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(baseline, actual)))

    def test_bad_hidden_shape_size_dtype_or_nonfinite_is_rejected(self):
        bank, _ = character_bank()
        n = len(bank.ids)
        bad = (torch.ones(n - 1, 2), torch.ones(n + 1, 2), torch.ones(2, n, 2),
               torch.ones(n, 3), torch.ones(n, 2, dtype=torch.long), torch.ones(2),
               torch.full((n, 2), float('nan')), torch.full((n, 2), float('inf')))
        for hidden in bad:
            with self.subTest(shape=hidden.shape, dtype=hidden.dtype), self.assertRaises(ValueError):
                m.boundary_scores(identity_head(), hidden, bank)

    def test_missing_biased_or_mismatched_rank_head_is_rejected(self):
        bank, _ = character_bank()
        hidden = torch.ones(len(bank.ids), 2)
        heads = []
        head = identity_head();del head['qe'];heads.append(head)
        head = identity_head();head['qs'] = torch.nn.Linear(2, 2, bias=True);heads.append(head)
        head = identity_head();head['ke'] = torch.nn.Linear(2, 3, bias=False);heads.append(head)
        head = identity_head();head['ks'] = head['ks'].double();heads.append(head)
        head = identity_head()
        with torch.no_grad():head['ke'].weight[0, 0] = float('nan')
        heads.append(head)
        for head in heads:
            with self.subTest(head=head), self.assertRaises(ValueError):
                m.boundary_scores(head, hidden, bank)

    def test_projection_overflow_is_rejected(self):
        bank, _ = character_bank()
        with self.assertRaises(ValueError):
            m.boundary_scores(identity_head(), torch.full((len(bank.ids), 2), 1e30), bank)

    def test_double_hidden_uses_head_projection_dtype_then_fp32_dot(self):
        bank, _ = character_bank()
        scores = m.boundary_scores(identity_head(), torch.ones(len(bank.ids), 2, dtype=torch.float64), bank)
        self.assertTrue(all(value.dtype == torch.float32 for value in scores))

    def test_ambient_cpu_autocast_does_not_change_fp32_scoring(self):
        bank, _ = character_bank()
        hidden = torch.arange(len(bank.ids) * 2, dtype=torch.float32).reshape(-1, 2) / 7.
        head = identity_head()
        expected = m.boundary_scores(head, hidden, bank)
        with torch.autocast('cpu', dtype=torch.bfloat16):
            actual = m.boundary_scores(head, hidden, bank)
        self.assertTrue(all(v.dtype == torch.float32 for v in actual))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(expected, actual)))


if __name__ == '__main__':
    unittest.main()
