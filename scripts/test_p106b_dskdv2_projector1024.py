import unittest
from scripts import diag_p106b_dskdv2_projector1024 as big


class ExpandedAdapterContracts(unittest.TestCase):
    def test_same_immutable_optimization_code_reused(self):
        self.assertIs(big.build_inner().__code__,big.old.actual_inner.__code__)
    def test_output_and_selector_are_private_and_old_native_is_unchanged(self):
        original=big.old.native.selected;fn=big.build_inner()
        self.assertIsNot(fn.__globals__['native'],big.old.native)
        self.assertIs(fn.__globals__['native'].selected,big.selected)
        self.assertIs(big.old.native.selected,original);self.assertEqual(fn.__globals__['BASE'],big.BASE)
    def test_original_or_foreign_output_is_rejected(self):
        for p in [big.old.BASE,big.ROOT/'datasets/TinyDataset']:
            with self.assertRaises(ValueError):big.build_inner(p)


if __name__=='__main__':unittest.main()
