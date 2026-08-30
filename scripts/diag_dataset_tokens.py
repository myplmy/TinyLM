#!/usr/bin/env python3
"""★TinyDataset JSON 의 **실제 토큰 수**를 우리 토크나이저로 잰다. torch 불필요(`tokenizers` 만).

## 왜 이 도구가 생겼나 (2026-08-30)

`docs/20260829_TinyDataset-stage1-고밀도-데이터셋-품질검토.md` §10 이 분량을
**`UTF-8 바이트 / 4.366`** 으로 추정했다. 그 계수는 **일반 코퍼스**(결과 053 §S1.7.4)에서
잰 것인데, 이 데이터는 **짧고 정형화된 정의문**이라 분절이 다를 수 있다.

★**그것이 이 도구의 전부다**: 추정 계수를 쓰지 말고 **실제로 인코딩해서 센다.**
그리고 ★**그 데이터 고유의 `bytes_per_token` 을 되돌려 준다** — 다음 추정이 정확해진다.

🚫**이 도구는 품질을 안 본다.** 중복·오염은 `diag_dataset_quality.py` 다.

★★**성공 시 나와야 하는 값**(함정 34 — 기준값을 먼저 적는다)
  · `bytes_per_token` 이 **3.0 ~ 6.0** 대역이면 정상이다.
    **1.0 미만이면 토크나이저가 안 맞은 것**이고, **10 초과면 인코딩이 깨진 것**이다.
  · 레코드 수 × 평균 토큰이 총 토큰과 맞아야 한다(자명하지만 0 을 잡는다).
  · 🚫**레코드 0건이면 종료코드 1** — "측정 0, 종료 0" 은 최악의 실패 양식이다(R19).

사용:
    python scripts/diag_dataset_tokens.py --train "datasets/.../train/*_v*.json"
    python scripts/diag_dataset_tokens.py --train "..." --val "..." --fields text
    python scripts/diag_dataset_tokens.py --train "..." --target-train 486000
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))   # ★2026-08-30 — 이 줄이 없어 P075 단계0b 가 죽었다.
#   스크립트를 직접 실행하면 sys.path[0] 은 scripts/ 라 tinylm 을 못 찾는다.


def load(patterns):
    """glob 여러 개 -> 레코드 목록. `records`/`data`/최상위 list 를 다 받는다."""
    out = []
    for pat in patterns or []:
        for p in sorted(glob.glob(pat)):
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            rs = d if isinstance(d, list) else (d.get("records") or d.get("data") or [])
            for r in rs:
                r["_f"] = os.path.basename(p)
                out.append(r)
    return out


def text_of(rec, fields):
    """`fields` 가 'text' 면 본문만, 'all' 이면 메타까지 이어 붙인다."""
    if fields == "text":
        return rec.get("text", "") or ""
    parts = [rec.get("text", "") or ""]
    for k in ("concepts", "relations"):
        v = rec.get(k) or []
        parts.append(" ".join(str(x) for x in v))
    return " ".join(p for p in parts if p)


def measure(tok, recs, fields):
    n_tok, n_byte, per = 0, 0, []
    for r in recs:
        s = text_of(r, fields)
        k = len(tok.encode(s).ids)
        n_tok += k
        n_byte += len(s.encode("utf-8"))
        per.append(k)
    return n_tok, n_byte, per


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="*", help="glob 패턴(여러 개 가능)")
    ap.add_argument("--val", nargs="*", help="glob 패턴")
    ap.add_argument("--tok", default=None, help="tokenizer.json 경로(기본 = ko-en 32768)")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--fields", choices=["text", "all"], default="text",
                    help="text = 본문만(★현재 학습 결정) / all = concepts·relations 포함")
    ap.add_argument("--target-train", type=float, default=486000.0)
    ap.add_argument("--target-val", type=float, default=54000.0)
    a = ap.parse_args()

    try:
        from tokenizers import Tokenizer
    except ImportError:
        print("🚫 `tokenizers` 가 없다. 학습 환경에서 돌린다.")
        return 2

    if a.tok:
        tp = a.tok
    else:
        import tinylm                                    # noqa: F401  (HF 캐시 리다이렉트)
        from tinylm.data import tokenizer_path
        tp = str(tokenizer_path(a.data))
    tok = Tokenizer.from_file(tp)

    tr = load(a.train)
    va = load(a.val)

    print("=" * 96)
    print("  TinyDataset 실제 토큰 수 — ★추정 계수를 쓰지 않는다")
    print("=" * 96)
    print(f"  토크나이저 {os.path.basename(tp)}  vocab {tok.get_vocab_size():,}")
    print(f"  학습에 넣는 필드 = ★**{a.fields}**"
          + ("  (본문만 — 2026-08-30 사용자 결정)" if a.fields == "text" else "  (메타 포함)"))
    print("  ★★기준값: bytes_per_token 이 3.0~6.0 이면 정상 · 1.0 미만이면 토크나이저 불일치")

    if not tr and not va:
        print("\n🚫 레코드 0건이다 — glob 패턴을 확인한다. (측정 0건은 종료코드 1)")
        return 1

    rows = []
    for name, recs, target in (("train", tr, a.target_train), ("val", va, a.target_val)):
        if not recs:
            continue
        n_tok, n_byte, per = measure(tok, recs, a.fields)
        bpt = n_byte / n_tok if n_tok else 0.0
        rows.append((name, recs, n_tok, n_byte, bpt, per, target))

    print(f"\n{'구분':>6} {'레코드':>8} {'바이트':>12} {'★토큰':>11} "
          f"{'bytes/tok':>10} {'토큰/레코드':>11} {'목표대비':>9}")
    print("-" * 96)
    for name, recs, n_tok, n_byte, bpt, per, target in rows:
        print(f"{name:>6} {len(recs):>8,} {n_byte:>12,} {n_tok:>11,} "
              f"{bpt:>10.3f} {statistics.fmean(per):>11.1f} "
              f"{n_tok / target * 100:>8.1f}%")
    print("-" * 96)

    print("\n## ★추정 계수와의 대조 — 종전 추정이 얼마나 틀렸나")
    EST = 4.366
    for name, recs, n_tok, n_byte, bpt, per, target in rows:
        est = n_byte / EST
        err = (est - n_tok) / n_tok * 100 if n_tok else 0.0
        flag = "✅" if abs(err) < 5 else ("⚠️" if abs(err) < 15 else "🚫★")
        print(f"  {name:>6}  ⚙추정({EST}) {est:>10,.0f}  vs  ✅실측 {n_tok:>10,}  "
              f"오차 {err:>+6.1f}%  {flag}")
    print(f"  ★이 데이터 고유의 bytes_per_token = "
          + " · ".join(f"{n} **{b:.3f}**" for n, _, _, _, b, _, _ in rows))
    print("  → ★다음 추정에는 이 값을 쓴다(일반 코퍼스 계수가 아니라).")

    print("\n## ★남은 분량")
    for name, recs, n_tok, n_byte, bpt, per, target in rows:
        need = max(0.0, target - n_tok)
        per_rec = statistics.fmean(per)
        print(f"  {name:>6}  목표 {target:>9,.0f}  현재 {n_tok:>9,}  "
              f"부족 {need:>9,.0f}  = ⚙레코드 {need / per_rec:>7,.0f}건 "
              f"(150건/파일이면 **{need / per_rec / 150:.1f}파일**)")

    print("\n" + "=" * 96)
    print("  🚫**이 도구는 분량만 센다.** 중복·오염은 `diag_dataset_quality.py`,")
    print("     학습 스트림 오염은 `diag_common_text.py` 다.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
