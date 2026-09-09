import unittest
import torch
from scripts.diag_group_agg import group_geometry
from tinylm.config import TMTConfig, mlp_group_members
from tinylm.model.checkpoint_io import normalize_state_dict


class GroupTests(unittest.TestCase):
    def test_opposite_weights_cancel(self):
        w = torch.arange(1, 13).reshape(3, 4).float()
        result = group_geometry([w, -w])
        self.assertAlmostEqual(result["shrink_ratio"], 0)
        self.assertAlmostEqual(result["mean_pair_cosine"], -1)

    def test_identical_weights_do_not_cancel(self):
        w = torch.ones(2, 3)
        self.assertAlmostEqual(group_geometry([w, w])["shrink_ratio"], 1)

    def test_compile_prefix_collision_fails(self):
        with self.assertRaises(ValueError):
            normalize_state_dict({"a": 1, "_orig_mod.a": 2})
        self.assertEqual(normalize_state_dict({"_orig_mod._orig_mod.a": 1}), {"a": 1})

    def test_unequal_groups_use_canonical_members(self):
        cfg = TMTConfig(n_middle=16, mlp_group=8, mlp_split=(4,))
        self.assertEqual(mlp_group_members(cfg, 0), list(range(4)))
        self.assertEqual(mlp_group_members(cfg, 1), list(range(4, 16)))
