#!/usr/bin/env python3
"""★★**벤치마크 전수 평가 — 13종. 학습 0.**

## 왜 전부 구현하는가 (사용자 지시 2026-08-22)

> *"사용자 제안 벤치마크는 **예상되는 결과와 무관하게 모두 구현**할 것."*
> *"실제 SFT 학습내용과 무관하게 **실제 검사하여 결과를 확인할 필요는 있음**."*

★★**동의한다. 그리고 내 종전 판단을 철회한다.**
`docs/methods/11_benchmarks.md` §3.2 는 IFEval·HE+·BFCLv3·MuSR·GSM8K 를 **기각**했는데,
그 기각의 근거는 *"점수가 0 일 것"* 이었다. **그건 기각 사유가 아니라 예측**이다.
🚫**예측으로 측정을 대신하면 그 예측은 영원히 검증되지 않는다** — 의사결정함정 D1 계열.
→ ★**전부 구현하고, 0 이 나오면 0 을 기록한다.**

⚠️★**다만 "구현" 과 "채점" 이 다른 과제가 있다** — 아래 §채점 한계를 반드시 읽는다.

## 네 가지 채점 방식

| kind | 무엇 | 과제 |
|---|---|---|
| ★**mc** | 후보별 **평균 로그우도 + PMI 보정** argmax | hellaswag piqa winogrande arc_e arc_c boolq mmlu mmlu_redux musr |
| ★**cloze** | 마지막 단어 **정확 일치 + PPL** | lambada |
| ★**gen** | 그리디 생성 후 규칙 채점 | gsm8k ifeval |
| ★**gen_save** | 그리디 생성 후 **파일로 저장**(채점은 외부 하네스) | humaneval humaneval_plus bfcl_v3 |

### ★채점 한계 — **숨기지 않는다**

| 과제 | 우리가 하는 것 | 🚫**우리가 못 하는 것** |
|---|---|---|
| **HumanEval / HE+** | 생성 + **문법 검사**(`ast.parse`) + **정답 CE** | 🚫**pass@1** — 생성된 코드를 **실행**해야 한다. 우리는 **모델이 만든 코드를 실행하지 않는다.** `--out-jsonl` 로 저장하니 공식 `evalplus` 하네스로 사용자가 채점한다 |
| **BFCL v3** | 생성 + **AST 파싱 성공률** + 정답 CE | 🚫**공식 AST/실행 채점** — 서버 상태가 필요한 항목이 있다 |
| **IFEval** | 생성 + **검증 가능한 제약 8종** 자체 구현 | ⚠️공식은 25종. **우리 8종은 부분집합**이고 그렇게 인쇄한다 |
| **GSM8K** | 생성 EM + ★**정답 CE**(보조 지표) | — |

★**보조 지표 `정답 CE` 를 함께 재는 이유**: **정확도가 0 이어도 CE 는 연속값**이라
**모델 간 서열을 만든다.** 결과 050 이 KorQuAD 에서 쓴 것과 같은 수법이다.
⚠️**단 필요 N 을 함께 인쇄**한다 — KorQuAD 는 24만이 필요했다.

## 계측 규약 (`docs/methods/11_benchmarks.md` §4, 8개 전부 지킨다)

    1 우연 수준을 결과보다 먼저 인쇄     5 prompt 에는 loss 를 주지 않는다
    2 공식 metric 이름을 우리 지표에 안 쓴다  6 SD·SE·95%CI·필요N 을 함께 인쇄
    3 고정 시드 + 문항 id 로그            7 퇴화 감지(한 라벨 90% 초과)
    4 모델 간 공통 문항만 비교            8 PMI 정규화

사용법
    python scripts/fetch_bench_data.py --all              # 먼저 (사용자, 네트워크)
    python scripts/eval_bench_suite.py --task hellaswag --n 500 \
        --models mC_initonly mC_d36_ag4_nokd --preset m100R1c
    python scripts/eval_bench_suite.py --task all --n 200 --models mC_initonly
    python scripts/eval_bench_suite.py --task lambada --n 500 --models ... --wandb
"""
from __future__ import annotations

import argparse
import ast as _ast
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "datasets" / "bench"

