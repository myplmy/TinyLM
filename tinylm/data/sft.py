# -*- coding: utf-8 -*-
"""★★SFT — **assistant-only 손실 마스크 loader**(P090 선결, 2026-09-10(2차) 구현).

## 무엇을 하나

canonical 대화(`tinylm/chat/canonical.py` 규약)를 받아
**`(input_ids, labels)`** 를 만든다. `labels` 는 **assistant 가 쓴 토큰만** 남기고
나머지를 **`-100`**(파이토치 CE 의 `ignore_index`)으로 덮는다.

## ★왜 이것이 선결인가

🚫**보통의 언어모델 손실을 SFT 대화에 그대로 걸면 모델이 *질문 쓰는 법*을 배운다.**
우리 코퍼스는 지도 토큰이 **전체의 29.9%**(실측, 2026-09-10 감사)라서
마스크가 없으면 **손실의 70.1% 가 입력 재현**에 쓰인다.

## ★규약 — 문자 구간에서 토큰 구간으로

`tinylm.chat.serialize.loss_spans()` 가 **문자 구간**을 준다(토크나이저를 안 부른다).
여기서 `tokenizers` 의 **`offsets`** 로 토큰에 매핑한다.

    문자 [s, e)  ⊃  토큰 t 의 offsets (a, b)   ⇔   a >= s and b <= e

★**부분 겹침은 포함하지 않는다.** 경계에 걸친 토큰을 넣으면 **입력의 마지막 글자**가
지도 토큰이 되고, 그것은 *"질문의 끝을 예측하라"* 는 신호다.
⚠️단 우리 어휘에 `<|im_start|>`·`<|im_end|>` 가 **아직 없어서**(P075 단계1 대기)
경계 문자열이 여러 토큰으로 쪼개진다 — 그래도 **구간이 문자 기준이라 매핑은 정확**하다.

## ★한 칸 밀림 — **여기서 처리하지 않는다**

학습 루프가 `x = ids[:-1]`, `y = ids[1:]` 로 자른다(`trainer.py` 규약).
그래서 이 loader 는 **밀지 않은 `labels`** 를 준다. 🚫**두 곳에서 밀면 한 칸 어긋난다.**
★쓰는 쪽이 `labels[1:]` 을 타깃으로 쓴다 — `sft_targets()` 가 그것을 대신 해 준다.

## 🚫이 파일이 하지 않는 것

- **학습하지 않는다.** 배치 구성·패딩은 쓰는 쪽 몫이다.
- **토크나이저를 만들지 않는다.** 받은 것을 쓴다(`tinylm.data.load_tokenizer`).
- 🚫**`train_thinking=False` 를 안 쓴다** — `loss_spans` 가 아직 블록 분할을 안 한다.
"""
from __future__ import annotations

import json
from pathlib import Path

IGNORE = -100

#: ★지도 토큰이 이 비율보다 적으면 **경고**한다. 실측 v1 = 29.9%.
#:   🚫성공 기준값이 아니라 **계측 경보**다 — 0 이면 마스크가 통째로 비었다는 뜻이다.
MIN_SUPERVISED_RATIO = 0.02


def _spans_to_token_mask(offsets, spans):
    """문자 구간 → 토큰 마스크(bool 리스트). ★**완전 포함만** 센다."""
    keep = [False] * len(offsets)
    for i, (a, b) in enumerate(offsets):
        if b <= a:                       # 특수토큰은 (0,0) 으로 오는 구현이 있다
            continue
        for s, e in spans:
            if a >= s and b <= e:
                keep[i] = True
                break
    return keep


def encode_conversation(conv, tok, kind="chatml", *, add_generation_prompt=False):
    """canonical 대화 하나 → `(ids, labels, text)`.

    `labels[i]` 는 `ids[i]` 가 **assistant 가 쓴 토큰**이면 그 값, 아니면 `IGNORE`.
    🚫**한 칸 밀지 않는다**(위 §규약).
    """
    from ..chat.serialize import serialize, loss_spans

    text = serialize(conv, kind, add_generation_prompt=add_generation_prompt)
    spans = loss_spans(conv, kind)
    enc = tok.encode(text)
    ids = list(enc.ids)
    offs = list(enc.offsets)
    keep = _spans_to_token_mask(offs, spans)
    labels = [i if k else IGNORE for i, k in zip(ids, keep)]
    return ids, labels, text


def mask_detail(conv, tok, kind="chatml"):
    """★진단용 — `ids`·`labels`·`offsets`·`spans`·`text` 를 통째로 돌려준다.

    ★**`decode()` 로 검사하지 않는다** — 합성 스텁의 `decode` 는 의미 없는 문자열을 낸다.
    ★**offsets 로 원문을 되짚는 것이 토크나이저 무관하고 더 정확**하다.
    """
    from ..chat.serialize import serialize, loss_spans

    text = serialize(conv, kind)
    spans = loss_spans(conv, kind)
    enc = tok.encode(text)
    ids, offs = list(enc.ids), list(enc.offsets)
    keep = _spans_to_token_mask(offs, spans)
    labels = [i if k else IGNORE for i, k in zip(ids, keep)]
    return {"ids": ids, "labels": labels, "offsets": offs, "spans": spans,
            "text": text, "keep": keep}


def covered_text(text, offsets, keep):
    """지도 토큰이 **원문에서 덮은 문자**를 그대로 이어 붙인다(토크나이저 무관)."""
    hit = [False] * len(text)
    for (a, b), k in zip(offsets, keep):
        if k:
            for i in range(max(0, a), min(len(text), b)):
                hit[i] = True
    return "".join(c for c, h in zip(text, hit) if h)


def sft_targets(ids, labels):
    """학습 루프 규약에 맞춘 `(x, y)`. `x = ids[:-1]` · `y = labels[1:]`.

    ★**밀기를 한 곳에서만** 한다 — `trainer.py` 가 하는 것과 같은 규약이다.
    """
    return ids[:-1], labels[1:]


def load_canonical(path):
    """canonical `.jsonl` 을 읽는다. 🚫**빈 파일이면 거절한다**(R19)."""
    p = Path(path)
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not rows:
        raise ValueError(f"{p}: canonical 레코드가 0개다")
    bad = [i for i, r in enumerate(rows) if not isinstance(r, dict) or "messages" not in r]
    if bad:
        raise ValueError(f"{p}: `messages` 가 없는 레코드 {len(bad)}개 (첫 index {bad[0]})")
    return rows


def mask_stats(rows, tok, kind="chatml"):
    """코퍼스 전체의 마스크 통계. ★**학습 전에 이 수를 본다.**

    반환 dict — `records`·`tokens`·`supervised`·`ratio`·`empty_mask`·
    `max_len`·`per_record`(지도 토큰 수 리스트).
    """
    total = sup = 0
    empty = 0
    lens, per = [], []
    for r in rows:
        ids, labels, _ = encode_conversation(r, tok, kind)
        n = len(ids)
        s = sum(1 for x in labels if x != IGNORE)
        total += n
        sup += s
        lens.append(n)
        per.append(s)
        if s == 0:
            empty += 1
    return {"records": len(rows), "tokens": total, "supervised": sup,
            "ratio": (sup / total if total else 0.0), "empty_mask": empty,
            "max_len": (max(lens) if lens else 0), "per_record": per}
