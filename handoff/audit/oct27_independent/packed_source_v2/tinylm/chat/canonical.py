"""★canonical 스키마 — **OpenAI/Claude 공통분모의 블록 모델**.

> 설계: `docs/20260829_TinyLM-채팅템플릿-설계검토와-제안.md` §5.1 (사용자 승인 2026-08-30)

## ★세 가지 설계 결정과 이유

| # | 결정 | 왜 |
|---|---|---|
| **1** | 🚫**`tool` role 이 없다.** `tool_result` 는 **`user` 메시지 안의 블록** | Claude 가 그렇게 한다. OpenAI 의 `role:"tool"` 은 **어댑터가 무손실로 만들 수 있지만 반대는 못 한다.** ★**좁은 쪽이 canonical 이어야 왕복이 산다** |
| **2** | 🚫**`developer` 가 별도 role 이 아니다.** `role:"system"` + `channel:"developer"` | 100M 급에 둘을 구분해 가르칠 데이터가 없다 |
| **3** | ✅**`meta.canonical_version`** | 버전이 없으면 v2 에서 기존 코퍼스를 못 읽는다. 비용 0 |

## 형태

```python
{
  "messages": [
    {"role": "system",    "content": [{"type": "text", "text": "..."}]},
    {"role": "user",      "content": [{"type": "text", "text": "..."}]},
    {"role": "assistant", "content": [
        {"type": "thinking",  "text": "..."},
        {"type": "tool_call", "id": "c1", "name": "f", "arguments": {}},
        {"type": "text",      "text": "..."}]},
    {"role": "user",      "content": [
        {"type": "tool_result", "tool_call_id": "c1",
         "content": [{"type": "text", "text": "..."}], "is_error": False}]},
  ],
  "tools": [],
  "meta": {"canonical_version": 1},
}
```

🚫**이 모듈은 토크나이저도 모델도 안 건드린다.** 순수 dict 검증·정규화다.
"""
from __future__ import annotations

CANONICAL_VERSION = 1

ROLES = ("system", "user", "assistant")
BLOCK_TYPES = ("text", "thinking", "tool_call", "tool_result", "image", "audio")

#: 어느 role 이 어떤 블록을 담을 수 있는가. ★**한 곳에서만 정의한다**(R14).
ALLOWED = {
    "system":    {"text"},
    "user":      {"text", "tool_result", "image", "audio"},
    "assistant": {"text", "thinking", "tool_call"},
}


class ChatValidationError(ValueError):
    """canonical 스키마 위반. ★**조용히 넘어가지 않는다** — 채팅 데이터의 결함은
    학습 스트림에 그대로 들어가고 거기서는 안 보인다."""


def _err(path, msg):
    raise ChatValidationError(f"{path}: {msg}")


