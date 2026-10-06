#!/usr/bin/env python3
"""CPU-only held entry prolog fixtures. Never execute any experiment body."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'run_P106B_Stage5cWb_lora_conditioned_final_verdict-hold.sh',
    'run_P106B_Stage4cWc_balanced_final_verdict-hold.sh',
    'run_P106B_Stage5dWb_review_conditioned_final_verdict-hold.sh',
    'run_P106B_Stage4cW_mixed_chat32_repeat4-hold.sh',
)


class HoldTests(unittest.TestCase):
    def test_only_prolog_stops_held_names(self):
        for name in FILES:
            text = (ROOT / name).read_text(encoding='utf-8')
            prolog, body = text.split('repo_root=', 1)
            self.assertIn('scripts/runlog.py', body)
            self.assertNotIn('source ', prolog)
            self.assertNotIn('python', prolog)
            for called in (name, name.replace('-hold.sh', '-HOLD.sh')):
                with self.subTest(name=called):
                    r = subprocess.run(['bash', '-c', prolog + '\nprintf BODY_NOT_EXECUTED', called],
                                       capture_output=True, text=True, timeout=5)
                    self.assertEqual(r.returncode, 8)
                    self.assertIn('[HOLD]', r.stderr)
                    self.assertNotIn('BODY_NOT_EXECUTED', r.stdout)

    def test_unmarked_name_releases_only_prolog(self):
        for name in FILES:
            prolog = (ROOT / name).read_text(encoding='utf-8').split('repo_root=', 1)[0]
            r = subprocess.run(['bash', '-c', prolog + '\nprintf RELEASED_FIXTURE',
                                name.replace('-hold.sh', '.sh')], capture_output=True, text=True, timeout=5)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, 'RELEASED_FIXTURE')


if __name__ == '__main__':
    unittest.main()
