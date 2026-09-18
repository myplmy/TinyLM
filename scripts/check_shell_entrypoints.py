#!/usr/bin/env python3
"""Static-only validation for shared Linux/WSL entrypoints. GPU/model work: 0."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parent.parent
COMMON_SHELL_FILES = (
    ROOT / "run_queue.sh",
    ROOT / "run_cleanup_checkpoints.sh",
    ROOT / "run_smoke_check.sh",
    ROOT / "scripts" / "shell" / "tinylm_env.sh",
)


def shell_files() -> tuple[Path, ...]:
    """공통 진입점과 루트의 모든 실험/게이트 SH를 빠짐없이 검사한다."""
    root_entries = tuple(sorted(ROOT.glob("run_P*.sh")))
    return COMMON_SHELL_FILES + root_entries


def experiment_log_contract_errors(path: Path, data: bytes) -> list[str]:
    """Every P-plan shell entry must preserve stdout through runlog.

    The queue deliberately only invokes entrypoints.  Without this contract a
    native WSL gate can print PASS/FAIL and return the right status while
    silently leaving no evidence in test_result.
    """
    if not path.name.startswith("run_P") or not path.name.endswith(".sh"):
        return []
    text = data.decode("utf-8", errors="replace")
    active = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    runlog_lines = [line for line in active if "scripts/runlog.py" in line]
    errors = []
    if not runlog_lines:
        errors.append("does not invoke scripts/runlog.py")
        return errors
    joined = " ".join(active)
    if "--name P" not in joined:
        errors.append("runlog name does not start with a P-plan number")
    if " -- " not in joined:
        errors.append("runlog child delimiter `--` is missing")
    return errors


def find_bash() -> str | None:
    if os.name != "nt":
        return shutil.which("bash")
    # Do not accept Windows System32/bash.exe: that is a WSL launcher, not Git Bash.
    probe = subprocess.run(
        ["git", "--exec-path"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if probe.returncode != 0:
        return None
    git_exec = Path(probe.stdout.strip())
    if len(git_exec.parents) >= 3:
        candidate = git_exec.parents[2] / "bin" / "bash.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def to_bash_path(path: Path | PureWindowsPath, *, windows: bool | None = None) -> str:
    windows = os.name == "nt" if windows is None else windows
    if not windows:
        return str(path)
    raw = str(path if isinstance(path, PureWindowsPath) else path.resolve())
    win_path = PureWindowsPath(raw)
    drive = win_path.drive.rstrip(":").lower()
    if not drive:
        return win_path.as_posix()
    tail = "/".join(win_path.parts[1:])
    return f"/{drive}/{tail}"


def main() -> int:
    errors: list[str] = []
    entries = shell_files()
    for path in entries:
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(ROOT).as_posix()}")
            continue
        data = path.read_bytes()
        if not data.startswith(b"#!/usr/bin/env bash\n"):
            errors.append(f"bad shebang: {path.relative_to(ROOT).as_posix()}")
        if b"\r" in data:
            errors.append(f"CR byte found: {path.relative_to(ROOT).as_posix()}")
        if os.name != "nt" and not os.access(path, os.X_OK):
            errors.append(f"not executable: {path.relative_to(ROOT).as_posix()}")
        for detail in experiment_log_contract_errors(path, data):
            errors.append(
                f"experiment log contract {path.relative_to(ROOT).as_posix()}: {detail}"
            )

    bash = find_bash()
    if bash is None:
        errors.append("bash executable not found; shell syntax NOT_RUN")
    else:
        for path in entries:
            if not path.is_file():
                continue
            completed = subprocess.run(
                [bash, "-n", to_bash_path(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()
                errors.append(
                    f"bash -n {path.relative_to(ROOT).as_posix()}: {detail}"
                )

    commands = (
        [sys.executable, str(ROOT / "scripts" / "smoke_module.py"), "--check"],
        [sys.executable, str(ROOT / "scripts" / "queue_menu_linux.py"), "--audit"],
    )
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).strip()
            errors.append(f"{Path(command[1]).name} rc={completed.returncode}: {detail}")

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        print(f"[shell-entrypoints] errors={len(errors)}")
        return 1
    print(
        f"[PASS] shell entrypoints={len(entries)}; "
        "LF/shebang/mode/bash syntax/runlog/smoke grammar/Linux queue audit"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
