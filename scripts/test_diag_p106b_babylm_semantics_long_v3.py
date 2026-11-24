"""Long-window admission and source/input immutability regression contracts."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import diag_p106b_babylm_semantics_long_v3 as driver

class LongWindowContracts(unittest.TestCase):
    def test_full_hard_interval_must_fit_with_cleanup_reserve(self):
        driver.admit_wall(100,hard=200,cutoff=360)
        with self.assertRaises(driver.Hold):driver.admit_wall(100.001,hard=200,cutoff=360)
    def test_remaining_uses_both_monotonic_budget_and_absolute_deadline(self):
        self.assertEqual(driver.remaining_wall(25,100,hard=200,cutoff=1000),175)
        self.assertEqual(driver.remaining_wall(25,100,hard=200,cutoff=160),30)
        self.assertLess(driver.remaining_wall(201,100,hard=200,cutoff=1000),0)
    def test_source_and_input_drift_each_refuse_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.txt';source.write_text('original')
            identity=dict(files={'fake':'same'},sha256='frozen')
            profile=dict(user_directive=161,policy=dict(new_model_cutoff=driver.CUTOFF),
                sources=identity,pins={'source.txt':driver.prior.digest(source)})
            profile_path=root/'profile.json';profile_path.write_text(json.dumps(profile))
            with patch.object(driver,'ROOT',root),patch.object(driver,'PROFILE',profile_path),patch.object(
                    driver,'signature',return_value=identity):
                self.assertEqual(driver.verify_profile()['user_directive'],161)
                source.write_text('drift')
                with self.assertRaisesRegex(ValueError,'input changed'):driver.verify_profile()
                source.write_text('original')
                with patch.object(driver,'signature',return_value=dict(files={},sha256='drift')):
                    with self.assertRaisesRegex(ValueError,'source changed'):driver.verify_profile()

if __name__=='__main__':unittest.main()


