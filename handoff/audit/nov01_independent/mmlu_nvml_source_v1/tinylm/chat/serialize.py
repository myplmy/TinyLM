"""★직렬화기 — **하나의 canonical 에서 여러 문자열 규약**.

> 설계: `docs/20260829_TinyLM-채팅템플릿-설계검토와-제안.md` §5.2 · §7 (사용자 승인 2026-08-30)

## ★왜 여러 개인가 — 사용자 지시 6 의 답

*"qwen3 와 gemma-3 의 chat template 을 공통 메시지 -> 토크나이저별 직렬화기 구조로
구현해서 어느 쪽이 더 효과적인지 비교"*

→ ✅**구조는 이것으로 가능해졌다.** 🚫**그러나 지금 비교하면 무효다** —
**우리 32k 어휘에 두 후보의 경계 토큰이 다 없어서 둘 다 5~8토큰으로 쪼개진다**
(§9, `scripts/diag_chat_overhead.py`). ★**슬롯 예약(P075 단계1) 이후에 유효해진다.**

## ★TinyLM v1 = `chatml`

🚫**Gemma 문자열을 안 쓰는 이유는 단순함이 아니라 역할 이름**이다 —
Gemma 는 `model`, 우리 canonical 은 `assistant` 라 **매 턴 이름 매핑**이 필요하다.

## loss masking (§7)

| 블록 | loss |
|---|---|
| `system` · `user` · `tool_result` | 🚫**제외** — 입력이다 |
| ★**경계 토큰 `<\\|im_end\\|>`** | ✅★**포함** — 모델이 **언제 멈출지**를 배우는 곳이다 |
| `assistant` 의 `text` | ✅포함 |
| `assistant` 의 `thinking` | ⚠️**설정으로**(`train_thinking`) — 기본 포함 |
"""
from __future__ import annotations

import json

from .canonical import normalize, validate


# ─────────────────────────────────────────────────────────────────────────
#  규약별 어휘 — ★**한 곳에서만 정의한다**(R14). 새 규약은 여기 한 줄이다.
# ─────────────────────────────────────────────────────────────────────────
SPECS = {
    # 안 A / TinyLM v1 — ChatML (Qwen 계열)
    "chatml": {
        "start": "<|im_start|>", "end": "<|im_end|>", "sep": "\n",
        "roles": {"system": "system", "user": "user", "assistant": "assistant"},
        "think": ("<|think|>", "<|/think|>"),
        "call": ("<|tool_call|>", "<|/tool_call|>"),
        "result": ("<|tool_result|>", "<|/tool_result|>"),
    },
    # 안 B — Gemma 계열. ★역할 이름이 `model` 이다
    "gemma": {
        "start": "<start_of_turn>", "end": "<end_of_turn>", "sep": "\n",
        "roles": {"system": "user", "user": "user", "assistant": "model"},
        "think": ("<|think|>", "<|/think|>"),
        "call": ("<|tool_call|>", "<|/tool_call|>"),
        "result": ("<|tool_result|>", "<|/tool_result|>"),
    },
    # 안 D — 역할까지 토큰 하나로. ★가장 짧지만 어휘 슬롯을 더 먹는다
    "minimal": {
        "start": None, "end": "<|end|>", "sep": "",
        "roles": {"system": "<|sys|>", "user": "<|user|>", "assistant": "<|asst|>"},
        "think": ("<|think|>", "<|/think|>"),
        "call": ("<|tool_call|>", "<|/tool_call|>"),
        "result": ("<|tool_result|>", "<|/tool_result|>"),
    },
    # 대조군 — 특수토큰 0. ★슬롯 예약의 값어치를 재는 바닥이다
    "plain": {
        "start": None, "end": "\n", "sep": "",
        "roles": {"system": "[시스템] ", "user": "[사용자] ", "assistant": "[어시스턴트] "},
        "think": ("[생각] ", "[/생각] "),
        "call": ("[호출] ", "[/호출] "),
        "result": ("[결과] ", "[/결과] "),
    },
}

SERIALIZERS = tuple(SPECS)


