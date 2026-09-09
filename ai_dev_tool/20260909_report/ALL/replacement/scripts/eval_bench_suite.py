#!/usr/bin/env python3
"""A01/A03: 원문 ID·skip·선택비용을 기록하는 로컬 평가기.
MC는 token 평균 NLL 및 선택적 평균 PMI이며 공식 acc_norm 재현이 아니다.
IFEval은 부분 제약, HumanEval/BFCL은 생성과 parse만 기록한다.
생성 코드는 실행하지 않으며 공식 점수로 승격하지 않는다.
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
    # ★2026-09-05 — 검정력용(세 split 전부). 기존 `arc_easy` 와 **다른 과제로 센다**
    "arc_easy_full":  ("mc",       0.25,  "acc / acc_norm",   "★4지선다 과학 전량 5,197"),
    # ★★2026-09-05 — KoBEST. 논문 지표는 **F1** 이지만 🚫우리 지표에 그 이름을 쓰지 않는다(규약 2)
    "kobest_copa":    ("mc",       0.50,  "F1(공식)",          "★한국어 2지선다 인과"),
    "kobest_hellaswag": ("mc",     0.25,  "F1(공식)",          "★한국어 4지선다 문장완성"),
    # ★★2026-09-06 — 우리가 만든 한국어 held-out. v2.7 에서 D6(정답이 둘)이 0 이 되어 열렸다.
    #   ⚠️**공식 metric 이 없다** — 외부 벤치가 아니라 우리 문항이다. 우연 25.0%.
    "stage1_heldout": ("mc",          0.25,  "(우리 것)",          "★한국어 4지선다 관계추론(자체)"),
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
    from tinylm.eval.audit_io import read_records
    return read_records(p)


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
    fn = json.dumps(r.get("function", r.get("tools", [])), ensure_ascii=False)
    return {"ctx": f"Available functions: {fn}\nUser: {q}\nFunction call:",
            "gold": json.dumps(r.get("ground_truth", ""), ensure_ascii=False),
            "meta": {"id": r.get("id", "")}}


def _ad_kobest_copa(r):
    """KB-COPA — 전제 + 원인/결과 + 후보 2. 논문 §4.2.1 은 **최저 perplexity 후보**를 고른다.

    ★`label` 은 0/1 이고 `alternative_1/2` 에 대응한다(논문 Table 2 의 `Correct Alternative: 2`
    는 1-기반 표기다 — 데이터의 `label` 은 0-기반이다).
    ⚠️`question` 은 **`원인` 또는 `결과`** 이고 그것이 방향을 정한다 — 문맥에 넣어야 한다.
    """
    q = r["question"]
    ctx = f"{r['premise']} 그 {q}(으)로 알맞은 것은?"
    return {"ctx": ctx,
            "choices": [" " + r["alternative_1"], " " + r["alternative_2"]],
            "gold": int(r["label"])}


def _ad_kobest_hellaswag(r):
    """KB-HellaSwag — 문맥 + 후보 4. `ending_1..4` · `label` 0-기반."""
    return {"ctx": r["context"],
            "choices": [" " + r[f"ending_{i}"] for i in (1, 2, 3, 4)],
            "gold": int(r["label"])}


def _ad_stage1_heldout(r):
    from tinylm.eval.heldout import adapt_heldout
    item = adapt_heldout(r)
    item["choices"] = [" " + c.lstrip() for c in item["choices"]]
    return item


ADAPTERS = {
    "hellaswag": _ad_hellaswag, "piqa": _ad_piqa, "winogrande": _ad_winogrande,
    "arc_easy": _ad_arc, "arc_easy_full": _ad_arc, "arc_challenge": _ad_arc, "boolq": _ad_boolq,
    "kobest_copa": _ad_kobest_copa, "kobest_hellaswag": _ad_kobest_hellaswag,
    "stage1_heldout": _ad_stage1_heldout,
    "mmlu": _ad_mmlu, "mmlu_redux": _ad_mmlu_redux, "musr": _ad_musr,
    "lambada": _ad_lambada, "gsm8k": _ad_gsm8k, "ifeval": _ad_ifeval,
    "humaneval": _ad_humaneval, "humaneval_plus": _ad_humaneval, "bfcl_v3": _ad_bfcl,
}



def ifeval_check(iid, kw, resp):
    kw = kw or {}
    if iid.endswith("number_words"):
        n = len(resp.split())
        rel, want = kw.get("relation"), kw.get("num_words")
        if want is None:
            return None
        return n >= want if rel == "at least" else n <= want if rel == "at most" else None
    if iid.endswith("number_sentences"):
        n = len([s for s in re.split(r"[.!?]+", resp) if s.strip()])
        rel, want = kw.get("relation"), kw.get("num_sentences")
        if want is None:
            return None
        return n >= want if rel == "at least" else n <= want if rel == "at most" else None
    if iid.endswith("existence") and kw.get("keywords"):
        return all(k.lower() in resp.lower() for k in kw["keywords"])
    if iid.endswith("forbidden_words") and kw.get("forbidden_words"):
        return not any(k.lower() in resp.lower() for k in kw["forbidden_words"])
    if iid.endswith("english_lowercase"):
        return bool(re.search(r"[A-Za-z]", resp)) and resp == resp.lower()
    if iid.endswith("english_capital"):
        return bool(re.search(r"[A-Za-z]", resp)) and resp == resp.upper()
    if iid.endswith("number_bullet_lists"):
        n = len(re.findall(r"^\s*[\*\-]\s", resp, re.M))
        return n == kw.get("num_bullets") if kw.get("num_bullets") is not None else None
    if iid.endswith("quotation"):
        r = resp.strip()
        return len(r) >= 2 and r[0] == '"' and r[-1] == '"'
    return None                                    # ★미구현 = 미평가. 실패가 아니다




# A01/A03 교체본. 공개 benchmark 공식 점수를 재현한다고 주장하지 않는다.
from tinylm.eval.audit_io import digest_json, item_id, sha256_file, write_json_new
from tinylm.eval.model_adapter import (continuation_nll, greedy_completion,
                                      load_local_model, parse_map)
from tinylm.eval.paired_records import mc_metrics, summarize_paired


def _evaluate_item(task, kind, item, model, tok, device, seq_max, max_new, no_pmi, ce_chunk):
    base = {"id": item["_id"], "task": task, "gold": item.get("gold"),
            "family": item.get("family"), "item_sha256": item["_item_sha256"],
            "status": "ok", "scoring_profile": "tinylm.mean_token_nll.v2"
            + (".no_pmi" if no_pmi or item.get("pairs") else ".pmi_mean")}
    if kind == "mc":
        pairs = item.get("pairs") or [(item["ctx"], c) for c in item["choices"]]
        gold = item.get("gold")
        if isinstance(gold, bool) or not isinstance(gold, int) or not 0 <= gold < len(pairs):
            return dict(base, status="skipped", reason="invalid_gold")
        rows = []
        for context, candidate in pairs:
            rec, reason = continuation_nll(model, tok, context, candidate, device=device,
                                           seq_max=seq_max, ce_chunk=ce_chunk)
            if rec is None:
                return dict(base, status="skipped", reason=reason)
            rows.append(rec)
        costs = [r["nll_mean"] for r in rows]
        unconditioned = None
        if not no_pmi and not item.get("pairs"):
            unconditioned = []
            for candidate in item["choices"]:
                rec, reason = continuation_nll(model, tok, "", candidate, device=device,
                                               seq_max=seq_max, ce_chunk=ce_chunk)
                if rec is None:
                    return dict(base, status="skipped", reason="pmi_" + reason)
                unconditioned.append(rec)
            costs = [x - y["nll_mean"] for x, y in zip(costs, unconditioned)]
        norm_pred = min(range(len(rows)), key=lambda i: rows[i]["nll_mean"])
        base.update(mc_metrics(costs, gold), choices=rows, costs=costs,
                    unconditioned=unconditioned, gold_ce=rows[gold]["nll_mean"],
                    correct_raw_mean_nll=int(norm_pred == gold))
        return base

    response = greedy_completion(model, tok, item["ctx"], device=device,
                                 seq_max=seq_max, max_new=6 if kind == "cloze" else max_new,
                                 stop_strings=("\nQuestion:", "\n\n\n"))
    base.update(generation=response, completion=response["text"],
                prompt=item["ctx"], task_id=(item.get("meta") or {}).get("task_id", item["_id"]),
                scoring_profile="tinylm.greedy.partial_tasks.v2")
    if response["status"] != "ok":
        return dict(base, status="skipped", reason=response["reason"])
    gold_text = item.get("gold_full") or item.get("gold")
    if isinstance(gold_text, str) and gold_text:
        rec, reason = continuation_nll(model, tok, item["ctx"], gold_text, device=device,
                                       seq_max=seq_max, ce_chunk=ce_chunk)
        base["gold_ce"] = rec["nll_mean"] if rec else None
        base["gold_nll_sum"] = rec["nll_sum"] if rec else None
        base["gold_ce_skip_reason"] = reason
    text = response["text"]
    if kind == "cloze":
        base["correct"] = int(text.strip().split()[:1] == item["gold"].strip().split()[:1])
    elif task == "gsm8k":
        nums = re.findall(r"-?\d[\d,]*\.?\d*", text.replace(",", ""))
        base["correct"] = int(bool(nums) and nums[-1].rstrip(".") == item["gold"])
        base["metric_scope"] = "local last-number EM; not official strict EM"
    elif task == "ifeval":
        ids = item["meta"]["ids"]
        kwargs = item["meta"]["kw"] or [{} for _ in ids]
        if len(kwargs) != len(ids):
            raise ValueError("IFEval kwargs/instruction 개수 불일치")
        judged = [ifeval_check(i, k, text) for i, k in zip(ids, kwargs)]
        base.update(instruction_results=judged,
                    inst_eval=sum(v is not None for v in judged),
                    inst_ok=sum(v is True for v in judged),
                    inst_unimpl=sum(v is None for v in judged),
                    metric_scope="partial local constraints; not official IFEval")
    else:
        try:
            if task.startswith("humaneval"):
                _ast.parse(item["ctx"] + text)
            else:
                json.loads(text.strip())
            base["parse_ok"] = 1
        except (SyntaxError, ValueError):
            base["parse_ok"] = 0
        base["metric_scope"] = "syntax/JSON parsing only; generated code is never executed"
    return base


def main():
    import datetime
    import random
    import uuid
    import torch
    from tinylm import paths
    from tinylm.eval.heldout import load_cache, cache_path

    ap = argparse.ArgumentParser(description="A01/A03 ID 기반 로컬 벤치; 공식 harness와 구분")
    ap.add_argument("--task", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--n", type=int, default=200, help="0=전량")
    ap.add_argument("--seq-max", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--device", default=None)
    ap.add_argument("--max-new", type=int, default=96)
    ap.add_argument("--no-pmi", action="store_true")
    ap.add_argument("--ce-chunk", type=int, default=256)
    ap.add_argument("--out-jsonl", default=None, help="모든 문항의 결과; 기존 파일 덮어쓰기 금지")
    ap.add_argument("--checkpoint", nargs="*", help="TAG=체크포인트 경로")
    ap.add_argument("--hf-model", nargs="*", help="TAG=로컬 HF 모델 폴더")
    ap.add_argument("--tokenizer", nargs="*", help="TAG=tokenizer.json")
    ap.add_argument("--tokenizer-hf", nargs="*", help="TAG=로컬 HF tokenizer 폴더")
    ap.add_argument("--heldout-version", choices=("2.7", "2.8"), default="2.7")
    ap.add_argument("--heldout-source-sha256", default=None)
    ap.add_argument("--family-map", help="JSON item id -> 감사된 family id; relation은 자동 family로 쓰지 않음")
    ap.add_argument("--wandb", action="store_true")
    ap.add_argument("--wandb-project", default="tinylm")
    ap.add_argument("--wandb-standalone", action="store_true")
    a = ap.parse_args()
    if a.n < 0 or a.seq_max < 2 or a.max_new < 1 or a.ce_chunk < 1:
        ap.error("n/seq-max/max-new/ce-chunk 범위 오류")
    if len(set(a.models)) != len(a.models):
        ap.error("중복 model tag")
    tasks = list(TASKS) if a.task == "all" else [a.task]
    if any(t not in TASKS for t in tasks):
        ap.error("미등록 task")
    ckmap, hfmap = parse_map(a.checkpoint), parse_map(a.hf_model)
    tokmap, thmap = parse_map(a.tokenizer), parse_map(a.tokenizer_hf)
    if set(ckmap) & set(hfmap):
        ap.error("한 tag에 TinyLM/HF 모델을 동시에 지정할 수 없음")
    if (set(ckmap) | set(hfmap) | set(tokmap) | set(thmap)) - set(a.models):
        ap.error("모델 목록에 없는 TAG 옵션")
    if a.wandb and hfmap:
        ap.error("HF 외부모델은 기존 TinyLM W&B run에 결합하지 않음; 별도 로컬 출력 사용")
    families = (json.loads(Path(a.family_map).read_text(encoding="utf-8"))
                if a.family_map else {})
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(a.out_jsonl) if a.out_jsonl else ROOT / "runs" / "eval" / f"a03_{stamp}_{uuid.uuid4().hex[:8]}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    summary_path = out.with_suffix(".summary.json")
    if out.exists() or summary_path.exists():
        ap.error("출력 파일이 존재함; 새 경로 지정 필요")
    device = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    all_summary, pair_summary = {}, {}
    a._resolved_checkpoints = {}
    failed = False
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        for task in tasks:
            kind, chance, official, desc = TASKS[task]
            dataset_meta = None
            if task == "stage1_heldout":
                rows, dataset_meta = load_cache(ROOT, a.heldout_version, a.heldout_source_sha256)
                source = cache_path(ROOT, a.heldout_version)
            else:
                source = BENCH / f"{task}.jsonl"
                if not source.exists():
                    all_summary[task] = {"status": "no_data"}
                    failed = True
                    continue
                rows = load_rows(task)
            dataset_sha = sha256_file(source)
            indices = list(range(len(rows)))
            random.Random(a.seed).shuffle(indices)
            indices = sorted(indices[:a.n] if a.n else indices)
            items = []
            seen = set()
            for i in indices:
                item = ADAPTERS[task](rows[i])
                ident = item_id(task, rows[i], i)
                if ident in seen:
                    raise ValueError(f"중복 문항 id: {ident}")
                seen.add(ident)
                item.update(_id=ident, _item_sha256=digest_json(item))
                item["family"] = families.get(ident, rows[i].get("family_id"))
                items.append(item)
            print(f"{task}: 요청 {len(items)}/{len(rows)}, chance={chance}, 공식 참고={official}")
            print("실제 점수: 명시된 로컬 token 평균 NLL/PMI; 공식 harness 재현이 아님")
            per_tag, all_summary[task] = {}, {}
            for tag in a.models:
                ck = None if tag in hfmap else Path(ckmap.get(tag) or paths.resolve_ckpt(
                    a.preset, a.data, a.tokens, tag))
                model, tok, provenance = load_local_model(
                    tag, checkpoint=ck, hf_path=hfmap.get(tag), data=a.data,
                    tokenizer_path=tokmap.get(tag), tokenizer_hf=thmap.get(tag), device=device)
                if ck is not None:
                    a._resolved_checkpoints[tag] = str(ck)
                records = []
                for item in items:
                    r = _evaluate_item(task, kind, item, model, tok, device,
                                       min(a.seq_max, provenance["max_seq_len"]),
                                       a.max_new, a.no_pmi, a.ce_chunk)
                    r.update(model=tag, model_provenance=provenance,
                             dataset_sha256=dataset_sha, dataset_metadata=dataset_meta,
                             sample_seed=a.seed)
                    stream.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n")
                    stream.flush()
                    records.append(r)
                scored = [r for r in records if r["status"] == "ok"]
                correct = [r["correct"] for r in scored if "correct" in r]
                ce = [r["gold_ce"] for r in scored if r.get("gold_ce") is not None]
                result = {"tag": tag, "n_asked": len(records), "n": len(scored),
                          "skipped": len(records) - len(scored),
                          "acc": statistics.fmean(correct) if correct else None,
                          "gold_ce": statistics.fmean(ce) if ce else None,
                          "scoring_profile": scored[0]["scoring_profile"] if scored else None,
                          "dataset_sha256": dataset_sha, "status": "ok" if scored else "no_scored_items"}
                for field in ("mean_wrong_margin", "best_wrong_margin", "choice_nll", "choice_brier"):
                    values = [r[field] for r in scored if field in r]
                    result[field] = statistics.fmean(values) if values else None
                if kind == "mc":
                    result["local_acc_raw_mean_nll"] = (statistics.fmean(r["correct_raw_mean_nll"] for r in scored)
                                          if scored else None)
                    result["mean_margin_note"] = "mean_wrong_margin은 최근접 오답 경계가 아님"
                if task == "gsm8k":
                    result["em"] = result["acc"]
                if task == "ifeval":
                    total = sum(r["inst_eval"] for r in scored)
                    result.update(inst_eval=total, inst_unimpl=sum(r["inst_unimpl"] for r in scored),
                                  inst_acc=sum(r["inst_ok"] for r in scored) / total if total else None)
                parsed = [r["parse_ok"] for r in scored if "parse_ok" in r]
                if parsed:
                    result["parse_ok"] = statistics.fmean(parsed)
                if not scored:
                    failed = True
                per_tag[tag] = records
                all_summary[task][tag] = result
                print(json.dumps(result, ensure_ascii=False, allow_nan=False))
                del model
                if str(device).startswith("cuda"):
                    torch.cuda.empty_cache()
            pairs = []
            tags = list(per_tag)
            for i, left in enumerate(tags):
                for right in tags[i + 1:]:
                    for metric in ("gold_ce", "correct", "best_wrong_margin"):
                        if metric == "gold_ce":
                            ta = per_tag[left][0]["model_provenance"]["tokenizer_sha256"]
                            tb = per_tag[right][0]["model_provenance"]["tokenizer_sha256"]
                            if ta != tb:
                                pairs.append({"a": left, "b": right, "metric": metric,
                                              "status": "incomparable_tokenizers"})
                                continue
                        result = summarize_paired(per_tag[left], per_tag[right], metric)
                        result.update(a=left, b=right)
                        pairs.append(result)
            pair_summary[task] = pairs
    write_json_new(summary_path, {"schema": "tinylm.bench-records.v2",
                                 "summary": all_summary, "paired": pair_summary,
                                 "records": str(out), "records_sha256": sha256_file(out),
                                 "command": vars(a), "scope": "one checkpoint per tag"})
    if a.wandb:
        _push_wandb(all_summary, a)
    print(f"문항별 결과: {out}\n요약: {summary_path}")
    return 2 if failed else 0


def _run_name(a, tag):
    """★학습 런과 **같은 이름**. `wandb_sync` 가 `runs/logs/*.json` 의 stem 을 쓰고,
    그 stem 이 `{preset}_{data}_{tokens}_{tag}` 이므로 여기서도 그대로 만든다.

    ★★2026-09-04 수정 — **프리셋을 CLI 가 아니라 실제 체크포인트에서 읽는다.**

    🚫종전에는 `a.preset` 을 그대로 썼다. 그래서 배치가 세 모델에 `--preset m100R1c`
    하나를 주면(실제는 `m100s8`/`m100s12`/`m100R1c`) **런 이름 둘이 틀렸고**
    `_bench_eligible` 이 *"학습 json 이 없다"* 로 **두 모델을 건너뛰었다**
    (사용자 보고: *"마지막 모델 데이터만 업로드된다"*, 결과 074 §5).

    ★체크포인트 로딩은 **전역 검색으로 자기 복구**했으므로 **수치는 처음부터 정상**이었다 —
    복구되지 않은 것은 이름뿐이다. 그 파일명이 곧 `{preset}_{data}_{tokens}_{tag}.pt` 이므로
    **거기서 stem 을 떼면 이름이 언제나 맞는다.**
    """
    actual = getattr(a, "_resolved_checkpoints", {}).get(tag)
    if actual:
        return Path(actual).stem
    hit = sorted((ROOT / "runs" / "ckpt").glob(f"*_{a.data}_{a.tokens}_{tag}.pt"))
    hit = [p for p in hit if not p.stem.endswith("_best")]
    if len(hit) == 1:
        return hit[0].stem
    if len(hit) > 1:
        # 🚫여러 프리셋에 같은 태그가 있으면 **추측하지 않는다** — CLI 값을 쓴다
        print(f"  ⚠️`{tag}` 가 프리셋 {len(hit)}개에 있다 — `--preset {a.preset}` 을 그대로 쓴다: "
              + ", ".join(p.stem.split("_")[0] for p in hit))
    return f"{a.preset}_{a.data}_{a.tokens}_{tag}"


def _bench_eligible(a, tag):
    """★250스텝 프로브를 W&B 에 올리지 않는다(2026-08-23 사용자 지시, 2026-09-03 재확인).

    사용자가 **짧은 프로브 데이터를 이미 한 번 지웠다.** 벤치 경로에도 같은 게이트를 건다.
    판정은 스텝이 아니라 **학습 토큰**이다 — `steps` 는 유효배치에 따라 뜻이 달라진다.
    """
    import json
    p = ROOT / "runs" / "logs" / f"{_run_name(a, tag)}.json"
    if not p.exists():
        return False, f"학습 json 이 없다({p.name}) - 어느 런의 벤치인지 결합할 수 없다"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return False, f"{p.name} 을 못 읽었다"
    tk = int(d.get("tokens") or 0)
    if tk < 50_000_000:
        return False, (f"★짧은 프로브({tk/1e6:.1f}M 토큰 < 50M) - 품질을 읽지 않는 런이다. "
                       f"전체 런과 섞이면 착오가 난다")
    return True, ""


def _push_wandb(summary, a):
    """명시한 --wandb에서만 업로드. v1 summary/TSV와 별도 bench_v2 namespace."""
    import wandb
    from wandb_sync import read_key
    wandb.login(key=read_key())
    grouped = {}
    for task, per in summary.items():
        if per.get("status"):
            continue
        for tag, rec in per.items():
            grouped.setdefault(tag, {})[task] = rec
    for tag, tasks in grouped.items():
        ok, why = _bench_eligible(a, tag)
        if not ok:
            print(f"W&B 제외 {tag}: {why}")
            continue
        rid = "bench-v2-" + _run_name(a, tag) if a.wandb_standalone else _run_name(a, tag)
        run = wandb.init(project=a.wandb_project, id=rid, name=rid, resume="allow", reinit=True)
        flat = {}
        for task, rec in tasks.items():
            for key, value in rec.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    flat[f"bench_v2/{task}/{key}"] = value
            flat[f"bench_v2/{task}/seed"] = a.seed
        run.summary.update(flat)
        run.finish()


if __name__ == "__main__":
    raise SystemExit(main())
