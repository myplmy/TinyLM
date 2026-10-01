"""CPU source/command coverage only, never execute smoke or protected checks."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_static_all as suite


class Tests(unittest.TestCase):
    def test_codex_profile_has_independent_checker_and_regression(self):
        entries = {name: argv for name, argv, _why in suite.checks_for_profile("codex-safe")}
        for name in ("check_handoff_codex", "test_handoff_codex_contract"):
            self.assertIn(name, entries)
            self.assertNotIn(name, suite.CODEX_SAFE_EXCLUDED)
            command = suite.command_for_check(name, entries[name])
            self.assertEqual(command[1:3], ["-I", "-B"])
            self.assertTrue(Path(command[3]).is_file())
            self.assertIn(".agents/skills/session-handoff/", Path(command[3]).resolve().as_posix())

    def test_legacy_checker_remains_excluded_from_codex(self):
        self.assertIn("check_handoff", suite.CODEX_SAFE_EXCLUDED)
        self.assertTrue(all("check_handoff.py" not in argv for _name, argv, _why in suite.CODEX_SAFE_CHECKS))

    def test_all_profile_not_silently_replaced(self):
        names = {name for name, _argv, _why in suite.checks_for_profile("all")}
        self.assertIn("check_handoff", names)
        self.assertNotIn("check_handoff_codex", names)
        self.assertNotIn("test_handoff_codex_contract", names)

    def test_existing_commands_keep_argument_layout(self):
        command = suite.command_for_check("fixture", ["fixture.py", "--check"])
        self.assertEqual(command, [sys.executable, str(suite.ROOT / "scripts/fixture.py"), "--check"])


if __name__ == "__main__":
    unittest.main()