def validate(conv: dict, *, strict: bool = True) -> dict:
    """canonical 대화를 검증한다. 통과하면 **그대로** 돌려준다(사본 아님).

    `strict=False` 면 **알 수 없는 키를 경고 없이 허용**한다(어댑터 개발용).
    ★**기본은 strict** — 규약 위반을 나중에 발견하면 코퍼스를 다시 만들어야 한다.
    """
    if not isinstance(conv, dict):
        _err("conv", f"dict 여야 한다 (지금 {type(conv).__name__})")

    meta = conv.get("meta") or {}
    ver = meta.get("canonical_version")
    if ver is None:
        _err("meta.canonical_version", "필수다 — 버전이 없으면 v2 에서 못 읽는다")
    if strict and ver != CANONICAL_VERSION:
        _err("meta.canonical_version",
             f"{ver} 은 이 코드가 아는 버전({CANONICAL_VERSION})이 아니다")

    msgs = conv.get("messages")
    if not isinstance(msgs, list) or not msgs:
        _err("messages", "비어 있지 않은 list 여야 한다")

    seen_tool_calls = set()
    for i, m in enumerate(msgs):
        p = f"messages[{i}]"
        if not isinstance(m, dict):
            _err(p, "dict 여야 한다")
        role = m.get("role")
        if role not in ROLES:
            _err(f"{p}.role", f"{role!r} 은 canonical role 이 아니다 (허용 {ROLES}). "
                              "★`tool`/`developer` 는 canonical 에 없다 — 어댑터가 변환한다")
        blocks = m.get("content")
        if not isinstance(blocks, list) or not blocks:
            _err(f"{p}.content", "비어 있지 않은 블록 list 여야 한다 "
                                 "(문자열이면 normalize() 를 먼저 부른다)")
        if role == "system" and m.get("channel") not in (None, "system", "developer"):
            _err(f"{p}.channel", f"{m.get('channel')!r} — system/developer 만 된다")

        for j, b in enumerate(blocks):
            q = f"{p}.content[{j}]"
            if not isinstance(b, dict):
                _err(q, "dict 여야 한다")
            t = b.get("type")
            if t not in BLOCK_TYPES:
                _err(f"{q}.type", f"{t!r} 은 알 수 없는 블록이다 (허용 {BLOCK_TYPES})")
            if t not in ALLOWED[role]:
                _err(f"{q}.type",
                     f"role={role!r} 은 {t!r} 블록을 담을 수 없다 (허용 {sorted(ALLOWED[role])})")
            if t in ("text", "thinking") and not isinstance(b.get("text"), str):
                _err(f"{q}.text", "문자열이어야 한다")
            if t == "tool_call":
                if not b.get("id"):
                    _err(f"{q}.id", "tool_call 은 id 가 필요하다 (tool_result 가 참조한다)")
                if not b.get("name"):
                    _err(f"{q}.name", "tool_call 은 name 이 필요하다")
                if not isinstance(b.get("arguments", {}), dict):
                    _err(f"{q}.arguments", "dict 여야 한다")
                seen_tool_calls.add(b["id"])
            if t == "tool_result":
                cid = b.get("tool_call_id")
                if not cid:
                    _err(f"{q}.tool_call_id", "tool_result 는 어느 호출의 결과인지 밝혀야 한다")
                if strict and cid not in seen_tool_calls:
                    _err(f"{q}.tool_call_id",
                         f"{cid!r} 에 대응하는 tool_call 이 **앞에** 없다 — "
                         "★순서가 뒤집히면 직렬화가 조용히 틀린다")
                if not isinstance(b.get("content"), list):
                    _err(f"{q}.content", "블록 list 여야 한다(중첩)")

    if not isinstance(conv.get("tools", []), list):
        _err("tools", "list 여야 한다")
    return conv


def normalize(conv: dict) -> dict:
    """느슨한 입력을 canonical 로 올린다. ★**새 dict 를 돌려준다**(원본 불변).

    받아 주는 것:
      · `content` 가 **문자열**이면 `[{"type": "text", "text": ...}]` 로 감싼다
      · `meta` 가 없으면 현재 버전을 넣는다
      · `tools` 가 없으면 빈 list
      · ★`role="tool"`(OpenAI 식)이면 **`user` 안의 `tool_result` 블록으로 옮긴다**

    🚫**추측해서 고치지 않는다** — 위 넷 말고는 그대로 두고 `validate` 가 잡게 한다.
    """
    out = {"messages": [], "tools": list(conv.get("tools", []) or []),
           "meta": dict(conv.get("meta") or {})}
    out["meta"].setdefault("canonical_version", CANONICAL_VERSION)

    for m in conv.get("messages", []) or []:
        m = dict(m)
        c = m.get("content")
        if isinstance(c, str):
            c = [{"type": "text", "text": c}]
        m["content"] = [dict(b) if isinstance(b, dict) else b for b in (c or [])]

        if m.get("role") == "tool":                 # ★OpenAI 어댑터 (설계 결정 1)
            cid = m.pop("tool_call_id", None) or m.pop("id", None)
            inner = m["content"]
            m = {"role": "user",
                 "content": [{"type": "tool_result", "tool_call_id": cid,
                              "content": inner, "is_error": bool(m.get("is_error"))}]}
        elif m.get("role") == "developer":           # ★설계 결정 2
            m["role"], m["channel"] = "system", "developer"
        out["messages"].append(m)
    return out
