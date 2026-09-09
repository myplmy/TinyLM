#!/usr/bin/env python3
"""★TinyDataset JSON 의 **실제 토큰 수**를 우리 토크나이저로 잰다. torch 불필요(`tokenizers` 만).

## 왜 이 도구가 생겼나 (2026-08-30)

`docs/20260829_TinyDataset-stage1-고밀도-데이터셋-품질검토.md` §10 이 분량을
**`UTF-8 바이트 / 4.366`** 으로 추정했다. 그 계수는 **일반 코퍼스**(결과 053 §S1.7.4)에서
잰 것인데, 이 데이터는 **짧고 정형화된 정의문**이라 분절이 다를 수 있다.

★**그것이 이 도구의 전부다**: 추정 계수를 쓰지 말고 **실제로 인코딩해서 센다.**
그리고 ★**그 데이터 고유의 `bytes_per_token` 을 되돌려 준다** — 다음 추정이 정확해진다.

🚫**이 도구는 품질을 안 본다.** 중복·오염은 `diag_dataset_quality.py` 다.

계측의 통과 조건은 레코드와 token 수의 정합성이다. bytes/token의 보편적인 정상 범위를 가정하지 않는다.

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
    from tinylm.audit_io import expanded_paths, read_records
    out = []
    for p in expanded_paths(patterns):
        for r in read_records(p):
            out.append(dict(r, _f=p.name))
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
    ap.add_argument("--fields", choices=["text", "all", "messages"], default="text",
                    help="text = 본문만(★현재 학습 결정) / all = concepts·relations 포함")
    ap.add_argument("--target-train", type=float, default=486000.0)
    ap.add_argument("--target-val", type=float, default=54000.0)
    ap.add_argument("--serializer", choices=("chatml", "plain", "minimal", "gemma"), default="chatml")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--overflow", choices=("error", "truncate"), default="error")
    ap.add_argument("--no-train-thinking", action="store_true")
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()
    if a.out_json and a.fields != "messages":
        ap.error("--out-json은 messages 계측에서만 지원")

    try:
        from tokenizers import Tokenizer
    except ImportError:
        print("🚫 `tokenizers` 가 없다. 학습 환경에서 돌린다.")
        return 2

    # ★★2026-09-08(3차) B1 전면이관 — `--data synthetic` 은 토크나이저 파일이 **설계상 없다**.
    #   🚫`Tokenizer.from_file(tokenizer_path(...))` 를 무조건 부르면 `os error 2` 로 죽는다(함정 45).
    #   ✅`--tok` 로 명시한 경로는 그대로 두고, 없을 때만 `load_tokenizer` 가 판단한다.
    if a.tok:
        tok = Tokenizer.from_file(a.tok)
    else:
        import tinylm                                    # noqa: F401  (HF 캐시 리다이렉트)
        from tinylm.data import load_tokenizer
        tok = load_tokenizer(a.data)

    tr = load(a.train)
    va = load(a.val)

    print("=" * 96)
    print("  TinyDataset 실제 토큰 수 — ★추정 계수를 쓰지 않는다")
    print("=" * 96)
    print(f"  토크나이저 {(os.path.basename(a.tok) if a.tok else 'load_tokenizer:' + a.data)}  vocab {tok.get_vocab_size():,}")
    print(f"  학습에 넣는 필드 = ★**{a.fields}**"
          + ("  (본문만 — 2026-08-30 사용자 결정)" if a.fields == "text" else "  (메타 포함)"))
    print("  bytes/token은 자료·직렬화기별 관측값이다. 고정 범위만으로 정상/오류를 판정하지 않는다.")

    if not tr and not va:
        print("\n🚫 레코드 0건이다 — glob 패턴을 확인한다. (측정 0건은 종료코드 1)")
        return 1

    if a.fields == "messages":
        from tinylm.chat.supervision import encode_sample, sample_totals
        from tinylm.audit_io import tokenizer_digest, write_json_new
        report = {"tokenizer_sha256": tokenizer_digest(tok), "serializer": a.serializer,
                  "seq": a.seq, "objective": "assistant"}
        for name, recs in (("train", tr), ("val", va)):
            if recs:
                samples = [encode_sample(r, tok, kind=a.serializer, max_length=a.seq + 1,
                                         train_thinking=not a.no_train_thinking,
                                         overflow=a.overflow) for r in recs]
                report[name] = sample_totals(samples)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if a.out_json:
            write_json_new(a.out_json, report)
        return 0

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
        if per_rec <= 0:
            raise ValueError("text 필드에 유효 token이 없음; messages 자료이면 --fields messages 필요")
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
