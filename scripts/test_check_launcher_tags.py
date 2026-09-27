#!/usr/bin/env python3
"""Contract fixtures for existing input tags and required BAT/SH ckpt guards."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_launcher_tags import audit_launcher, live_launchers  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        ckpt = root / "runs" / "ckpt"
        ckpt.mkdir(parents=True)
        for tag in ("p076_b3_ag2_mean_s1337", "p076_b3_ag2_attnorm_s1337"):
            (ckpt / f"m100R1c_ko-en_300M_{tag}.pt").write_bytes(b"fixture")
        head = (
            "for tag in p076_b3_ag2_mean_s1337 p076_b3_ag2_attnorm_s1337; do\n"
            "  ckpt=\"runs/ckpt/m100R1c_ko-en_300M_tied_${tag}.pt\"\n"
            "  if [[ ! -f \"$ckpt\" || -L \"$ckpt\" ]]; then exit 9; fi\n"
            "done\n"
        )
        command = (
            '"$python_bin" scripts/runlog.py --name P076_Stage2eWb -- '
            '"$python_bin" -B -X utf8 scripts/paired_eval.py '
            '--preset m100R1c --data ko-en --tokens 600M --ckpt-tokens 300M '
            '--models p076_b3_ag2_mean_s1337 p076_b3_ag2_attnorm_s1337\n'
        )
        errors, count = audit_launcher(root, root / "run_P076_Stage2eWb.sh", head + command)
        if count != 4 or not any("required checkpoint guard" in error for error in errors):
            raise AssertionError(f"historic duplicated _tied_ guard escaped: {count} {errors}")
        fixed = head.replace("_tied_${tag}", "_${tag}")
        errors, count = audit_launcher(root, root / "run_P076_Stage2eWb.sh", fixed + command)
        if errors or count != 4:
            raise AssertionError(f"real input names were rejected: {count} {errors}")
        errors, count = audit_launcher(root, root / "run_P076_Stage2eWb.sh",
                                       command.replace("p076_b3_ag2_attnorm_s1337", "missing_attnorm"))
        if count != 2 or not any("input tag absent" in error for error in errors):
            raise AssertionError(f"missing --models input was accepted: {count} {errors}")
        train = ('python run100m.py train --preset m100R1c --data ko-en --tokens 300M '
                 '--init-from-tag missing_parent --tag brand_new_output\n')
        errors, count = audit_launcher(root, root / "run_P106_Stage1.bat", train)
        if (count != 1 or not any("missing_parent" in error for error in errors)
                or any("brand_new_output" in error for error in errors)):
            raise AssertionError(f"output tag was confused with input: {count} {errors}")
        legacy = root / "run_P076_Stage2eW-done.sh"
        legacy.write_text(head + command, encoding="utf-8")
        current = root / "run_P076_Stage2eWb.sh"
        current.write_text(fixed + command, encoding="utf-8")
        if live_launchers(root) != [current]:
            raise AssertionError("historical -done launcher was treated as live")
    print("[PASS] BAT/SH input-tag existence, duplicated _tied_ guard, output-tag immunity, -done exclusion")


if __name__ == "__main__":
    main()
