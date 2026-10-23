"""CPU source/command coverage only, never execute smoke or protected checks."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
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

    def test_default_manifest_git_command_is_unchanged(self):
        reply=SimpleNamespace(returncode=0,stdout="")
        with patch.object(suite.subprocess,"run",return_value=reply) as call:
            rows,_=suite._worktree_manifest()
        self.assertEqual(rows,[])
        self.assertEqual(call.call_args.args[0],["git","-c","core.quotepath=false","status","--porcelain=v1","--untracked-files=all"])

    def test_safe_manifest_reuses_runlog_exclusions_before_git(self):
        import runlog
        reply=SimpleNamespace(returncode=0,stdout="")
        with patch.object(suite.subprocess,"run",return_value=reply) as call:
            rows,_=suite._worktree_manifest(profile="codex-safe")
        actual=call.call_args.args[0]
        self.assertEqual(actual[6:],runlog._git_status_command({"TL_RUNLOG_GIT_SCOPE":"codex-safe"})[3:])
        self.assertIn(":(exclude)datasets/TinyDataset",actual)
        self.assertEqual(rows,[])

    def test_bad_profile_never_invokes_git(self):
        with patch.object(suite.subprocess,"run") as call:
            with self.assertRaises(ValueError):suite._worktree_manifest(profile="codex_saf")
        call.assert_not_called()

    def test_scoped_git_failure_never_falls_back_to_full_tree(self):
        with patch.object(suite.subprocess,"run",return_value=SimpleNamespace(returncode=128,stdout="")) as call:
            with self.assertRaises(RuntimeError):suite._worktree_manifest(profile="codex-safe")
        call.assert_called_once()

    def test_scoped_manifest_hashes_only_the_returned_permitted_fixture(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/"docs").mkdir();(root/"docs/example.md").write_bytes(b"owned synthetic text")
            reply=SimpleNamespace(returncode=0,stdout="?? docs/example.md\n")
            with patch.object(suite,"ROOT",root),patch.object(suite.subprocess,"run",return_value=reply):
                rows,digest=suite._worktree_manifest(profile="codex-safe")
            self.assertEqual(rows,[dict(status="??",path="docs/example.md",sha256=hashlib.sha256(b"owned synthetic text").hexdigest().upper())])
            raw=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            self.assertEqual(digest,hashlib.sha256(raw.encode()).hexdigest().upper())


if __name__ == "__main__":
    unittest.main()
