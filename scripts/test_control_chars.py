#!/usr/bin/env python3
"""Regression tests for valid ANSI CSI versus accidental control bytes."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import check_control_chars as check
from check_control_chars import first_bad_control


def main() -> int:
    assert first_bad_control(b"plain text\n") is None
    assert first_bad_control(b"\x1b[1;34mwandb\x1b[0m: run\n") is None
    print("[PASS] plain text and complete ANSI CSI sequences are accepted")

    assert first_bad_control(b"broken \x1b text") == (7, 0x1B)
    assert first_bad_control(b"broken \x1b[31") == (7, 0x1B)
    print("[PASS] isolated and incomplete ESC sequences are rejected")

    assert first_bad_control(b"scripts\batch") == (7, 0x08)
    print("[PASS] accidental backspace remains rejected")
    original="한글 "+chr(2)+" literal \\u0002 "+chr(10)+chr(13)+chr(9)+' "quote"'
    shown=check.display_text(original)
    assert json.loads(shown)==original
    assert first_bad_control(shown.encode()) is None
    assert not any(byte in check.BAD for byte in shown.encode())
    assert "한글" in shown
    print("[PASS] quoted display round-trips literal escapes and Korean without controls")

    for value in sorted(check.BAD):
        raw=("before"+chr(value)+"after").encode()
        assert first_bad_control(raw)==(6,value)
        assert first_bad_control(check.display_text(raw.decode()).encode()) is None
        assert not any(byte in check.BAD for byte in check.display_text(raw.decode()).encode())
    print("[PASS] every forbidden control remains detected but cannot propagate through display")

    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);source=root/"fixture.txt"
        raw=("원문"+chr(2)+chr(8)+chr(11)+" "+chr(27)+"[31m색상"+chr(27)+"[0m\n").encode()
        source.write_bytes(raw);output=io.StringIO()
        # Display a synthetic control-bearing path without creating an invalid
        # Windows filename. The real input file has an ordinary portable name.
        display_path=SimpleNamespace(read_bytes=source.read_bytes,
            relative_to=lambda unused:"fixture"+chr(2)+".txt")
        with patch.object(check,'ROOT',root),patch.object(check,'_targets',return_value=[display_path]),redirect_stdout(output):
            result=check.main()
        assert result==1 and source.read_bytes()==raw
        assert first_bad_control(output.getvalue().encode()) is None
        assert not any(byte in check.BAD for byte in output.getvalue().encode())
        assert '1파일' in output.getvalue() and '원본 로그' in output.getvalue()
    print("[PASS] actual diagnostic keeps nonzero finding and original bytes while escaping context and path")

    import check_static_all as suite
    for name,_args,reason in suite.CHECKS:
        assert first_bad_control(reason.encode()) is None,name
        assert not any(byte in check.BAD for byte in reason.encode()),name
    print("[PASS] suite description strings cannot manufacture forbidden control bytes")
    print("[PASS] control character regression 7/7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
