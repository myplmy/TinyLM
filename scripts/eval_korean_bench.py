#!/usr/bin/env python3
"""P064 — **한국어 벤치마크(KLUE / KorQuAD)로 품질을 재는 도구.** 학습 0.

★왜 필요한가 (`docs/methods/08_paper_review.md` §12)
   우리는 지금까지 **val_loss 하나로만** 모델을 골랐다. P037 이 *"val 셋 자체가
   판정을 왜곡하는가"* 를 물어 놓고 답이 없다. **다른 자로 한 번 재 본다.**

★★이 도구가 **하지 않는** 것 — 생성 채점(EM/F1)
   우리 모델은 **100M 급 base LM 이고 SFT 를 한 적이 없다.** 지시를 안 따른다.
   EM/F1 은 전부 0 이 나오고, **0 은 모델 간 서열을 못 만든다**(재려는 차이가 0.008 이다).
   KorQuAD 2.0 논문도 **BERT-multilingual 이 F1 46.0%**(사람 85.7%)라고 보고한다.
   → 대신 **우도 채점**을 쓴다. base LM 이 정당하게 답할 수 있는 형식이고 **연속값**이다.

세 과제
   ynat     주제분류 7지선다  — 라벨 문자열의 **평균 로그우도 argmax**. 우연 14.3%
   nli      함의 3지선다      — 동                                   우연 33.3%
   korquad  KorQuAD 1.0       — ★**정답 토큰 CE(nats)** + **모델쌍 paired Δ·SE·t**

★★핵심 설계 = **paired**
   결과 049 가 증명했다 — 같은 문항 위에서 문항별 차를 보면 SE 가 0.001 대로 내려간다.
   **100문항 unpaired 로는 아무것도 안 보이지만 paired 면 보인다.**

계측 규약 (`scripts/check_diag_data.py` 계약)
   1. 절대지표에 **난수 정답을 쓰지 않는다** — 실제 dev 라벨만 쓴다
   2. **성공 기준값(우연 수준)을 먼저 인쇄**한다
   3. 문항 선택은 **고정 시드**, 문항 id 를 **로그에 남긴다**(모델마다 다른 문항이면 무효)

사용법
   python scripts/eval_korean_bench.py --task korquad --n 100 \
       --models mC_wsd mC_initonly mC_d36_ag4 p6d --preset m100R1c
   python scripts/eval_korean_bench.py --task ynat --n 500 --models mC_initonly p6d
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DS = ROOT / "datasets"
YNAT = DS / "KLUE" / "klue_benchmark" / "ynat-v1.1" / "ynat-v1.1_dev.json"
NLI = DS / "KLUE" / "klue_benchmark" / "klue-nli-v1.1" / "klue-nli-v1.1_dev.json"
KORQUAD = DS / "KorQuad" / "KorQuAD_2.1" / "KorQuAD_v1.0_dev.json"

# ★라벨 문자열은 **데이터에 있는 그대로** 쓴다. 우리가 지어내면 그건 다른 과제가 된다.
YNAT_LABELS = ["IT과학", "경제", "사회", "생활문화", "세계", "스포츠", "정치"]
NLI_LABELS = {"entailment": "맞다", "contradiction": "틀리다", "neutral": "알 수 없다"}


def banner(s, ch="="):
    print("\n" + ch * 92)
    print(f"  {s}")
    print(ch * 92)


def _arch_of(tag):
    return "dense" if tag.startswith(("p6d", "dense", "p12d")) else "tied"


# ---------------------------------------------------------------- 문항 만들기

def load_items(task, n, seed):
    """(prompt, 후보들, 정답index 또는 정답문자열, guid) 리스트를 돌려준다.

    ★고정 시드로 뽑고 **guid 를 반환**한다 — 모델마다 다른 문항이면 paired 가 무효다.
    """
    rng = random.Random(seed)
    if task == "ynat":
        d = json.loads(YNAT.read_text(encoding="utf-8"))
        rng.shuffle(d)
        out = []
        for r in d[:n]:
            p = f"다음 뉴스 제목의 분야는 무엇인가?\n제목: {r['title']}\n분야:"
            out.append((p, [" " + x for x in YNAT_LABELS],
                        YNAT_LABELS.index(r["label"]), r["guid"], None))
        return out
    if task == "nli":
        d = json.loads(NLI.read_text(encoding="utf-8"))
        rng.shuffle(d)
        keys = list(NLI_LABELS)
        out = []
        for r in d[:n]:
            p = (f"전제: {r['premise']}\n가설: {r['hypothesis']}\n"
                 f"가설은 전제에 비추어 맞다/틀리다/알 수 없다 중 무엇인가?\n답:")
            out.append((p, [" " + NLI_LABELS[k] for k in keys],
                        keys.index(r["gold_label"]), r["guid"], None))
        return out
    if task == "korquad":
        d = json.loads(KORQUAD.read_text(encoding="utf-8"))
        flat = []
        for art in d["data"]:
            for par in art["paragraphs"]:
                for qa in par["qas"]:
                    flat.append((par["context"], qa["question"],
                                 qa["answers"][0]["text"], qa["id"]))
        rng.shuffle(flat)
        out = []
        for ctx, q, ans, gid in flat[:n]:
            # ★두 프롬프트를 함께 만든다 — 두 번째는 **지문을 뺀 것**이다(§NC).
            #   차이 `CE(ans|q) − CE(ans|ctx,q)` 가 **문맥을 실제로 썼는가**를 잰다.
            #   외부 검토문서 §5 가 지적한 어휘 사전지식 교락("대한민국↔서울")의 **대조군**이고,
            #   그 문서는 문제만 적고 통제는 제안하지 않았다.
            p_ctx = f"지문: {ctx}\n질문: {q}\n답:"
            p_noctx = f"질문: {q}\n답:"
            out.append((p_ctx, [" " + ans], 0, gid, p_noctx))
        return out
    raise ValueError(task)


# ---------------------------------------------------------------- 채점

def score_continuations(model, tok, device, prompt, conts, seq_max, torch, F):
    """각 후보 이어쓰기의 **평균 로그우도**(길이 정규화)와 **합 CE** 를 돌려준다.

    ★길이 정규화를 하는 이유 — 라벨 길이가 다르다("사회" 2자 vs "생활문화" 4자).
      합으로 비교하면 **짧은 라벨이 항상 이긴다.** 그건 모델이 아니라 자의 성질이다.
    """
    pids = tok.encode(prompt).ids
    res = []
    for c in conts:
        cids = tok.encode(c).ids
        ids = pids + cids
        if len(ids) > seq_max:
            return None, len(ids)          # ★자르지 않는다 — 자르면 정답이 사라진다
        x = torch.tensor([ids[:-1]], dtype=torch.long, device=device)
        y = torch.tensor([ids[1:]], dtype=torch.long, device=device)
        with torch.no_grad(), torch.autocast(device, dtype=torch.bfloat16,
                                             enabled=(device == "cuda")):
            logits = model(x)
        ce = F.cross_entropy(logits.reshape(-1, logits.size(-1)).float(),
                             y.reshape(-1), reduction="none")
        tail = ce[-len(cids):]             # 이어쓰기 부분만
        res.append((float(tail.mean()), float(tail.sum()), len(cids)))
    return res, len(ids)


def paired_stats(a, b):
    """(평균Δ, SD, SE, t, 95%CI 반폭, A승률, 필요 N) — 외부 검토문서 §6·§7 반영.

    ★`need_n` = **목표 SE 0.002 를 얻는 데 필요한 문항 수**.
      `SE = SD/√N` 이므로 `N* = (SD/0.002)²`. **100 이 충분한지를 이 런이 스스로 답한다**
      (검토문서 §7 이 옳게 지적했다 — 1464 크롭의 SE 를 100문항에 옮겨 적을 수 없다).
    """
    d = [x - y for x, y in zip(a, b)]
    m = statistics.fmean(d)
    sd = statistics.stdev(d) if len(d) > 1 else 0.0
    se = sd / math.sqrt(len(d)) if d else 0.0
    t = m / se if se else 0.0
    ci = 1.96 * se
    win = sum(1 for v in d if v > 0) / len(d) * 100
    need = int(math.ceil((sd / 0.002) ** 2)) if sd else 0
    return m, sd, se, t, ci, win, need


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="KLUE/KorQuAD 우도 채점 (학습 0)")
    ap.add_argument("--task", choices=["ynat", "nli", "korquad"], required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seq-max", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=99)     # val 크롭 규약과 같은 고정값
    ap.add_argument("--device", default=None)
    a = ap.parse_args()

    import torch
    import torch.nn.functional as F
    from tokenizers import Tokenizer
    from tinylm import paths
    from tinylm.data import tokenizer_path
    from tinylm.infer.generate import load_model

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    banner("P064 — 한국어 벤치마크 **보조 진단**(auxiliary diagnostic) · 학습 0 · 생성 0", "#")
    # ★★명명 규약 (외부 검토문서 §2·§3·§4·§12 반영, 2026-08-21)
    #   공식 metric 과 **이름을 섞지 않는다** — 공식 YNAT = macro F1(KLUE 논문 §3.1.2),
    #   공식 NLI = accuracy(§3.3.2), 공식 KorQuAD = EM/F1. 우리가 내는 것은 전부 다른 양이다.
    print("  🚫★이 도구가 내는 점수는 **공식 benchmark score 가 아니다.**")
    print("     공식 YNAT = macro F1 (KLUE 논문 §3.1.2) · 공식 NLI = accuracy (§3.3.2)")
    print("     · 공식 KorQuAD = EM/F1.  우리 것은 다음 이름으로만 부른다:")
    print("       ynat/nli  -> label-likelihood accuracy (auxiliary)")
    print("       korquad   -> gold-answer conditional CE (auxiliary)")
    print(f"  task={a.task}  n={a.n}  seed={a.seed}  device={dev}  seq_max={a.seq_max}")

    # ★규약 2 — 성공 기준값을 **먼저** 인쇄한다(함정 34: 게이트를 나중에 지어내지 않는다)
    chance = {"ynat": 100 / len(YNAT_LABELS), "nli": 100 / len(NLI_LABELS),
              "korquad": None}[a.task]
    if chance is not None:
        print(f"  ★성공 기준값: 우연 수준 = {chance:.1f}%. **이보다 낮으면 모델이 아니라 "
              f"프롬프트를 먼저 의심한다.**")
    else:
        print("  ★성공 기준값: 절대 CE 에는 기준선이 없다. **모델 간 paired Δ 로만 읽는다.**")
        print("  ⚠️ CE 절대값을 val_loss 와 비교하지 않는다 — 다른 분포·다른 자다(함정 1).")

    items = load_items(a.task, a.n, a.seed)
    print(f"  문항 {len(items)}개 로드. guid 예시: {items[0][3]} … {items[-1][3]}")

    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))

    per_item, acc, skipped = {}, {}, {}
    no_ctx, ans_len = {}, {}
    for tag in a.models:
        ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, tag)
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {ck.name}")
            continue
        model, cfg, _ = load_model(arch=_arch_of(tag), ckpt_path=str(ck), device=dev)
        vals, hit, nskip, lens, alens, nc = [], 0, 0, [], [], []
        for prompt, conts, gold, _gid, p_noctx in items:
            r, tot = score_continuations(model, tok, dev, prompt, conts,
                                         a.seq_max, torch, F)
            if r is None:
                nskip += 1
                vals.append(None)
                nc.append(None)
                continue
            lens.append(tot)
            means = [m for m, _s, _n in r]
            alens.append(r[0][2])              # ★정답(또는 라벨) 토큰 길이 — 검토문서 §8
            if a.task == "korquad":
                vals.append(means[0])           # gold-answer conditional CE
                # ★NC 대조군 — 지문을 뺀 같은 정답의 CE. 차이가 "문맥 이용도" 다.
                r2, _ = score_continuations(model, tok, dev, p_noctx, conts,
                                            a.seq_max, torch, F)
                nc.append(float(r2[0][0]) if r2 else None)
            else:
                pick = min(range(len(means)), key=lambda i: means[i])
                hit += int(pick == gold)
                vals.append(float(pick == gold))
                nc.append(None)
        per_item[tag] = vals
        no_ctx[tag] = nc
        ans_len[tag] = alens
        skipped[tag] = nskip
        n_ok = len(items) - nskip
        acc[tag] = (hit / n_ok * 100) if (a.task != "korquad" and n_ok) else None
        ok_vals = [v for v in vals if v is not None]
        mean = statistics.fmean(ok_vals) if ok_vals else float("nan")
        print(f"\n  {tag:<18} n={n_ok:<4} 건너뜀={nskip:<3} "
              f"{'label-LL 정확도 %.1f%%' % acc[tag] if acc[tag] is not None else 'gold-answer CE %.4f' % mean}")
        print(f"      전체 토큰길이 중앙값 {statistics.median(lens) if lens else 0:.0f}"
              f"  ·  정답 토큰길이 중앙값 {statistics.median(alens) if alens else 0:.0f}"
              f"  (최대 {max(alens) if alens else 0})")
        if a.task == "korquad":
            pair = [(v, w) for v, w in zip(vals, nc) if v is not None and w is not None]
            if pair:
                gain = statistics.fmean(w - v for v, w in pair)
                print(f"      ★문맥 이용도 CE(ans|q) − CE(ans|ctx,q) = {gain:+.4f}"
                      f"  (양수면 지문이 실제로 도움이 됐다)")
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()

    if len(per_item) < 2:
        print("\n  비교할 모델이 2개 미만이다.")
        return 2

    # ★공통 문항만 — 어느 모델이든 건너뛴 문항은 **전부** 뺀다(paired 전제)
    tags = list(per_item)
    keep = [i for i in range(len(items))
            if all(per_item[t][i] is not None for t in tags)]
    print(f"\n  ★paired 대상 공통 문항 {len(keep)}개 "
          f"(전체 {len(items)} 중 {len(items) - len(keep)}개는 어느 모델이 건너뛰어 제외)")

    banner("paired 비교 — 같은 문항 위에서 문항별 차 (95% CI · 필요 N 포함)")
    unit = "CE(nats)" if a.task == "korquad" else "정답률"
    print(f"  {'A':<16}{'B':<16}{'Δ(A−B) ' + unit:>16}{'SD':>9}{'SE':>9}"
          f"{'95%CI±':>9}{'t':>7}{'A승률':>8}{'필요N':>8}")
    print("  " + "-" * 98)
    needs = []
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            A, B = tags[i], tags[j]
            va = [per_item[A][k] for k in keep]
            vb = [per_item[B][k] for k in keep]
            m, sd, se, t, ci, win, need = paired_stats(va, vb)
            needs.append(need)
            print(f"  {A:<16}{B:<16}{m:>+16.4f}{sd:>9.4f}{se:>9.4f}"
                  f"{ci:>9.4f}{t:>7.2f}{win:>7.1f}%{need:>8}")

    # ★★검토문서 §7 반영 — **100 은 확정 표본이 아니라 pilot 이다**
    if needs:
        banner("표본 크기 판정 — 이 런이 스스로 답한다")
        print(f"  관측 SD 로 계산한 **목표 SE 0.002 를 얻는 데 필요한 문항 수**: "
              f"최대 {max(needs)}개 (현재 {len(keep)}개)")
        if max(needs) > len(keep):
            print(f"  🚫★**부족하다.** 이번 런은 **pilot** 이고, 본 측정은 --n {max(needs)} 이상으로 다시 돈다.")
        else:
            print("  ✅ 현재 표본으로 목표 SE 를 만족한다.")
        print("  ⚠️ 1464 크롭 full-val 의 SE(0.0011~0.0014)를 이 표본에 옮겨 적지 않는다 —")
        print("     **모집단이 다르다**(외부 검토문서 §7 이 옳게 지적한 지점).")

    print("\n  ⚠️ |t| ^< 2 는 **구분 불가**다. 부호만 보고 서열을 매기지 않는다.")
    print("  ⚠️ 이것은 **체크포인트 간** 비교다. 아키텍처 우열은 여기서 나오지 않는다"
          "(paired_eval 과 같은 한계).")
    print("  🚫★**공식 benchmark score 가 아니다**(§명명 규약). 문서에도 그 이름으로 적지 않는다.")
    if a.task == "korquad":
        print("  ★CE 는 **낮을수록 좋다** — Δ 가 음수면 A 가 낫다.")
        print("  ★**문맥 이용도가 0 근처면** 이 지표는 QA 가 아니라 **어휘 사전지식**을 재고 있다"
              "(검토문서 §5).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
