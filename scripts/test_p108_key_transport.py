import unittest
import torch
from scripts import p108_key_transport as core
from scripts import p108_value_edit as value


class KeyTransportContracts(unittest.TestCase):
    def test_gain_angle_and_zero_response_are_separate(self):
        target = torch.tensor([3., 4.])
        r = core.response_geometry(target * 2, target)
        self.assertAlmostEqual(r['projection_gain'], 2.)
        self.assertAlmostEqual(r['norm_ratio'], 2.)
        self.assertAlmostEqual(r['cosine'], 1.)
        self.assertAlmostEqual(r['relative_residual'], 1.)
        self.assertIsNone(core.response_geometry(torch.zeros(2), target)['cosine'])

    def test_invalid_shape_nonfinite_and_zero_target_fail_closed(self):
        for a, b in ((torch.ones(2), torch.ones(3)), (torch.ones(2), torch.zeros(2)),
                     (torch.tensor([float('nan')]), torch.ones(1)),
                     (torch.ones(1, 2), torch.ones(1, 2))):
            with self.assertRaises(ValueError): core.response_geometry(a, b)

    def test_flags_allow_overlapping_mechanisms_and_no_truth_inference(self):
        r = core.evidence_flags(False, False, True, False)
        self.assertTrue(r['fixed_value_insufficient'])
        self.assertTrue(r['non_subject_loss'])
        self.assertFalse(r['key_response_loss'])
        self.assertTrue(core.evidence_flags(False, True, False, False)['key_response_loss'])
        with self.assertRaises(ValueError): core.evidence_flags(0, True, True, True)

    def test_real_matrix_response_and_token_only_intervention_differ_elsewhere(self):
        layer = torch.nn.Linear(3, 2, bias=False)
        x = torch.tensor([[[1., 2., 0.], [2., 0., 1.], [0., 3., 1.]]])
        delta = torch.tensor([[1., 0., 0.], [0., 1., 0.]])
        original = layer(x).detach()
        full = torch.nn.functional.linear(x, layer.weight.detach() + delta)
        response = full[0, 1] - original[0, 1]
        with value.inject(layer, 1, response): only = layer(x).detach()
        torch.testing.assert_close(only[:, 1], full[:, 1])
        torch.testing.assert_close(only[:, [0, 2]], original[:, [0, 2]])
        self.assertFalse(torch.equal(only[:, 0], full[:, 0]))


if __name__ == '__main__': unittest.main()
