#!/usr/bin/env python3
"""Network/GPU-free regression for the WSL native PATH contract."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_SCRIPT = ROOT / "scripts" / "shell" / "tinylm_env.sh"


def main() -> int:
    env = dict(os.environ)
    env["WSL_DISTRO_NAME"] = "Ubuntu"
    env["PATH"] = "/linux/custom:/mnt/c/Windows/System32:/usr/bin:/mnt/w/blocked:/bin"
    command = (
        f"source {ENV_SCRIPT!s}; "
        "printf '%s' \"$PATH\"; "
        "python3 -c 'import subprocess; "
        "\ntry: subprocess.check_output([\"nvcc\", \"--version\"])"
        "\nexcept FileNotFoundError: print(\"NVCC_NOT_FOUND_OK\")'"
    )
    completed = subprocess.run(
        ["/usr/bin/bash", "-c", command],
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    path, marker = completed.stdout.split("NVCC_NOT_FOUND_OK", 1)
    assert marker == "\n"
    assert path == "/linux/custom:/usr/bin:/bin", path
    print("[PASS] WSL native PATH removes mounted Windows entries and nvcc lookup is FileNotFoundError")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
