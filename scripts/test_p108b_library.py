"""CPU contracts for original-grid reuse and fixed auxiliary recipe."""
import unittest
from unittest.mock import patch

from scripts import diag_p108b_value_library as library


def rows():
    return [dict(id=f'f{f}:{i}', fact=f'f{f}', split='fit', expected=f'a{f}')
            for f in range(12) for i in range(2)]


class LibraryTests(unittest.TestCase):
    def test_cpu_cleanup_is_not_claimed_as_cuda_runtime(self):
        report = dict(status='COMPLETE')
        with patch.object(library.torch.cuda, 'is_initialized', return_value=False):
            self.assertIsNone(library.cleanup(report))
        self.assertEqual(report['cuda_cleanup_scope'], 'CUDA_NOT_INITIALIZED')

    def test_cleanup_failure_cannot_remain_success(self):
        report = dict(status='COMPLETE')
        with patch.object(library.torch.cuda, 'is_initialized', return_value=True), \
                patch.object(library, 'close_owned_cuda', side_effect=RuntimeError('live tensor')), \
                patch.object(library.torch.cuda, 'memory_allocated', return_value=8), \
                patch.object(library.torch.cuda, 'memory_reserved', return_value=512):
            self.assertIsInstance(library.cleanup(report), RuntimeError)
        self.assertEqual(report['status'], 'ERROR_FINAL_CUDA_CLEANUP')
        self.assertEqual(report['cuda_allocated_after_bytes'], 8)

    def test_full14_grid(self):
        grid = library.library_grid(rows())
        self.assertEqual(len(grid), 168)
        self.assertEqual({layer for _, layer in grid}, set(range(14)))
        self.assertEqual(sum(layer not in (2, 5, 8, 11) for _, layer in grid), 120)

    def test_missing_fact_and_duplicate_id_rejected(self):
        for invalid in (rows()[:-2], rows()+[rows()[0]]):
            with self.assertRaises(ValueError):
                library.library_grid(invalid)

    def test_conflicting_answer_rejected(self):
        data = rows(); data[0]['expected'] = 'different'
        with self.assertRaises(ValueError):
            library.library_grid(data)

    def test_other_depth_not_silently_called_full14(self):
        with self.assertRaises(ValueError):
            library.library_grid(rows(), 12)

    def test_candidate_full_value_and_recipe(self):
        c = dict(fact='f0', layer=13, value_delta=[0.]*768,
                 optimization=dict(value_optimizer_updates=40), oracle_fit=dict(items=2))
        self.assertIs(library.verify_candidate(c, 'f0', 13), c)
        for replacement in ([0.]*767, [float('nan')]*768):
            with self.assertRaises(ValueError):
                library.verify_candidate(dict(c, value_delta=replacement), 'f0', 13)
        with self.assertRaises(ValueError):
            library.verify_candidate(dict(c, optimization=dict(value_optimizer_updates=80)), 'f0', 13)


if __name__ == '__main__':
    unittest.main()
