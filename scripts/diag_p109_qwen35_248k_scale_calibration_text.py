"""Run the native request contract for the calibrated packed vocabulary."""

from pathlib import Path
from unittest.mock import patch

from scripts import diag_p109_qwen35_248k_cached_kl_text as native
from scripts import diag_p109_qwen35_248k_scale_calibration as tuned


TAG = "p109_qwen35_248k_scale_calibration_text_v1_20261119"
OUT = tuned.OUT.with_name(TAG)


def main():
    original = native.original
    source = Path(__file__)
    pin = original.io.digest(source)
    assert original.io.load(tuned.OUT/"report.json")["recovery_gate"]
    with (
        patch.object(original,"OUT",OUT),
        patch.object(original,"TAG",TAG),
        patch.object(original.learned,"OUT",tuned.OUT),
        patch.object(original.learned,"PROFILE",tuned.PROFILE),
        patch.object(original.learned,"EXPORT",tuned.EXPORT),
        patch.object(native,"OUT",OUT),
        patch.object(original.engine,"compile_binaries",native.reuse_binaries),
    ):
        status=original.run(expected_updates=tuned.STEPS)
    assert original.io.digest(source)==pin
    original.io.write(OUT/"dispatch.json",dict(launcher_sha256=pin,actual_exit=status))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
