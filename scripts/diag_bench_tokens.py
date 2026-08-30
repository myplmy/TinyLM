"""P080 단계0 — **저밀도 벤치마크를 토크나이저 눈으로 실사한다.** 학습 0 · GPU 0.

## 왜

held-out v2.3 은 **문자 길이**로는 균형이 맞았다(자명 전략 최대 27.0%, 우연과 0.8시그마).
🚫**그런데 우리 모델은 문자를 안 본다. 토큰을 본다.**
어휘 32,768 로 한국어 개념어를 쪼개면 **문자 길이가 같아도 토큰 길이는 다를 수 있다.**
강제선택 채점기가 로그우도를 쓰는 한 **토큰 수가 점수에 직접 들어간다.**

그리고 두 번째 질문: **그 토큰들이 학습에서 충분히 등장했는가**(Fishing for Magikarp).

## ★노름 휴리스틱을 쓰지 않는다

Magikarp 의 *"임베딩 노름이 작으면 미학습"* 은 **untied 헤드를 전제**한다.
🚫**우리는 헤드가 임베딩과 tie 돼 있고, 결과 025 §2 가 부호 역전을 실측했다**:

    사용됨(freq^>0)  32,715개  노름 중위 0.5201
    미사용(freq=0)       53개  노름 중위 0.8315   <- **더 크다**(비 1.599)

★그래서 이 도구는 **빈도를 직접 센다.** 노름은 **부수 관측으로만** 인쇄하고
🚫**판정에 쓰지 않는다.**

## 무엇을 인쇄하나

| 지표 | 판정 기준(P080 §2.3) |
|---|---|
| 정답/오답 **토큰 길이 비** 중위 | 0.95~1.05 -> ✅편향 없음 |
| 정답이 **최소 토큰**인 비율 | 25% 근처 -> ✅ |
| 빈도 **하위 0.1%** 토큰을 쓴 문항 비율 | ^< 5% ✅ / ^> 15% 🚫슬라이스 분리 |
| 빈도 **0** 토큰을 쓴 문항 | 0 이어야 한다 |

    python scripts/diag_bench_tokens.py \
        --bench datasets/TinyDataset/stage1_dataset/held-out_v2.3/stage1_heldout_benchmark_v2.3_300.json \
        --data ko-en --tokens 300M
"""
from __future__ import annotations
import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ★성공 기준값 — `check_diag_data` 가 본다(함정 32).
LEN_LO, LEN_HI = 0.95, 1.05
RARE_OK, RARE_BAD = 0.05, 0.15
RARE_PCT = 0.001                    # 하위 0.1%