# ── 과제 등록부. ★**단일 소스다** — 목록을 두 곳에 두지 않는다(폐기 원장 D-04)
#    (kind, 우연 수준(정확도 과제만), 공식 metric 이름, 한 줄 설명)
TASKS = {
    "hellaswag":      ("mc",       0.25,  "acc / acc_norm",   "4지선다 문장완성"),
    "piqa":           ("mc",       0.50,  "acc",              "2지선다 물리상식"),
    "winogrande":     ("mc",       0.50,  "acc",              "2지선다 대명사해소"),
    "arc_easy":       ("mc",       0.25,  "acc / acc_norm",   "4지선다 과학"),
    "arc_challenge":  ("mc",       0.25,  "acc / acc_norm",   "4지선다 과학(난)"),
    # ★★0a-2 조회 정정(arXiv:1905.10044 초록) — **majority-baseline 62%**.
    #   50% 를 우연으로 쓰면 **퇴화(항상 yes)를 "우연 초과" 로 오독**한다.
    "boolq":          ("mc",       0.62,  "acc(vs 다수결62%)", "예/아니오 ⚠️다수결 62%"),
    "mmlu":           ("mc",       0.25,  "acc",              "4지선다 57과목"),
    "mmlu_redux":     ("mc",       0.25,  "acc",              "MMLU 재라벨"),
    # ⚠️★0a-2 조회(arXiv:2310.16049) — 지문이 **약 1000단어**다. seq 1024 토큰으로는
    #   대부분 **길이 초과로 제외**될 것이다. 제외 수를 반드시 읽는다.
    "musr":           ("mc",       0.50,  "acc",              "다단계추론 ⚠️1000단어"),
    "lambada":        ("cloze",    None,  "acc / ppl",        "★마지막 단어 예측"),
    "gsm8k":          ("gen",      0.00,  "EM(strict)",       "다단계 산술"),
    "ifeval":         ("gen",      None,  "prompt/inst acc",  "지시 따르기(부분집합)"),
    "humaneval":      ("gen_save", 0.00,  "pass@1",           "코드 생성 🚫실행 안 함"),
    "humaneval_plus": ("gen_save", 0.00,  "pass@1",           "HE+ 🚫실행 안 함"),
    "bfcl_v3":        ("gen_save", 0.00,  "AST acc",          "함수 호출 🚫실행 안 함"),
}


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def _arch_of(tag):
    return "dense" if tag.startswith("dense") else "tied"


def load_rows(task):
    p = BENCH / f"{task}.jsonl"
    if not p.exists():
        raise FileNotFoundError(
            f"{p} 가 없다. 먼저 `python scripts/fetch_bench_data.py --only {task}` 를 돌리세요.")
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


# ─────────────────────────────────────────────────────────────── 어댑터
# ★각 어댑터는 원본 행을 우리 공통 형식으로 바꾼다.
#   mc      -> {"ctx": str, "choices": [str…], "gold": int}
#   cloze   -> {"ctx": str, "gold": str}
#   gen     -> {"ctx": str, "gold": str, "meta": {...}}
# ⚠️**필드 이름은 데이터카드마다 다르다.** 없으면 `KeyError` 로 즉사시킨다 —
#   조용히 빈 문자열을 넣으면 **우연 수준이 나오고 그것을 모델 탓으로 읽는다**(함정 31).

def _ad_hellaswag(r):
    ctx = (r["ctx_a"] + " " + r["ctx_b"].capitalize()) if r.get("ctx_b") else r["ctx"]
    ctx = f"{r['activity_label']}: {ctx}"
    return {"ctx": ctx, "choices": [" " + c.strip() for c in r["endings"]], "gold": int(r["label"])}


def _ad_piqa(r):
    return {"ctx": f"Question: {r['goal']}\nAnswer:",
            "choices": [" " + r["sol1"], " " + r["sol2"]], "gold": int(r["label"])}


def _ad_winogrande(r):
    # ★공식 규약(lm-eval-harness): 빈칸을 후보로 **치환**하고 **빈칸 뒤쪽만** 채점한다.
    #   앞부분이 후보마다 같으면 그 부분의 우도는 서열에 기여하지 못한다.
    i = r["sentence"].index("_")
    tail = r["sentence"][i + 1:]
    return {"ctx": None, "gold": int(r["answer"]) - 1,
            "pairs": [(r["sentence"][:i] + r[f"option{k}"], tail) for k in (1, 2)]}


