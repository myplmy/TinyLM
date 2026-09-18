#!/usr/bin/env python3
"""Regression for executable post-delete guidance."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("sync_experiments_tsv.py")
SPEC = importlib.util.spec_from_file_location("tinylm_sync_experiments", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class PostDeleteGuidanceTests(unittest.TestCase):
    def test_ids_guidance_has_required_batch_argument(self) -> None:
        guidance = "\n".join(SYNC.POST_DELETE_GUIDANCE)
        self.assertIn("sync_experiments_tsv.py --apply", guidance)
        self.assertIn("queue_menu.py --audit", guidance)
        self.assertIn("queue_menu.py --ids <배치명...>", guidance)
        self.assertNotIn("queue_menu.py --ids`", guidance)

    def test_apply_moves_deleted_native_shell_row_to_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tsv = root / "experiments.tsv"
            header = "prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\tnegative_rc\n"
            row = "1\t-\trun_fixture_gate.sh\tD\t0.1\tN\tN\tfixture\t8\n"
            tsv.write_text(header + row, encoding="utf-8")
            SYNC.report_orphans(True, tsv=tsv, root=root)
            text = tsv.read_text(encoding="utf-8")
            self.assertNotIn("\n1\t-\trun_fixture_gate.sh", text)
            self.assertIn("#   1\t-\trun_fixture_gate.sh", text)

    def test_done_native_shell_row_stays_until_launcher_is_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tsv = root / "experiments.tsv"
            row = "1\t-\trun_fixture_gate.sh\tD\t0.1\tN\tN\tfixture\t8\n"
            tsv.write_text(
                "prio\tplan\tbatch\tgpu\thours\talone\twatch\tnote\tnegative_rc\n" + row,
                encoding="utf-8",
            )
            (root / "run_fixture_gate-done.sh").write_text("#!/usr/bin/env bash\n", encoding="ascii")
            SYNC.report_orphans(True, tsv=tsv, root=root)
            self.assertIn("\n1\t-\trun_fixture_gate.sh", tsv.read_text(encoding="utf-8"))

    def test_shell_runlog_command_is_extracted_and_python_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run_fixture-done.sh"
            path.write_text(
                '#!/usr/bin/env bash\n'
                'exec "$python_bin" scripts/runlog.py --name P000_fixture -- \\\n'
                '  "$python_bin" scripts/diag_fixture.py --steps 3\n',
                encoding="utf-8",
            )
            commands = SYNC.batch_commands(path)
            self.assertEqual(len(commands), 1)
            self.assertEqual(
                SYNC.norm(commands[0]),
                SYNC.norm("/home/user/miniforge3/envs/tlm_torch/bin/python scripts/diag_fixture.py --steps 3"),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
