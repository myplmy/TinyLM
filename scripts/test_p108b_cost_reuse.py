"""Independent small-array physical-budget checks; no checkpoint or model."""
import unittest
import numpy as np
from scripts import diag_p108b_cost_reuse as c


class CostReuseContracts(unittest.TestCase):
    def test_constructor_parameter_owners_are_distinct_from_logical_layer_paths(self):
        cfg=dict(n_prelude=2,n_middle=10,n_coda=2,dim=768,ffn_dim=2048,tie_mlp=False)
        names=[f"pre_mlps.{i}.down_proj.weight"for i in range(2)]
        names += [f"mid_mlps.{i}.down_proj.weight"for i in range(10)]
        names += [f"coda_mlps.{i}.down_proj.weight"for i in range(2)]
        actual=c.checkpoint_keys(cfg,list(reversed(names)))
        self.assertEqual(actual[0],"pre_mlps.0.down_proj.weight")
        self.assertEqual(actual[2],"mid_mlps.0.down_proj.weight")
        self.assertEqual(actual[-1],"coda_mlps.1.down_proj.weight")
        with self.assertRaises(ValueError):c.checkpoint_keys(cfg,[f"layers.{i}.mlp.down.weight"for i in range(14)])
        with self.assertRaises(ValueError):c.checkpoint_keys(dict(cfg,tie_mlp=True),names)
        with self.assertRaises(ValueError):c.checkpoint_keys(dict(cfg,n_middle=9),names)

    def test_same_matrix_cross_term_and_ever_touched_differ_from_final_net(self):
        zero = np.zeros((1,2), np.float32)
        a = np.array([[3.,0.]], np.float32); b = np.array([[3.,4.]], np.float32)
        result, _, _ = c.physical_trace({0:zero}, [(0,a,a),(0,b-a,b)])
        self.assertEqual(result["net_norm"],5.)
        self.assertEqual(result["path_norm"],7.)
        self.assertEqual(result["ever_changed_entries"],2)

    def test_undo_is_not_free_path_or_unchanged_ever_touched(self):
        zero = np.zeros((1,1), np.float32); two = np.array([[2.]],np.float32)
        result, _, _ = c.physical_trace({0:zero},[(0,two,two),(0,-two,zero)])
        self.assertEqual(result["net_norm"],0.)
        self.assertEqual(result["path_norm"],4.)
        self.assertEqual(result["changed_entries"],0)
        self.assertEqual(result["ever_changed_entries"],1)
        self.assertEqual(result["sum_step_changed_entries"],2)

    def test_distinct_matrices_combine_by_square_sum(self):
        zero = np.zeros((1,1),np.float32); a=np.array([[3.]],np.float32);b=np.array([[4.]],np.float32)
        result,_,_=c.physical_trace({0:zero,1:zero},[(0,a,a),(1,b,b)])
        self.assertEqual(result["net_norm"],5.)
        self.assertEqual(result["path_norm"],7.)

    def test_nonphysical_or_dtype_changed_write_rejected(self):
        zero=np.zeros((1,1),np.float32);one=np.ones((1,1),np.float32)
        with self.assertRaises(ValueError):c.physical_trace({0:zero},[(0,one,zero)])
        with self.assertRaises(ValueError):c.physical_trace({0:zero},[(0,one.astype(float),one)])

    def test_generated_calls_count_duplicate_prompts_as_actual_calls(self):
        record=dict(generation=dict(prompt_tokens=10,generated_tokens=3))
        costs=c.generation_cost([record,record])
        self.assertEqual(costs["calls"],2)
        self.assertEqual(costs["prompt_tokens_sum"],20)
        self.assertEqual(costs["generated_tokens_sum"],6)


if __name__ == "__main__":
    unittest.main()
