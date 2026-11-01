"""CPU-only validation isolation tests; fixtures live outside the real repo."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validation_scope as v
import check_static_all as suite

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))


class Fixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tl_scope_fixture_")
        self.root = Path(self.temp.name)
        self.write(v.BOOTSTRAP, (SOURCE / v.BOOTSTRAP).read_text())
        self.counter = 0

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def manifest(self, names, *, command=None, children=None):
        command = command or ["scripts/probe.py"]
        self.names = sorted(set([v.BOOTSTRAP, *names]))
        self.data = dict(schema=v.SCHEMA, mode=v.MODE, repository=str(self.root),
                         exclusions=["datasets/TinyDataset", "foreign_session", "scripts/excluded.py"],
                         inputs=[dict(path=name, role="shared" if name == v.BOOTSTRAP else "owned",
                                      sha256=v.sha256(self.root / name)) for name in self.names],
                         commands=[dict(name="probe", argv=command)],
                         child_commands=children or [])
        self.path = self.write("scope.json", json.dumps(self.data))
        return v.Scope(self.path, v.sha256(self.path), root=self.root)

    def run(self, scope, *, isolated=False):
        self.counter += 1
        receipt = self.root / "output" / (str(self.counter) + ".json")
        command = [sys.executable, *( ["-I", "-B"] if isolated else ["-B"] ),
                   str(self.root / scope.commands["probe"][0]), *scope.commands["probe"][1:]]
        wrapped = v.scoped_command(command, scope, receipt, "probe")
        result = subprocess.run(wrapped, cwd=self.root, capture_output=True, text=True, timeout=30)
        row = json.loads(receipt.read_text()) if receipt.is_file() else None
        return result, row

    def close(self):
        self.temp.cleanup()


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)

    def probe(self, code, children=None):
        self.fx.write("scripts/probe.py", code)
        return self.fx.manifest(["scripts/probe.py"], children=children)

    def test_no_environment_keeps_global_and_half_environment_fails(self):
        self.assertIsNone(v.from_environment({}))
        for env in ({v.ENV_PATH: "scope.json"}, {v.ENV_SHA: "0" * 64}):
            with self.assertRaises(ValueError):
                v.from_environment(env)

    def test_hash_and_unknown_role_and_duplicate_rejected(self):
        scope = self.probe("pass")
        with self.assertRaises(ValueError):
            v.Scope(self.fx.path, "0" * 64, root=self.fx.root)
        for mutate in (lambda d: d["inputs"][0].update(role="foreign"),
                       lambda d: d["inputs"].append(d["inputs"][0])):
            data = json.loads(json.dumps(self.fx.data))
            mutate(data)
            self.fx.path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                v.Scope(self.fx.path, v.sha256(self.fx.path), root=self.fx.root)
        self.assertTrue(scope.commands)

    def test_traversal_alias_protected_and_foreign_paths_rejected(self):
        for name in ("../outside", "/etc/passwd", "scripts/../file.py",
                     "datasets/TinyDataset/source.jsonl", ".claude/hooks.py", "ai_dev_tool/00_rules.md"):
            with self.assertRaises(ValueError):
                v._relative(name)
        self.fx.write("real.txt", "real")
        (self.fx.root / "alias.txt").symlink_to(self.fx.root / "real.txt")
        with self.assertRaises(ValueError):
            v._regular(self.fx.root, "alias.txt")
        os.link(self.fx.root / "real.txt", self.fx.root / "hardlink.txt")
        with self.assertRaises(ValueError):
            v._regular(self.fx.root, "hardlink.txt")

    def test_explicit_foreign_prefix_is_rejected_before_file_read(self):
        scope = self.probe("pass")
        data = json.loads(json.dumps(self.fx.data))
        data["inputs"].append(dict(path="foreign_session/private.txt", role="shared", sha256="A" * 64))
        self.fx.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "excluded prefix"):
            v.Scope(self.fx.path, v.sha256(self.fx.path), root=self.fx.root)
        self.assertTrue(scope.inputs)

    def test_collectors_select_before_any_excluded_read(self):
        self.fx.write("scripts/excluded.py", "raise RuntimeError('private canary')")
        scope = self.probe("import glob,json,os\nfrom pathlib import Path\n"
                           "print(json.dumps({'path': sorted(p.name for p in Path('scripts').glob('*.py')),"
                           "'recursive':sorted(p.name for p in Path('.').rglob('*.py')) ,"
                           "'glob':sorted(glob.glob('scripts/*.py')), 'dir':sorted(os.listdir('scripts'))}))\n")
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 0, result.stderr)
        found = json.loads(result.stdout)
        self.assertNotIn("excluded.py", str(found))
        self.assertEqual(found["path"], ["probe.py", "validation_scope.py"])
        self.assertFalse(row["scope_violations"])
        self.assertNotIn("scripts/excluded.py", row["actual_reads"])
        self.assertFalse(row["global_pass_eligible"])

    def test_caught_read_denial_still_forces_failure(self):
        self.fx.write("canary.txt", "must never be read")
        scope = self.probe("from pathlib import Path\ntry:\n Path('canary.txt').read_text()\nexcept PermissionError:\n pass\n")
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertEqual(row["checker_returncode"], 0)
        self.assertTrue(row["scope_violations"])
        self.assertNotIn("canary.txt", row["actual_reads"])

    def test_raw_posix_directory_enumeration_is_not_a_bypass(self):
        scope = self.probe("import posix\ntry:\n posix.listdir('scripts')\nexcept PermissionError:\n pass\n")
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertTrue(row["scope_violations"])

    def test_original_attrs_checker_still_detects_owned_defect(self):
        self.fx.write("scripts/check_attrs.py", (SOURCE / "scripts/check_attrs.py").read_text())
        self.fx.write("tinylm/config.py", "class TMTConfig:\n good: int = 1\n")
        self.fx.write("scripts/owned.py", "def use(cfg):\n return cfg.not_declared\n")
        self.fx.write("scripts/excluded.py", "def use(cfg):\n return cfg.excluded_canary\n")
        scope = self.fx.manifest(["scripts/check_attrs.py", "scripts/owned.py", "tinylm/config.py"],
                                 command=["scripts/check_attrs.py"])
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("not_declared", result.stdout)
        self.assertNotIn("excluded_canary", result.stdout)
        self.assertFalse(row["scope_violations"])

    def test_global_checker_and_scoped_input_sets_really_differ(self):
        self.fx.write("scripts/check_attrs.py", (SOURCE / "scripts/check_attrs.py").read_text())
        self.fx.write("tinylm/config.py", "class TMTConfig:\n good: int = 1\n")
        self.fx.write("scripts/owned.py", "def use(cfg):\n return cfg.good\n")
        self.fx.write("scripts/excluded.py", "def use(cfg):\n return cfg.excluded_canary\n")
        scope = self.fx.manifest(["scripts/check_attrs.py", "scripts/owned.py", "tinylm/config.py"],
                                 command=["scripts/check_attrs.py"])
        scoped, row = self.fx.run(scope)
        global_result = subprocess.run([sys.executable, "-B", "scripts/check_attrs.py"],
                                       cwd=self.fx.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(scoped.returncode, 0, scoped.stderr)
        self.assertEqual(global_result.returncode, 1, global_result.stderr)
        self.assertIn("excluded_canary", global_result.stdout)
        self.assertFalse(row["global_pass_eligible"])

    def test_isolated_python_child_inherits_and_receipt_is_verified(self):
        child = "print('child-ok')"
        scope = self.probe("import subprocess,sys\nsubprocess.run([sys.executable,'-I','-B','-X','utf8','-c',"
                           + repr(child) + "],check=True)\n", children=[["-c", child]])
        result, row = self.fx.run(scope, isolated=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(row["children"]), 1)
        self.assertIn("child-ok", result.stdout)
        self.assertFalse(row["children"][0]["scope_violations"])

    def test_child_catches_denial_but_parent_cannot_hide_it(self):
        self.fx.write("canary.txt", "never read")
        child = "from pathlib import Path\ntry:\n Path('canary.txt').read_text()\nexcept PermissionError:\n pass"
        scope = self.probe("import subprocess,sys\nsubprocess.run([sys.executable,'-c'," + repr(child) + "])\n",
                           children=[["-c", child]])
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertEqual(row["children"][0]["returncode"], 91)
        self.assertTrue(row["scope_violations"])

    def test_nested_children_propagate_boundary_and_expected_nonzero_is_preserved(self):
        self.fx.write("canary.txt", "never read")
        grandchild = "from pathlib import Path\ntry:\n Path('canary.txt').read_text()\nexcept PermissionError:\n pass"
        child = "import subprocess,sys\nsubprocess.run([sys.executable,'-I','-c'," + repr(grandchild) + "])"
        scope = self.probe("import subprocess,sys\nsubprocess.run([sys.executable,'-c'," + repr(child) + "])\n",
                           children=[["-c", child], ["-c", grandchild]])
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertTrue(row["children"][0]["scope_violations"])
        expected_failure = "raise SystemExit(2)"
        scope = self.probe("import subprocess,sys\nr=subprocess.run([sys.executable,'-c',"
                           + repr(expected_failure) + "])\nassert r.returncode==2\n",
                           children=[["-c", expected_failure]])
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(row["children"][0]["returncode"], 2)
        self.assertFalse(row["scope_violations"])

    def test_unregistered_child_native_shell_and_mutation_are_not_silent(self):
        probes = ["import subprocess,sys\ntry:\n subprocess.run([sys.executable,'-c','pass'])\nexcept PermissionError:\n pass",
                  "import subprocess\ntry:\n subprocess.run(['/bin/true'])\nexcept PermissionError:\n pass",
                  "import os\ntry:\n os.system('true')\nexcept PermissionError:\n pass",
                  "from pathlib import Path\ntry:\n Path('new_user_file').write_text('bad')\nexcept PermissionError:\n pass"]
        for code in probes:
            scope = self.probe(code)
            result, row = self.fx.run(scope)
            self.assertEqual(result.returncode, 91, result.stderr)
            self.assertTrue(row["scope_violations"])
            self.assertFalse((self.fx.root / "new_user_file").exists())

    def test_input_change_invalidates_manifest(self):
        scope = self.probe("pass")
        self.fx.write("scripts/probe.py", "print('changed')")
        self.assertFalse(scope.unchanged())
        with self.assertRaises(ValueError):
            v.Scope(self.fx.path, scope.digest, root=self.fx.root)

    def test_receipt_write_once_and_original_argv_kept(self):
        scope = self.probe("pass")
        first, _ = self.fx.run(scope)
        self.assertEqual(first.returncode, 0, first.stderr)
        receipt = self.fx.root / "output/1.json"
        before = receipt.read_bytes()
        command = v.scoped_command([sys.executable, "-I", "-B", "-X", "utf8",
                                    str(self.fx.root / "scripts/probe.py")], scope, receipt, "probe")
        self.assertEqual(command[1:5], ["-I", "-B", "-X", "utf8"])
        result = subprocess.run(command, cwd=self.fx.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 91)
        self.assertEqual(before, receipt.read_bytes())

    def test_shared_whitelist_rows_selected_before_original_stale_predicate(self):
        self.fx.write("scripts/check_flag_whitelist.py", (SOURCE / "scripts/check_flag_whitelist.py").read_text())
        self.fx.write("scripts/parser.py", "import argparse\np=argparse.ArgumentParser()\np.add_argument('--owned')\n")
        self.fx.write("scripts/flag_whitelist.tsv", "flag\tgrade\tevidence\tchecked\tdeclared_in\n"
                      "--init\tok\t\t2026\tscripts/check_flag_whitelist.py\n"
                      "--sync\tok\t\t2026\tscripts/check_flag_whitelist.py\n"
                      "--verbose\tok\t\t2026\tscripts/check_flag_whitelist.py\n"
                      "--owned\tok\t\t2026\tscripts/excluded.py\n"
                      "--foreign\tok\t\t2026\tscripts/excluded.py\n")
        names = ["scripts/check_flag_whitelist.py", "scripts/parser.py", "scripts/flag_whitelist.tsv"]
        scope = self.fx.manifest(names, command=["scripts/check_flag_whitelist.py"])
        result, row = self.fx.run(scope)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertFalse(row["scope_violations"])
        self.fx.write("scripts/flag_whitelist.tsv", "flag\tgrade\tevidence\tchecked\tdeclared_in\n"
                      "--stale\tok\t\t2026\tscripts/parser.py\n")
        scope = self.fx.manifest(names, command=["scripts/check_flag_whitelist.py"])
        result, _ = self.fx.run(scope)
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)

    def test_explicit_manifest_never_calls_git_status(self):
        scope = self.probe("pass")
        with patch.object(suite.subprocess, "run") as call:
            rows, digest = suite._worktree_manifest(scope=scope)
        call.assert_not_called()
        self.assertEqual(len(rows), len(scope.inputs))
        self.assertEqual(len(digest), 64)

    def test_original_static_suite_records_subset_and_missing_receipt_is_error(self):
        self.fx.write("scripts/check_static_all.py", (SOURCE / "scripts/check_static_all.py").read_text())
        self.fx.write("scripts/check_attrs.py", "print('checker ok')")
        self.fx.write("handoff/test.md", "- **Codex 세션 ID**: `cpu-fixture`\n")
        names = ["scripts/check_static_all.py", "scripts/check_attrs.py", "handoff/test.md"]
        scope = self.fx.manifest(names, command=["scripts/check_attrs.py"])
        # Use the canonical name; this is still the unmodified suite loop.
        self.fx.data["commands"][0]["name"] = "check_attrs"
        self.fx.path.write_text(json.dumps(self.fx.data))
        env = dict(os.environ, **{v.ENV_PATH: str(self.fx.path), v.ENV_SHA: v.sha256(self.fx.path)})
        def run(output):
            return subprocess.run([sys.executable, "-B", "scripts/check_static_all.py", "--quiet",
                                   "--profile", "codex-safe", "--json", output, "--wip", "handoff/test.md"],
                                  cwd=self.fx.root, env=env, capture_output=True, text=True, timeout=30)
        good = run("output/good.json")
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        report = json.loads((self.fx.root / "output/good.json").read_text())
        self.assertEqual(report["schema"], "TINYLM_SCOPED_STATIC_AUDIT_V1")
        self.assertEqual(report["counts"]["pass"], 1)
        self.assertEqual(len(report["checks"]), len(suite.checks_for_profile("codex-safe")))
        self.assertEqual(report["counts"]["not_run"], len(report["checks"]) - 1)
        self.assertFalse(report["global_pass_eligible"])
        before = (self.fx.root / "output/good.json").read_bytes()
        collision = run("output/good.json")
        self.assertEqual(collision.returncode, 2, collision.stdout + collision.stderr)
        self.assertEqual((self.fx.root / "output/good.json").read_bytes(), before)
        self.fx.write("scripts/check_attrs.py", "import os\nos._exit(0)")
        for row in self.fx.data["inputs"]:
            row["sha256"] = v.sha256(self.fx.root / row["path"])
        self.fx.path.write_text(json.dumps(self.fx.data))
        env[v.ENV_SHA] = v.sha256(self.fx.path)
        bad = run("output/missing_receipt.json")
        self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
        report = json.loads((self.fx.root / "output/missing_receipt.json").read_text())
        self.assertEqual(report["counts"]["errors"], 1)

    def test_owned_subset_cannot_satisfy_existing_global_wip_closure(self):
        import wip
        path = self.fx.write('handoff/WIP_fixture.md', '- **Codex 세션 ID**: `fixture`\n')
        audit = self.fx.write('output/scoped.json', json.dumps(dict(
            schema='TINYLM_SCOPED_STATIC_AUDIT_V1', profile='codex-safe',
            global_pass_eligible=False, counts=dict(errors=0, actionable_warnings=0),
            wip=dict(path='handoff/WIP_fixture.md', sha256=v.sha256(path), session_id='fixture'))))
        with patch.object(wip, 'ROOT', self.fx.root):
            with self.assertRaisesRegex(ValueError, 'schema'):
                wip._validate_static_audit(path, audit)


class SmokeScopeTests(unittest.TestCase):
    def test_scoped_source_pins_do_not_walk_the_repository(self):
        from scripts.smoke_execution_contract import execution_source_pins, CODEX_CHECKER
        from scripts.smoke_module import parse_smoke_module
        names = {'scripts/batch/tool_smoke.bat', 'scripts/codex_smoke.py',
                 'scripts/smoke_execution_contract.py', CODEX_CHECKER,
                 'scripts/runlog.py', 'scripts/smoke_module.py',
                 'scripts/summarize_smoke.py', 'scripts/check_smoke.py',
                 'scripts/smoke_diag_contract.tsv', v.BOOTSTRAP, 'tinylm/config.py'}
        for action in parse_smoke_module():
            names.update(value for value in action.argv if value.endswith('.py'))
        class Explicit:
            inputs = dict.fromkeys(names)
            def unchanged(self):
                return True
        with patch.object(Path, 'iterdir', side_effect=AssertionError('unexpected traversal')):
            pins = execution_source_pins(SOURCE, scope=Explicit())
        self.assertEqual(set(pins), names)
        class Missing:
            inputs = {}
            def unchanged(self):
                return True
        with self.assertRaises(ValueError):
            execution_source_pins(SOURCE, scope=Missing())

    def test_same_actions_and_model_argv_only_four_collectors_change(self):
        from scripts.codex_smoke import build_plan, environment
        from scripts.smoke_execution_contract import SCOPED_COLLECTORS, scope_collector_actions
        _target, original, base, changes = build_plan(SOURCE, "scope_cpu_contract")
        self.assertEqual(len(changes), 2)
        self.assertEqual(len(original), 106)
        scope = type("FakeScope", (), {})()
        scope.root, scope.path, scope.digest = SOURCE, SOURCE / "scope.json", "A" * 64
        scope.commands = {name: [path] for path, name in SCOPED_COLLECTORS.items()}
        changed, edits = scope_collector_actions(base, scope, SOURCE / "tmp/collector_reads")
        self.assertEqual(len(edits), 4)
        self.assertEqual(len(changed), len(base))
        count = 0
        for before, after in zip(base, changed):
            self.assertEqual((before.kind, before.line, before.seconds), (after.kind, after.line, after.seconds))
            if "run100m.py" in before.argv:
                self.assertEqual(before.argv, after.argv)
                count += 1
        self.assertEqual(count, 33)
        self.assertEqual(sum(x.kind == "run" and "--" in x.argv for x in changed), 44)
        env = environment(SOURCE / "tmp/runtime", "fixture", "stamp",
                          {v.ENV_PATH: "scope.json", v.ENV_SHA: "A" * 64, "KEEP": "same"})
        self.assertNotIn(v.ENV_PATH, env)
        self.assertNotIn(v.ENV_SHA, env)
        self.assertEqual(env["KEEP"], "same")
        scope.commands.pop("smoke_check_links")
        with self.assertRaises(ValueError):
            scope_collector_actions(base, scope, SOURCE / "tmp/collector_reads")


if __name__ == "__main__":
    unittest.main()
