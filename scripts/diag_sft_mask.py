#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★★P090 선결 게이트 — **assistant-only 손실 마스크가 정말 assistant 만 덮는가**(학습 0 · GPU 0).

## 왜 이 도구가 있나 (2026-09-10(2차), 사용자 지시 3)

`tinylm/data/sft.py` 가 canonical 대화를 `(ids, labels)` 로 바꾸고 **assistant 가 쓴 토큰만**
남긴다. 🚫**그것이 "구현했다" 의 증거는 아니다** — 함정 37 의 다섯째 얼굴이 될 자리다:

> **마스크가 만들어졌다 ≠ 그 마스크가 옳은 자리를 덮는다.**

★**실패 모드 넷**을 각각 재는 것이 이 도구다:

| # | 실패 | 증상 | 검사 |
|---|---|---|---|
| **M1** | 마스크가 **통째로 비었다** | 지도 토큰 0 → 손실이 0 이거나 NaN | `supervised > 0` |
| **M2** | 마스크가 **전부 켜졌다** | 모델이 **질문 쓰는 법**을 배운다 | `ratio < 0.9` |
| ★**M3** | 경계가 **한 칸 밀렸다** | 입력의 마지막 글자가 지도 토큰이 된다 | ★**복호 대조** |
| ★**M4** | **`<|im_end|>` 가 빠졌다** | 생성이 안 멈춘다(결과 014 §10.6) | 끝 토큰이 켜져 있는가 |

## ★성공 기준값 — 결과 전에 고정한다(`check_diag_data` 요구)

- **PASS**: 지도 비율이 `[0.02, 0.90]` 안 · **빈 마스크 0건** · **M3 위반 0건** · **M4 위반 0건**
- **FAIL(exit 1)**: 위 중 하나라도 어긋난다
- ⚠️**참고값**: SFT fresh v1 의 지도 토큰 비율 **실측 29.9%**(2026-09-10 감사)

## 사용법

    python scripts/diag_sft_mask.py                       # 합성 대화 4종(파일 불필요)
    python scripts/diag_sft_mask.py --corpus datasets/TinyDataset/SFT/train/sft_fresh_v1_train_1000.canonical.jsonl
    python scripts/diag_sft_mask.py --data ko-en          # 실토크나이저(기본은 합성 스텁)

★**합성 모드가 기본**이다 — 스모크에서 **파일 없이** 돌아야 한다(2026-09-08(2차) 팔 [21c] 사고).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tinylm                                   # noqa: E402  ★R40 — HF 캐시 리다이렉트 먼저

_ = tinylm

# ★성공 기준값 (함정 32 — `check_diag_data` 가 이 상수의 존재를 본다)
RATIO_MIN = 0.02
RATIO_MAX = 0.90
SUPERVISED_MIN = 1

