#!/usr/bin/env python3
"""Regression for WSL SH reproduction-command append without document overwrite."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "append_repro.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("append_repro_under_test", SCRIPT)
assert spec and spec.loader
APP = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = APP
spec.loader.exec_module(APP)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_name:
        root = Path(temp_name)
        results = root / "test_result"
        results.mkdir()
        launcher = root / "run_P097_Stage1aB_control_v2_300M-done.sh"
        launcher.write_text(
            """#!/usr/bin/env bash
python_bin=/x/python
"$python_bin" scripts/runlog.py --name P097_Stage1aB_control_v2_300M --note "note"
exec "$python_bin" scripts/runlog.py --name P097_Stage1aB_control_v2_300M -- \
  "$python_bin" run100m.py train --tag p097_ctrl_v2
""",
            encoding="utf-8",
        )
        (results / "090_log_20260919_P097_Stage1aB_control_v2_300M.txt").write_text(
            "log", encoding="utf-8"
        )
        doc = results / "090_result.md"
        original = "# result 090\n\nbody sentinel\n"
        doc.write_text(original, encoding="utf-8")

        old_root, old_res, old_argv = APP.ROOT, APP.RES, sys.argv
        APP.ROOT, APP.RES = root, results
        try:
            number, mapped = APP.result_doc_for(launcher)
            assert number == "090" and mapped == doc
            sys.argv = ["append_repro.py", "--apply"]
            with contextlib.redirect_stdout(io.StringIO()):
                assert APP.main() == 0
            once = doc.read_text(encoding="utf-8")
            assert once.startswith(original.rstrip())
            assert "body sentinel" in once
            assert "run100m.py train --tag p097_ctrl_v2" in once
            with contextlib.redirect_stdout(io.StringIO()):
                assert APP.main() == 0
            assert doc.read_text(encoding="utf-8") == once
        finally:
            APP.ROOT, APP.RES, sys.argv = old_root, old_res, old_argv

    print("[PASS] append_repro: WSL SH/P-suffix mapping, preservation, idempotence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
