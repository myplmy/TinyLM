#!/usr/bin/env python3
"""CPU-only regression for strict paired input resolution and write-once output."""
from __future__ import annotations

from pathlib import Path
import tempfile

from paired_eval import preflight_inputs


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p076-paired-input-") as folder:
        base = Path(folder)
        expected = {
            "p076_a": base / "m100R1c_ko-en_300M_p076_a.pt",
            "p076_b": base / "m100R1c_ko-en_300M_p076_b.pt",
        }
        expected["p076_a"].write_bytes(b"a")
        expected["p076_b"].write_bytes(b"b")

        def resolve(preset, data, tokens, tag, must_exist=False):
            assert (preset, data, tokens, must_exist) == ("m100R1c", "ko-en", "300M", True)
            return expected[tag]

        tags = ["p076_a", "p076_b"]
        crops = base / "new-crops.json"
        assert preflight_inputs("m100R1c", "ko-en", "300M", tags, crops,
                                resolver=resolve) == expected
        assert not crops.exists()

        expected["p076_b"].unlink()
        try:
            preflight_inputs("m100R1c", "ko-en", "300M", tags, crops, resolver=resolve)
        except ValueError:
            pass
        else:
            raise AssertionError("missing second checkpoint was accepted")

        expected["p076_b"].symlink_to(expected["p076_a"])
        try:
            preflight_inputs("m100R1c", "ko-en", "300M", tags, crops, resolver=resolve)
        except ValueError:
            pass
        else:
            raise AssertionError("linked checkpoint was accepted")

        expected["p076_b"].unlink()
        expected["p076_b"].write_bytes(b"b")
        crops.write_text("already used", encoding="utf-8")
        try:
            preflight_inputs("m100R1c", "ko-en", "300M", tags, crops, resolver=resolve)
        except FileExistsError:
            pass
        else:
            raise AssertionError("existing crop output was accepted")
    print("[PASS] paired input names/missing/symlink/write-once; model/GPU NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
