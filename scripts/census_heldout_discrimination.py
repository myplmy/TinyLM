#!/usr/bin/env python3
"""★★무변별 문항 census — **held-out 의 어느 문항이 실제로 일하는가**를 센다.

## 왜 생겼나 (2026-09-10 사용자 지시 2C 허가)

[고검정력 조사](../docs/20260908_초소형-모델에서-고검정력-계기를-만들-수-있나.md) §2 의 결론:

> ★**문제는 문항 수가 아니라 문항당 정보다.** 300문항 중 실제로 일하는 것이
> **60~103개**이고 **66~80%가 정보를 0 준다.**

그리고 [증보 요청서](../review_request/20260908_held-out-v2.7-증보-요청서.md) §2 가
**이 census 를 증보 규모의 선결**로 못박았다. §5 의 ★**D9(변별 대역 ≥60%)** 도 이 도구 몫이다.

## 무엇을 세나

| # | 이름 | 정의 |
|---|---|---|
| **B1** | 포화(쉬움) | 모든 체크포인트가 **맞힌** 문항 |
| **B2** | 바닥(어려움) | 모든 체크포인트가 **틀린** 문항 |
| ★**B3** | 변별 대역 | 문항별 정답률이 **0.3~0.7** 인 문항 |
| ★**D9** | 변별 대역 비율 | B3 / 전체 — ★**요청서 문턱 ≥60%** |
| **M** | McNemar 불일치 쌍 | 모델 쌍마다 *"한쪽만 맞힌"* 문항 수 = **실제로 일한 문항** |
| ★**I** | 문항당 정보 | 이진 엔트로피 H(p) 의 평균(bit). p = 그 문항의 모델 간 정답률 |

★**부수 산출 — 라벨 검증**: v2.8 은 `difficulty_target`·`relation` 을 스스로 붙였다.
**그 라벨이 실제 난이도와 맞는지**를 여기서 처음 확인한다.
🚫*"mid 70%"* 는 생성 측의 **주장**이고 이 도구가 **관측**이다(함정 43 회피 — 두 값이 독립이다).

## 🚫이 도구는 학습하지 않는다

체크포인트를 **읽기만** 한다. 그래도 **GPU/모델 로드**가 필요하므로 ★**AI 가 아니라 사용자가 돌린다.**

    python scripts/census_heldout_discrimination.py ^
        --models d12_cla2_r20_muon15=m100s8 d14_cla2_norecur_muon15=m100s10 ^
                 d16_cla2_norecur_muon15=m100s12 d18_cla2_norecur_muon15=m100s14 ^
        --n 4500

★**`태그=프리셋` 형태를 받는다** — 🚫`eval_bench_suite` 는 `--preset` 이 **하나뿐**이라
깊이가 다른 모델을 한 호출에 섞으면 **체크포인트를 못 찾는다**(2026-09-10 발견).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "runs" / "census"
BAND = (0.30, 0.70)
D9_MIN = 0.60


def banner(s, ch="="):
    print()
    print(ch * 96)
    print("  " + s)
    print(ch * 96)


def h2(p):
    """이진 엔트로피(bit). p=0 또는 1 이면 0 — **그 문항은 정보를 안 준다**."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def main():
    ap = argparse.ArgumentParser(description="무변별 문항 census (학습 0 · 모델 로드 있음)")
    ap.add_argument("--models", nargs="+", required=True,
                    help="`태그` 또는 `태그=프리셋`. 프리셋을 생략하면 --preset 을 쓴다")
    ap.add_argument("--preset", default="m100s12")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--task", default="stage1_heldout")
    ap.add_argument("--n", type=int, default=4500)
    ap.add_argument("--seq-max", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--device", default=None)
    ap.add_argument("--no-pmi", action="store_true")
    ap.add_argument("--out", default=None, help="결과 json 경로(기본 runs/census/<task>.json)")
    a = ap.parse_args()

    import torch
    import torch.nn.functional as F
    import random
    from tinylm import paths
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model
    from eval_bench_suite import ADAPTERS, load_rows, run_mc, _arch_of

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    tok = load_tokenizer(a.data)

    banner("★무변별 문항 census — **문항 수가 아니라 문항당 정보를 센다**", "#")
    print("  device=%s  task=%s  n=%d  PMI=%s"
          % (dev, a.task, a.n, "off" if a.no_pmi else "on"))
    print("  🚫이 도구는 **학습하지 않는다.** 체크포인트를 읽기만 한다.")

    rows = load_rows(a.task)
    rnd = random.Random(a.seed)
    idx = list(range(len(rows)))
    rnd.shuffle(idx)
    idx = sorted(idx[:min(a.n, len(rows))])
    items = [ADAPTERS[a.task](rows[i]) for i in idx]
    print("  전체 %s행 중 **%d문항** (seed=%d)" % ("{:,}".format(len(rows)), len(idx), a.seed))

    # ★라벨은 원본 행에서 가져온다(어댑터는 ctx/choices/gold 만 남긴다)
    labels = [{"id": rows[i].get("id"),
               "difficulty": rows[i].get("difficulty_target") or rows[i].get("difficulty"),
               "relation": rows[i].get("relation")} for i in idx]

    per_ok = {}
    for spec in a.models:
        tag, _, pre = spec.partition("=")
        pre = pre or a.preset
        ck = paths.resolve_ckpt(pre, a.data, a.tokens, tag)
        if not ck.exists():
            print("  [건너뜀] 체크포인트 없음: %s  (프리셋 %s)" % (ck.name, pre))
            continue
        model, cfg, _ = load_model(arch=_arch_of(tag), ckpt_path=str(ck), device=dev)
        model.eval()
        _picks, ok, _okn, sk, _ce, _mg = run_mc(a.task, items, model, tok, dev,
                                                a.seq_max, torch, F, a.no_pmi)
        if sk:
            print("  ⚠️%s — 건너뛴 문항 %d개. **문항 정렬이 어긋나므로 census 를 신뢰하지 않는다**"
                  % (tag, sk))
        per_ok[tag] = ok
        print("  %-34s (%s)  정답률 %.1f%%  N=%d"
              % (tag, pre, 100.0 * sum(ok) / max(1, len(ok)), len(ok)))
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()

    if len(per_ok) < 2:
        print("\n  🚫**모델이 2개 미만이다** — census 는 모델 간 차이를 세는 것이라 뜻이 없다.")
        return 2
    n = min(len(v) for v in per_ok.values())
    tags = list(per_ok)

    # ------------------------------------------------------------ B1·B2·B3·D9
    banner("B1·B2·B3 — **어느 문항이 실제로 일하는가**")
    rates = [sum(per_ok[t][i] for t in tags) / float(len(tags)) for i in range(n)]
    b1 = sum(1 for r in rates if r == 1.0)
    b2 = sum(1 for r in rates if r == 0.0)
    b3 = sum(1 for r in rates if BAND[0] <= r <= BAND[1])
    work = n - b1 - b2
    print("  전체 %d문항 · 체크포인트 %d개" % (n, len(tags)))
    print("  B1 전부 맞힘(포화)      %5d  (%.1f%%)" % (b1, 100.0 * b1 / n))
    print("  B2 전부 틀림(바닥)      %5d  (%.1f%%)" % (b2, 100.0 * b2 / n))
    print("  ★일한 문항(B1·B2 밖)   %5d  (%.1f%%)" % (work, 100.0 * work / n))
    d9 = b3 / float(n)
    print()
    print("  ★★D9 변별 대역(정답률 %.1f~%.1f)  %5d  (**%.1f%%**)   문턱 >=%.0f%%  -> %s"
          % (BAND[0], BAND[1], b3, 100.0 * d9, 100.0 * D9_MIN,
             "✅통과" if d9 >= D9_MIN else "🚫**미달**"))
    print("  ⚠️★체크포인트가 %d개뿐이라 문항별 정답률의 격자가 성기다"
          " — 대역 판정은 **개수를 늘릴수록** 정확해진다." % len(tags))

    # ------------------------------------------------------------ 정보량
    banner("I — 문항당 정보(bit)")
    bits = [h2(r) for r in rates]
    tot = sum(bits)
    print("  평균 %.4f bit/문항 · 합계 **%.1f bit**" % (statistics.fmean(bits), tot))
    print("  ★같은 정보를 정보 1.0 bit 짜리 문항으로만 모으면 **%d문항**이면 된다" % math.ceil(tot))
    z = sum(1 for b in bits if b == 0.0)
    print("  🚫정보 0 인 문항 %d개 (**%.1f%%**) — 이 문항들은 돌리는 시간만 쓴다"
          % (z, 100.0 * z / n))

    # ------------------------------------------------------------ McNemar
    banner("M — 모델 쌍별 McNemar 불일치 쌍 (= 그 비교에서 실제로 일한 문항)")
    print("  %-32s %-32s %8s %8s %8s" % ("A", "B", "A만맞", "B만맞", "불일치"))
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            A, B = tags[i], tags[j]
            a_only = sum(1 for k in range(n) if per_ok[A][k] and not per_ok[B][k])
            b_only = sum(1 for k in range(n) if per_ok[B][k] and not per_ok[A][k])
            print("  %-32s %-32s %8d %8d %8d" % (A, B, a_only, b_only, a_only + b_only))

    # ------------------------------------------------------------ 라벨 검증
    banner("★라벨 검증 — 생성 측의 `difficulty_target` 이 실제 난이도와 맞는가")
    by = defaultdict(list)
    for k in range(n):
        by[labels[k]["difficulty"]].append(rates[k])
    print("  %-10s %6s %10s %10s %10s" % ("라벨", "문항", "평균정답률", "변별대역%", "정보bit/문항"))
    for lab, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        band = sum(1 for r in rs if BAND[0] <= r <= BAND[1]) / float(len(rs))
        print("  %-10s %6d %9.1f%% %9.1f%% %10.4f"
              % (lab, len(rs), 100.0 * statistics.fmean(rs), 100.0 * band,
                 statistics.fmean([h2(r) for r in rs])))
    print("  ★**단조여야 한다**(easy > mid > hard 정답률). 안 그러면 라벨이 난이도가 아니다.")

    byr = defaultdict(list)
    for k in range(n):
        byr[labels[k]["relation"]].append(rates[k])
    if len(byr) > 1:
        banner("★관계 유형별 — 어느 관계가 변별을 만드나")
        print("  %-12s %6s %10s %10s" % ("relation", "문항", "평균정답률", "변별대역%"))
        for lab, rs in sorted(byr.items(), key=lambda kv: -statistics.fmean(
                [h2(r) for r in kv[1]])):
            band = sum(1 for r in rs if BAND[0] <= r <= BAND[1]) / float(len(rs))
            print("  %-12s %6d %9.1f%% %9.1f%%"
                  % (lab, len(rs), 100.0 * statistics.fmean(rs), 100.0 * band))

    # ------------------------------------------------------------ 저장
    OUT.mkdir(parents=True, exist_ok=True)
    p = Path(a.out) if a.out else OUT / ("%s_census.json" % a.task)
    p.write_bytes(json.dumps({
        "task": a.task, "n": n, "models": tags,
        "b1_saturated": b1, "b2_floor": b2, "b3_band": b3, "d9": d9,
        "bits_total": tot, "zero_info": z,
        "per_item_rate": rates,
        "ids": [labels[k]["id"] for k in range(n)],
        "per_ok": {t: per_ok[t][:n] for t in tags},
    }, ensure_ascii=False, indent=1).encode("utf-8"))
    print()
    print("  ★저장: %s" % p)
    print("  ★이 파일이 있으면 **증보 규모를 산술로 정할 수 있다** — "
          "필요 불일치 쌍 / 현재 변별 대역 비율.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