SAMPLE = [
    {"messages": [
        {"role": "user", "content": [{"type": "text", "text": "가람표가 무엇인가?"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "분류 전 접수물이다."}]}]},
    {"messages": [
        {"role": "system", "content": [{"type": "text", "text": "짧게 답한다."}]},
        {"role": "user", "content": [{"type": "text", "text": "둘 중 무엇인가?"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "앞의 것이다."}]}]},
    {"messages": [
        {"role": "user", "content": [{"type": "text", "text": "첫 물음"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "첫 답"}]},
        {"role": "user", "content": [{"type": "text", "text": "둘째 물음"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "둘째 답"}]}]},
    {"messages": [
        {"role": "user", "content": [{"type": "text", "text": "A" * 200}]},
        {"role": "assistant", "content": [{"type": "text", "text": "짧다"}]}]},
]


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def main() -> int:
    ap = argparse.ArgumentParser(description="SFT assistant-only 마스크 검사 (학습 0)")
    ap.add_argument("--corpus", default=None,
                    help="canonical jsonl. 미지정이면 **내장 합성 대화 4종**")
    ap.add_argument("--data", default="synthetic",
                    help="토크나이저 데이터셋. 기본 synthetic(결정적 스텁 — 파일 불필요)")
    ap.add_argument("--kind", default="chatml")
    ap.add_argument("--limit", type=int, default=0, help="코퍼스에서 앞 N개만(0=전부)")
    a = ap.parse_args()

    from tinylm.data import load_tokenizer
    from tinylm.data.sft import (IGNORE, encode_conversation, sft_targets,
                                 load_canonical, mask_stats, mask_detail, covered_text)
    from tinylm.chat.serialize import SPECS

    tok = load_tokenizer(a.data)
    rows = load_canonical(a.corpus) if a.corpus else list(SAMPLE)
    if a.limit:
        rows = rows[: a.limit]

    banner("P090 선결 — assistant-only 손실 마스크 실사 (학습 0 · GPU 0)")
    print(f"  코퍼스 = {a.corpus or '(내장 합성 4종)'}  ·  레코드 {len(rows):,}개  ·  "
          f"토크나이저 = {a.data}  ·  규약 = {a.kind}")
    print(f"  ★성공 기준: 지도 비율 [{RATIO_MIN:.0%}, {RATIO_MAX:.0%}] · 빈 마스크 0 · "
          f"M3 0 · M4 0")

    st = mask_stats(rows, tok, a.kind)
    print()
    print(f"  ── M1·M2 규모 " + "-" * 60)
    print(f"     토큰 {st['tokens']:,}  ·  ★지도 토큰 {st['supervised']:,}  ·  "
          f"★**비율 {st['ratio']:.1%}**")
    print(f"     빈 마스크 레코드 {st['empty_mask']}개  ·  최장 {st['max_len']:,} 토큰")

    fails = []
    if st["supervised"] < SUPERVISED_MIN:
        fails.append("M1 지도 토큰이 0 이다 — 마스크가 통째로 비었다")
    if st["empty_mask"]:
        fails.append(f"M1b 빈 마스크 레코드 {st['empty_mask']}개")
    if not (RATIO_MIN <= st["ratio"] <= RATIO_MAX):
        fails.append(f"M2 지도 비율 {st['ratio']:.1%} 이 [{RATIO_MIN:.0%}, {RATIO_MAX:.0%}] 밖")

    # ── M3 : 복호 대조 — 지도 토큰을 이어 붙이면 **assistant 가 쓴 글**이어야 한다
    print()
    print(f"  ── M3 경계 " + "-" * 62)
    end_tok = SPECS[a.kind]["end"]
    m3, m4, m5, shown = 0, 0, 0, 0
    for r in rows[: min(len(rows), 200)]:
        d = mask_detail(r, tok, a.kind)
        got = covered_text(d["text"], d["offsets"], d["keep"])
        # assistant 본문을 canonical 에서 직접 뽑아 비교한다(직렬화기를 다시 안 부른다).
        # ⚠️★**턴마다 따로 본다** — 여러 턴이면 덮인 글에 경계 토큰이 사이에 끼므로
        #   이어 붙인 문자열로 검사하면 **멀쩡한 마스크가 위반으로 보인다**(2026-09-10 초판 오탐).
        wants = [b.get("text", "")
                 for m in r["messages"] if m["role"] == "assistant"
                 for b in m["content"] if b.get("type") == "text"]
        miss = [w for w in wants if w and w not in got]
        if miss:
            m3 += 1
            if shown < 3:
                print("     🚫M3 위반 — 지도 구간이 assistant 본문을 안 덮는다")
                print(f"        원했다: {miss[0][:60]!r}")
                print(f"        덮었다: {got[:60]!r}")
                shown += 1
        # ★★M5 — **입력이 새어 들어왔나.** user/system 본문이 지도 구간에 있으면 안 된다.
        leak = [b.get("text", "") for m in r["messages"] if m["role"] != "assistant"
                for b in m["content"] if b.get("type") == "text"]
        if any(t and t in got for t in leak):
            m5 += 1
            if shown < 3:
                print("     🚫M5 위반 — **입력 본문이 지도 구간 안에 있다**")
                print(f"        샌 것: {[t for t in leak if t and t in got][0][:60]!r}")
                shown += 1
        # ── M4 : 경계 토큰이 지도에 포함됐는가
        if end_tok and end_tok not in got:
            m4 += 1
    if m3:
        fails.append(f"M3 경계 위반 {m3}건 — 지도 구간이 assistant 본문을 안 덮는다")
    print(f"     M3 위반 {m3}건  ·  ★M5(입력 누출) {m5}건  (검사 {min(len(rows), 200)}개)")
    # ★표지는 **고정 문자열**이어야 한다 — `smoke_diag_contract` 가 소스에서 부분문자열로 찾는다.
    #   🚫`f"M4 `{end_tok}` …"` 처럼 값이 섞이면 표와 소스가 못 만난다(2026-09-10 초판).
    print(f"     M4 경계 토큰 미포함 {m4}건  (`{end_tok}`)")
    if m5:
        fails.append(f"M5 입력 누출 {m5}건 — **user/system 본문이 지도 구간 안에 있다**")
    if m4:
        fails.append(f"M4 경계 토큰 `{end_tok}` 이 지도에서 빠진 레코드 {m4}건 — "
                     f"생성이 안 멈춘다(결과 014 §10.6)")

    # ── 밀기 규약
    print()
    print(f"  ── 밀기 규약 " + "-" * 60)
    ids, labels, _ = encode_conversation(rows[0], tok, a.kind)
    x, y = sft_targets(ids, labels)
    print(f"     ids {len(ids)} -^> x {len(x)} · y {len(y)}  "
          f"({'✅같다' if len(x) == len(y) else '🚫길이 불일치'})")
    if len(x) != len(y):
        fails.append("밀기 규약이 깨졌다 — x 와 y 의 길이가 다르다")
    print("     ★밀기는 **여기서 한 번만** 한다 — `trainer.py` 와 같은 규약이다")

    print()
    if fails:
        for f in fails:
            print(f"  🚫★**{f}**", file=sys.stderr)
        print(f"\n  🚫**실패 {len(fails)}건** — 이 마스크로 SFT 를 돌리지 않는다.", file=sys.stderr)
        return 1
    print(f"  ✅**통과** — 지도 비율 {st['ratio']:.1%} · 빈 마스크 0 · M3 0 · M4 0")
    print("  ⚠️★**이 도구는 마스크만 본다.** 그 마스크로 학습했을 때 좋아지는지는 P090 이 잰다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
