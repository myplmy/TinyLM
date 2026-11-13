"""Meaningful CPU algebra, native realization and rollback checks; no assets."""
import copy
import unittest

import torch

from scripts import p108_native_scale as n
from scripts import p108_weight_space as old
from scripts import p108_native_practice as data
from scripts.p106b_weight_route import weight_route
from scripts.test_p108_weight_space import fixture


class NativeAlgebra(unittest.TestCase):
    def setUp(self):
        self.w = torch.tensor([[1., -1., -0., 2.], [-.5, 0., 1., -1.]])

    def test_projection_has_fixed_scales_and_discrete_values(self):
        delta = torch.tensor([[-2., .7, 1.8, -1.3], [.8, -.4, -.6, .7]])
        target = n.project(self.w, delta, 2, allow_zero=True)
        self.assertTrue(torch.equal(target, torch.tensor([[-1., 0., 2., 0.], [.5, -.5, 0., 0.]])))
        n.transitions(self.w, target, 2)

    def test_sign_policy_keeps_mask_and_magnitude(self):
        target = n.project(self.w, -3 * self.w + 5 * (self.w == 0), 2, allow_zero=False)
        self.assertTrue(torch.equal(target.abs(), self.w.abs()))
        self.assertTrue(torch.equal(target[self.w != 0], -self.w[self.w != 0]))
        self.assertTrue(torch.equal(target == 0, self.w == 0))

    def test_noop_preserves_signed_zero_bytes(self):
        for zero in (False, True):
            target = n.project(self.w, torch.zeros_like(self.w), 2, allow_zero=zero)
            self.assertEqual(old.tensor_sha(target), old.tensor_sha(self.w))

    def test_outside_requested_support_is_unchanged(self):
        delta = torch.zeros_like(self.w); delta[0, 0] = -4
        target = n.project(self.w, delta, 2, allow_zero=True)
        self.assertEqual(int(((target != self.w) & (delta == 0)).sum()), 0)

    def test_nonternary_matrix_rejected(self):
        with self.assertRaises(ValueError): n.layout(torch.tensor([[1., .7]]), 2)

    def test_invalid_dtype_group_and_delta_rejected(self):
        for group in (0, -2, 3, True):
            with self.assertRaises(ValueError): n.layout(self.w, group)
        with self.assertRaises(ValueError): n.layout(self.w.double(), 2)
        bad = torch.zeros_like(self.w); bad[0, 0] = float('nan')
        with self.assertRaises(ValueError): n.project(self.w, bad, 2, allow_zero=True)

    def test_packet_exact_roundtrip_and_origin_binding(self):
        target = n.project(self.w, -2 * self.w, 2, allow_zero=True)
        packet = n.packet(self.w, target, 2)
        self.assertEqual(old.tensor_sha(n.unpack(self.w, packet)), old.tensor_sha(target))
        with self.assertRaises(ValueError): n.unpack(-self.w, packet)
        bad = copy.deepcopy(packet); bad['scales_sha256'] = '0' * 64
        with self.assertRaises(ValueError): n.unpack(self.w, bad)

    def test_packet_rejects_duplicate_and_nonternary_code(self):
        target = n.project(self.w, -2 * self.w, 2, allow_zero=True)
        packet = n.packet(self.w, target, 2)
        bad = copy.deepcopy(packet); bad['indices'][1] = bad['indices'][0]
        with self.assertRaises(ValueError): n.unpack(self.w, bad)
        bad = copy.deepcopy(packet); bad['codes'][0] = 2
        with self.assertRaises(ValueError): n.unpack(self.w, bad)

    def test_zero_scale_cannot_be_unmasked(self):
        w = torch.zeros(1, 4)
        with self.assertRaises(ValueError): n.from_codes(w, torch.ones(1, 1, 4, dtype=torch.int8), 4)

    def test_random_control_preserves_group_transition_histogram(self):
        codes = torch.tensor([-1., 0., 1., 1., -1., 0., 1., -1.]).repeat(8, 1)
        w = codes * torch.arange(1, 9, dtype=torch.float32)[:, None]
        delta = torch.zeros_like(w)
        delta[:, 0] = -2 * w[:, 0]
        delta[:, 2] = -w[:, 2]
        target = n.project(w, delta, 8, allow_zero=True)
        a = n.random_control(w, target, 8, 17)
        b = n.random_control(w, target, 8, 17)
        self.assertTrue(torch.equal(a, b))
        self.assertTrue(torch.equal(n.transitions(w, a, 8), n.transitions(w, target, 8)))
        self.assertFalse(torch.equal(a, target))
        torch.testing.assert_close((a - w).norm(), (target - w).norm())


