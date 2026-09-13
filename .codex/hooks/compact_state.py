#!/usr/bin/env python3
"""PreCompact gate and compact-only SessionStart WIP capsule injector.

This hook only enumerates ``handoff/WIP_*_작업원장.md`` at repository root.
It never walks the repository or protected dataset paths.  Actual manual and
automatic compaction behavior remains E2E_NOT_RUN until observed in a trusted
fresh Codex session.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFF_DIR = REPO_ROOT / "handoff"
WIP_MODULE_PATH = REPO_ROOT / "scripts" / "wip.py"
PRE_COMPACT = "PreCompact"
SESSION_START = "SessionStart"
SESSION_ID_RE = re.compile(r"^- \*\*Codex 세션 ID\*\*: `([^`]+)`\s*$", re.MULTILINE)


def _configure_utf8_streams() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _open_wips(handoff_dir: Path = HANDOFF_DIR) -> list[Path]:
    return [
        path
        for path in sorted(handoff_dir.glob("WIP_*_작업원장.md"))
        if not path.name.endswith("-done.md")
    ]


def _capsule_reader(path: Path) -> str:
    spec = importlib.util.spec_from_file_location("tinylm_wip_for_compact", WIP_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {WIP_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.capsule_text(path)


def _wip_session_id(path: Path) -> str | None:
    match = SESSION_ID_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else None


def _stop(reason: str) -> dict[str, Any]:
    return {
        "continue": False,
        "stopReason": reason,
        "systemMessage": reason,
    }


def _routed_state(
    handoff_dir: Path,
    capsule_reader: Callable[[Path], str],
    session_id: str | None = None,
) -> tuple[Path | None, str | None, str | None, str | None]:
    """Route compact state without ever borrowing another session's WIP.

    A missing or unmatched session binding means there is no capsule to inject;
    it is not evidence that compaction itself is unsafe.  A duplicate exact
    binding or a stale exact-match capsule is state corruption and remains a
    fail-closed error.
    """
    wips = _open_wips(handoff_dir)
    if not wips:
        return None, None, None, None
    names = ", ".join(path.name for path in wips)
    if not session_id:
        return None, None, (
            f"compact state routing warning: session_id is missing; skipped {len(wips)} "
            f"open WIP(s) without selecting a foreign capsule ({names})"
        ), None
    matches = [path for path in wips if _wip_session_id(path) == session_id]
    if not matches:
        return None, None, (
            f"compact state routing warning: session_id {session_id!r} matched 0 WIPs; "
            f"skipped {len(wips)} open WIP(s) without selecting a foreign capsule ({names})"
        ), None
    if len(matches) > 1:
        matched = ", ".join(path.name for path in matches)
        return None, None, None, (
            f"compact state gate: session_id {session_id!r} matched {len(matches)} WIPs "
            f"({matched}); exact ownership is ambiguous"
        )
    path = matches[0]
    try:
        capsule = capsule_reader(path)
    except Exception as exc:
        return path, None, None, (
            f"compact state gate: invalid or stale capsule ({type(exc).__name__}: {exc})"
        )
    return path, capsule, None, None


def evaluate_event(
    event: Any,
    *,
    handoff_dir: Path = HANDOFF_DIR,
    capsule_reader: Callable[[Path], str] = _capsule_reader,
) -> dict[str, Any] | None:
    if not isinstance(event, dict):
        return None
    hook_event = event.get("hook_event_name")
    raw_session_id = event.get("session_id")
    session_id = raw_session_id.strip() if isinstance(raw_session_id, str) and raw_session_id.strip() else None
    if hook_event == PRE_COMPACT:
        if event.get("trigger") not in {"manual", "auto"}:
            return None
        _, _, warning, error = _routed_state(handoff_dir, capsule_reader, session_id)
        if error:
            return _stop(error)
        if warning:
            return {"continue": True, "systemMessage": warning}
        return {"continue": True, "suppressOutput": True}

    if hook_event == SESSION_START:
        if event.get("source") != "compact":
            return None
        path, capsule, warning, error = _routed_state(handoff_dir, capsule_reader, session_id)
        if error:
            return _stop(error)
        if warning:
            context = (
                "[TinyLM compact recovery v1]\n"
                f"{warning}. 현재 세션 WIP로 선택·수정·종료하지 않는다. "
                "완료·승인·NOT_RUN 상태를 추측하지 말고 현재 사용자 지시와 "
                "최신 유효 핸드오프부터 다시 확인한다."
            )
        elif path is None or capsule is None:
            context = (
                "[TinyLM compact recovery v1]\n"
                "열린 WIP 없음. 완료·승인·NOT_RUN 상태를 추측하지 말고 현재 사용자 지시와 "
                "최신 유효 핸드오프부터 다시 확인한다."
            )
        else:
            try:
                relative = path.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                relative = path.name
            context = (
                "[TinyLM compact recovery v1]\n"
                f"다음은 {relative}에서 해시 검증한 현재 상태 캡슐이다. "
                "제안→승인, NOT_RUN→PASS, 미확인→실패로 바꾸지 말고 이 상태에서 계속한다.\n\n"
                f"{capsule}"
            )
        return {
            "hookSpecificOutput": {
                "hookEventName": SESSION_START,
                "additionalContext": context,
            }
        }
    return None


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
        response = _stop(f"compact state hook internal failure: {type(exc).__name__}: {exc}")
    if response is not None:
        print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
