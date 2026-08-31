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
# ★★2026-08-31 신설 — **자명 선택기 게이트**(결과 068 §오류 E3).
#   종전에는 비율 중위(0.9712)만 보고 ✅ 를 찍었는데, 같은 출력의 순위 분포가
#   156/41/73/30 이었다. **최단 선택 52.0% = 우연 25% 에서 10.8σ** 다.
#   비율 중위는 **크기**를 재고 순위 분포는 **방향의 일관성**을 잰다 — 다른 양이다(함정 40).
#   ⚠️동점 처리: "최단이 여럿이면 무작위" 를 가정해 1/동점수 로 센다.
#     그래야 데이터셋팀이 문자 길이로 쓰던 *"최장선택 39.0% -> 25.0%"* 와 같은 단위가 된다.
TRIVIAL_MAX_SIGMA = 3.0             # |z| 이 이 값을 넘으면 자명 선택기가 산다


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
    trivial_short = trivial_long = 0.0        # ★자명 선택기의 기대 정답률(동점=무작위)
    # ★★2026-08-31 — **문자 축도 함께 인쇄한다**(결과 068 §7.1).
    #   v2.3 은 문자 기준으로 최단·최장 둘 다 **정확히 25.0%** 인데 토큰 기준은 52.0% 였다.
    #   두 축을 한 출력에 나란히 두지 않으면 *"데이터셋 팀이 실패했다"* 로 잘못 읽는다 —
    #   실제로는 **시킨 것을 정확히 해냈고 두 축이 독립**이다.
    char_short = char_long = 0.0
    for r in recs:
        cands = r["candidates"]
        ids = [tok.encode(c).ids for c in cands]
        L = [len(x) for x in ids]
        C = [len(c) for c in cands]
        tok_lens += L
        ci = r["correct_index"]
        w = [x for i, x in enumerate(L) if i != ci]
        ratios.append(L[ci] / (sum(w) / len(w)))
        rank_of_correct[sum(1 for x in L if x < L[ci]) + 1] += 1
        if L[ci] == min(L):
            trivial_short += 1.0 / L.count(min(L))
        if L[ci] == max(L):
            trivial_long += 1.0 / L.count(max(L))
        if C[ci] == min(C):
            char_short += 1.0 / C.count(min(C))
        if C[ci] == max(C):
            char_long += 1.0 / C.count(max(C))
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
    ok_ratio = LEN_LO <= med <= LEN_HI
    print(f"         -> {'✅길이비 통과' if ok_ratio else '⚠️길이비 편향'}"
          f"  (기준 {LEN_LO}~{LEN_HI})")

    # ── ①-b ★자명 선택기 — **비율 중위가 통과해도 여기서 죽을 수 있다** ────────
    k = max(len(r["candidates"]) for r in recs)
    chance = 1.0 / k
    sd = (chance * (1 - chance) / n) ** 0.5
    zs = (trivial_short / n - chance) / sd
    zl = (trivial_long / n - chance) / sd
    print(f"\n  [자명] ★**길이만 보는 선택기**의 정답률 (우연 {chance:.1%}, "
          f"1σ {sd:.1%}, 동점은 무작위)")
    print(f"         {'축':<8}{'최단':>10}{'z':>9}{'최장':>10}{'z':>9}")
    print(f"         {'문자':<8}{char_short / n:>10.1%}"
          f"{(char_short / n - chance) / sd:>+8.1f}σ{char_long / n:>10.1%}"
          f"{(char_long / n - chance) / sd:>+8.1f}σ")
    print(f"         {'★토큰':<8}{trivial_short / n:>10.1%}{zs:>+8.1f}σ"
          f"{trivial_long / n:>10.1%}{zl:>+8.1f}σ")
    print("         ⚠️★**두 축은 독립이다** — 문자를 맞춰도 토큰이 쏠릴 수 있다"
          "(결과 068 §7.1: v2.3 은 문자 25.0/25.0 인데 토큰 52.0 이었다).")
    print("         ★**판정은 토큰 축으로 한다** — 모델이 보는 것이 그쪽이다.")
    ok_triv = abs(zs) <= TRIVIAL_MAX_SIGMA and abs(zl) <= TRIVIAL_MAX_SIGMA
    if ok_triv:
        print(f"         -> ✅자명 선택기가 안 산다  (기준 |z| ^<= {TRIVIAL_MAX_SIGMA:g})")
    else:
        print(f"         -> 🚫★**자명 선택기가 산다** (기준 |z| ^<= {TRIVIAL_MAX_SIGMA:g})")
        print(f"            ★**문자 길이를 맞춘 것으로는 부족하다** — 모델은 토큰을 본다.")
        print(f"            🚫**이 벤치마크의 절대 정답률을 능력으로 인용하지 않는다.**")
        print(f"            기준선을 우연 {chance:.1%} 가 아니라 "
              f"**{max(trivial_short, trivial_long) / n:.1%}** 로 적는다.")
    ok_len = ok_ratio and ok_triv
    print(f"\n  [길이 종합] -> "
          f"{'✅토크나이저 길이 편향 없음' if ok_len else '⚠️편향 있음 — 슬라이스로 분리한다'}")

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
    # ── ★종료코드 — **인쇄와 판정이 갈라지지 않게**(함정 38) ─────────────
    #   2026-08-31 이전에는 무조건 0 이었다. 결과 068 이 자명 선택기 52.0% 를
    #   인쇄하면서 exit 0 · ✅ 를 함께 찍었고, 배치는 성공으로 넘어갔다.
    fails = []
    if not ok_ratio:
        fails.append(f"길이비 중위 {med:.4f} 가 {LEN_LO}~{LEN_HI} 밖")
    if not ok_triv:
        fails.append(f"자명 선택기 최단 {trivial_short / n:.1%}(z {zs:+.1f}) "
                     f"· 최장 {trivial_long / n:.1%}(z {zl:+.1f})")
    if fr > RARE_BAD:
        fails.append(f"희귀 토큰 문항 {fr:.1%} ^> {RARE_BAD:.0%}")
    if n_zero:
        fails.append(f"빈도 0 토큰 문항 {n_zero}건")

    print("=" * 96)
    print("  ⚠️이 도구는 **토크나이저와 빈도**만 본다. 문항이 좋은 문항인지는 안 본다.")
    print("  ⚠️빈도는 캐시 **앞쪽 표본**이다 — 전량이 아니면 희귀 토큰이 과대 집계될 수 있다.")
    if fails:
        print("\n  🚫**실패 " + str(len(fails)) + "건**")
        for f in fails:
            print(f"     · {f}")
        print("  ★이 벤치마크를 지금 쓰면 **점수가 능력이 아니라 형식을 잰다.**")
        return 1
    print("\n  ✅전 게이트 통과 — 이 벤치마크는 토크나이저 쪽에서 깨끗하다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
