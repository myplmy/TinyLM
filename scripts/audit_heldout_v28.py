#!/usr/bin/env python3
"""★held-out v2.8 감사기 — **증보 요청서 §5 의 D1·D6~D9 를 우리 쪽에서 다시 잰다**.

## 왜 생겼나 (2026-09-10 사용자 지시 2B)

> *"데이터셋팀에서 데이터 생성하였으나 **적절한 감사도구가 없었으므로** 감사를 위한 도구가
>  적절히 구비되어있는지 확인바람. 해당 데이터셋도 **claude가 직접 감사** 수행해야 함."*

실사 결과:

| 기존 도구 | v2.8 에 쓸 수 있나 |
|---|---|
| `check_heldout_defects.py`(D1·D1b·D4~D7) | 🚫**못 쓴다** — v2.4 계열 스키마(`answer`·`required_relations_canonical`)를 전제한다. v2.8 은 `ctx`/`choices`/`gold` 다 |
| `label_heldout_controlled.py` | ⚠️**부분** — 자명 선택기(최장/최단)는 겹치지만 v2.8 스키마 대응이 필요하다 |
| `diag_bench_overlap.py` | ✅**쓸 수 있다**(오염) — 단 토크나이저가 필요하다 |

→ **v2.8 스키마를 아는 감사기가 없었다.** 이 파일이 그것이다.

## ★이 도구가 새로 보는 것 — **정형구(boilerplate)**

v2.8 은 길이 편향을 없애려고 **모든 후보에 공통 문장 두 개**를 덧댔다. 그것이 만드는 것 둘:

1. ⚠️**희석** — 실제로 변별하는 내용이 후보 길이의 일부뿐이다. **문항당 정보**가 줄어든다
   (고검정력 조사 §2 가 지적한 바로 그 축이다).
2. 🚫★★**새 단서** — 두 번째 정형구는 **후보마다 다르다**. 그 변형이 정답과 상관되면
   **모델이 내용을 안 읽고도 맞힐 수 있다**. ★길이 단서를 없애려다 **표면 단서를 새로 만든 것**이다.

🚫**D9(변별 대역)는 이 도구가 못 잰다** — 체크포인트가 필요하다. `census_heldout_discrimination.py` 몫이다.

    python scripts/audit_heldout_v28.py
    python scripts/audit_heldout_v28.py --tokenizer data_cache/tok-ko-en-32768.json --sft
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = (ROOT / "datasets" / "TinyDataset" / "stage1_dataset" / "held-out_v2.8"
           / "stage1_heldout_benchmark_v2.8.jsonl")
SFT_TRAIN = ROOT / "datasets/TinyDataset/SFT/train/sft_fresh_v1_train_1000.canonical.jsonl"
SFT_EVAL = ROOT / "datasets/TinyDataset/SFT/eval/sft_fresh_v1_eval_300.canonical.jsonl"
V27 = (ROOT / "datasets/TinyDataset/stage1_dataset/held-out_v2.7"
       / "stage1_heldout_benchmark_v2.7_300.json")

POS_BAND = (0.22, 0.28)      # 요청서 §3 금지 3
LEN_CUE_MAX = 0.30           # 요청서 §5 D7
MID_MIN = 0.70               # 요청서 §3 난이도 규약
BOILER_MIN_SHARE = 0.02      # 이 비율 이상 반복되면 정형구로 본다

FAILS: list[str] = []
WARNS: list[str] = []


def bad(m):
    FAILS.append(m); print("  [FAIL] " + m)


def warn(m):
    WARNS.append(m); print("  [WARN] " + m)


def ok(m):
    print("  [ok]   " + m)


def info(m):
    print("         " + m)


def head(t):
    print(); print("=" * 96); print("  " + t); print("=" * 96)


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def sentences(s):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", s.strip()) if x.strip()]


def load(p: Path):
    txt = p.read_text(encoding="utf-8")
    if p.suffix == ".json":
        o = json.loads(txt)
        return o.get("records") or o.get("items") or o
    return [json.loads(x) for x in txt.splitlines() if x.strip()]


def ngrams(s, n=8):
    t = norm(s).replace(" ", "")
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT))
    ap.add_argument("--tokenizer", default=None)
    ap.add_argument("--sft", action="store_true", help="SFT fresh 와의 오염을 함께 본다")
    ap.add_argument("--dup-sample", type=int, default=800)
    a = ap.parse_args()

    p = Path(a.file)
    head("held-out v2.8 감사 — 정본은 증보 요청서 §3·§5")
    if not p.exists():
        bad("%s 가 없다" % p); return 2
    R = load(p)
    info("%s — %d문항" % (p.name, len(R)))

    tk = None
    if a.tokenizer:
        try:
            from tokenizers import Tokenizer          # type: ignore
            tk = Tokenizer.from_file(str(ROOT / a.tokenizer))
        except Exception as e:                        # noqa: BLE001
            warn("토크나이저를 못 썼다(%s) — 토큰 기준 검사를 건너뛴다" % e)

    # ------------------------------------------------------------ H1 스키마
    head("H1 스키마 · ID")
    need = ("id", "ctx", "choices", "gold", "relation", "difficulty_target", "source")
    miss = Counter()
    for r in R:
        for k in need:
            if k not in r:
                miss[k] += 1
        if len(r.get("choices") or []) != 4:
            miss["choices != 4"] += 1
        if not isinstance(r.get("gold"), int) or not (0 <= r["gold"] < 4):
            miss["gold 범위"] += 1
    if miss:
        for k, v in miss.most_common():
            bad("스키마 위반 %d건 — %s" % (v, k))
    else:
        ok("필수 키 7개 · 후보 4개 · gold 범위 — 위반 0건")
    ids = Counter(r["id"] for r in R)
    dupid = [k for k, v in ids.items() if v > 1]
    (bad if dupid else ok)("ID 중복 %d건" % len(dupid))

    # ------------------------------------------------------------ H2 위치
    head("H2 정답 위치 분포 — 요청 22~28% (§3 금지 3)")
    g = Counter(r["gold"] for r in R)
    for i in range(4):
        s = g[i] / float(len(R))
        line = "gold=%d  %.1f%% (%d건)" % (i, s * 100, g[i])
        (ok if POS_BAND[0] <= s <= POS_BAND[1] else bad)(line)

    # ------------------------------------------------------------ H3 길이 단서
    head("H3 자명 선택기 — 최장/최단 정답률 (§5 D7, 문턱 <=30%%, 우연 25%%)")

    def cue(fn, label):
        hit_long = hit_short = 0
        for r in R:
            L = [fn(c) for c in r["choices"]]
            if L.index(max(L)) == r["gold"]:
                hit_long += 1
            if L.index(min(L)) == r["gold"]:
                hit_short += 1
        for nm, h in (("최장", hit_long), ("최단", hit_short)):
            s = h / float(len(R))
            line = "%s %s 선택기 %.1f%%" % (label, nm, s * 100)
            (ok if s <= LEN_CUE_MAX else bad)(line)

    cue(lambda c: len(norm(c)), "문자")
    if tk:
        cue(lambda c: len(tk.encode(c).ids), "토큰")
    else:
        info("토큰 기준은 --tokenizer 가 있어야 한다")

    # ------------------------------------------------------------ H4 난이도
    head("H4 난이도 라벨 — 요청 mid >= 70%")
    d = Counter(r["difficulty_target"] for r in R)
    mid = d.get("mid", 0) / float(len(R))
    (ok if mid >= MID_MIN else bad)("mid %.1f%% · hard %.1f%% · easy %.1f%%"
                                    % (mid * 100, 100.0 * d.get("hard", 0) / len(R),
                                       100.0 * d.get("easy", 0) / len(R)))
    info("⚠️**라벨은 생성 측의 주장이다.** 실제 난이도는 D9(census)가 답한다.")

    # ------------------------------------------------------------ H5 배타성
    head("H5 후보 배타성 (§3 금지 4)")
    same = sum(1 for r in R if len({norm(c) for c in r["choices"]}) < 4)
    (bad if same else ok)("한 문항 안에서 후보가 문자열로 겹치는 문항 %d건" % same)

    # ------------------------------------------------------------ H6 정형구
    head("H6 ★정형구 — 문항 간 반복되는 후보 문장")
    sc = Counter()
    for r in R:
        for c in r["choices"]:
            for s in sentences(c):
                sc[norm(s)] += 1
    tot = len(R) * 4
    boiler = {s for s, n in sc.items() if n / float(tot) >= BOILER_MIN_SHARE}
    info("정형구 문장 %d종(후보의 %.0f%% 이상에 반복)" % (len(boiler), BOILER_MIN_SHARE * 100))
    for s, n in sc.most_common(6):
        info("  %5.1f%%  %s" % (100.0 * n / tot, s[:78]))
    bch = bcont = 0
    for r in R:
        for c in r["choices"]:
            ss = sentences(c)
            bch += sum(len(norm(x)) for x in ss if norm(x) in boiler)
            bcont += len(norm(c))
    share = bch / float(max(1, bcont))
    line = "후보 문자 중 정형구 몫 **%.1f%%** (고유 내용은 %.1f%%)" % (share * 100, 100 - share * 100)
    if share >= 0.40:
        bad(line + "  -> ★**문항당 정보가 희석된다**(고검정력 조사 §2 와 정반대 방향)")
    else:
        ok(line)

    # ------------------------------------- H7 정형구가 정답을 예측하는가 (새 단서)
    head("H7 ★★정형구가 정답을 예측하는가 — **길이 단서를 없애려다 만든 새 단서**")
    sig_gold = defaultdict(Counter)     # 서명 -> (정답인가) 카운트
    per_q_hit = 0
    for r in R:
        sigs = []
        for c in r["choices"]:
            s = tuple(x for x in (norm(y) for y in sentences(c)) if x in boiler)
            sigs.append(s)
        for i, s in enumerate(sigs):
            sig_gold[s][i == r["gold"]] += 1
        # ★같은 서명을 가진 후보끼리 묶어, **가장 드문 서명**을 고르는 자명 선택기
        cnt = Counter(sigs)
        rare = min(range(4), key=lambda i: (cnt[sigs[i]], i))
        if rare == r["gold"]:
            per_q_hit += 1
    rate = per_q_hit / float(len(R))
    line = "'가장 드문 정형구 서명' 선택기 정답률 **%.1f%%** (우연 25%%)" % (rate * 100)
    if rate > LEN_CUE_MAX:
        bad(line + "  -> 🚫**내용을 안 읽고도 맞힌다**")
    else:
        ok(line)
    tops = sorted(sig_gold.items(), key=lambda kv: -sum(kv[1].values()))[:6]
    info("서명별 정답 비율(상위 6종, 우연 25%):")
    for s, c in tops:
        n = sum(c.values())
        info("  %5d개 중 정답 %5.1f%%   %s"
             % (n, 100.0 * c[True] / max(1, n), (" | ".join(x[:34] for x in s))[:88] or "(정형구 없음)"))
    skew = [(sum(c.values()), c[True] / float(max(1, sum(c.values())))) for _, c in tops]
    worst = max((r for n, r in skew if n >= 200), default=0.25)
    if worst > 0.35:
        bad("어떤 정형구 서명은 정답률 **%.1f%%** — 서명이 정답과 상관된다" % (worst * 100))

    # ------------------------------------------------------------ H8 근접중복
    head("H8 문항 근접중복 (ctx 문자 8-gram 자카드, 표본 %d)" % a.dup_sample)
    S = R[:a.dup_sample]
    G = [ngrams(r["ctx"]) for r in S]
    hi = 0
    worst = 0.0
    for i in range(len(S)):
        for j in range(i + 1, len(S)):
            u = len(G[i] | G[j])
            s = (len(G[i] & G[j]) / float(u)) if u else 0.0
            if s >= 0.70:
                hi += 1
            worst = max(worst, s)
    info("최고 자카드 %.4f" % worst)
    if hi:
        warn("자카드 >= 0.70 인 문항 쌍 %d개 — 템플릿 재사용이 많다" % hi)
    else:
        ok("자카드 >= 0.70 인 쌍 0개")

    # ------------------------------------------------------------ H9 오염
    head("H9 ★D8 오염 — 금지집합과 8-gram(문자) 겹침")
    mine = set()
    for r in R:
        mine |= ngrams(r["ctx"])
        for c in r["choices"]:
            mine |= ngrams(c)
    if V27.exists():
        o = load(V27)
        other = set()
        for it in (o if isinstance(o, list) else []):
            other |= ngrams(json.dumps(it, ensure_ascii=False))
        inter = mine & other
        (warn if inter else ok)("v2.7 300문항과 8-gram 겹침 %d개" % len(inter))
    if a.sft and SFT_TRAIN.exists():
        other = set()
        for f in (SFT_TRAIN, SFT_EVAL):
            if not f.exists():
                continue
            for ln in f.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                r = json.loads(ln)
                for m in r.get("messages", []):
                    for b in m.get("content", []):
                        other |= ngrams(b.get("text", ""))
        inter = mine & other
        if inter:
            warn("SFT fresh 와 8-gram 겹침 %d개 — 예: %s"
                 % (len(inter), sorted(inter)[:4]))
        else:
            ok("SFT fresh 와 8-gram 겹침 0개 (요청서 §4-4)")
    else:
        info("--sft 를 안 줬거나 SFT 파일이 없다 — 건너뛴다")

    # ------------------------------------------------------------ H10 어휘
    head("H10 어휘·템플릿 다양성")
    if tk:
        n_tok = sum(len(tk.encode(r["ctx"]).ids)
                    + sum(len(tk.encode(c).ids) for c in r["choices"]) for r in R)
        info("전체 토큰 %s — 문항당 평균 %.0f" % ("{:,}".format(n_tok), n_tok / float(len(R))))
    heads = Counter(norm(r["ctx"])[:18] for r in R)
    info("문두 앞 18자 고유 %d종 (문항 %d개) — 최빈 %d회"
         % (len(heads), len(R), heads.most_common(1)[0][1]))
    tails = Counter(sentences(r["ctx"])[-1] if sentences(r["ctx"]) else "" for r in R)
    info("문두 마지막 문장(질문) 고유 %d종 — 최빈 %d회 (%s)"
         % (len(tails), tails.most_common(1)[0][1], tails.most_common(1)[0][0][:56]))
    if len(tails) < len(R) * 0.05:
        warn("질문 문장이 %d종뿐 — 문항 %d개에 **질문 템플릿이 %.1f개당 1종**"
             % (len(tails), len(R), len(R) / float(max(1, len(tails)))))

    # ------------------------------------------------------------ 요약
    head("요약")
    print("  실패 %d건 · 경고 %d건" % (len(FAILS), len(WARNS)))
    for m in FAILS:
        print("    [FAIL] " + m)
    for m in WARNS:
        print("    [WARN] " + m)
    print()
    print("  🚫★**D9(변별 대역 >=60%)는 이 도구가 못 잰다** — 체크포인트가 필요하다.")
    print("     `scripts/census_heldout_discrimination.py` 가 그것을 답한다.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