def _ad_arc(r):
    ch = r["choices"]
    keys = list(ch["label"])
    gold = keys.index(r["answerKey"]) if r["answerKey"] in keys else -1
    return {"ctx": f"Question: {r['question']}\nAnswer:",
            "choices": [" " + t for t in ch["text"]], "gold": gold}


def _ad_boolq(r):
    return {"ctx": f"{r['passage']}\nQuestion: {r['question']}?\nAnswer:",
            "choices": [" no", " yes"], "gold": int(bool(r["answer"]))}


def _ad_mmlu(r):
    ch = r["choices"]
    q = f"The following is a multiple choice question about {r.get('subject','knowledge')}.\n\n{r['question']}\n"
    for k, c in zip("ABCD", ch):
        q += f"{k}. {c}\n"
    return {"ctx": q + "Answer:", "choices": [f" {k}" for k in "ABCD"[:len(ch)]],
            "gold": int(r["answer"])}


def _ad_mmlu_redux(r):
    ch = r["choices"] if isinstance(r.get("choices"), list) else \
        [r[k] for k in ("A", "B", "C", "D") if k in r]
    gold = r.get("answer", r.get("correct_answer"))
    gold = int(gold) if str(gold).isdigit() else "ABCD".index(str(gold).strip()[:1])
    q = f"{r['question']}\n" + "".join(f"{k}. {c}\n" for k, c in zip("ABCD", ch))
    return {"ctx": q + "Answer:", "choices": [f" {k}" for k in "ABCD"[:len(ch)]], "gold": gold}


def _ad_musr(r):
    # MuSR 은 선택지가 **문자열로 직렬화된 리스트**로 오는 판이 있다.
    ch = r["choices"]
    if isinstance(ch, str):
        ch = _ast.literal_eval(ch)
    return {"ctx": f"{r['narrative']}\n\n{r['question']}\nAnswer:",
            "choices": [" " + str(c) for c in ch], "gold": int(r["answer_index"])}


def _ad_lambada(r):
    t = r["text"].rstrip()
    i = t.rindex(" ")
    return {"ctx": t[:i], "gold": t[i:]}          # 앞 공백 포함 = 토큰 경계 보존


def _ad_gsm8k(r):
    ans = r["answer"]
    final = ans.split("####")[-1].strip().replace(",", "")
    return {"ctx": f"Question: {r['question']}\nAnswer:", "gold": final,
            "gold_full": " " + ans.strip(), "meta": {}}


def _ad_ifeval(r):
    return {"ctx": r["prompt"], "gold": None,
            "meta": {"ids": r.get("instruction_id_list", []), "kw": r.get("kwargs", [])}}


def _ad_humaneval(r):
    return {"ctx": r["prompt"], "gold": r.get("canonical_solution", ""),
            "meta": {"task_id": r.get("task_id", "")}}


def _ad_bfcl(r):
    q = r.get("question") or r.get("prompt") or ""
    if isinstance(q, list):
        q = " ".join(str(x.get("content", x)) if isinstance(x, dict) else str(x) for x in q)
    fn = json.dumps(r.get("function", r.get("tools", [])), ensure_ascii=False)[:1500]
    return {"ctx": f"Available functions: {fn}\nUser: {q}\nFunction call:",
            "gold": json.dumps(r.get("ground_truth", ""), ensure_ascii=False),
            "meta": {"id": r.get("id", "")}}


ADAPTERS = {
    "hellaswag": _ad_hellaswag, "piqa": _ad_piqa, "winogrande": _ad_winogrande,
    "arc_easy": _ad_arc, "arc_challenge": _ad_arc, "boolq": _ad_boolq,
    "mmlu": _ad_mmlu, "mmlu_redux": _ad_mmlu_redux, "musr": _ad_musr,
    "lambada": _ad_lambada, "gsm8k": _ad_gsm8k, "ifeval": _ad_ifeval,
    "humaneval": _ad_humaneval, "humaneval_plus": _ad_humaneval, "bfcl_v3": _ad_bfcl,
}


