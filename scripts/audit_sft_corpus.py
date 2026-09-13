#!/usr/bin/env python3
"""★SFT 코퍼스 감사기 — `datasets/TinyDataset/SFT/` 를 **요청서 사양에 대고** 읽는다.

## 왜 생겼나 (2026-09-10 사용자 지시 2A)

> *"데이터셋팀에서 작성을 하였으나 **감사는 claude가 수행해야함** … 덧붙여 해당 데이터
>  감사를 위한 **도구가 적절히 구비되어 있는지** 확인바람."*

실사 결과 **우리 `scripts/` 에 SFT 감사기가 없었다.** 데이터셋 팀이 자기 폴더에 둔
`SFT/tools/build_phase1.py` 는 **생성기**이고, 자기 산출물을 자기가 검사한다
(★함정 43 — **자기 사본과 대조하는 게이트는 게이트가 아니다**). 그래서 **요청서를 정본으로
읽는 독립 감사기**를 우리 쪽에 만든다.

## 무엇을 보나 — 정본은 `review_request/20260908_SFT용-데이터셋-생성-요청-프롬프트.md` 부록 B

    A1 규모(레코드)      B.1.3  25,000~40,000
    A2 규모(토큰)        B.1.3  10M 권장 · 5M 최소
    A3 canonical 스키마  B.2
    A4 assistant-only 마스크 가능성   B.2
    A5 채점 등급 T1/T2/T3/T4 비율     B.4.1  50/25/15/10
    A6 F3 주제 중복 상한 5%           B.3
    A7 F4 레코드별 생성 출처          B.3
    A8 J1 채점 키 · J2 참조답안 2개 이상 · J3 사람 표본 50건   B.4.2
    A9 train <-> eval source-disjoint
    A10 내부 근사중복(문자 5-gram 자카드)
    A11 F2 held-out 오염(고유명사 집합)
    A12 지도 토큰 비율(assistant 몫)

🚫**이 도구는 데이터를 고치지 않는다.** 읽기 전용이다(`datasets/TinyDataset` 은 사용자 허가 사항).
⚠️**토큰 수는 토크나이저가 있어야 정확하다** — 없으면 문자수 기반 ⚙추정을 인쇄하고
   그 사실을 표시한다(🚫추정을 실측으로 적지 않는다).

    python scripts/audit_sft_corpus.py
    python scripts/audit_sft_corpus.py --tokenizer data_cache/tok-ko-en-32768.json
    python scripts/audit_sft_corpus.py --root datasets/TinyDataset/SFT/v2/revision1 \
        --tokenizer data_cache/tok-ko-en-32768.json --serialized-chatml \
        --records-informational
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SFT = ROOT / "datasets" / "TinyDataset" / "SFT"

#: ★요청서 부록 B 의 수. **이 수가 정본이고 데이터가 따라온다.**
WANT_RECORDS = (25_000, 40_000)
WANT_TOKENS_MIN = 5_000_000
WANT_TOKENS_REC = 10_000_000
WANT_GRADE_MIX = {"T1": 0.50, "T2": 0.25, "T3": 0.15, "T4": 0.10}
TOPIC_SHARE_MAX = 0.05
JUDGE_SAMPLE_MIN = 50

#: ⚙문자 -> 토큰 환산. 한국어 BPE 32,768 에서 관측된 대역(결과 060·075).
#: 🚫**이것은 추정이고 실측이 아니다.**
CHARS_PER_TOKEN = 2.2

FAILS: list[str] = []
WARNS: list[str] = []


def bad(msg):
    FAILS.append(msg)
    print("  [FAIL] " + msg)


def warn(msg):
    WARNS.append(msg)
    print("  [WARN] " + msg)


def ok(msg):
    print("  [ok]   " + msg)


def info(msg):
    print("         " + msg)


def head(title):
    print()
    print("=" * 96)
    print("  " + title)
    print("=" * 96)


def read_jsonl(p: Path):
    out = []
    for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception as e:                                  # noqa: BLE001
            bad("%s:%d JSON 파싱 실패 — %s" % (p.name, i, e))
    return out


def texts(msg):
    """canonical content 배열에서 text 만 잇는다."""
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(b.get("text", "") for b in c if isinstance(b, dict))
    return ""


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip()


def grade_of(rec):
    """레코드를 T1~T4 로 분류한다. ★분류 규약을 한 곳에서만 정의한다(함정 18).

    ★**T1 의 정의는 '보기가 있다' 가 아니라 '우도 비교로 채점된다' 이다**(요청서 B.4.1 —
    *"생성이 없다"* 가 T1 의 타당성 근거다). 그래서 **후보 목록이 별도 필드(`choices`)로
    있고 답이 그 중 하나의 인덱스/문자열일 때만** T1 로 센다.
    🚫보기를 질문 **문장 안에** 넣고 답을 **문장으로 생성**하게 하면 그것은 T1 이 아니다 —
    채점기가 생성물을 봐야 하므로 T3 다.
    """
    meta = rec.get("meta") or {}
    g = meta.get("grading") or {}
    mode = str(g.get("scoring_mode", ""))
    rtype = str(meta.get("response_type", ""))

    if g.get("choices") or mode in ("multiple_choice", "likelihood_choice"):
        return "T1"
    if mode in ("exact_match", "normalized_exact", "accepted_answers") or rtype == "exact_short":
        return "T2"
    if g.get("format_constraints") or mode in ("constraint", "format",
                                               "required_elements_and_format"):
        return "T3"
    if mode in ("required_elements", "choice_and_required_elements") \
            or rtype in ("grounded_qa", "choice_with_reason", "constraint_response"):
        # 규칙 채점(필수 요소 포함 / 금칙 요소 배제) — 사람이 필요 없다.
        return "T3"
    return "T4"


def ngrams(s, n):
    s = norm(s)
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def message_text(rec):
    return " ".join(texts(message) for message in rec.get("messages", []))


def structural_text(rec, source_by_id):
    """가공어·표면 슬롯을 가려 이름만 다른 template 복제를 드러낸다."""
    meta = rec.get("meta") or {}
    source = source_by_id.get(meta.get("source_id")) or {}
    value = message_text(rec)
    replacements = set(meta.get("concepts") or [])
    replacements.update(
        item for item in (source.get("surface_axes") or {}).values()
        if isinstance(item, str)
    )
    replacements.update((meta.get("topic_label"), meta.get("coined_stem")))
    for item in sorted((item for item in replacements if item), key=len, reverse=True):
        value = value.replace(item, "<X>")
    value = re.sub(r"\d+", "<N>", value)
    return norm(value)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(SFT),
                    help="감사할 SFT package root. 기본값은 기존 datasets/TinyDataset/SFT")
    ap.add_argument("--tokenizer", default=None,
                    help="tokenizers json 경로. 주면 토큰을 **실측**한다")
    ap.add_argument("--serialized-chatml", action="store_true",
                    help="본문 합이 아니라 canonical ChatML 직렬화 총토큰과 supervised mask를 센다")
    ap.add_argument("--records-informational", action="store_true",
                    help="레코드 수를 실패 게이트가 아닌 정보로만 센다(v2 요청서 C.4)")
    ap.add_argument("--structural-audit", action="store_true",
                    help="가공어·표면 슬롯을 가린 train 내부 및 train/eval template 근접도를 전수 검사")
    ap.add_argument("--heldout", default=None,
                    help="held-out json/jsonl (F2 오염 대조)")
    ap.add_argument("--dup-sample", type=int, default=1500,
                    help="A10 내부 근사중복을 볼 표본 크기(O(n^2))")
    a = ap.parse_args()

    head("SFT 코퍼스 감사 — 정본은 요청서 부록 B")
    sft = Path(a.root)
    if not sft.is_absolute():
        sft = ROOT / sft
    if not sft.exists():
        bad("%s 가 없다" % sft)
        return 2

    train_p = sorted(sft.glob("train/*.canonical.jsonl"))
    eval_p = sorted(sft.glob("eval/*.canonical.jsonl"))
    if not train_p:
        bad("train/*.canonical.jsonl 이 없다")
        return 2
    train = read_jsonl(train_p[0])
    ev = read_jsonl(eval_p[0]) if eval_p else []
    info("train %s (%d건) · eval %s (%d건)"
         % (train_p[0].name, len(train), eval_p[0].name if eval_p else "-", len(ev)))

    # ---------------------------------------------------------------- A1 규모
    head("A1 규모(레코드) — 요청 25,000~40,000 (B.1.3)")
    n = len(train)
    if a.records_informational:
        info("train %d건 — v2 요청서 C.4에 따라 토큰 수가 1차 기준이고 레코드 수는 정보값" % n)
    elif n < WANT_RECORDS[0]:
        bad("train %d건 — 요청 최소 %d건의 **%.1f%%**"
            % (n, WANT_RECORDS[0], 100.0 * n / WANT_RECORDS[0]))
    else:
        ok("train %d건" % n)

    # ---------------------------------------------------------------- A2 토큰
    head("A2 규모(토큰) — 요청 10M 권장 · 5M 최소 (B.1.3)")
    all_txt, asst_txt = [], []
    for r in train:
        for m in r.get("messages", []):
            t = texts(m)
            all_txt.append(t)
            if m.get("role") == "assistant":
                asst_txt.append(t)
    chars = sum(len(t) for t in all_txt)
    a_chars = sum(len(t) for t in asst_txt)
    tok = a_tok = None
    tk = None
    if a.tokenizer:
        try:
            from tokenizers import Tokenizer            # type: ignore
            tk = Tokenizer.from_file(str(ROOT / a.tokenizer)
                                     if not Path(a.tokenizer).is_absolute() else a.tokenizer)
            tok = sum(len(tk.encode(t).ids) for t in all_txt)
            a_tok = sum(len(tk.encode(t).ids) for t in asst_txt)
        except Exception as e:                                  # noqa: BLE001
            warn("토크나이저를 못 썼다(%s) — ⚙문자 기반 추정으로 내려간다" % e)
    if tok is not None and a.serialized_chatml:
        try:
            from tinylm.data.sft import mask_stats
            stats = mask_stats(train, tk, "chatml")
            tok = stats["tokens"]
            a_tok = stats["supervised"]
            mark = "실측(ChatML 직렬화·assistant-only mask)"
        except Exception as e:                                  # noqa: BLE001
            bad("ChatML 직렬화 토큰 계측 실패(%s)" % e)
            tok = a_tok = None
    if tok is None:
        tok = int(chars / CHARS_PER_TOKEN)
        a_tok = int(a_chars / CHARS_PER_TOKEN)
        mark = "⚙추정(문자/%.1f)" % CHARS_PER_TOKEN
    elif not a.serialized_chatml:
        mark = "실측"
    info("문자 %s · 토큰 %s (%s) · assistant 토큰 %s"
         % ("{:,}".format(chars), "{:,}".format(tok), mark, "{:,}".format(a_tok)))
    if tok < WANT_TOKENS_MIN:
        bad("토큰 %s — **최소 5M 의 %.1f%%**, 권장 10M 의 %.1f%% (%s)"
            % ("{:,}".format(tok), 100.0 * tok / WANT_TOKENS_MIN,
               100.0 * tok / WANT_TOKENS_REC, mark))
    elif tok < WANT_TOKENS_REC:
        warn("토큰 %s — 최소는 넘고 권장 10M 미달 (%s)" % ("{:,}".format(tok), mark))
    else:
        ok("토큰 %s (%s)" % ("{:,}".format(tok), mark))
    steps = tok / 16384.0
    info("유효배치 16,384 기준 1 epoch = **%.0f 스텝** (요청서 B.1.1 문턱 300)" % steps)
    if steps < 300:
        bad("1 epoch %.0f 스텝 — **B.1.1 의 문턱 300 미달**(3 epoch 도 %.0f)"
            % (steps, steps * 3))
    info("지도 토큰 비율 = %.1f%% (assistant 몫; 요청서 추정 40~60%%)"
         % (100.0 * a_tok / max(1, tok)))

    # ------------------------------------------------------------ A3 스키마
    head("A3 canonical 스키마 (B.2)")
    bad_schema = Counter()
    for r in train + ev:
        ms = r.get("messages") or []
        meta = r.get("meta") or {}
        if meta.get("canonical_version") != 1:
            bad_schema["canonical_version != 1"] += 1
        roles = [m.get("role") for m in ms]
        if roles != ["user", "assistant"]:
            bad_schema["roles != [user, assistant] (%s)" % roles] += 1
        for m in ms:
            c = m.get("content")
            if not isinstance(c, list) or not all(
                    isinstance(b, dict) and b.get("type") == "text" for b in c):
                bad_schema["content 가 text 블록 배열이 아니다"] += 1
    if bad_schema:
        for k, v in bad_schema.most_common(6):
            bad("스키마 위반 %d건 — %s" % (v, k))
    else:
        ok("canonical_version=1 · user->assistant 2턴 · text 블록 — 위반 0건 (%d건 검사)"
           % (len(train) + len(ev)))

    # -------------------------------------------------- A4 assistant-only 마스크
    head("A4 assistant-only 마스크 가능성 (B.2)")
    empty = sum(1 for r in train if not norm(texts(r["messages"][1])))
    dup = sum(1 for r in train
              if norm(texts(r["messages"][1])) == norm(texts(r["messages"][0])))
    if empty:
        bad("assistant 텍스트가 빈 레코드 %d건 — 손실 대상이 0 이 된다" % empty)
    if dup:
        bad("assistant 가 user 와 문자열 동일한 레코드 %d건" % dup)
    if not empty and not dup:
        ok("assistant span 이 비지 않고 user 와 다르다 — 마스크 경계가 유일하다")
    info("⚠️**이 검사는 정적이다.** loader 가 정말 user 를 −100 으로 마스크하는지는 "
         "별도 assistant-only 스모크가 답한다.")

    # ------------------------------------------------------------ A5 채점 등급
    head("A5 채점 등급 분포 — 요청 T1 50% / T2 25% / T3 15% / T4 10% (B.4.1)")
    gr = Counter(grade_of(r) for r in train)
    ge = Counter(grade_of(r) for r in ev)
    modes = Counter(str(((r.get("meta") or {}).get("grading") or {}).get("scoring_mode"))
                    for r in train)
    for g in ("T1", "T2", "T3", "T4"):
        got = gr.get(g, 0) / float(max(1, len(train)))
        want = WANT_GRADE_MIX[g]
        line = "%s  요청 %4.0f%%  실제 %5.1f%%  (%d건)" % (g, want * 100, got * 100, gr.get(g, 0))
        if abs(got - want) > 0.10:
            bad(line)
        else:
            ok(line)
    info("scoring_mode 분포: " + ", ".join("%s=%d" % kv for kv in modes.most_common()))
    info("eval 등급: " + ", ".join("%s=%d" % kv for kv in ge.most_common()))

    # ------------------------------------------------------ A5b T1 token length
    head("A5b T1 정답 선택지 토큰 길이 편향 (B.4.1)")
    if tk is None:
        info("토크나이저 실측이 없어 T1 정답의 최장·최단 여부를 건너뛴다")
    else:
        longest = shortest = malformed = 0
        checked = 0
        for rec in train:
            if grade_of(rec) != "T1":
                continue
            grading = ((rec.get("meta") or {}).get("grading") or {})
            choices = grading.get("choices")
            gold = grading.get("gold")
            if not isinstance(choices, list) or not isinstance(gold, int) \
                    or not (0 <= gold < len(choices)):
                malformed += 1
                continue
            lengths = [len(tk.encode(str(choice)).ids) for choice in choices]
            checked += 1
            longest += int(lengths[gold] == max(lengths))
            shortest += int(lengths[gold] == min(lengths))
        if malformed:
            bad("T1 grading choices/gold 형식 오류 %d건" % malformed)
        line = "T1 %d건 검사 · 정답이 토큰 최장 %d건 · 최단 %d건" % (
            checked, longest, shortest
        )
        if longest or shortest:
            bad(line + " — 요청은 각각 0건")
        else:
            ok(line)

    # ---------------------------------------------------------------- A6 F3
    head("A6 F3 주제 중복 상한 5% (B.3)")
    for field in ("topic_label", "source_family", "primary_concept"):
        c = Counter((r.get("meta") or {}).get(field) for r in train)
        c.pop(None, None)
        if not c:
            warn("`%s` 필드가 비어 있다" % field)
            continue
        top, cnt = c.most_common(1)[0]
        share = cnt / float(len(train))
        line = "%-16s 고유 %4d개 · 최대 점유 %.2f%% (%s)" % (field, len(c), share * 100, top)
        if share > TOPIC_SHARE_MAX:
            bad(line + "  -> 5% 초과")
        else:
            ok(line)

    # ---------------------------------------------------------------- A7 F4
    head("A7 F4 레코드별 생성 출처 (B.3 — 100% 요구)")
    keys = ("generator", "prompt_version", "prompt_sha256", "batch_id", "model")
    has = sum(1 for r in train
              if any(k in (r.get("meta") or {}) for k in keys))
    if has < len(train):
        bad("레코드에 생성 출처 필드가 %d/%d 건뿐 — 요청은 **레코드마다 100%%**"
            % (has, len(train)))
        info("현재는 매니페스트에만 있다(`manifests/*_manifest.json` 의 `generator`). "
             "★매니페스트는 파일 단위라 **레코드를 쪼개 섞으면 출처가 끊긴다**(D21).")
    else:
        ok("레코드마다 생성 출처가 있다")

    # ------------------------------------------------------------- A8 J1~J3
    head("A8 T4 채점 요구 J1·J2·J3 (B.4.2)")
    t4 = [r for r in train + ev if grade_of(r) == "T4"]
    if not t4:
        info("T4 레코드가 0건 — J1~J3 는 **적용 대상 없음**(그 자체가 A5 의 문제다)")
    else:
        j1 = sum(1 for r in t4 if ((r.get("meta") or {}).get("grading") or {}).get("required_elements"))
        j2 = sum(1 for r in t4
                 if len(((r.get("meta") or {}).get("grading") or {}).get("reference_answers") or []) >= 2)
        if j1 < len(t4):
            bad("J1 채점 키가 %d/%d" % (j1, len(t4)))
        if j2 < len(t4):
            bad("J2 참조답안 2개 이상이 %d/%d" % (j2, len(t4)))
    judge = list(sft.glob("**/*judge*"))
    human = list(sft.glob("**/*human*"))
    judge_used = None
    for manifest_path in sorted(sft.glob("manifests/*manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if "llm_judge_used" in manifest:
            judge_used = bool(manifest["llm_judge_used"])
            break
    if judge_used is False and not judge:
        info("LLM 심판 미사용 — 요청서의 조건부 J3 사람 50건 대조는 적용 대상 아님")
    elif (judge_used is True or judge) and not human:
        bad("LLM 심판을 썼지만 J3 사람 표본 %d건 대조 자료가 **없다**" % JUDGE_SAMPLE_MIN)
    elif judge_used is None and not judge and not human:
        warn("LLM 심판 사용 여부를 확인할 manifest가 없어 J3 적용 여부를 판정하지 못했다")

    # ---------------------------------------------------------------- A9
    head("A9 train <-> eval source-disjoint")
    if ev:
        st = {(r.get("meta") or {}).get("source_id") for r in train}
        se = {(r.get("meta") or {}).get("source_id") for r in ev}
        inter = (st & se) - {None}
        if inter:
            bad("source_id 교집합 %d건" % len(inter))
        else:
            ok("source_id 교집합 0건 (train %d · eval %d)" % (len(st), len(se)))
        ft = {(r.get("meta") or {}).get("source_family") for r in train}
        fe = {(r.get("meta") or {}).get("source_family") for r in ev}
        fi = (ft & fe) - {None}
        if fi:
            bad("source_family 교집합 %d건 — %s" % (len(fi), sorted(fi)[:5]))
        else:
            ok("source_family 교집합 0건")
    else:
        warn("eval 파일이 없다")

    # ----------------------------------------------- A9b structural disjoint
    if a.structural_audit and ev:
        head("A9b 구조 template 격리 — 이름·표면 슬롯을 가린 5-gram Jaccard")
        train_source_p = sorted(sft.glob("sources/*source_ledger*.jsonl"))
        eval_source_p = sorted(sft.glob("eval/*source_ledger*.jsonl"))
        source_rows = []
        for path in train_source_p + eval_source_p:
            source_rows.extend(read_jsonl(path))
        source_by_id = {
            row.get("source_id"): row for row in source_rows
            if isinstance(row.get("source_id"), str)
        }
        train_struct = [structural_text(rec, source_by_id) for rec in train]
        eval_struct = [structural_text(rec, source_by_id) for rec in ev]

        internal_groups = {}
        for rec, value in zip(train, train_struct):
            meta = rec.get("meta") or {}
            key = (meta.get("semantic_task"), meta.get("logic_archetype"),
                   meta.get("topic_label"))
            internal_groups.setdefault(key, []).append((rec, ngrams(value, 5)))
        internal_pairs = 0
        internal_high = 0
        internal_records = set()
        internal_max = 0.0
        for rows in internal_groups.values():
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    internal_pairs += 1
                    score = jaccard(rows[i][1], rows[j][1])
                    internal_max = max(internal_max, score)
                    if score >= 0.80:
                        internal_high += 1
                        internal_records.add((rows[i][0].get("meta") or {}).get("id"))
                        internal_records.add((rows[j][0].get("meta") or {}).get("id"))
        info("train 동일 task·logic·topic 쌍 %d개 중 >=0.80 %d쌍 · 관련 레코드 %d/%d · max %.4f"
             % (internal_pairs, internal_high, len(internal_records), len(train), internal_max))
        if internal_high:
            bad("구조 template 내부 근사중복 >=0.80 이 %d쌍" % internal_high)

        cross_groups = {}
        for rec, value in zip(train, train_struct):
            meta = rec.get("meta") or {}
            key = (meta.get("semantic_task"), meta.get("logic_archetype"))
            cross_groups.setdefault(key, []).append(ngrams(value, 5))
        nearest = []
        for rec, value in zip(ev, eval_struct):
            meta = rec.get("meta") or {}
            key = (meta.get("semantic_task"), meta.get("logic_archetype"))
            query = ngrams(value, 5)
            nearest.append(max((jaccard(query, candidate)
                                for candidate in cross_groups.get(key, [])), default=0.0))
        high_08 = sum(score >= 0.80 for score in nearest)
        high_09 = sum(score >= 0.90 for score in nearest)
        info("eval nearest: >=0.80 %d/%d · >=0.90 %d/%d · median %.4f · min %.4f · max %.4f"
             % (high_08, len(ev), high_09, len(ev), statistics.median(nearest),
                min(nearest), max(nearest)))
        if high_08:
            bad("train/eval 구조 template 근접도 >=0.80 인 eval이 %d/%d" % (high_08, len(ev)))

    # ---------------------------------------------------------------- A10
    head("A10 내부 근사중복 (문자 5-gram 자카드, 표본 %d)" % a.dup_sample)
    sample = train[:a.dup_sample]
    grams = [ngrams(texts(r["messages"][0]) + " " + texts(r["messages"][1]), 5)
             for r in sample]
    worst, pairs_hi = 0.0, 0
    wi = wj = -1
    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            s = jaccard(grams[i], grams[j])
            if s >= 0.80:
                pairs_hi += 1
            if s > worst:
                worst, wi, wj = s, i, j
    info("최고 유사도 %.4f  (%s vs %s)"
         % (worst,
            (sample[wi].get("meta") or {}).get("id") if wi >= 0 else "-",
            (sample[wj].get("meta") or {}).get("id") if wj >= 0 else "-"))
    if pairs_hi:
        warn("자카드 >= 0.80 인 쌍 %d개 — **유니크 착시**(리라이팅 실패 4번)와 같은 형태다"
             % pairs_hi)
    else:
        ok("자카드 >= 0.80 인 쌍 0개")

    # ---------------------------------------------------------------- A11
    head("A11 F2 held-out 오염 (고유명사 집합)")
    if a.heldout:
        hp = Path(a.heldout)
        raw = hp.read_text(encoding="utf-8")
        items = (json.loads(raw) if hp.suffix == ".json"
                 else [json.loads(x) for x in raw.splitlines() if x.strip()])
        if isinstance(items, dict):
            items = items.get("items") or items.get("questions") or []
        hs = set()
        for it in items:
            hs |= set(re.findall(r"[가-힣]{2,}", json.dumps(it, ensure_ascii=False)))
        cs = set()
        for r in train:
            for c in (r.get("meta") or {}).get("concepts") or []:
                cs.add(c)
        inter = cs & hs
        if inter:
            warn("held-out 텍스트와 겹치는 concept %d개 — %s"
                 % (len(inter), sorted(inter)[:8]))
        else:
            ok("concept 겹침 0개 (concept %d개 · held-out 어휘 %d개)" % (len(cs), len(hs)))
    else:
        info("--heldout 를 안 줬다 — 건너뛴다")

    # ---------------------------------------------------------------- 요약
    head("요약")
    print("  실패 %d건 · 경고 %d건" % (len(FAILS), len(WARNS)))
    for m in FAILS:
        print("    [FAIL] " + m)
    for m in WARNS:
        print("    [WARN] " + m)
    print()
    print("  ⚠️이 도구는 **요청서 사양과의 대조**만 본다. 문장이 사실인지·자연스러운지는 안 본다.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
