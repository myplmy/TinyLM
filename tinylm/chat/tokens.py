"""★예약 토큰 슬롯 — **어휘를 재학습하기 전에 정해야 하는 유일한 것**.

> 승인: 사용자 2026-08-30 — *"채팅 슬롯 예약 승인 -> 보수적으로 32로 수행"*
> 설계: `docs/20260829_TinyLM-채팅템플릿-설계검토와-제안.md` §6

## 왜 지금 정해야 하나

우리 임베딩은 **인수분해**(`vocab x E` + `E x d`)이고 어휘는 토크나이저 학습 시 고정된다.
🚫**어휘가 정해진 뒤에는 토큰을 못 더한다** — 행렬 shape 이 바뀌면 체크포인트가 안 맞는다.
★**P075 단계1 이 어휘를 재학습하면 그때가 마지막 기회**다.

## 비용 (E=256 기준)

토큰 하나 = 입력 행 **256** + 출력 행 **256** = **512 파라미터**.

| 슬롯 | 파라미터 | fp32 | int8 | 어휘 16,384 대비 |
|---:|---:|---:|---:|---:|
| 16 | 8,192 | 0.031 MiB | 0.008 | 0.098% |
| ★**32** | **16,384** | ★**0.063 MiB** | 0.016 | **0.195%** |

★**32 로 확정**했다. 🚫**gemma 처럼 6,242 는 안 된다** — 우리 어휘의 38% 다.

## ★이름 규약

★**`<|이름|>` 파이프 형식으로 통일**한다. 🚫**꺾쇠 단독(`<think>`)은 쓰지 않는다** —
평문(HTML·수식)에 나타날 수 있고 그러면 토크나이저가 **의도치 않게 특수토큰을 만든다**.
"""
from __future__ import annotations

# ── v1 필수 (지금 쓴다) ────────────────────────────────────────────────────
V1 = ["<|im_start|>", "<|im_end|>"]

# ── v2 reasoning (도입 시) ────────────────────────────────────────────────
V2 = ["<|think|>", "<|/think|>"]

# ── v3 도구 ───────────────────────────────────────────────────────────────
V3 = ["<|tool_call|>", "<|/tool_call|>", "<|tool_result|>", "<|/tool_result|>"]

# ── v4 멀티모달 (schema 만) ───────────────────────────────────────────────
V4 = ["<|image|>", "<|audio|>"]

#: ★예비 — **미상의 용도.** 이름을 지금 정하지 않는 것이 요점이다.
RESERVED_SPARE = [f"<|reserved_{i}|>" for i in range(22)]

#: ★**정본 목록.** 순서가 곧 토큰 id 순서다 — 🚫**한 번 정하면 안 바꾼다**(체크포인트 호환).
SLOT_NAMES = V1 + V2 + V3 + V4 + RESERVED_SPARE

#: 사용자 승인 개수
RESERVED_SLOTS = 32

assert len(SLOT_NAMES) == RESERVED_SLOTS, (
    f"슬롯 목록 {len(SLOT_NAMES)}개 != 승인 {RESERVED_SLOTS}개 — "
    "★개수를 바꾸려면 사용자 승인이 필요하다(어휘 재학습이 걸린다)")
assert len(set(SLOT_NAMES)) == len(SLOT_NAMES), "슬롯 이름 중복"
assert all(s.startswith("<|") and s.endswith("|>") for s in SLOT_NAMES), (
    "★이름 규약 위반 — `<|이름|>` 파이프 형식만 쓴다(§6.2)")


def slot_report(emb_rank: int = 256, vocab: int = 16384) -> dict:
    """슬롯 예약 비용. ★**하드코딩이 아니라 계산**한다(레버 인용 시 경로를 붙이기 위해)."""
    params = RESERVED_SLOTS * emb_rank * 2          # 입력 행 + 출력 행
    return {
        "slots": RESERVED_SLOTS,
        "emb_rank": emb_rank,
        "params": params,
        "fp32_mib": params * 4 / 1024 ** 2,
        "int8_mib": params * 1 / 1024 ** 2,
        "vocab_frac_pct": RESERVED_SLOTS / vocab * 100,
        "names": list(SLOT_NAMES),
    }


if __name__ == "__main__":                          # 값싼 자기점검
    r = slot_report()
    print(f"슬롯 {r['slots']}개 · 파라미터 {r['params']:,} · "
          f"fp32 {r['fp32_mib']:.4f} MiB · int8 {r['int8_mib']:.4f} MiB · "
          f"어휘 대비 {r['vocab_frac_pct']:.3f}%")
    for i, n in enumerate(SLOT_NAMES):
        print(f"  {i:>2} {n}")