# ─────────────────────────────────────────────────────────── 채점 도구
def seq_ce(model, tok, device, prompt, cont, seq_max, torch, F):
    """`cont` 부분의 (평균CE, 합CE, 토큰수). 길이 초과면 None."""
    pids = tok.encode(prompt).ids if prompt else [tok.encode("\n").ids[0]]
    cids = tok.encode(cont).ids
    if not cids:
        return None
    ids = pids + cids
    if len(ids) > seq_max:
        return None                                # ★자르지 않는다 — 자르면 정답이 사라진다
    x = torch.tensor([ids[:-1]], dtype=torch.long, device=device)
    y = torch.tensor([ids[1:]], dtype=torch.long, device=device)
    with torch.no_grad(), torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
        logits = model(x)
    ce = F.cross_entropy(logits.reshape(-1, logits.size(-1)).float(), y.reshape(-1),
                         reduction="none")
    tail = ce[-len(cids):]
    return float(tail.mean()), float(tail.sum()), len(cids)


def greedy(model, tok, device, prompt, max_new, seq_max, torch, stop=None):
    """그리디 생성. ★샘플링을 쓰지 않는다 — **재현 가능해야** 모델 비교가 성립한다."""
    ids = tok.encode(prompt).ids
    if len(ids) + max_new > seq_max:
        ids = ids[-(seq_max - max_new):]           # ⚠️생성 과제는 앞을 자른다(정답은 뒤에 있다)
    out = []
    for _ in range(max_new):
        x = torch.tensor([ids], dtype=torch.long, device=device)
        with torch.no_grad(), torch.autocast(device, dtype=torch.bfloat16,
                                             enabled=(device == "cuda")):
            logits = model(x)
        nxt = int(logits[0, -1].argmax())
        ids.append(nxt)
        out.append(nxt)
        txt = tok.decode(out)
        if stop and any(s in txt for s in stop):
            break
    return tok.decode(out)


