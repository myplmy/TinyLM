#!/usr/bin/env python3
"""Codex PreToolUse guard for risky backslash escapes in shell write commands.

This hook is deliberately narrow. It does not try to authorize commands or replace
Codex permissions. It only blocks a known class of accidental text corruption.
Unrecognized input and internal failures are fail-open; internal failures emit a
visible warning so the skipped protection is not mistaken for a pass.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HOOK_EVENT = "PreToolUse"
SHELL_TOOL = "Bash"
SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWLIST_PATH = SCRIPT_DIR / "backslash_whitelist.tsv"

CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
RISKY_ESCAPE_RE = re.compile(
    r"""
    \\
    (?:
        [ntrbfv]
        | 0[0-7]{0,2}
        | x[0-9A-Fa-f]{2}
        | u[0-9A-Fa-f]{4}
        | U[0-9A-Fa-f]{8}
    )
    """,
    re.VERBOSE,
)

# Windows paths naturally contain backslashes. Mask clear path-shaped tokens before
# looking for escape sequences so C:\temp\new.txt does not look like tab/newline data.
WINDOWS_PATH_RE = re.compile(
    r"""
    (?:
        \b[A-Z]:\\[^\s'"|><;]+
        | \\\\[^\s'"|><;]+
        | (?<!\w)\.{1,2}\\[^\s'"|><;]+
        | (?<![\w.])(?:[\w.@-]+\\)+[\w.@-]+\.[A-Z0-9]{1,12}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

NULL_REDIRECT_RE = re.compile(
    r"""
    (?:
        (?:^|\s)\d*>{1,2}\s*(?:/dev/null|NUL|\$null)(?=\s|$)
        | 2>&1
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

WRITE_INTENT_RES = (
    re.compile(r"(?:^|\s)\d*>{1,2}(?![&=])"),
    re.compile(
        r"(?i)\b(?:Set-Content|Add-Content|Out-File|Export-Csv|Export-Clixml)\b"
    ),
    re.compile(r"(?i)\b(?:tee|Tee-Object)\b"),
    re.compile(r"(?i)\b(?:sed|perl)\b[^\r\n]*(?:\s-i|\s-pi)\b"),
    re.compile(r"(?i)\b(?:write_text|write_bytes|writelines)\s*\("),
    re.compile(r"(?i)\.write\s*\("),
    re.compile(r"""(?ix)\bopen\s*\([^)]*,\s*['"][wax](?:[bt+]{0,2})['"]"""),
    re.compile(r"(?i)\[(?:System\.)?IO\.File\]::(?:Write|Append|Create)"),
    re.compile(r"(?m)^\s*<<-?\s*['\"]?[A-Za-z_][A-Za-z0-9_]*['\"]?\s*$"),
)


def _configure_utf8_streams() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _load_allow_tokens(path: Path = ALLOWLIST_PATH) -> tuple[str, ...]:
    tokens: list[str] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = raw_line.split("\t")
        if len(fields) < 2 or fields[0].strip() != "escape":
            raise ValueError(f"unsupported allowlist row at line {line_number}")
        token = fields[1].strip()
        if not token:
            raise ValueError(f"empty allow token at line {line_number}")
        tokens.append(token)
    if not tokens:
        raise ValueError("allowlist has no escape token")
    return tuple(dict.fromkeys(tokens))


def _has_write_intent(command: str) -> bool:
    without_null_redirects = NULL_REDIRECT_RE.sub(" ", command)
    return any(pattern.search(without_null_redirects) for pattern in WRITE_INTENT_RES)


def _risky_markers(command: str) -> list[str]:
    markers: list[str] = []
    if CONTROL_CHARACTER_RE.search(command):
        markers.append("actual-control-character")

    masked = WINDOWS_PATH_RE.sub("<WINDOWS_PATH>", command)
    for match in RISKY_ESCAPE_RE.finditer(masked):
        marker = match.group(0)
        if marker not in markers:
            markers.append(marker)
    return markers


def _warning(message: str) -> dict[str, str]:
    return {"systemMessage": message}


def _deny(markers: list[str]) -> dict[str, Any]:
    marker_text = ", ".join(markers[:5])
    reason = (
        "Codex 전용 역슬래시 보호 훅이 쓰기 명령에서 위험한 이스케이프를 감지했습니다"
        f" ({marker_text}). here-string, apply_patch 또는 안전한 파일 API를 사용하고, "
        "의도한 리터럴이면 backslash_whitelist.tsv의 명시 토큰을 명령에 포함하십시오."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": HOOK_EVENT,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def evaluate_event(
    event: Any, *, allowlist_path: Path = ALLOWLIST_PATH
) -> dict[str, Any] | None:
    """Return a hook response, or None when the command should continue silently."""

    if not isinstance(event, dict):
        return None
    if event.get("hook_event_name") != HOOK_EVENT:
        return None
    if event.get("tool_name") != SHELL_TOOL:
        return None

    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    if not _has_write_intent(command):
        return None

    markers = _risky_markers(command)
    if not markers:
        return None

    try:
        allow_tokens = _load_allow_tokens(allowlist_path)
    except Exception as exc:
        return _warning(
            "Codex 역슬래시 보호 훅의 예외 목록을 읽지 못해 검사를 건너뛰었습니다 "
            f"({type(exc).__name__}). 명령 내용을 직접 확인하십시오."
        )

    matched_token = next((token for token in allow_tokens if token in command), None)
    if matched_token is not None:
        return _warning(
            "Codex 역슬래시 보호 훅의 명시적 예외 토큰을 사용했습니다. "
            "실행 전 리터럴 역슬래시가 의도된 것인지 다시 확인하십시오."
        )

    return _deny(markers)


def main() -> int:
    _configure_utf8_streams()
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return 0

    try:
        response = evaluate_event(event)
    except Exception as exc:
        response = _warning(
            "Codex 역슬래시 보호 훅 내부 오류로 검사를 건너뛰었습니다 "
            f"({type(exc).__name__}). 명령 내용을 직접 확인하십시오."
        )

    if response is not None:
        print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
