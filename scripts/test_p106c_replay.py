#!/usr/bin/env python3
"""P106C CPU contracts, including actual toy AdamW/Muon state and fixed denominator."""
from __future__ import annotations
import copy
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106c_data as data
from scripts import p106c_replay as replay


class DataTests(unittest.TestCase):
    def test_split_roles_pairs_gold_negatives(self):
        groups = {r: data.make_role(r) for r in data.ROLES}
        data.validate_roles(groups)
        self.assertEqual(len(groups["train"]), 512)
        self.assertEqual(len(groups["sealed"]), 128)
        self.assertEqual(len(data.positive_controls()), 64)
        self.assertEqual(len({r['question'] for r in data.positive_controls()}), 64)
        self.assertEqual(data.data_hash(groups["train"]), data.data_hash(data.make_role("train")))
        for role, rows in groups.items():
            for i in range(0, len(rows), 2):
                self.assertEqual(rows[i]["pair_id"], rows[i+1]["pair_id"])
                self.assertNotEqual(rows[i]["gold"], rows[i+1]["gold"])

    def test_roles_reject_question_leak(self):
        groups = {r: data.make_role(r) for r in data.ROLES}
        groups["dev"][0]["question"] = groups["train"][0]["question"]
        with self.assertRaises(ValueError):
            data.validate_roles(groups)

    def test_policy_target_mass_language_and_exposure_match(self):
        train = [([1]*(15+i%3), [1]*(15+i%3), 1+i%2) for i in range(512)]
        rehearsal = [([1]*12, [1]*12, 2) for _ in range(256)]
        languages = ["ko" if i%2 else "en" for i in range(512)]
        plan = data.policy_plan(train, rehearsal, (1, 3, 8, 12), languages=languages)
        self.assertLessEqual(max(plan["max_exposures"].values()), 16)
        for left, right in zip(plan["baseline"], plan["selected"]):
            self.assertEqual(left["rehearsal"], right["rehearsal"])
            for a, b in zip(left["candidate"], right["candidate"]):
                self.assertEqual((len(train[a][0]), train[a][2], languages[a]),
                                 (len(train[b][0]), train[b][2], languages[b]))

    def test_infeasible_exposure_is_not_silent_repetition(self):
        tr = [([1], [1], 1) for _ in range(32)]
        with self.assertRaises(ValueError):
            data.policy_plan(tr, tr, (), cap=1)

    def test_loop_observation_and_paired_interval(self):
        self.assertTrue(replay.loop_observed([1, 2, 1, 2, 1, 2]))
        self.assertFalse(replay.loop_observed([1, 2, 3, 4]))
        result = replay.paired_interval({'a': False, 'b': False}, {'a': True, 'b': True}, 100)
        self.assertEqual((result['delta'], result['low'], result['high']), (1, 1, 1))
        with self.assertRaises(ValueError):
            replay.paired_interval({'a': True}, {'b': True})

    def test_cost_keeps_retention_decode_restore_and_compile(self):
        costs = replay.cost_estimate(1, 2, 3, 12, 3, .5, 20, 30, 2)
        self.assertEqual(costs['updates'], 568)
        self.assertEqual(costs['retention_scores'], 420)
        self.assertEqual(costs['four_compile_warmups'], 120)
        self.assertEqual(costs['greedy_answers'], 452)
        with self.assertRaises(ValueError):
            replay.cost_estimate(float('nan'), 0, 0, 0, 0, 0, 0, 0, 0)


class StateTests(unittest.TestCase):
    def setUp(self):
        import torch
        from tinylm.train.muon import Muon
        torch.manual_seed(15)
        self.torch = torch
        self.model = torch.nn.Linear(4, 4)
        self.opt = (torch.optim.AdamW([self.model.bias], lr=1e-3),
                    Muon([self.model.weight], lr=4e-3, scale_mode="rms"))

    def step(self):
        for opt in self.opt:
            opt.zero_grad(set_to_none=True)
        y = self.model(self.torch.randn(3, 4)).square().sum()
        y.backward()
        self.torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1)
        for opt in self.opt:
            opt.step()

    def test_restore_actual_adam_muon_rng_replays_bitwise(self):
        initial = replay.snapshot(self.model, self.opt)
        hashes = []
        for _ in range(2):
            replay.restore(self.model, self.opt, initial)
            self.step()
            state = replay.snapshot(self.model, self.opt)
            hashes.append(replay.tree_hash(state))
        self.assertEqual(hashes[0], hashes[1])

    def test_snapshot_is_deep_and_moments_restored(self):
        self.step()
        saved = replay.snapshot(self.model, self.opt)
        original_hash = replay.tree_hash(saved)
        self.step()
        self.assertEqual(replay.tree_hash(saved), original_hash)
        replay.restore(self.model, self.opt, saved)
        self.assertEqual(replay.tree_hash(replay.snapshot(self.model, self.opt)), original_hash)

    def test_duplicate_optimizer_parameter_rejected(self):
        extra = self.torch.optim.SGD([self.model.weight], lr=.1)
        with self.assertRaisesRegex(ValueError, "duplicated"):
            replay.ownership(self.model, (*self.opt, extra))

    def test_fixed_denominator_zero_weight_not_renormalized(self):
        torch = self.torch
        logits = torch.randn(2, 3, 5, requires_grad=True)
        targets = torch.tensor([[1, 2, -100], [3, 4, 1]])
        got = replay.weighted_ce(logits, targets, [0, 1], 5)
        expected = torch.nn.functional.cross_entropy(logits[1], targets[1], reduction="sum")/5
        self.assertTrue(torch.allclose(got, expected))
        grads = torch.autograd.grad(got, logits)[0]
        self.assertEqual(int(torch.count_nonzero(grads[0])), 0)
        self.assertGreater(int(torch.count_nonzero(grads[1])), 0)

    def test_serial_weighted_micro_grad_matches_whole_before_clipping(self):
        torch = self.torch
        a = torch.randn(4, 3, 5, requires_grad=True)
        y = torch.tensor([[1,2,-100],[2,1,0],[1,-100,-100],[3,2,1]])
        denominator = int((y!=-100).sum())
        whole = replay.weighted_ce(a, y, [1,0,1,1], denominator)
        first = replay.weighted_ce(a[:2], y[:2], [1,0], denominator)
        second = replay.weighted_ce(a[2:], y[2:], [1,1], denominator)
        g0 = torch.autograd.grad(whole, a, retain_graph=True)[0]
        g1 = torch.autograd.grad(first+second, a)[0]
        self.assertTrue(torch.allclose(g0, g1, atol=1e-7, rtol=1e-6))

    def test_zero_gradient_and_none_gradient_are_distinct(self):
        self.step()
        initial = replay.snapshot(self.model, self.opt)
        for parameter in self.model.parameters():
            parameter.grad = self.torch.zeros_like(parameter)
        for opt in self.opt:
            opt.step()
        with_zero = replay.tree_hash(self.model.state_dict())
        replay.restore(self.model, self.opt, initial)
        for parameter in self.model.parameters():
            parameter.grad = None
        for opt in self.opt:
            opt.step()
        with_none = replay.tree_hash(self.model.state_dict())
        self.assertNotEqual(with_zero, with_none)


if __name__ == "__main__":
    unittest.main()
