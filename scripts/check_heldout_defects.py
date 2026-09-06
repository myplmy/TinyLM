#!/usr/bin/env python3
"""★★held-out 벤치마크의 **의미 결함**을 잡는다 — 구조가 아니라 **뜻**을 본다.

## 왜 이 검사가 생겼나 (2026-09-03)

사람 검수 30문항이 기계 검수가 **한 건도 못 본 것**을 짚었다. 종전 검사는 구조만 봤다
(정답 불변 · 금지관계 정합 · 중복 · 문자폭). 그래서 이런 것이 통과했다:

    질문      "공기는 하나의 순수한 물질인가?"
    answer   "아니다. 공기는 혼합물이다."          ← 옳다
    정답 후보 "공기는 혼합물 범주에 속하지 않는다"   ← 🚫**answer 와 정면 모순**

생성기가 **부정할 명사를 질문이 아니라 답에서** 골랐다. ★**지식과 역상관**이라
**사실을 아는 모델일수록 틀린다.**

## 두 검사

| | 무엇 | 성질 |
|---|---|---|
| **D1** | 오답 후보가 **정답 후보와 같아졌는가**(정답이 둘) | ★**정확**하다. 술어를 뽑아 **완전 일치**로 본다 |
| **D2** | 정답 후보가 **`answer` 를 부정하고 있는가** | ⚠️**휴리스틱**이다. 거짓 양성이 난다 — 사람이 읽는다 |

🚫★**D1 을 부분문자열로 하면 안 된다.** `식물` 이 `양치식물` 안에 있어서
초기 스캔이 **0건**을 냈다(2026-09-03 사고). 그래서 **술어를 정규식으로 뽑아** 비교한다.

사용법
    python scripts/check_heldout_defects.py --dir <held-out 폴더>
    python scripts/check_heldout_defects.py            # v2.3 · v2.4 둘 다
종료코드 0 = D1 0건 / 1 = D1 이 걸렸다  (D2 는 경고이지 실패가 아니다)
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "datasets" / "TinyDataset" / "stage1_dataset"

# ★서술어를 뽑는다 — "X는 <서술>이다/다." 의 <서술>.
#   🚫부분문자열 비교 금지(`식물` ⊂ `양치식물`). 뽑은 뒤 **완전 일치**로만 본다.
RE_PRED = re.compile(r"[은는이가]\s*(.+?)(?:이다|다)[.。]?\s*$")
RE_NEG = re.compile(r"(않는다|않다|아니다|아니라고|없다)")


def first_sentence(s: str) -> str:
    """★**첫 문장만** 쓴다.

    🚫2026-09-03 오탐: 후보 뒤에 *"이는 주어진 조건에 따른 판단이다."* 라는 **상투 문장**이
    붙어 있어, 문장 전체에서 서술어를 뽑으면 **모든 후보가 같아 보였다**(22건 거짓 양성).
    ★게이트를 먼저 의심한 결과다(함정 34 — 4번 중 4번 게이트가 틀렸다).
    """
    return re.split(r"[.。]\s*", (s or "").strip())[0]


def predicate(s: str) -> str:
    s = first_sentence(s)
    m = RE_PRED.search(s + ".")
    return (m.group(1) if m else s).strip()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def content_words(s: str):
    """조사·군더더기를 걷어낸 내용어 후보(2자 이상 한글 덩어리)."""
    drop = {"범주", "속한다", "판단할", "있다", "것으로", "그것", "대상"}
    return {w for w in re.findall(r"[가-힣]{2,}", s or "") if w not in drop}


def load(folder: Path):
    # 🚫★`*metadata*` 를 먼저 집으면 **엉뚱한 파일을 채점**한다 —
    #   v2.3 이 0건으로 나오던 원인이 이것이었다(2026-09-03).
    for f in sorted(p for p in folder.glob("*benchmark*300.json")
                    if "metadata" not in p.name):
        d = json.load(io.open(f, encoding="utf-8"))
        recs = d.get("records") if isinstance(d, dict) else d
        if recs:
            return f, recs
    return None, None


def scan(folder: Path):
    f, recs = load(folder)
    if not recs:
        print(f"  🚫 {folder.name}: benchmark json 을 못 찾았다")
        return None, None, None
    d1, d2, d3 = [], [], []
    for r in recs:
        cands = r.get("candidates") or []
        ci = r.get("correct_index")
        if not cands or ci is None or not (0 <= ci < len(cands)):
            continue
        gold_c = cands[ci]

        # ── D1: 오답이 정답 후보와 **같은 서술**이 됐는가 (정답이 둘)
        gp = predicate(gold_c)
        for k, c in enumerate(cands):
            if k == ci:
                continue
            # ★D1 = **완전 일치만** 본다(정규화 공백 무시). 모호함이 0 이다.
            #   🚫서술어 비교는 **버렸다** — `novel_relation` 후보가 전부
            #   *"... 관계다. 이는 주어진 조건에 따른 판단이다."* 꼴이라
            #   어떤 추출 규칙을 써도 **모든 후보가 '관계' 로 축약**된다(2026-09-03 오탐 22건).
            if norm(c) == norm(gold_c):
                d1.append((r.get("id"), k, c))

        # ── ★D2: 정답 후보가 **`answer` 의 서술어를 부정**하고 있는가
        #   🚫초판 조건이 틀렸다 — *"answer 에 부정어가 없을 때만"* 이라 걸었는데
        #   결함 문항의 answer 는 *"아니다. 공기는 혼합물이다."* 처럼 **부정어로 시작**한다.
        #   그래서 알려진 9건을 **한 건도 못 잡았다.**
        #   ★옳은 조건: **정답 후보가 부정문이고, 그 안에 `answer` 의 *서술어 명사* 가 있다.**
        #     예) answer 서술어 = `혼합물` · 정답 후보 = "공기는 **혼합물** 범주에 속하지 **않는다**"
        #     → 부정할 대상을 **질문이 아니라 답에서** 골랐다는 신호다.
        ans = r.get("answer") or ""
        ans_last = re.split(r"[.。]\s*", ans.strip())
        ans_pred = predicate(ans_last[-1] if ans_last[-1] else
                             (ans_last[-2] if len(ans_last) > 1 else ans))
        if RE_NEG.search(gold_c):
            shared = content_words(ans_pred) & content_words(gold_c)
            if shared:
                d2.append((r.get("id"), sorted(shared)[:3], gold_c))

        # ── ★D1b: 오답 후보가 **`answer` 의 서술어와 같아졌는가** (E-020 형태)
        for k, c in enumerate(cands):
            if k == ci:
                continue
            if ans_pred and len(ans_pred) >= 2 and predicate(c) == ans_pred:
                d1.append((r.get("id"), k, "오답이 정답 문장의 서술어와 동일: " + c))

        # ── ★D3(정보): 후보에 **질문의 내용어가 하나도 없는가**
        #   사용자 지적(2026-09-03): *"후보문장들이 과하게 일반화 되어있어서
        #   후보문장들끼리만 비교했을때 중복문장이 많아보임"*.
        #   ⚠️**이것은 결함 판정이 아니다** — 틀을 맞춘 것은 길이 편향 제거를 위한 설계다.
        #   ★다만 **내용어까지 사라지면** 개념 지식이 아니라 대명사 결합을 재게 된다.
        pw = content_words(r.get("prompt"))
        if pw and not any(content_words(c) & pw for c in cands):
            d3.append((r.get("id"), r.get("split")))
    return d1, d2, d3


# ★★D4 (2026-09-04 신설) — **부정 지름길**
#
#   held-out v2.5 검증 중 발견했다. 우리 문형은 대개 *"X 는 A 범주에 속한다"* 셋 +
#   *"X 는 A 범주에 속하지 **않는다**"* 하나다. 그러면 후보만 보고 **부정형을 고르는**
#   전략이 성립한다 — **모델이 X 도 A 도 몰라도** 된다.
#
#   실측(v2.5): 부정 후보가 **정확히 하나**인 문항 **90 / 300**, 그중 그것이 정답인 경우
#   **85 (94.4%)**. 부정 선택기의 전체 기대 정답률 **31.3%**(우연 25.0, z 약 +2.4).
#   🚫**길이 축(30.3%)보다 강한 지름길**인데 지금까지 아무도 안 쟀다.
#
#   ⚠️**이것은 결함 판정이 아니라 계측**이다 — |z| ^> 3 이면 그때 결함이다(결과 068 규약).
_NEG = re.compile(r"않는다|없다|아니다|못한다")


def d4_negation(recs):
    """-> (부정후보 1개인 문항 수, 그중 정답인 수, 부정선택기 기대정답률%)"""
    only = hit = 0
    acc = 0.0
    for r in recs:
        cands = r.get("candidates") or []
        ci = r.get("correct_index")
        if not cands or ci is None:
            continue
        negs = [i for i, c in enumerate(cands) if _NEG.search(str(c))]
        if len(negs) == 1:
            only += 1
            if negs[0] == ci:
                hit += 1
        if negs:
            acc += (1.0 / len(negs)) if ci in negs else 0.0
    n = len(recs) or 1
    return only, hit, 100.0 * acc / n


# ★★D5·D6·D7 (2026-09-05 신설, v2.6 검증 중 발견) ─────────────────────────────
#
#   D5 — **양태 지름길**. v2.6 이 D4(부정 어미)를 피하려고 정답을 *"확정하기에는
#        **부족**하다"* 로, 오답을 *"확정하기에 **충분**하다"* 로 썼다. 어미는 긍정이 됐지만
#        ★**"약한 쪽 하나를 고르는" 전략이 그대로 성립**한다 — 실측 4/4 = 100%.
#        🚫**D4 를 우회한 같은 결함**이다(함정 28: 한 결함이 두 얼굴).
#        ⚠️지금은 4문항뿐이라 전체 선택기 정답률이 25.2%(z +0.1) = 무해하다.
#        ★**그래서 지금 재 둔다** — 다음 개정이 이 방식을 12건에 더 쓰면 그때는 안 무해하다.
#
#   D6 — ★**정답이 둘인 문항**. `required_relations_canonical` 과
#        `forbidden_relations_canonical` 이 **겹치면** 같은 관계가 정답이자 오답이다.
#        실측 2건(E-157 · E-205)이고 **v2.3 부터 그대로 있었다** — 아무도 이 축을 안 봤다.
#        🚫E-272(정답 없음)의 **거울상**이다.
#
#   D7 — 후보 안에 **같은 문장이 두 번**. 실측 41건(*"이는 주어진 조건에 따른 판단이다."* ×2).
#        네 후보 모두에 있어 지름길은 아니지만 **템플릿 결함**이고 토큰을 낭비한다.
_WEAK = ("부족", "충분하지", "불충분")


def d5_modality(recs):
    """'충분' 셋 + '부족' 하나 대조가 있는 문항 수와 그중 정답인 수, 전체 선택기 정답률."""
    only = hit = 0
    acc = 0.0
    for r in recs:
        cands = r.get("candidates") or []
        ci = r.get("correct_index")
        if not cands or ci is None:
            continue
        weak = [i for i, c in enumerate(cands) if any(w in str(c) for w in _WEAK)]
        strong = [i for i, c in enumerate(cands)
                  if "충분" in str(c) and not any(w in str(c) for w in _WEAK)]
        if len(weak) == 1 and len(strong) == len(cands) - 1:
            only += 1
            if weak[0] == ci:
                hit += 1
        if weak:
            acc += (1.0 / len(weak)) if ci in weak else 0.0
        else:
            acc += 1.0 / max(1, len(cands))
    n = len(recs) or 1
    return only, hit, 100.0 * acc / n


def d6_two_answers(recs):
    """required 와 forbidden 이 겹치는 문항 = **정답이 둘일 수 있다**."""
    out = []
    for r in recs:
        req = set(r.get("required_relations_canonical") or [])
        fb = set(r.get("forbidden_relations_canonical") or [])
        both = sorted(req & fb)
        if both:
            out.append((r.get("id"), both))
    return out


def d7_dup_sentence(recs):
    """한 후보 안에 같은 문장이 두 번 들어간 문항."""
    out = []
    for r in recs:
        for c in (r.get("candidates") or []):
            parts = [t.strip() for t in str(c).split(".") if t.strip()]
            if len(parts) != len(set(parts)):
                out.append(r.get("id"))
                break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    a = ap.parse_args()

    dirs = ([Path(a.dir)] if a.dir else
            [p for p in sorted(BASE.glob("held-out_v2.*")) if p.is_dir()])

    print("=" * 96)
    print("  check_heldout_defects — 구조가 아니라 **뜻**을 본다 (2026-09-03 신설)")
    print("=" * 96)

    # ★★2026-09-06 — **판정은 최신본 하나로 한다**(사용자 지시 (5) 처리 중 발견).
    #   🚫종전은 `held-out_v2.*` **전부**를 합산해서 exit code 를 냈다. 옛 판(v2.3~v2.6)은
    #   **우리가 안 고치는 기록**이라 D6 이 영원히 남고, 게이트가 **영구히 빨갛다.**
    #   ★영구히 빨간 게이트는 게이트가 아니다 — 아무도 안 본다(알람 피로).
    #   → **최신 판만 exit code 에 넣고 옛 판은 인쇄만** 한다.
    latest = dirs[-1].name if dirs else None
    total_d1 = 0
    total_d6 = 0
    recs_count = {}
    for folder in dirs:
        _judge = (folder.name == latest)
        d1, d2, d3 = scan(folder)
        if d1 is None:
            continue
        recs_count[folder.name] = load(folder)[1]
        if _judge:
            total_d1 += len(d1)
        print(f"{chr(10)}=== {folder.name}"
              + ("   ★**정본 — 이 판만 종료코드에 들어간다**" if _judge else "   (참고·판정 제외)"))
        print(f"  D1 오답이 정답과 같아짐 : {'🚫 %d건' % len(d1) if d1 else '✅ 0건'}")
        for rid, k, c in d1:
            print(f"       {rid}  후보[{k}]  {c[:64]}")
        print(f"  D2 정답 후보가 답을 부정 : {'⚠️ %d건(사람이 읽는다)' % len(d2) if d2 else '✅ 0건'}")
        for rid, sh, c in d2[:12]:
            print(f"       {rid}  공유어 {sh}  {c[:56]}")
        if len(d2) > 12:
            print(f"       … 외 {len(d2) - 12}건")
        n = len(recs_count.get(folder.name, [])) or 300
        print(f"  D3 후보에 질문 내용어 0개 : {len(d3)}건 / {n} "
              f"({100.0 * len(d3) / n:.1f}%)  ⚠️정보이지 결함 판정이 아니다")
        if d3:
            from collections import Counter
            for sp, cnt in Counter(x[1] for x in d3).most_common():
                print(f"       {sp}: {cnt}건")
        _rs = recs_count.get(folder.name) or []
        if _rs:
            only, hit, rate = d4_negation(_rs)
            _z = (rate - 25.0) / ((25.0 * 75.0 / len(_rs)) ** 0.5) if len(_rs) else 0.0
            _m = "🚫**결함**" if abs(_z) > 3 else "⚠️정보"
            print(f"  D4 부정 지름길           : 부정후보 1개 {only}/{len(_rs)}건 · "
                  f"그중 정답 {hit} ({100.0*hit/max(1,only):.1f}%) · "
                  f"부정선택기 **{rate:.1f}%**(우연 25.0, z {_z:+.1f})  {_m}")
            o5, h5, r5 = d5_modality(_rs)
            _z5 = (r5 - 25.0) / ((25.0 * 75.0 / len(_rs)) ** 0.5)
            _m5 = "🚫**결함**" if abs(_z5) > 3 else "⚠️정보"
            print(f"  D5 양태 지름길(충분/부족): 대조 {o5}/{len(_rs)}건 · "
                  f"그중 정답 {h5} ({100.0*h5/max(1,o5):.1f}%) · "
                  f"약함선택기 **{r5:.1f}%**(우연 25.0, z {_z5:+.1f})  {_m5}")
            d6 = d6_two_answers(_rs)
            print(f"  D6 정답이 둘일 수 있다   : {'🚫 %d건' % len(d6) if d6 else '✅ 0건'}"
                  + ("  " + " · ".join(f"{i}({','.join(b)})" for i, b in d6[:6]) if d6 else ""))
            if _judge:
                total_d6 += len(d6)
            d7 = d7_dup_sentence(_rs)
            print(f"  D7 후보 안 문장 중복     : {'⚠️ %d건' % len(d7) if d7 else '✅ 0건'}"
                  + (f"  {', '.join(d7[:6])} …" if len(d7) > 6 else
                     ("  " + ", ".join(d7) if d7 else "")))

    print()
    print("  ★D1 은 정확한 검사다 — **0건이어야 한다.**")
    print("  ⚠️D2 는 휴리스틱이다 — 거짓 양성이 난다. **무시하지 말고 문항 번호를 적어 회신**한다.")
    print("  🚫이 검사도 *'정답 문장이 사실인가'* 는 못 본다 — 그것은 사람 몫이다.")
    print("  ★D4·D5 는 **결함이 아니라 계측**이다 — |z| > 3 이면 그때 결함으로 센다(결과 068 규약).")
    print("  ★★D5 는 D4 의 **두 번째 얼굴**이다 — 어미를 긍정으로 바꿔도 *'약한 쪽 고르기'* 는 남는다.")
    print("  🚫★**D6 은 정확한 검사다 — 0건이어야 한다.** 정답이 둘이면 그 문항은 채점할 수 없다.")
    print(f"  ★★**종료코드는 최신본 `{latest}` 만 본다** — 옛 판은 고치지 않는 기록이라"
          " 합산하면 게이트가 **영구히 빨갛다**(2026-09-06 개정).")
    return 1 if (total_d1 or total_d6) else 0


if __name__ == "__main__":
    sys.exit(main())