def wilson(k, n):
    """★이항 비율의 **Wilson 95% CI**. 정규근사는 0·1 근처에서 무너진다 —
    우리는 **0 이 나올 것을 알면서** 재므로 정규근사를 쓰면 CI 가 [0,0] 이 된다."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def paired_stats(a, b):
    d = [x - y for x, y in zip(a, b)]
    m = statistics.fmean(d)
    sd = statistics.stdev(d) if len(d) > 1 else 0.0
    se = sd / math.sqrt(len(d)) if d else 0.0
    return m, sd, se, (m / se if se else 0.0), 1.96 * se, \
        (sum(1 for v in d if v > 0) / len(d) * 100 if d else 0.0), \
        (int(math.ceil((sd / 0.002) ** 2)) if sd else 0)


# ─────────────────────────────────────────────────── IFEval 제약 검증기
# ⚠️★**공식은 25종이다. 아래는 8종 = 부분집합**이고 그렇게 인쇄한다.
#   구현 못 한 제약은 **"미평가"** 로 세지 **"실패"로 세지 않는다** — 둘을 섞으면
#   점수가 모델 탓처럼 보인다(함정 31 계열).
def ifeval_check(iid, kw, resp):
    kw = kw or {}
    if iid.endswith("number_words"):
        n = len(resp.split())
        rel, want = kw.get("relation"), kw.get("num_words")
        if want is None:
            return None
        return n >= want if rel == "at least" else n <= want
    if iid.endswith("number_sentences"):
        n = len([s for s in re.split(r"[.!?]+", resp) if s.strip()])
        rel, want = kw.get("relation"), kw.get("num_sentences")
        if want is None:
            return None
        return n >= want if rel == "at least" else n <= want
    if iid.endswith("existence") and kw.get("keywords"):
        return all(k.lower() in resp.lower() for k in kw["keywords"])
    if iid.endswith("forbidden_words") and kw.get("forbidden_words"):
        return not any(k.lower() in resp.lower() for k in kw["forbidden_words"])
    if iid.endswith("english_lowercase"):
        return resp == resp.lower()
    if iid.endswith("english_capital"):
        return resp == resp.upper()
    if iid.endswith("number_bullet_lists"):
        n = len(re.findall(r"^\s*[\*\-]\s", resp, re.M))
        return n == kw.get("num_bullets") if kw.get("num_bullets") is not None else None
    if iid.endswith("quotation"):
        r = resp.strip()
        return len(r) >= 2 and r[0] == '"' and r[-1] == '"'
    return None                                    # ★미구현 = 미평가. 실패가 아니다


# ─────────────────────────────────────────────────────────────── 본체
def run_mc(task, items, model, tok, dev, seq_max, torch, F, no_pmi):
    """평균 로그우도 + ★PMI 보정. `acc_norm`(합CE/길이) 도 함께 낸다."""
    picks, ok, ok_norm, skipped, per_item = Counter(), [], [], 0, []
    for it in items:
        if it.get("pairs"):                        # winogrande — 문맥이 후보마다 다르다
            rs = [seq_ce(model, tok, dev, p, c, seq_max, torch, F) for p, c in it["pairs"]]
        else:
            rs = [seq_ce(model, tok, dev, it["ctx"], c, seq_max, torch, F) for c in it["choices"]]
        if any(r is None for r in rs) or it["gold"] < 0:
            skipped += 1
            continue
        mean = [r[0] for r in rs]
        if no_pmi or it.get("pairs"):
            score = mean
        else:                                      # ★PMI: 문맥 없는 우도를 뺀다
            base = [seq_ce(model, tok, dev, "", c, seq_max, torch, F) for c in it["choices"]]
            score = [m - (b[0] if b else 0.0) for m, b in zip(mean, base)]
        p = min(range(len(score)), key=lambda i: score[i])
        pn = min(range(len(rs)), key=lambda i: rs[i][1] / max(rs[i][2], 1))
        picks[p] += 1
        ok.append(1 if p == it["gold"] else 0)
        ok_norm.append(1 if pn == it["gold"] else 0)
        per_item.append(rs[it["gold"]][0])         # ★정답 후보의 평균CE = paired 용 연속값
    return picks, ok, ok_norm, skipped, per_item


def run_cloze(items, model, tok, dev, seq_max, torch, F):
    ok, ces, skipped = [], [], 0
    for it in items:
        r = seq_ce(model, tok, dev, it["ctx"], it["gold"], seq_max, torch, F)
        if r is None:
            skipped += 1
            continue
        gen = greedy(model, tok, dev, it["ctx"], 6, seq_max, torch)
        ok.append(1 if gen.strip().split()[:1] == it["gold"].strip().split()[:1] else 0)
        ces.append(r[1])                           # ★합CE = 그 단어의 -logP -^> PPL 로 간다
    return ok, ces, skipped


def main():
    ap = argparse.ArgumentParser(description="벤치마크 전수 평가 (학습 0)")
    ap.add_argument("--task", required=True, help=f"{'|'.join(TASKS)}|all")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seq-max", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--device", default=None)
    ap.add_argument("--max-new", type=int, default=96, help="생성 과제의 최대 새 토큰")
    ap.add_argument("--no-pmi", action="store_true", help="PMI 보정 끄기(대조용)")
    ap.add_argument("--out-jsonl", default=None, help="gen_save 과제의 생성물 저장 경로")
    ap.add_argument("--wandb", action="store_true",
                    help="★결과를 W&B 온라인으로 보낸다(사용자 지시 2026-08-22)")
    ap.add_argument("--wandb-project", default="tinylm-bench")
    a = ap.parse_args()

    tasks = list(TASKS) if a.task == "all" else [a.task]
    for t in tasks:
        assert t in TASKS, f"모르는 과제: {t}. 가능: {'|'.join(TASKS)}"

    import random
    import torch
    import torch.nn.functional as F
    from tokenizers import Tokenizer
    from tinylm import paths
    from tinylm.data import tokenizer_path
    from tinylm.infer.generate import load_model

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))

    banner("★벤치마크 전수 — 학습 0. **우연 수준을 결과보다 먼저 인쇄한다**(함정 34)", "#")
    print(f"  device={dev}  n={a.n}  seq_max={a.seq_max}  seed={a.seed}  "
          f"PMI={'off' if a.no_pmi else 'on'}")
    print("  ⚠️★우리 모델은 **100M base LM(SFT 없음)** 이다. 생성 과제는 0 이 정상이고,")
    print("     ★**0 이 나오면 0 을 기록한다** — 그것을 확인하는 것이 이 런의 목적이다.")
    print("  ⚠️★공식 metric 이름을 우리 지표에 쓰지 않는다(규약 2). 아래 '공식' 열은 참고다.")

    all_summary = {}
    for task in tasks:
        kind, chance, official, desc = TASKS[task]
        banner(f"[{task}] {desc}   kind={kind}   공식 metric={official}")
        try:
            rows = load_rows(task)
        except FileNotFoundError as e:
            print(f"  🚫 {e}")
            print("  ★**데이터 없음은 '구현 안 함' 이 아니다.** 결과문서에 그대로 적는다.")
            all_summary[task] = {"status": "no_data"}
            continue

        rnd = random.Random(a.seed)
        idx = list(range(len(rows)))
        rnd.shuffle(idx)
        idx = sorted(idx[:min(a.n, len(rows))])     # ★고정 시드 + id 로그(규약 3)
        print(f"  전체 {len(rows):,}행 중 {len(idx)}문항 (seed={a.seed})  "
              f"id 앞 10개: {idx[:10]}")
        if chance is not None:
            print(f"  ★**우연 수준 = {chance:.1%}** — 이 값보다 유의하게 높지 않으면 "
                  f"'모델이 못 푼다' 가 답이다")

        try:
            items = [ADAPTERS[task](rows[i]) for i in idx]
        except (KeyError, ValueError, IndexError) as e:
            print(f"  🚫 어댑터 실패: {type(e).__name__}: {e}")
            print("  ★필드 이름이 데이터카드와 다르다 — **조용히 넘기지 않는다**(함정 31). "
                  "`head -1` 로 원본 키를 확인하고 어댑터를 고치세요.")
            all_summary[task] = {"status": f"adapter_error:{type(e).__name__}"}
            continue

        per_model = {}
        for tag in a.models:
            ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, tag)
            if not ck.exists():
                print(f"  [건너뜀] 체크포인트 없음: {ck.name}")
                continue
            model, cfg, _ = load_model(arch=_arch_of(tag), ckpt_path=str(ck), device=dev)
            model.eval()
            rec = {"tag": tag, "n_asked": len(items)}

            if kind == "mc":
                picks, ok, okn, sk, ce = run_mc(task, items, model, tok, dev, a.seq_max,
                                                torch, F, a.no_pmi)
                p, lo, hi = wilson(sum(ok), len(ok))
                pn, _l2, _h2 = wilson(sum(okn), len(okn))
                rec.update(acc=p, acc_ci=[lo, hi], acc_norm=pn, n=len(ok), skipped=sk,
                           gold_ce=statistics.fmean(ce) if ce else None)
                print(f"\n  {tag:<18} 우도acc **{p:.1%}** [95%CI {lo:.1%}~{hi:.1%}]  "
                      f"길이정규acc {pn:.1%}  정답CE {rec['gold_ce']:.4f}  "
                      f"N={len(ok)} 제외={sk}")
                tot = sum(picks.values())
                frac = max(picks.values()) / tot if tot else 0
                if frac >= 0.90:
                    print(f"  🚫★**퇴화** — 한 선택지를 {frac:.1%} 로 찍는다. "
                          f"이 숫자는 능력이 아니라 **편향**이다(규약 7)")
                per_model[tag] = ce

            elif kind == "cloze":
                ok, ces, sk = run_cloze(items, model, tok, dev, a.seq_max, torch, F)
                p, lo, hi = wilson(sum(ok), len(ok))
                ppl = math.exp(statistics.fmean(ces)) if ces else float("nan")
                rec.update(acc=p, acc_ci=[lo, hi], ppl=ppl, n=len(ok), skipped=sk,
                           gold_ce=statistics.fmean(ces) if ces else None)
                print(f"\n  {tag:<18} 마지막단어acc **{p:.1%}** [95%CI {lo:.1%}~{hi:.1%}]  "
                      f"PPL {ppl:,.1f}  N={len(ok)} 제외={sk}")
                per_model[tag] = ces

            elif kind == "gen":
                hits, ces, inst_ok, inst_tot, inst_skip = [], [], 0, 0, 0
                gens = []
                for it in items:
                    g = greedy(model, tok, dev, it["ctx"], a.max_new, a.seq_max, torch,
                               stop=["\nQuestion:", "\n\n\n"])
                    gens.append(g)
                    if task == "gsm8k":
                        nums = re.findall(r"-?\d[\d,]*\.?\d*", g.replace(",", ""))
                        hits.append(1 if nums and nums[-1].rstrip(".") == it["gold"] else 0)
                        r = seq_ce(model, tok, dev, it["ctx"], it["gold_full"], a.seq_max, torch, F)
                        if r:
                            ces.append(r[0])
                    else:                                   # ifeval
                        for iid, kw in zip(it["meta"]["ids"], (it["meta"]["kw"] or [{}])
                                           * len(it["meta"]["ids"])):
                            v = ifeval_check(iid, kw, g)
                            inst_tot += 1
                            if v is None:
                                inst_skip += 1
                            elif v:
                                inst_ok += 1
                if task == "gsm8k":
                    p, lo, hi = wilson(sum(hits), len(hits))
                    rec.update(em=p, em_ci=[lo, hi], gold_ce=statistics.fmean(ces) if ces else None,
                               n=len(hits))
                    print(f"\n  {tag:<18} EM **{p:.1%}** [95%CI {lo:.1%}~{hi:.1%}]  "
                          f"★정답CE {rec['gold_ce']:.4f}  N={len(hits)}")
                    print("  ★EM 이 0 이어도 **정답CE 는 연속값**이라 서열을 만든다(결과 050 의 수법)")
                    per_model[tag] = ces
                else:
                    ev = inst_tot - inst_skip
                    p, lo, hi = wilson(inst_ok, ev)
                    rec.update(inst_acc=p, inst_ci=[lo, hi], inst_eval=ev,
                               inst_unimpl=inst_skip, n=len(items))
                    print(f"\n  {tag:<18} 제약충족 **{p:.1%}** [95%CI {lo:.1%}~{hi:.1%}]  "
                          f"평가 {ev} / 미구현제약 {inst_skip} / 전체 {inst_tot}")
                    print("  ⚠️★**미구현 제약은 '실패' 가 아니라 '미평가' 다.** 공식 25종 중 우리는 8종")
                if a.out_jsonl:
                    _dump(a.out_jsonl, task, tag, items, gens)

            else:                                            # gen_save
                gens, syn_ok, ces = [], 0, []
                for it in items:
                    g = greedy(model, tok, dev, it["ctx"], a.max_new, a.seq_max, torch,
                               stop=["\ndef ", "\nclass ", "\n#", "\n\n\n"])
                    gens.append(g)
                    if task.startswith("humaneval"):
                        try:
                            _ast.parse(it["ctx"] + g)
                            syn_ok += 1
                        except SyntaxError:
                            pass
                    else:
                        try:
                            json.loads(g.strip())
                            syn_ok += 1
                        except Exception:                    # noqa: BLE001
                            pass
                    if it.get("gold"):
                        r = seq_ce(model, tok, dev, it["ctx"], it["gold"], a.seq_max, torch, F)
                        if r:
                            ces.append(r[0])
                p, lo, hi = wilson(syn_ok, len(items))
                rec.update(parse_ok=p, parse_ci=[lo, hi],
                           gold_ce=statistics.fmean(ces) if ces else None, n=len(items))
                _gce = "n/a" if rec["gold_ce"] is None else f"{rec['gold_ce']:.4f}"
                print(f"\n  {tag:<18} 파싱성공 **{p:.1%}** [95%CI {lo:.1%}~{hi:.1%}]  "
                      f"정답CE {_gce}  N={len(items)}")
                print("  🚫★**pass@1 은 여기서 안 낸다** — 생성 코드를 **실행해야** 하고 "
                      "우리는 모델이 만든 코드를 실행하지 않는다.")
                print(f"  ★`--out-jsonl` 로 저장한 뒤 공식 하네스(evalplus / BFCL)로 채점하세요.")
                if a.out_jsonl:
                    _dump(a.out_jsonl, task, tag, items, gens)
                per_model[tag] = ces

            all_summary.setdefault(task, {})[tag] = rec
            del model
            if dev == "cuda":
                torch.cuda.empty_cache()

        # ★paired — 연속값(정답CE)이 있을 때만. 규약 4: 공통 문항만.
        keys = [k for k in per_model if per_model[k]]
        if len(keys) >= 2:
            n = min(len(per_model[k]) for k in keys)
            print(f"\n  ── paired 정답CE 비교 (공통 {n}문항) ──")
            for i in range(len(keys) - 1):
                for j in range(i + 1, len(keys)):
                    m, sd, se, t, ci, win, need = paired_stats(per_model[keys[i]][:n],
                                                               per_model[keys[j]][:n])
                    print(f"    {keys[i]} - {keys[j]}: Δ {m:+.4f} ± {ci:.4f}  "
                          f"SD {sd:.4f} SE {se:.4f} t {t:+.2f}  승률 {win:.1f}%  "
                          f"필요N(SE0.002) **{need:,}**")
                    if need > n:
                        print(f"      ⚠️★**{n} 문항으로는 부족하다**(필요 {need:,}). "
                              f"이 Δ 로 **서열을 매기지 않는다**")

    _final(all_summary)
    if a.wandb:
        _push_wandb(all_summary, a)
    return 0


def _dump(path, task, tag, items, gens):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for it, g in zip(items, gens):
            f.write(json.dumps({"task": task, "model": tag,
                                "task_id": (it.get("meta") or {}).get("task_id", ""),
                                "prompt": it["ctx"], "completion": g}, ensure_ascii=False) + "\n")
    print(f"  ✅ 생성물 저장: {p}  (공식 하네스로 채점하세요)")


def _final(s):
    banner("요약 — ★이 표를 결과문서에 그대로 옮긴다", "#")
    print(f"  {'과제':<16}{'모델':<20}{'주지표':>10}  비고")
    print("-" * 96)
    for task, per in s.items():
        if per.get("status"):
            print(f"  {task:<16}{'-':<20}{'-':>10}  🚫 {per['status']}")
            continue
        for tag, r in per.items():
            main_v = r.get("acc", r.get("em", r.get("inst_acc", r.get("parse_ok"))))
            if main_v is None:
                print(f"  {task:<16}{tag:<20}{'n/a':>10}  주지표 없음")
                continue
            extra = []
            if r.get("gold_ce") is not None:
                extra.append(f"정답CE {r['gold_ce']:.4f}")
            if r.get("ppl"):
                extra.append(f"PPL {r['ppl']:,.0f}")
            if r.get("skipped"):
                extra.append(f"제외 {r['skipped']}")
            print(f"  {task:<16}{tag:<20}{main_v:>9.1%}  {' / '.join(extra)}")
    print("\n  ⚠️★**우연 수준 근처면 그 과제는 이 모델을 서열화하지 못한다.**")
    print("     ★그래도 지운다는 뜻이 아니다 — **'못 푼다' 는 것이 측정된 사실**이다.")


def _push_wandb(summary, a):
    """★결과를 W&B 온라인으로 보낸다(사용자 지시 2026-08-22 §7).

    ⚠️**키는 `wandb_sync.read_key()` 로만 읽는다** — 값을 인쇄하지도, 어디에도 남기지도 않는다.
    """
    banner("W&B 업로드 — 벤치마크 결과", "#")
    try:
        import wandb
    except ImportError:
        print("  🚫 wandb 가 없다 — `pip install wandb`")
        return
    sys.path.insert(0, str(ROOT / "scripts"))
    from wandb_sync import read_key
    wandb.login(key=read_key())                    # ★키는 여기서만 쓰인다
    for task, per in summary.items():
        if per.get("status"):
            continue
        for tag, rec in per.items():
            rid = f"bench-{task}-{tag}"
            r = wandb.init(project=a.wandb_project, id=rid, name=rid, resume="allow",
                           reinit=True, config={"task": task, "model": tag,
                                                "preset": a.preset, "n": a.n,
                                                "seed": a.seed, "pmi": not a.no_pmi})
            r.summary.update({k: v for k, v in rec.items()
                              if isinstance(v, (int, float, str, bool)) or v is None})
            r.finish()
            print(f"  ✅ {rid}")
    print("  ★런 이름은 `bench-{과제}-{태그}` 다 — 학습 런(`{preset}_{data}_{tokens}_{tag}`)과 "
          "**네임스페이스가 분리**된다.")


if __name__ == "__main__":
    sys.exit(main())
