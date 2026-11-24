"""Input-only cost extrapolation and full denominator/storage guard tests."""
import unittest
from scripts import diag_p106b_babylm_semantics as driver

class SemanticsDriverContracts(unittest.TestCase):
    def test_spaced_cost_indices_preserve_both_source_ends(self):
        for n in (1,7,2315,49340):
            selected=driver.selected_indices(n)
            self.assertIn(0,selected);self.assertIn(n-1,selected)
            self.assertEqual(len(selected),min(n,32))
    def test_forecast_uses_all_files_and_padded_native_shape_not_row_shortcut(self):
        costs={'short':dict(wall_seconds=2.),'long':dict(wall_seconds=5.)}
        sweeps={'short':dict(padded_input_positions=1000,cost_padded_input_positions=100),
            'long':dict(padded_input_positions=400,cost_padded_input_positions=200)}
        self.assertEqual(driver.forecast(costs,sweeps),165.)
        with self.assertRaises(driver.Hold):driver.forecast({'short':costs['short']},sweeps)

if __name__=='__main__':unittest.main()
