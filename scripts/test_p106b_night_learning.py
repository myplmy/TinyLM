"""CPU-only loss, causal alignment, denominator and pairing regression."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import torch
import torch.nn.functional as F
from scripts import p106b_night_learning as m
from tinylm.train.mtp_sft import Record


class Toy(torch.nn.Module):
    def __init__(self):
        super().__init__(); self.head = torch.nn.Linear(3, 7, bias=False)
    def _head_logits(self, x):
        return self.head(x)


def rec(prefix=2, targets=(2, 3, 4)):
    y = [-100] * prefix + list(targets)
    return Record([1] * len(y), y, [0] * prefix + [1] * len(targets))


class NightLearning(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(13)

    def test_identical_zero(self):
        x = torch.randn(4, 7, requires_grad=True)
        y = m.symmetric_kl(x, x)
        self.assertTrue(torch.equal(y, torch.zeros_like(y)))
        y.sum().backward(); self.assertTrue(torch.equal(x.grad, torch.zeros_like(x)))

    def test_formula_and_symmetry(self):
        x = torch.randn(3, 7, requires_grad=True); y = torch.randn(3, 7, requires_grad=True)
        px = x.softmax(-1); py = y.softmax(-1)
        expected = .5 * ((px * (px.log() - py.log())).sum(-1)
                         + (py * (py.log() - px.log())).sum(-1))
        self.assertTrue(torch.allclose(m.symmetric_kl(x, y), expected, atol=2e-7))
        self.assertTrue(torch.allclose(m.symmetric_kl(x, y), m.symmetric_kl(y, x)))
        m.symmetric_kl(x, y).sum().backward()
        self.assertGreater(float(x.grad.abs().sum()), 0)
        self.assertGreater(float(y.grad.abs().sum()), 0)

    def test_vocab_sum_not_mean(self):
        x = torch.tensor([[3., 0., -1.]])
        y = torch.tensor([[-1., 0., 3.]])
        actual = m.symmetric_kl(x, y)
        wrong = .5 * ((x.softmax(-1) - y.softmax(-1)) * (x.log_softmax(-1) - y.log_softmax(-1))).mean(-1)
        self.assertTrue(torch.allclose(actual, 3 * wrong))

    def test_own_shifted_positions(self):
        a, b = rec(2), rec(5)
        value = m.paired_positions([a, b], 4)[0]
        self.assertEqual(value[1], [2, 3, 4]); self.assertEqual(value[3], [5, 6, 7])

    def test_different_gold_refused(self):
        with self.assertRaises(ValueError): m.paired_positions([rec(), rec(targets=(2, 1, 4))], 4)

    def test_multiturn_refused(self):
        a, b = rec(), rec(); b.segments[-1] = 2
        with self.assertRaises(ValueError): m.paired_positions([a, b], 4)

    def test_nonterminal_eot_refused(self):
        with self.assertRaises(ValueError): m.paired_positions([rec(targets=(4, 3, 4))] * 2, 4)

    def test_eot_ce_not_kl(self):
        a = torch.randn(3, 7); b = torch.randn(3, 7)
        t = torch.tensor([2, 3, 4]); first = m.pair_statistics(a, b, t)
        b[-1] += torch.tensor([9., -4., 2., -2., 7., 3., 1.])
        second = m.pair_statistics(a, b, t)
        self.assertNotEqual(float(first[0]), float(second[0]))
        self.assertTrue(torch.equal(first[1:], second[1:]))

    def test_valid_mass_only(self):
        model = Toy(); hidden = torch.randn(2, 8, 3, requires_grad=True)
        a, b = rec(2), rec(5)
        values, n, pairs = m.natural_sums(model, hidden, [a, b], 4, False)
        self.assertEqual((n, pairs), (2, 1))
        expected = m.pair_statistics(model.head(hidden[0, [2, 3, 4]]),
                                     model.head(hidden[1, [5, 6, 7]]), torch.tensor([2, 3, 4]))
        self.assertTrue(torch.allclose(values, expected))
        values.sum().backward()
        self.assertEqual(float(hidden.grad[0, :2].abs().sum()), 0)
        self.assertEqual(float(hidden.grad[1, :5].abs().sum()), 0)

    def test_checkpoint_gradient_parity(self):
        model = Toy(); h = torch.randn(2, 8, 3, requires_grad=True)
        a, b = rec(2), rec(5)
        v, _, _ = m.natural_sums(model, h, [a, b], 4, False)
        (v[0] + .05 * v[1]).backward(); expected_h = h.grad.clone(); expected_w = model.head.weight.grad.clone()
        h.grad = None; model.zero_grad()
        v, _, _ = m.natural_sums(model, h, [a, b], 4, True)
        (v[0] + .05 * v[1]).backward()
        self.assertTrue(torch.allclose(h.grad, expected_h, atol=1e-6))
        self.assertTrue(torch.allclose(model.head.weight.grad, expected_w, atol=1e-6))

    def test_multiple_pairs_and_lengths_checkpoint_parity(self):
        model = Toy(); h = torch.randn(8, 12, 3, requires_grad=True)
        records = [rec(p, tuple([2] * (i + 1) + [4])) for i in range(4) for p in (1, 3)]
        v, content, pairs = m.natural_sums(model, h, records, 4, False)
        (v[0] + .05 * v[1]).backward()
        gh = h.grad.clone(); gw = model.head.weight.grad.clone()
        h.grad = None; model.zero_grad()
        w, n, p = m.natural_sums(model, h, records, 4, True)
        (w[0] + .05 * w[1]).backward()
        self.assertEqual((content, pairs, n, p), (10, 4, 10, 4))
        self.assertTrue(torch.allclose(v, w, atol=1e-6))
        self.assertTrue(torch.allclose(h.grad, gh, atol=1e-6))
        self.assertTrue(torch.allclose(model.head.weight.grad, gw, atol=1e-6))

    def test_whole_update_normalization(self):
        a = torch.tensor(30., requires_grad=True); b = torch.tensor(10., requires_grad=True)
        loss = m.update_loss(a, 20, b, 5, .05)
        self.assertAlmostEqual(float(loss), 1.6, places=6)
        loss.backward(); self.assertAlmostEqual(float(a.grad), .05, places=7)
        self.assertAlmostEqual(float(b.grad), .01, places=7)

    def test_zero_weight_same_ce_gradient(self):
        a = torch.tensor(30., requires_grad=True); b = torch.tensor(10., requires_grad=True)
        loss = m.update_loss(a, 20, b, 5, 0.)
        loss.backward(); self.assertEqual(float(b.grad), 0.)
        self.assertAlmostEqual(float(a.grad), .05, places=7)

    def test_no_natural_micro_safe(self):
        a = torch.tensor(3., requires_grad=True); z = torch.tensor(0., requires_grad=True)
        self.assertEqual(float(m.update_loss(a, 3, z, 0, .05).detach()), 1.)

    def test_complete_atomic_schedule(self):
        result = m.schedule(8192, 4096, 0)
        self.assertEqual(len(result), 160); self.assertTrue(all(len(g) == 16 for g in result))
        natural = [i for g in result for b in g if b.kind == 'natural' for i in b.indices]
        replay = [i for g in result for b in g if b.kind == 'replay' for i in b.indices]
        self.assertEqual(sorted(natural), list(range(8192)))
        self.assertEqual(sorted(replay), list(range(4096)))
        self.assertEqual(result, m.schedule(8192, 4096, 0))
        self.assertNotEqual(result, m.schedule(8192, 4096, 1))

    def test_partial_schedule_refused(self):
        with self.assertRaises(ValueError): m.schedule(8, 8, 0)

    def test_qa_metric_scoped(self):
        self.assertEqual(m.qa_scores('The Eiffel tower.', ['Eiffel tower'], 'en')['em'], 1)
        self.assertEqual(m.qa_scores('서울 시', ['서울시'], 'ko')['em'], 1)
        self.assertEqual(m.qa_scores('1935', ['3층'], 'ko')['em'], 0)

    def test_numeric_sign_and_decimal_not_erased(self):
        for language in ('ko', 'en'):
            self.assertEqual(m.qa_scores('-5', ['5'], language)['em'], 0)
            self.assertEqual(m.qa_scores('1.5', ['15'], language)['em'], 0)
        self.assertEqual(m.qa_scores(' The Eiffel tower.', ['Eiffel tower'], 'en')['raw_exact'], 0)

    def test_cuda_never_initialized(self):
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__': unittest.main()
