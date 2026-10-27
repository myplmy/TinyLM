"""CPU orchestration contracts; full GPU cost and real gradients are separate."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from scripts import diag_p005b_adamuon as diag


class CostContract(unittest.TestCase):
    def test_real_matrix_and_adamw_partition_is_complete(self):
        model = torch.nn.Sequential(torch.nn.Embedding(7, 3), torch.nn.Linear(3, 4), torch.nn.LayerNorm(4))
        rows = diag.catalog(model)
        self.assertEqual(sum(row["matrix"] for row in rows), 1)
        self.assertEqual(sum(row["elements"] for row in rows), sum(p.numel() for p in model.parameters()))
        params = list(model.parameters())
        for arm in ("muon", "normuon", "adamuon_fp32v"):
            matrix, adam = diag.make_optimizers(rows, params, arm)
            ids = [id(p) for opt in (matrix, adam) for g in opt.param_groups for p in g["params"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(set(ids), {id(p) for p in params})

    def test_state_signature_catches_changes_none_and_names(self):
        x = torch.arange(6.).reshape(2, 3)
        first = diag.tensor_signature([("x", x), ("y", None)])
        self.assertEqual(first, diag.tensor_signature([("x", x.clone()), ("y", None)]))
        self.assertNotEqual(first, diag.tensor_signature([("renamed", x), ("y", None)]))
        self.assertNotEqual(first, diag.tensor_signature([("x", x + 1), ("y", None)]))

    def test_actual_matrix_state_formula_comes_from_tensors(self):
        from tinylm.train.adamuon import AdaMuon
        p = torch.nn.Parameter(torch.zeros(2, 3))
        p.grad = torch.ones_like(p)
        optimizer = AdaMuon([p])
        optimizer.step()
        report = diag.state_storage(optimizer)
        self.assertEqual(report["unique_storage_bytes"], 8 * p.numel())


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()