class NativeRealization(unittest.TestCase):
    def prepared(self, model, layer, mode):
        module = (model.a, model.b)[layer]
        group = module.cfg.micro_group or module.weight.shape[1]
        delta = -2 * module._wq.detach()
        target = n.project(module._wq.detach(), delta, group, allow_zero=mode == 'codes')
        return layer, n.packet(module._wq.detach(), target, group)

    def test_sign_requantizes_exactly_and_restores(self):
        model = fixture()
        with weight_route(model, 'ternary') as route, torch.no_grad():
            model.freeze_quant()
            master, cache = model.a.weight.clone(), model.a._wq
            edit = self.prepared(model, 0, 'sign')
            with n.apply(model, route, [edit], 'sign') as receipts:
                self.assertGreater(receipts[0]['changed'], 0)
                self.assertEqual(receipts[0]['changed_outside_requested'], 0)
                self.assertTrue(torch.equal(model.a.weight.abs(), master.abs()))
                self.assertFalse(torch.equal(model.a(torch.ones(1, 2)), torch.nn.functional.linear(torch.ones(1, 2), cache)))
            self.assertEqual(old.tensor_sha(model.a.weight), old.tensor_sha(master))
            self.assertIs(model.a._wq, cache)

    def test_codes_leave_master_unchanged_and_restore_cache(self):
        model = fixture()
        with weight_route(model, 'ternary') as route, torch.no_grad():
            model.freeze_quant()
            master, cache = model.a.weight.clone(), model.a._wq
            with n.apply(model, route, [self.prepared(model, 0, 'codes')], 'codes') as receipts:
                self.assertEqual(receipts[0]['latent_changed'], 0)
                self.assertEqual(old.tensor_sha(model.a.weight), old.tensor_sha(master))
            self.assertIs(model.a._wq, cache)

    def test_exception_restores_both_layers(self):
        model = fixture()
        with weight_route(model, 'ternary') as route, torch.no_grad():
            model.freeze_quant()
            before = [(m.weight.clone(), m._wq) for m in (model.a, model.b)]
            with self.assertRaisesRegex(RuntimeError, 'fixture stop'):
                with n.apply(model, route, [self.prepared(model, j, 'sign') for j in (0, 1)], 'sign'):
                    raise RuntimeError('fixture stop')
            for module, (master, cache) in zip((model.a, model.b), before):
                self.assertEqual(old.tensor_sha(module.weight), old.tensor_sha(master))
                self.assertIs(module._wq, cache)

    def test_all_packets_validated_before_any_mutation(self):
        model = fixture()
        with weight_route(model, 'ternary') as route, torch.no_grad():
            model.freeze_quant(); before = old.tensor_sha(model.a.weight)
            bad = self.prepared(model, 1, 'sign'); bad[1]['target_sha256'] = '0' * 64
            with self.assertRaises(ValueError):
                with n.apply(model, route, [self.prepared(model, 0, 'sign'), bad], 'sign'): pass
            self.assertEqual(old.tensor_sha(model.a.weight), before)

    def test_noop_keeps_cache_identity(self):
        model = fixture()
        with weight_route(model, 'ternary') as route, torch.no_grad():
            model.freeze_quant(); cache = model.a._wq
            packet = n.packet(cache, cache.clone(), model.a.cfg.micro_group)
            with n.apply(model, route, [(0, packet)], 'codes'):
                self.assertIs(model.a._wq, cache)


class Practice(unittest.TestCase):
    def test_data_counts_source_split_and_boolean_balance(self):
        rows = data.make_data()
        self.assertEqual(data.validate(rows)['counts'], {'dev': 128, 'test': 256, 'open_seen': 16, 'open_fresh': 16})

    def test_rule_numeric_answers_and_strict_scoring(self):
        for row in data.make_data():
            if row['family'] == 'arithmetic':
                self.assertEqual(row['expected'], str(row['rule']['a'] + row['rule']['b']))
            if row['expected'] is not None:
                self.assertTrue(data.strict_score(dict(row, answer=row['expected'])))
                self.assertFalse(data.strict_score(dict(row, answer='Question: ' + row['expected'])))


class Protocol(unittest.TestCase):
    def test_candidate_identity_is_independent_of_layer_order(self):
        from scripts.diag_p108_native_scale import identity
        packets = [(11, {'target_sha256': 'a'}), (10, {'target_sha256': 'b'})]
        self.assertEqual(identity(packets), identity(list(reversed(packets))))

    def test_noop_identity_matches_original_and_nonzero_is_distinct(self):
        from scripts.diag_p108_native_scale import identity
        original = [(10, {'target_sha256': 'a'}), (11, {'target_sha256': 'b'})]
        changed = [(10, {'target_sha256': 'a'}), (11, {'target_sha256': 'c'})]
        self.assertNotEqual(identity(original), identity(changed))

    def test_completed_phase_budget_is_rejected(self):
        from scripts.diag_p108_native_scale import Budget
        with self.assertRaises(TimeoutError): Budget({'max_phase_seconds': 0}).check()

    def test_selection_prioritizes_exact_then_protected(self):
        from scripts.diag_p108_native_scale import score_key
        a = dict(exact=1, protected_exact=0, empty=0, question_echoes=0, loop_indicators=0)
        b = dict(a, exact=2, loop_indicators=100)
        self.assertLess(score_key(b), score_key(a))
        self.assertLess(score_key(dict(a, protected_exact=1)), score_key(a))


if __name__ == '__main__':
    unittest.main()