def main() -> int:
    ap = argparse.ArgumentParser(description="P080 단계0 — 벤치마크 토큰 실사")
    ap.add_argument("--bench", required=True)
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--freq-cap", type=int, default=200_000_000,
                    help="빈도를 셀 학습 토큰 수(캐시 앞쪽). 전량이면 느리다")
    a = ap.parse_args()

    import numpy as np
    import tinylm                                    # noqa: F401
    from tinylm.data import prepare, tokenizer_path
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
    d = json.loads(Path(a.bench).read_text(encoding="utf-8"))
    recs = d["records"] if isinstance(d, dict) else d

    print("=" * 96)
    print("  P080 단계0 — 저밀도 벤치마크를 토크나이저 눈으로 (학습 0 · GPU 0)")
    print(f"  벤치 {Path(a.bench).name}  문항 {len(recs)}개  어휘 {tok.get_vocab_size():,}")
    print("=" * 96)

    # ── ① 후보 토큰 길이 ────────────────────────────────────────────
    ratios, rank_of_correct, tok_lens = [], collections.Counter(), []
    used = collections.Counter()
    for r in recs:
        cands = r["candidates"]
        ids = [tok.encode(c).ids for c in cands]
        L = [len(x) for x in ids]
        tok_lens += L
        ci = r["correct_index"]
        w = [x for i, x in enumerate(L) if i != ci]
        ratios.append(L[ci] / (sum(w) / len(w)))
        rank_of_correct[sum(1 for x in L if x < L[ci]) + 1] += 1
        for x in ids:
            used.update(x)

    med = statistics.median(ratios)
    n = len(recs)
    print(f"\n  [길이] 정답/오답평균 **토큰 길이비** 중위 {med:.4f}  "
          f"(0.8~1.2 안 {sum(1 for x in ratios if 0.8 <= x <= 1.2)}/{n})")
    print(f"         후보 토큰 길이 중위 {statistics.median(tok_lens):.0f}  "
          f"최소 {min(tok_lens)} 최대 {max(tok_lens)}")
    print(f"         정답의 토큰 길이 순위(짧은 쪽부터) 1/2/3/4 = "
          f"{rank_of_correct[1]}/{rank_of_correct[2]}/{rank_of_correct[3]}/{rank_of_correct[4]}"
          f"   (균등이면 각 {n//4})")
    ok_len = LEN_LO <= med <= LEN_HI
    print(f"         -> {'✅토크나이저 길이 편향 없음' if ok_len else '⚠️편향 있음 — 슬라이스로 분리한다'}"
          f"  (기준 {LEN_LO}~{LEN_HI})")

    # ── ② 학습 빈도 ─────────────────────────────────────────────────
    n_tok = int(float(a.tokens.rstrip("MmBb")) * (1e9 if a.tokens[-1] in "Bb" else 1e6))
    meta = prepare(a.data, n_tok)
    tb = np.memmap(Path(meta["dir"]) / "train.bin", dtype=np.uint16, mode="r")
    cap = min(len(tb), a.freq_cap)
    print(f"\n  [빈도] 학습 캐시 앞 {cap:,} 토큰을 센다 (전체 {len(tb):,})")
    freq = np.bincount(np.asarray(tb[:cap]), minlength=tok.get_vocab_size())
    order = np.argsort(freq)
    k = max(1, int(len(order) * RARE_PCT))
    rare = set(int(x) for x in order[:k])
    zero = set(int(x) for x in np.flatnonzero(freq == 0))
    print(f"         빈도 0 토큰 {len(zero):,}개 · 하위 {RARE_PCT:.1%} 토큰 {len(rare):,}개")

    n_rare = n_zero = 0
    for r in recs:
        ids = set()
        for c in r["candidates"]:
            ids.update(tok.encode(c).ids)
        ids.update(tok.encode(r.get("prompt", "")).ids)
        n_rare += bool(ids & rare)
        n_zero += bool(ids & zero)
    fr = n_rare / n
    print(f"         하위 {RARE_PCT:.1%} 토큰을 쓴 문항 {n_rare}/{n} = {fr:.1%}")
    print(f"         ★빈도 0 토큰을 쓴 문항 {n_zero}/{n}  (0 이어야 한다)")
    v = ("✅통과" if fr < RARE_OK else
         "🚫**그 문항들을 별도 슬라이스로 뺀다**" if fr > RARE_BAD else "⚠️경계 — 슬라이스를 만들어 둔다")
    print(f"         -> {v}  (기준 ^<{RARE_OK:.0%} 통과 / ^>{RARE_BAD:.0%} 분리)")

    # ── ③ 부수: 노름-빈도 관계 (판정에 쓰지 않는다) ──────────────────
    print(f"\n  [부수] 벤치마크가 쓰는 고유 토큰 {len(used):,}종 "
          f"(어휘의 {len(used)/tok.get_vocab_size():.1%})")
    print("         🚫**임베딩 노름은 판정에 쓰지 않는다** — 결과 025 §2 가 우리 tie 구조에서")
    print("            Magikarp 휴리스틱의 **부호 역전**을 실측했다(미사용 노름이 1.599배 크다).")
    print("=" * 96)
    print("  ⚠️이 도구는 **토크나이저와 빈도**만 본다. 문항이 좋은 문항인지는 안 본다.")
    print("  ⚠️빈도는 캐시 **앞쪽 표본**이다 — 전량이 아니면 희귀 토큰이 과대 집계될 수 있다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