def _blocks(blocks, spec, depth=0):
    """블록 목록 -> 문자열. `tool_result` 안의 중첩 블록도 같은 함수로 돈다."""
    out = []
    for b in blocks:
        t = b.get("type")
        if t == "text":
            out.append(b.get("text", ""))
        elif t == "thinking":
            a, z = spec["think"]
            out.append(f"{a}{b.get('text', '')}{z}")
        elif t == "tool_call":
            a, z = spec["call"]
            payload = json.dumps({"name": b.get("name"),
                                  "arguments": b.get("arguments", {})},
                                 ensure_ascii=False, sort_keys=True)
            out.append(f"{a}{payload}{z}")
        elif t == "tool_result":
            a, z = spec["result"]
            inner = _blocks(b.get("content", []), spec, depth + 1)
            flag = "!" if b.get("is_error") else ""
            out.append(f"{a}{flag}{inner}{z}")
        elif t in ("image", "audio"):
            out.append(f"<|{t}|>")
    return "".join(out)


def serialize(conv: dict, kind: str = "chatml", *,
              add_generation_prompt: bool = False,
              strict: bool = True) -> str:
    """canonical 대화 -> 문자열.

    `add_generation_prompt=True` 면 마지막에 **assistant 머리만** 붙인다(추론용).
    """
    if kind not in SPECS:
        raise ValueError(f"모르는 직렬화기 {kind!r} — 정본은 SERIALIZERS = {SERIALIZERS}")
    spec = SPECS[kind]
    conv = validate(normalize(conv), strict=strict)

    parts = []
    for m in conv["messages"]:
        rn = spec["roles"][m["role"]]
        body = _blocks(m["content"], spec)
        if spec["start"] is None:
            parts.append(f"{rn}{body}{spec['end']}{spec['sep']}")
        else:
            parts.append(f"{spec['start']}{rn}\n{body}{spec['end']}{spec['sep']}")
    s = "".join(parts)

    if add_generation_prompt:
        rn = spec["roles"]["assistant"]
        s += rn if spec["start"] is None else f"{spec['start']}{rn}\n"
    return s


def loss_spans(conv: dict, kind: str = "chatml", *,
               train_thinking: bool = True) -> list[tuple[int, int]]:
    """★손실을 **켤** 문자 구간 `[(start, end), ...]` 을 돌려준다.

    🚫**토큰 구간이 아니라 문자 구간**이다 — 토크나이저를 여기서 안 부른다(의존성 분리).
    쓰는 쪽이 `offsets` 로 토큰에 매핑한다.

    ★**경계 토큰 `end` 를 구간에 포함**한다(§7) — 모델이 **언제 멈출지** 배우는 곳이다.
    빼면 생성이 안 멈춘다(결과 014 §10.6 이 eos 미정지를 이미 겪었다).
    """
    spec = SPECS[kind]
    conv = validate(normalize(conv))
    spans, pos = [], 0
    for m in conv["messages"]:
        rn = spec["roles"][m["role"]]
        head = rn if spec["start"] is None else f"{spec['start']}{rn}\n"
        blocks = m["content"]
        if not train_thinking:
            blocks = [b for b in blocks if b.get("type") != "thinking"]
        body = _blocks(blocks, spec)
        whole = f"{head}{_blocks(m['content'], spec)}{spec['end']}{spec['sep']}"

        if m["role"] == "assistant":
            # ★머리(`<|im_start|>assistant\n`)는 제외, 본문 + end 는 포함
            s = pos + len(head)
            e = pos + len(head) + len(_blocks(m["content"], spec)) + len(spec["end"])
            if not train_thinking and body != _blocks(m["content"], spec):
                # thinking 을 뺐으면 구간을 잘게 나눠야 한다 — 아직 안 쓴다
                raise NotImplementedError(
                    "train_thinking=False 는 블록별 구간 분할이 필요하다. "
                    "★쓰는 쪽이 생기면 구현한다(지금 부르는 곳이 없다).")
            spans.append((s, e))
        pos += len(whole)
    return spans
