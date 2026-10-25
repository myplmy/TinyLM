"""TinyLM-adapted NorMuon의 CPU 텐서 계약. 전체 모델ㆍ자료ㆍCUDA 실행 없음."""
from __future__ import annotations

import copy
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from tinylm.train import muon as base
from tinylm.train import normuon as candidate
from tinylm.model.ternary import _TernarySTE


def matrix(shape, seed=7, *, dtype=torch.float32):
    generator = torch.Generator(device="cpu").manual_seed(seed)
    return torch.randn(shape, generator=generator, device="cpu", dtype=dtype) * 0.1


def row_oracle(values, old_v, beta2, eps):
    """작은 행렬만 받는 독립 Python/FP64 수식 oracle. 제품 helper 복제 아님."""
    rows = values.double().tolist()
    next_v = [beta2 * float(v) + (1 - beta2) * math.fsum(x * x for x in row) / len(row)
              for row, v in zip(rows, old_v.flatten().double().tolist())]
    normalized = [[x / (math.sqrt(v) + eps) for x in row]
                  for row, v in zip(rows, next_v)]
    before = math.sqrt(math.fsum(x * x for row in rows for x in row))
    after = math.sqrt(math.fsum(x * x for row in normalized for x in row))
    restored = [[x * before / (after + eps) for x in row] for row in normalized]
    return (torch.tensor(restored, dtype=torch.float32, device="cpu"),
            torch.tensor(next_v, dtype=torch.float32, device="cpu").unsqueeze(1))


class NorMuonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        cls.cuda_guard = patch("torch.cuda._lazy_init", side_effect=AssertionError("CUDA 금지"))
        cls.cuda_mock = cls.cuda_guard.start()
        cls.seed_guard = patch("torch.cuda.manual_seed_all", side_effect=AssertionError("CUDA seed 금지"))
        cls.seed_guard.start()

    @classmethod
    def tearDownClass(cls):
        cls.seed_guard.stop()
        cls.cuda_guard.stop()
        torch.set_num_threads(cls.previous_threads)
        if cls.cuda_mock.call_count:
            raise AssertionError("CUDA 초기화 호출이 있었다.")

    def close(self, actual, expected):
        # 독립 FP64 수식과 FP32 축약의 반올림만 허용하는 단위시험이다.
        torch.testing.assert_close(actual, expected, atol=2e-7, rtol=2e-6)

    def test_reuses_existing_helpers(self):
        self.assertIs(candidate._newton_schulz, base._newton_schulz)
        self.assertIs(candidate.update_scale, base.update_scale)
        self.assertIs(candidate.split_params, base.split_params)
        self.assertIs(candidate.NorMuon.scale_table, base.Muon.scale_table)

    def test_independent_row_math_and_input_nonmutation(self):
        values = torch.tensor([[3., 4.], [0., 2.]], device="cpu")
        original = values.clone()
        state = torch.tensor([[0.5], [3.]], dtype=torch.float32)
        expected, expected_v = row_oracle(values, state, .8, 1e-10)
        result = candidate._row_normalize(values, state, .8, 1e-10)
        self.close(result, expected)
        self.close(state, expected_v)
        self.assertTrue(torch.equal(values, original))
        self.close(result.norm(), original.norm())
        self.assertFalse(torch.allclose(result, original))

    def test_first_step_equal_row_norms_and_zero_row(self):
        for values in (torch.tensor([[3., 4.], [0., 2.]]),
                       torch.tensor([[0., 0.], [3., 4.]])):
            with self.subTest(values=values.tolist()):
                state = torch.zeros(2, 1)
                result = candidate._row_normalize(values, state, .95, 1e-10)
                self.close(result.norm(), values.norm())
                if bool(values[0].any()):
                    self.close(result[0].norm(), result[1].norm())
                else:
                    self.assertTrue(torch.equal(result[0], values[0]))

    def test_three_shapes_two_scales_nesterov_and_multistep_oracle(self):
        for shape in ((3, 3), (3, 5), (5, 3)):
            for mode in ("jordan", "rms"):
                for nesterov in (False, True):
                    with self.subTest(shape=shape, mode=mode, nesterov=nesterov):
                        parameter = torch.nn.Parameter(matrix(shape))
                        optimizer = candidate.NorMuon([parameter], lr=.012, momentum=.8,
                            beta2=.7, eps=1e-8, weight_decay=.13,
                            scale_mode=mode, nesterov=nesterov)
                        expected = parameter.detach().clone()
                        buf = torch.zeros_like(parameter)
                        row_v = torch.zeros(shape[0], 1)
                        for step in range(4):
                            grad = matrix(shape, seed=30 + step)
                            source = grad.clone()
                            # 기존 Muon prefix와 NS helper는 의도적으로 같은 것을 사용한다.
                            buf.mul_(.8).add_(grad)
                            direction = grad.add(buf, alpha=.8) if nesterov else buf
                            orthogonal = base._newton_schulz(direction, steps=5)
                            update, row_v = row_oracle(orthogonal, row_v, .7, 1e-8)
                            expected.mul_(1 - .012 * .13)
                            expected.add_(update, alpha=-.012 * base.update_scale(*shape, mode))
                            parameter.grad = grad
                            optimizer.step()
                            self.close(parameter, expected)
                            self.assertTrue(torch.equal(parameter.grad, source))
                            self.assertIs(parameter.grad, grad)
                            self.assertTrue(torch.equal(optimizer.state[parameter]["buf"], buf))
                            self.close(optimizer.state[parameter]["row_v"], row_v)

    def test_none_creates_no_state_and_applies_no_decay(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        before = parameter.detach().clone()
        optimizer = candidate.NorMuon([parameter], weight_decay=.5)
        optimizer.step()
        self.assertTrue(torch.equal(parameter, before))
        self.assertIsNone(parameter.grad)
        self.assertEqual(len(optimizer.state), 0)

    def test_zero_initial_gradient_only_decays_weight(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        before = parameter.detach().clone()
        optimizer = candidate.NorMuon([parameter], lr=.1, weight_decay=.2)
        parameter.grad = torch.zeros_like(parameter)
        optimizer.step()
        self.assertTrue(torch.equal(parameter, before * .98))
        self.assertTrue(torch.equal(optimizer.state[parameter]["buf"], parameter.grad))
        self.assertEqual(int(torch.count_nonzero(optimizer.state[parameter]["row_v"])), 0)

    def test_history_then_none_is_frozen_but_zero_continues_momentum(self):
        parameter = torch.nn.Parameter(matrix((3, 5)))
        optimizer = candidate.NorMuon([parameter], lr=.02, weight_decay=.2)
        parameter.grad = matrix((3, 5), seed=21)
        optimizer.step()
        before, saved = parameter.detach().clone(), copy.deepcopy(optimizer.state[parameter])
        parameter.grad = None
        optimizer.step()
        self.assertTrue(torch.equal(parameter, before))
        for key in saved:
            self.assertTrue(torch.equal(optimizer.state[parameter][key], saved[key]))
        parameter.grad = torch.zeros_like(parameter)
        optimizer.step()
        self.assertFalse(torch.equal(parameter, before))
        self.close(optimizer.state[parameter]["buf"], saved["buf"] * .95)
        self.assertEqual(int(torch.count_nonzero(parameter.grad)), 0)

    def test_weight_decay_order(self):
        left = torch.nn.Parameter(matrix((2, 3)))
        right = torch.nn.Parameter(left.detach().clone())
        a = candidate.NorMuon([left], lr=.02, weight_decay=0.)
        b = candidate.NorMuon([right], lr=.02, weight_decay=.3)
        initial = left.detach().clone()
        left.grad = matrix((2, 3), seed=22)
        right.grad = left.grad.clone()
        a.step()
        b.step()
        self.close(right, left.detach() - initial * (.02 * .3))

    def test_duplicate_parameter_is_rejected(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        with self.assertRaisesRegex(ValueError, "물리 파라미터"):
            candidate.NorMuon([parameter, parameter])
        optimizer = candidate.NorMuon([parameter])
        with self.assertRaisesRegex(ValueError, "물리 파라미터"):
            optimizer.add_param_group({"params": [parameter]})
        optimizer.param_groups[0]["params"].append(parameter)
        parameter.grad = torch.ones_like(parameter)
        before = parameter.detach().clone()
        with self.assertRaisesRegex(ValueError, "중복"):
            optimizer.step()
        self.assertTrue(torch.equal(parameter, before))
        self.assertEqual(len(optimizer.state), 0)

    def test_shared_parameter_is_updated_once_after_gradient_sum(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        embedding = torch.nn.Embedding.from_pretrained(torch.ones(2, 3), freeze=False)
        norm = torch.nn.Parameter(torch.ones(3))

        class RoutingFixture:
            def modules(self):
                return (embedding,)

            def parameters(self):
                return iter((parameter, parameter, embedding.weight, norm))

        matrices, others = candidate.split_params(RoutingFixture())
        self.assertEqual([id(p) for p in matrices], [id(parameter)])
        self.assertEqual({id(p) for p in others}, {id(embedding.weight), id(norm)})
        x, y = matrix((2, 3), seed=40), matrix((2, 3), seed=41)
        ((parameter * x).sum() + (parameter * y).sum()).backward()
        self.assertTrue(torch.equal(parameter.grad, x + y))
        reference = torch.nn.Parameter(parameter.detach().clone())
        reference.grad = parameter.grad.clone()
        actual_opt = candidate.NorMuon(matrices)
        reference_opt = candidate.NorMuon([reference])
        actual_opt.step()
        reference_opt.step()
        self.assertTrue(torch.equal(parameter, reference))
        self.assertEqual(len(actual_opt.state), 1)
        for key in ("buf", "row_v"):
            self.assertTrue(torch.equal(actual_opt.state[parameter][key], reference_opt.state[reference][key]))

    def test_actual_ste_damped_gradient_is_preserved(self):
        parameter = torch.nn.Parameter(torch.tensor([[.1, -.4, .3, -.2], [.2, .6, -.1, -.5]]))
        upstream = torch.tensor([[.2, -.1, .4, .3], [-.3, .5, -.2, .1]])
        quantized = _TernarySTE.apply(parameter, 2, .7, 1., False)
        (quantized * upstream).sum().backward()
        grad = parameter.grad.clone()
        self.assertTrue(bool((grad.abs() < upstream.abs()).all()))
        values = parameter.detach().reshape(2, 2, 2).double().abs()
        mask = values >= .7 * values.mean(dim=2, keepdim=True)
        alpha = (values * mask).sum(dim=2, keepdim=True) / mask.sum(dim=2, keepdim=True).clamp_min(1)
        expected = upstream.double().reshape(2, 2, 2) / (1 + (values / alpha.clamp_min(1e-8)).pow(4))
        self.close(grad, expected.reshape_as(parameter).float())
        reference = torch.nn.Parameter(parameter.detach().clone())
        reference.grad = grad.clone()
        a, b = candidate.NorMuon([parameter]), candidate.NorMuon([reference])
        a.step()
        b.step()
        self.assertTrue(torch.equal(parameter, reference))
        self.assertTrue(torch.equal(parameter.grad, grad))
        self.assertEqual(parameter.dtype, torch.float32)

    def test_state_dict_resume_matches_uninterrupted(self):
        for dtype in (torch.float32, torch.bfloat16):
            with self.subTest(dtype=dtype):
                parameter = torch.nn.Parameter(matrix((3, 5), dtype=dtype))
                optimizer = candidate.NorMuon([parameter], lr=.013, beta2=.73, eps=1e-8,
                                             scale_mode="rms", weight_decay=.2)
                parameter.grad = matrix((3, 5), seed=30, dtype=dtype)
                optimizer.step()
                state = copy.deepcopy(optimizer.state_dict())
                resumed = torch.nn.Parameter(parameter.detach().clone())
                second = candidate.NorMuon([resumed])
                second.load_state_dict(state)
                self.assertEqual(second.state[resumed]["row_v"].dtype, torch.float32)
                self.assertTrue(torch.equal(second.state[resumed]["row_v"], state["state"][0]["row_v"]))
                for step in range(3):
                    grad = matrix((3, 5), seed=31 + step, dtype=dtype)
                    parameter.grad, resumed.grad = grad.clone(), grad.clone()
                    optimizer.step()
                    second.step()
                    self.assertTrue(torch.equal(parameter, resumed))
                    for key in ("buf", "row_v"):
                        self.assertTrue(torch.equal(optimizer.state[parameter][key], second.state[resumed][key]))
                self.assertFalse(torch.equal(state["state"][0]["row_v"], optimizer.state_dict()["state"][0]["row_v"]))

    def test_bad_beta2_eps_and_other_options_rejected(self):
        for key, values in {"beta2": (-.1, 1., float("nan"), float("inf"), True),
                            "eps": (0., -1., 1e-100, 1e100, float("nan"), True),
                            "lr": (-1., float("inf")), "momentum": (1., -.1),
                            "weight_decay": (-1.,), "ns_steps": (0, 1.5, True),
                            "scale_mode": ("other",)}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    candidate.NorMuon([torch.nn.Parameter(torch.ones(2, 3))], **{key: value})
        for key in ("beta2", "eps"):
            with self.subTest(hidden_default=key), self.assertRaises(ValueError):
                candidate.NorMuon([{"params": [torch.nn.Parameter(torch.ones(2, 3))],
                                    "beta2": .9, "eps": 1e-8}], **{key: float("nan")})

    def test_only_nonempty_floating_dense_2d_parameters(self):
        for tensor in (torch.ones(3), torch.ones(2, 2, 2), torch.ones(0, 2),
                       torch.ones(2, 2, dtype=torch.complex64)):
            with self.subTest(shape=tuple(tensor.shape)), self.assertRaises(ValueError):
                candidate.NorMuon([torch.nn.Parameter(tensor)])

    def test_group_overrides_and_added_group(self):
        p, q = torch.nn.Parameter(torch.ones(2, 3)), torch.nn.Parameter(torch.ones(3, 2))
        optimizer = candidate.NorMuon([{"params": [p], "beta2": .6, "eps": 1e-7}], beta2=.8)
        optimizer.add_param_group({"params": [q]})
        self.assertEqual(optimizer.param_groups[0]["beta2"], .6)
        self.assertEqual(optimizer.param_groups[1]["beta2"], .8)
        p.grad, q.grad = torch.ones_like(p), torch.ones_like(q)
        optimizer.step()
        self.assertEqual(len(optimizer.state), 2)

    def test_nonfinite_gradient_preflight_changes_nothing(self):
        for value in (float("nan"), float("inf")):
            p, q = torch.nn.Parameter(matrix((2, 3))), torch.nn.Parameter(matrix((2, 3)))
            before = p.detach().clone()
            optimizer = candidate.NorMuon([p, q])
            p.grad, q.grad = torch.ones_like(p), torch.full_like(q, value)
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, "학습 중단"):
                optimizer.step()
            self.assertTrue(torch.equal(p, before))
            self.assertEqual(len(optimizer.state), 0)

    def test_nonfinite_weight_and_sparse_gradient_are_rejected(self):
        for bad in ("weight", "sparse_gradient"):
            p, q = torch.nn.Parameter(matrix((2, 3))), torch.nn.Parameter(matrix((2, 3)))
            optimizer = candidate.NorMuon([p, q])
            p.grad, q.grad = torch.ones_like(p), torch.ones_like(q)
            before = p.detach().clone()
            if bad == "weight":
                with torch.no_grad():
                    q[0, 0] = float("inf")
            else:
                q.grad = torch.sparse_coo_tensor(torch.tensor([[0], [1]]),
                                                 torch.tensor([1.]), (2, 3))
            with self.subTest(bad=bad), self.assertRaises((ValueError, RuntimeError)):
                optimizer.step()
            self.assertTrue(torch.equal(p, before))
            self.assertEqual(len(optimizer.state), 0)

    def test_bad_state_rejected_before_updates(self):
        for bad in ("shape", "dtype", "negative", "nan", "missing", "momentum_shape"):
            parameter = torch.nn.Parameter(matrix((2, 3)))
            optimizer = candidate.NorMuon([parameter])
            parameter.grad = torch.ones_like(parameter)
            optimizer.step()
            before = parameter.detach().clone()
            state = optimizer.state[parameter]
            if bad == "shape":
                state["row_v"] = torch.zeros(2)
            elif bad == "dtype":
                state["row_v"] = state["row_v"].to(torch.bfloat16)
            elif bad == "negative":
                state["row_v"][0, 0] = -1
            elif bad == "nan":
                state["row_v"][0, 0] = float("nan")
            elif bad == "missing":
                del state["row_v"]
            else:
                state["buf"] = torch.zeros(3, 2)
            with self.subTest(bad=bad), self.assertRaises((ValueError, RuntimeError)):
                optimizer.step()
            self.assertTrue(torch.equal(parameter, before))

    def test_bad_load_does_not_replace_current_state(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        optimizer = candidate.NorMuon([parameter])
        parameter.grad = torch.ones_like(parameter)
        optimizer.step()
        before = copy.deepcopy(optimizer.state_dict())
        broken = copy.deepcopy(before)
        broken["state"][0]["row_v"] = torch.zeros(3, 1)
        with self.assertRaises(ValueError):
            optimizer.load_state_dict(broken)
        self.assertTrue(torch.equal(optimizer.state[parameter]["row_v"], before["state"][0]["row_v"]))

    def test_legacy_muon_state_and_mutated_options_are_rejected(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        optimizer = candidate.NorMuon([parameter])
        original = base.Muon([parameter])
        with self.assertRaises(ValueError):
            optimizer.load_state_dict(original.state_dict())
        parameter.grad = torch.ones_like(parameter)
        optimizer.param_groups[0]["beta2"] = 1.
        before = parameter.detach().clone()
        with self.assertRaises(ValueError):
            optimizer.step()
        self.assertTrue(torch.equal(parameter, before))
        self.assertEqual(len(optimizer.state), 0)

    def test_nonfinite_ns_output_stops_before_weight_write(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        before = parameter.detach().clone()
        optimizer = candidate.NorMuon([parameter])
        parameter.grad = torch.ones_like(parameter)
        with patch.object(candidate, "_newton_schulz", return_value=torch.full((2, 3), float("nan"))):
            with self.assertRaisesRegex(RuntimeError, "NS 출력"):
                optimizer.step()
        self.assertTrue(torch.equal(parameter, before))

    def test_late_arithmetic_failure_is_not_global_rollback(self):
        p, q = torch.nn.Parameter(matrix((2, 3))), torch.nn.Parameter(matrix((2, 3)))
        optimizer = candidate.NorMuon([p, q])
        maximum = torch.finfo(torch.float32).max
        optimizer.state[q] = {"buf": torch.full_like(q, maximum), "row_v": torch.zeros(2, 1)}
        p.grad, q.grad = torch.ones_like(p), torch.full_like(q, maximum)
        p_before, q_before = p.detach().clone(), q.detach().clone()
        with self.assertRaisesRegex(RuntimeError, "모멘텀"):
            optimizer.step()
        self.assertFalse(torch.equal(p, p_before))
        self.assertTrue(torch.equal(q, q_before))
        # 이 객체는 정상 재개에 재사용하지 않는다. 총괄의 행렬별 중단 계약이다.

    def test_weight_overflow_guard_prevents_invalid_weight(self):
        parameter = torch.nn.Parameter(torch.full((2, 3), torch.finfo(torch.float32).max * .99))
        before = parameter.detach().clone()
        optimizer = candidate.NorMuon([parameter], lr=1e38)
        parameter.grad = -torch.ones_like(parameter)
        with self.assertRaisesRegex(RuntimeError, "overflow"):
            optimizer.step()
        self.assertTrue(torch.equal(parameter, before))

    def test_original_muon_stays_original(self):
        parameter = torch.nn.Parameter(matrix((2, 3)))
        expected = parameter.detach().clone()
        gradient = matrix((2, 3), seed=50)
        original_ns = base._newton_schulz
        optimizer = base.Muon([parameter], lr=.02, scale_mode="rms", weight_decay=.1)
        parameter.grad = gradient.clone()
        buf = gradient.clone()
        direction = gradient.add(buf, alpha=.95)
        expected.mul_(1 - .02 * .1)
        expected.add_(original_ns(direction), alpha=-.02 * base.update_scale(2, 3, "rms"))
        optimizer.step()
        self.assertTrue(torch.equal(parameter, expected))
        self.assertTrue(torch.equal(parameter.grad, gradient))
        self.assertNotIn("row_v", optimizer.state[parameter])
        self.assertIs(base._newton_schulz, original_ns)

    def test_cpu_rng_is_not_consumed(self):
        before = torch.get_rng_state().clone()
        parameter = torch.nn.Parameter(matrix((2, 3)))
        parameter.grad = matrix((2, 3), seed=60)
        candidate.NorMuon([parameter]).step()
        self.assertTrue(torch.equal(torch.get_rng_state(), before))


if __name__ == "__main__":
    unittest.main(verbosity=2)
