#!/usr/bin/env python3
"""★채팅 템플릿의 **토큰 오버헤드**를 우리 토크나이저로 실측한다. torch 불필요(`tokenizers` 만).

## 왜 이 도구가 생겼나 (2026-08-29)

채팅 템플릿 논쟁(`docs/20260829_TinyLM-채팅템플릿-설계검토와-제안.md`)의 핵심 수는
**"경계 토큰이 몇 토큰을 먹는가"** 다. 그런데 **우리 32k 어휘에는 `<|im_start|>` 도
`<start_of_turn>` 도 없다** — 어휘에 없는 문자열은 **여러 조각으로 쪼개진다.**

★**그것이 이 실험의 전부다**: 슬롯을 예약하면 **경계 하나가 1토큰**, 안 하면 **5~8토큰**이다.
seq 1024 에서 8턴 대화면 그 차이가 **컨텍스트의 몇 %** 인지 여기서 나온다.

🚫**이 도구는 품질을 재지 않는다.** **길이만** 잰다.

사용:
    python scripts/diag_chat_overhead.py                       # 우리 ko-en 토크나이저
    python scripts/diag_chat_overhead.py --hf HF/models--Qwen3-0.6B-Base
    python scripts/diag_chat_overhead.py --turns 8 --seq 1024
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ★후보 직렬화 — 같은 대화를 네 가지로 쓴다. **내용은 동일**하다.
SYS = "너는 도움이 되는 한국어 어시스턴트다."
USER = "대한민국의 수도는 어디인가?"
ASSIST = "대한민국의 수도는 서울이다."


def build(kind: str, turns: int) -> str:
    """네 후보 직렬화. `turns` = user/assistant 왕복 횟수."""
    if kind == "chatml":                       # 안 A (Qwen 계열)
        s = f"<|im_start|>system\n{SYS}<|im_end|>\n"
        for _ in range(turns):
            s += f"<|im_start|>user\n{USER}<|im_end|>\n"
            s += f"<|im_start|>assistant\n{ASSIST}<|im_end|>\n"
        return s
    if kind == "gemma":                        # 안 B (Gemma 계열)
        s = f"<start_of_turn>user\n{SYS}\n{USER}<end_of_turn>\n"
        for _ in range(turns - 1):
            s += f"<start_of_turn>user\n{USER}<end_of_turn>\n"
        s += f"<start_of_turn>model\n{ASSIST}<end_of_turn>\n" * turns
        return s
    if kind == "minimal":                      # 안 D — 역할 이름도 토큰으로
        s = f"<|sys|>{SYS}<|end|>"
        for _ in range(turns):
            s += f"<|user|>{USER}<|end|><|asst|>{ASSIST}<|end|>"
        return s
    if kind == "plain":                        # 대조군 — 특수토큰 0
        s = f"[시스템] {SYS}\n"
        for _ in range(turns):
            s += f"[사용자] {USER}\n[어시스턴트] {ASSIST}\n"
        return s
    raise ValueError(kind)


MARKERS = {
    "chatml": ["<|im_start|>", "<|im_end|>"],
    "gemma": ["<start_of_turn>", "<end_of_turn>"],
    "minimal": ["<|sys|>", "<|user|>", "<|asst|>", "<|end|>"],
    "plain": ["[시스템]", "[사용자]", "[어시스턴트]"],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf", default=None, help="HF 모델 폴더(tokenizer.json 이 있는 곳)")
    ap.add_argument("--data", default="ko-en", help="우리 토크나이저의 데이터 이름")
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--seq", type=int, default=1024)
    a = ap.parse_args()

    try:
        from tokenizers import Tokenizer
    except ImportError:
        print("🚫 `tokenizers` 가 없다. 학습 환경에서 돌린다.")
        return 2

    if a.hf:
        tok = Tokenizer.from_file(str(Path(a.hf) / "tokenizer.json"))
        name = Path(a.hf).name
    else:
        import tinylm                                     # noqa: F401  (HF 캐시 리다이렉트)
        from tinylm.data import tokenizer_path
        tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
        name = f"TinyLM {a.data}"

    print("=" * 92)
    print(f"  채팅 템플릿 토큰 오버헤드 — {name} (vocab {tok.get_vocab_size():,})")
    print(f"  {a.turns} 왕복 · seq 예산 {a.seq}")
    print("=" * 92)

    print("\n## 1. 경계 마커 하나가 몇 토큰인가 — ★이것이 전부다")
    print(f"  {'마커':22} {'토큰수':>6}  분해")
    seen = set()
    for ms in MARKERS.values():
        for m in ms:
            if m in seen:
                continue
            seen.add(m)
            ids = tok.encode(m).ids
            piece = "".join(f"[{tok.id_to_token(i)}]" for i in ids)[:56]
            flag = " ✅단일" if len(ids) == 1 else ""
            print(f"  {m:22} {len(ids):>6}  {piece}{flag}")

    print(f"\n## 2. 같은 대화, 네 직렬화 ({a.turns} 왕복)")
    base = len(tok.encode(build("plain", a.turns)).ids)
    print(f"  {'후보':10} {'총 토큰':>8} {'오버헤드':>8} {'턴당':>7} {'seq 대비':>9}")
    rows = {}
    for kind in ("chatml", "gemma", "minimal", "plain"):
        n = len(tok.encode(build(kind, a.turns)).ids)
        rows[kind] = n
        # 내용만의 토큰 = 마커를 뺀 것 — 근사로 plain 의 대괄호 마커를 뺀 값을 쓴다
        over = n - base
        print(f"  {kind:10} {n:>8,} {over:>+8,} {over/max(a.turns,1):>7.1f} "
              f"{n/a.seq*100:>8.1f}%")
    print("  ⚠️`plain`(0) 기준 상대값이다. plain 도 `[사용자]` 같은 문자열을 쓰므로 **절대 오버헤드가 아니다**.")

    print("\n## 3. ★슬롯을 예약하면 어떻게 되나 (⚙계산)")
    for kind in ("chatml", "gemma", "minimal"):
        ms = MARKERS[kind]
        cur = sum(len(tok.encode(m).ids) for m in ms) / len(ms)
        n_marks = 2 * (a.turns * 2 + 1) if kind != "minimal" else (a.turns * 2 + 1) * 2
        save = (cur - 1) * n_marks
        print(f"  {kind:10} 마커 평균 {cur:4.1f}토큰 → 1토큰이면 **{save:,.0f} 토큰 절약** "
              f"({save/a.seq*100:.1f}% of seq {a.seq})")
    print("  ★슬롯 예약 비용 = 어휘 행 하나 = `emb_rank`(입력) + `emb_rank`(출력) 파라미터.")
    print("    E=256 이면 토큰당 512 파라미터 = fp32 2 KB. **16개 예약해도 0.03 MiB.**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
