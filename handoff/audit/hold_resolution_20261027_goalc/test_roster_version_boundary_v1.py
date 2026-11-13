"""Version 3 replacement must not corrupt already inserted versions 30 or 31."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from advance_reviewed_roster_v5 import fixed_generator


class Versions(unittest.TestCase):
    def generate(self, text, version):
        source = "import json\ncode=INPUT\nfor prefix in PREFIXES:\n    before=prefix+'3';after=prefix+str(new_version)\n    assert before in code;code=code.replace(before,after)\n"
        scope = dict(INPUT=text, PREFIXES=['roster_reviewed_partial_v', 'ROOT_REVIEWED_PARTIAL_ADMISSIONS_V'], new_version=version)
        exec(fixed_generator(source), scope)
        return scope['code']

    def test_prior30_to_new31(self):
        self.assertEqual(self.generate('roster_reviewed_partial_v30/complete.json roster_reviewed_partial_v3/out ROOT_REVIEWED_PARTIAL_ADMISSIONS_V3.json',31),
                         'roster_reviewed_partial_v30/complete.json roster_reviewed_partial_v31/out ROOT_REVIEWED_PARTIAL_ADMISSIONS_V31.json')

    def test_prior31_and_version300_preserved(self):
        value = self.generate('roster_reviewed_partial_v31/a roster_reviewed_partial_v300/a roster_reviewed_partial_v3/b ROOT_REVIEWED_PARTIAL_ADMISSIONS_V3.json',32)
        self.assertIn('roster_reviewed_partial_v31/a', value)
        self.assertIn('roster_reviewed_partial_v300/a', value)
        self.assertIn('roster_reviewed_partial_v32/b', value)

    def test_single_digit_baseline_unchanged(self):
        self.assertEqual(self.generate('roster_reviewed_partial_v3/a ROOT_REVIEWED_PARTIAL_ADMISSIONS_V3.json',9),
                         'roster_reviewed_partial_v9/a ROOT_REVIEWED_PARTIAL_ADMISSIONS_V9.json')

    def test_regular29_to30(self):
        self.assertIn('roster_reviewed_partial_v29/a', self.generate('roster_reviewed_partial_v29/a roster_reviewed_partial_v3/b ROOT_REVIEWED_PARTIAL_ADMISSIONS_V3.json',30))

    def test_generator_anchor_drift_rejected(self):
        with self.assertRaises(AssertionError):
            fixed_generator('import json\nchanged_generator=True\n')


if __name__ == '__main__':
    unittest.main()
