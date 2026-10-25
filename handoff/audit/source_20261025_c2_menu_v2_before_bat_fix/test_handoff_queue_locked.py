#!/usr/bin/env python3
"""Queue-locked handoff inheritance uses only previous Markdown, never registry."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import handoff_queue
import queue_menu
import queue_menu_linux


class LockedInheritanceTests(unittest.TestCase):
    def test_locked_mode_never_loads_live_inventory(self):
        original = handoff_queue._load_registry
        handoff_queue._load_registry = lambda: (_ for _ in ()).throw(
            AssertionError("registry must not be opened")
        )
        try:
            with tempfile.TemporaryDirectory() as directory:
                previous = Path(directory) / "previous.md"
                previous.write_text(
                    "## 7. 다음 권장 실험 순서" + chr(10) +
                    "| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |" + chr(10) +
                    "|---:|---:|---|---|---:|---:|---|---|---|---|" + chr(10) +
                    "| 1 | 3 | P000 Stage0 | " + chr(96) + "run_P000_Stage0.sh" + chr(96) +
                    " | 1.5 | 1.5 | PRESENT | REVALIDATE | 현재 큐 잠금 | 역사 이유 |" + chr(10) +
                    "| 2 | — | P001 완료 | " + chr(96) + "run_P001-done.sh" + chr(96) +
                    " | 0.2 | 1.7 | DONE | DONE | 없음 | 완료 |" + chr(10),
                    encoding="utf-8",
                )
                rows = handoff_queue.inherited_rows_locked(previous)
        finally:
            handoff_queue._load_registry = original
        self.assertEqual(len(rows), 1)
        self.assertIn("| UNVERIFIED | REVALIDATE |", rows[0])
        self.assertIn("| 1.5 | 1.5 |", rows[0])
        self.assertIn("run_P000_Stage0.sh", rows[0])
        self.assertNotIn("run_P001-done.sh", rows[0])

    def test_unverified_normal_inheritance_never_stats_or_loads_registry(self):
        with tempfile.TemporaryDirectory() as raw:
            previous = Path(raw) / 'previous.md'
            previous.write_text(
                '## 7. 다음 권장 실험 순서\n'
                '| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |\n'
                '|---|---|---|---|---|---|---|---|---|---|\n'
                '| 1 | — | 합성 | run_locked.sh | 1 | 1 | UNVERIFIED | REVALIDATE | 잠금 | 역사 |\n')
            with patch.object(handoff_queue, 'registry_inventory', side_effect=AssertionError('메뉴 금지')), \
                    patch.object(Path, 'stat', side_effect=AssertionError('stat 금지')), \
                    patch.object(Path, 'glob', side_effect=AssertionError('glob 금지')):
                rows = handoff_queue.inherited_rows(previous, Path('/접근금지'))
            self.assertIn('| UNVERIFIED | REVALIDATE |', rows[0])


class MenuInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.names = ['run_smoke_check.sh', 'run_literal-done.sh', 'run_second.sh', 'run_first.sh',
            'run_held-hold.sh', 'run_cancel-cancel.sh', 'run_windows.bat', 'run_windows.sh',
            'run_missing_shell.bat', 'run_alias-done.sh', 'run_win_done-done.bat']
        for name in self.names:
            (self.root / name).write_text('합성 메뉴\n', encoding='utf-8')
        entries = [(0, 'run_smoke_check.sh'), (1, 'run_literal-done.sh'), (2, 'run_second.sh'),
            (2, 'run_first.sh'), (2, 'run_held-hold.sh'), (2, 'run_cancel-cancel.sh'),
            (2, 'run_windows.bat'), (2, 'run_missing_shell.bat'), (2, 'run_alias.sh'),
            (2, 'run_win_done-done.bat')]
        (self.root / 'experiments.tsv').write_text(
            'prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\n'
            + ''.join(f'{priority}\tP014\t{name}\tN\t.1\tN\tN\t합성\n' for priority, name in entries), encoding='utf-8')

    def actual_rows(self):
        with patch.object(queue_menu, 'ROOT', self.root), patch.object(queue_menu, 'TSV', self.root / 'experiments.tsv'):
            rows, warnings = queue_menu.load()
        self.assertEqual(warnings, [])
        return rows

    def previous(self, names):
        previous = self.root / 'previous.md'
        previous.write_text('## 7. 다음 권장 실험 순서\n'
            '| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |\n'
            '|---|---|---|---|---|---|---|---|---|---|\n' + ''.join(
                f'| {i} | 0 | 합성 | {name} | .1 | .1 | PRESENT | GATED | 선결 | 역사 |\n'
                for i, name in enumerate(names, 1)), encoding='utf-8')
        return previous

    def test_linux_ids_match_existing_available_filter_and_tsv_tie_order(self):
        rows = queue_menu_linux.with_shell_state(self.actual_rows(), self.root)
        expected = {row['shell_batch']: index for index, row in enumerate(queue_menu_linux.available(rows))}
        data = handoff_queue.registry_inventory(self.root, platform='posix')
        self.assertEqual(data['menu_ids'], expected)
        self.assertEqual(data['runnable_ids'], expected)
        self.assertEqual(list(expected), ['run_smoke_check.sh', 'run_second.sh', 'run_first.sh', 'run_windows.sh'])
        self.assertEqual(expected['run_second.sh'], 1)
        self.assertEqual(expected['run_first.sh'], 2)

    def test_windows_bat_menu_behavior_and_original_module_state_are_preserved(self):
        expected = {row['batch']: i for i, row in enumerate(queue_menu.available(self.actual_rows()))}
        before = queue_menu.ROOT, queue_menu.TSV, sys.modules['queue_menu'], list(sys.path)
        data = handoff_queue.registry_inventory(self.root, platform='nt')
        self.assertEqual(data['menu_ids'], expected)
        self.assertNotIn('run_second.sh', data['menu_ids'])
        self.assertIn('run_missing_shell.bat', data['runnable_ids'])
        self.assertIn('run_win_done-done.bat', data['menu_ids'])
        self.assertNotIn('run_win_done-done.bat', data['runnable_ids'])
        self.assertEqual(before, (queue_menu.ROOT, queue_menu.TSV, sys.modules['queue_menu'], list(sys.path)))

    def test_done_alias_literal_hold_and_missing_companion_are_distinct(self):
        rows = {row['batch']: row for row in handoff_queue.registry_inventory(self.root, platform='posix')['rows']}
        self.assertTrue(rows['run_literal-done.sh']['physical_exists'])
        self.assertEqual(rows['run_literal-done.sh']['inventory_state'], 'DONE')
        self.assertEqual(rows['run_alias.sh']['done_aliases'], ['run_alias-done.sh'])
        self.assertFalse(rows['run_alias.sh']['physical_exists'])
        self.assertEqual(rows['run_alias.sh']['inventory_state'], 'DONE')
        self.assertEqual(rows['run_held-hold.sh']['inventory_state'], 'HOLD')
        self.assertEqual(rows['run_cancel-cancel.sh']['inventory_state'], 'HOLD')
        self.assertTrue(rows['run_missing_shell.bat']['physical_exists'])
        self.assertFalse(rows['run_missing_shell.bat']['execution_file_exists'])
        self.assertFalse(rows['run_missing_shell.bat']['runnable'])

    def test_inherited_rows_keep_physical_hold_and_done_alias_without_fake_ids(self):
        previous = self.previous(['run_alias.sh', 'run_literal-done.sh', 'run_held-hold.sh',
            'run_missing_shell.bat', 'run_windows.sh', 'run_second.sh'])
        rows = handoff_queue.inherited_rows(previous, self.root, platform='posix')
        self.assertIn('| DONE | DONE |', rows[0])
        self.assertIn('| DONE | DONE |', rows[1])
        self.assertIn('| 0.1 | 0.0 | DONE |', rows[1])
        self.assertIn('| — |', rows[2])
        self.assertIn('| PRESENT | HOLD |', rows[2])
        self.assertIn('| PRESENT | HOLD |', rows[3])
        self.assertIn('| 3 | 합성 | `run_windows.sh`', rows[4])
        self.assertIn('| 1 | 합성 | `run_second.sh`', rows[5])

    def test_importlib_isolated_mode_needs_no_sibling_sys_path_or_environment_fallback(self):
        previous = self.previous(['run_second.sh'])
        script = """
import importlib.util,json,pathlib,sys
before=list(sys.path)
spec=importlib.util.spec_from_file_location('isolated_handoff',sys.argv[1])
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
rows=module.inherited_rows(pathlib.Path(sys.argv[3]),pathlib.Path(sys.argv[2]),platform='posix')
assert sys.path==before
assert 'queue_menu' not in sys.modules
print(json.dumps({'rows':rows,'torch_imported':'torch' in sys.modules}))
"""
        result = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', '-c', script,
            str(Path(handoff_queue.__file__).resolve()), str(self.root), str(previous)],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data['torch_imported'])
        self.assertIn('| 1 | 합성 | `run_second.sh`', data['rows'][0])


if __name__ == "__main__":
    unittest.main()
