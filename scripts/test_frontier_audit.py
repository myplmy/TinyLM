#!/usr/bin/env python3
"""Old and new plan IDs must both survive frontier compilation."""
from __future__ import annotations

import tempfile
import unittest
import subprocess
import sys
from pathlib import Path

from frontier_audit import compile_frontier, experiment_rows


def legacy_frontier_case() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for directory in ("test_plan", "handoff", "docs/review"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / "test_plan/P014_old.md").write_text(
            "# P014\n\n## Stage1 ⏳ 실행 전\n\n선결 없음.\n", encoding="utf-8"
        )
        (root / "test_plan/P097_new.md").write_text(
            "# P097 — 진행 중\n\n## Stage1 ✅ 완료\n\n## Stage2 ⏳ 실행 전\n", encoding="utf-8"
        )
        (root / "test_plan/실험계획목록.md").write_text(
            "## 1. 계획만 있고 실행 전\n\n| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |\n"
            "|---|---|---|---|\n| [P014](P014_old.md) | old | 실행 전 | 2026-01-01 |\n"
            "## 2. 진행 중\n\n| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |\n"
            "|---|---|---|---|\n| [P097](P097_new.md) | new | Stage2 | 2026-09-21 |\n"
            "## 3. 종결\n",
            encoding="utf-8",
        )
        (root / "experiments.tsv").write_text(
            "prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\n"
            "1\tP014\trun_P014.sh\tD\t0.1\tN\tY\told ready\n", encoding="utf-8"
        )
        (root / "run_P014.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (root / "handoff/COMPASS.md").write_text("| 속도 | P014 |\n", encoding="utf-8")
        data = compile_frontier(root)
        by_id = {row["plan_id"]: row for row in data["rows"]}
        assert set(by_id) == {"P014", "P097"}
        assert by_id["P014"]["readiness"] == "GATED"
        assert by_id["P097"]["readiness"] == "HOLD"
        assert data["set_differences"] == {"physical_without_index": [], "index_without_physical": []}
    print("[PASS] frontier preserves old P014 and new P097 with one row per physical plan")
    return 0


class FrontierInventoryTests(unittest.TestCase):
    def test_old_and_new_plan_ids_remain(self):
        self.assertEqual(legacy_frontier_case(), 0)

    def test_existing_package_import_still_works_from_repository_root(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            'from scripts import frontier_audit; print(callable(frontier_audit.experiment_rows))'],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'True')

    def test_direct_isolated_help_preserves_standard_library_only_entry(self):
        result = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8',
            str(Path(__file__).with_name('frontier_audit.py')), '--help'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--check', result.stdout)

    def test_arbitrary_isolated_import_and_error_restore_exact_local_module_state(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root, [('run_live.sh', .2)])
            (root / 'run_live.sh').write_text('#!/bin/sh\n')
            script = """
import importlib.util,json,pathlib,sys,types
before=list(sys.path)
alias='_tinylm_frontier_handoff_queue'
saved=types.ModuleType('saved_local_alias')
poison=types.ModuleType('handoff_queue')
def forbidden(*args,**kwargs): raise AssertionError('다른 환경 fallback 금지')
poison.registry_inventory=forbidden
saved_menu=types.ModuleType('saved_queue_menu')
sys.modules[alias]=saved
sys.modules['handoff_queue']=poison
sys.modules['queue_menu']=saved_menu
spec=importlib.util.spec_from_file_location('arbitrary.frontier_without_registration',sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root=pathlib.Path(sys.argv[2])
rows=module.experiment_rows(root)
assert rows[0]['runnable'] is True
assert sys.path==before
assert sys.modules[alias] is saved
assert sys.modules['handoff_queue'] is poison
assert sys.modules['queue_menu'] is saved_menu
module.__file__=str(root/'missing_frontier.py')
try: module.experiment_rows(root)
except FileNotFoundError: pass
else: raise AssertionError('로컬 소스 부재를 숨기지 않는다')
assert sys.path==before
assert sys.modules[alias] is saved
assert sys.modules['handoff_queue'] is poison
assert sys.modules['queue_menu'] is saved_menu
print(json.dumps({'rows':len(rows),'torch_imported':'torch' in sys.modules}))
"""
            result = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', '-c', script,
                str(Path(__file__).with_name('frontier_audit.py').resolve()), str(root)],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"torch_imported": false', result.stdout)

    def fixture(self, root, entries, *, closed=False):
        for name in ('test_plan', 'handoff', 'docs/review'):
            (root / name).mkdir(parents=True, exist_ok=True)
        (root / 'test_plan/P014_fixture.md').write_text(
            '# P014\n> 상태: 종결\n' if closed else '# P014\n## Stage1 실행 전\n', encoding='utf-8')
        (root / 'test_plan/실험계획목록.md').write_text(
            ('## 3. 종결\n' if closed else '## 1. 계획만 있고 실행 전\n')
            + '| [P014](P014_fixture.md) | 합성 | 선결 | 2026-10-25 |\n', encoding='utf-8')
        (root / 'handoff/COMPASS.md').write_text('| 합성 | P014 |\n', encoding='utf-8')
        (root / 'experiments.tsv').write_text(
            'prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\n' + ''.join(
                f'{i}\tP014\t{name}\tY\t{hours}\tN\tN\t합성\n' for i, (name, hours) in enumerate(entries)),
            encoding='utf-8')

    def test_terminal_physical_files_do_not_become_live_time_or_preflight(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            entries = [('run_done-done.sh', 99), ('run_held-hold.sh', 88),
                       ('run_cancelled-cancel.sh', 77), ('run_alias.sh', 66), ('run_live.sh', .2)]
            self.fixture(root, entries)
            for name, _ in entries:
                if name != 'run_alias.sh':
                    (root / name).write_text('#!/bin/sh\n')
            (root / 'run_alias-done.sh').write_text('#!/bin/sh\n')
            row = compile_frontier(root)['rows'][0]
            self.assertEqual(row['launcher_inventory']['live'], ['run_live.sh'])
            self.assertEqual(row['preflight_count'], 1)
            self.assertEqual(row['estimated_hours'], .2)
            self.assertIn('run_done-done.sh', row['launcher_inventory']['physical'])
            self.assertEqual(set(row['launcher_inventory']['done']), {'run_done-done.sh', 'run_alias-done.sh'})
            inventory = {item['batch']: item for item in experiment_rows(root)}
            self.assertTrue(inventory['run_done-done.sh']['exists'])
            self.assertFalse(inventory['run_done-done.sh']['runnable'])
            self.assertEqual(inventory['run_held-hold.sh']['inventory_state'], 'HOLD')

    def test_closed_plan_with_only_literal_done_launcher_has_no_live_conflict(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root, [('run_closed-done.sh', 99)], closed=True)
            (root / 'run_closed-done.sh').write_text('#!/bin/sh\n')
            row = compile_frontier(root)['rows'][0]
            self.assertEqual(row['readiness'], 'DONE')
            self.assertEqual(row['conflicts'], [])
            self.assertEqual(row['launcher_inventory']['live'], [])

    def test_bat_without_shell_companion_stays_physical_but_not_linux_live(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root, [('run_windows.bat', 12)])
            (root / 'run_windows.bat').write_text('REM 합성\n')
            row = compile_frontier(root)['rows'][0]
            self.assertEqual(row['launcher_inventory']['physical'], ['run_windows.bat'])
            self.assertEqual(row['readiness'], 'HOLD')
            self.assertEqual(row['estimated_hours'], 0)

    def test_bat_done_evidence_does_not_require_linux_shell(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root, [('run_literal-done.bat', 99), ('run_alias.bat', 88), ('run_live.sh', .2)])
            for name in ('run_literal-done.bat', 'run_alias-done.bat', 'run_live.sh'):
                (root / name).write_text('합성 완료\n')
            data = compile_frontier(root)['rows'][0]
            self.assertEqual(data['launcher_inventory']['live'], ['run_live.sh'])
            self.assertEqual(set(data['launcher_inventory']['done']), {'run_literal-done.bat', 'run_alias-done.bat'})
            self.assertEqual(data['estimated_hours'], .2)
            self.assertEqual(data['preflight_count'], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
