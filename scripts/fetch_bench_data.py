#!/usr/bin/env python3
"""★**벤치마크 데이터셋 내려받기 — 학습 0·GPU 0. 네트워크만 쓴다.**

## 왜 별도 도구인가

`eval_bench_suite.py` 는 **네트워크를 쓰지 않는다.** 평가 도중 다운로드가 섞이면
*"느린 것이 모델인가 네트워크인가"* 를 못 가른다. **받는 것과 재는 것을 분리**한다.

## 받는 것 (사용자 지시 2026-08-22 — **예상 결과와 무관하게 전부**)

    MMLU · MMLU-Redux · MuSR · IFEval · GSM8K · HumanEval+ · BFCL v3
    ARC(e/c) · BoolQ · HellaSwag · PIQA · WinoGrande · LAMBADA

⚠️★**HF 게이트가 걸린 것은 실패로 끝난다** — 그것도 결과다. **로그에 남긴다.**
⚠️★**받은 뒤 `--verify` 로 문항 수를 인쇄**한다. 공식 규모와 다르면 **split 을 잘못 잡은 것**이다.

사용법
    python scripts/fetch_bench_data.py --list          # 무엇을 받을지 (네트워크 0)
    python scripts/fetch_bench_data.py --all
    python scripts/fetch_bench_data.py --only hellaswag piqa lambada
    python scripts/fetch_bench_data.py --verify        # 이미 받은 것 점검 (네트워크 0)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "datasets" / "bench"

# (이름, HF id, config, split, 공식 규모, 비고)
# ★규모는 **각 논문/데이터카드의 통용값**이다. ⚠️조회 상태는 `docs/methods/11_benchmarks.md` §6.
SPECS = [
    ("hellaswag",     "Rowan/hellaswag",              None,            "validation", 10042, "4지선다 문장완성"),
    ("piqa",          "ybisk/piqa",                   None,            "validation",  1838, "2지선다 물리상식"),
    ("winogrande",    "allenai/winogrande",           "winogrande_xl", "validation",  1267, "2지선다 대명사"),
    ("arc_easy",      "allenai/ai2_arc",              "ARC-Easy",      "test",        2376, "4지선다 과학"),
    ("arc_challenge", "allenai/ai2_arc",              "ARC-Challenge", "test",        1172, "4지선다 과학(난)"),
    ("boolq",         "google/boolq",                 None,            "validation",  3270, "예/아니오. ⚠️라벨 불균형"),
    ("lambada",       "EleutherAI/lambada_openai",    "en",            "test",        5153, "★마지막 단어 예측"),
    ("mmlu",          "cais/mmlu",                    "all",           "test",       14042, "4지선다 57과목"),
    ("mmlu_redux",    "edinburgh-dawg/mmlu-redux-2.0", "all",          "test",        5700, "MMLU 오류 재라벨"),
    ("musr",          "TAUR-Lab/MuSR",                None,            "murder_mysteries", 250, "★MC 다. 생성 아님"),
    ("gsm8k",         "openai/gsm8k",                 "main",          "test",        1319, "다단계 산술"),
    ("ifeval",        "google/IFEval",                None,            "train",        541, "지시 따르기"),
    ("humaneval",     "openai/openai_humaneval",      None,            "test",         164, "코드 생성"),
    ("humaneval_plus", "evalplus/humanevalplus",      None,            "test",         164, "HE+ 확장 테스트"),
    ("bfcl_v3",       "gorilla-llm/Berkeley-Function-Calling-Leaderboard", None, "train", None, "함수 호출"),
]


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def do_list():
    banner("받을 목록 — 네트워크를 쓰지 않는다", "#")
    print(f"  저장 위치: datasets/bench/<이름>.jsonl")
    print(f"{'이름':<16}{'HF id':<52}{'config':<18}{'split':<12}{'공식 규모':>10}  비고")
    print("-" * 130)
    for n, hid, cfg, sp, sz, note in SPECS:
        have = (OUT / f"{n}.jsonl").exists()
        print(f"{('✅' if have else '  ') + n:<17}{hid:<52}{str(cfg or '-'):<18}"
              f"{sp:<12}{(str(sz) if sz else '?'):>10}  {note}")
    print(f"\n  ✅ = 이미 받음. 전부 받으려면 `--all`.")


def do_verify():
    banner("받은 것 점검 — 네트워크를 쓰지 않는다", "#")
    ok = miss = 0
    for n, _h, _c, _s, sz, _note in SPECS:
        p = OUT / f"{n}.jsonl"
        if not p.exists():
            print(f"  🚫 {n:<16} 없음")
            miss += 1
            continue
        cnt = sum(1 for _ in p.open(encoding="utf-8"))
        flag = "✅" if (sz is None or cnt == sz) else "⚠️"
        note = "" if (sz is None or cnt == sz) else f"  ← 공식 {sz} 와 다르다. **split 을 확인**"
        print(f"  {flag} {n:<16} {cnt:>7}행{note}")
        ok += 1
    print(f"\n  받음 {ok} / 없음 {miss}")
    print("  ⚠️★행 수가 공식 규모와 다르면 **split 을 잘못 잡은 것**이고, 그대로 재면 "
          "다른 논문 숫자와 비교할 수 없다.")
    return 1 if miss else 0


def fetch(name, hid, cfg, split):
    from datasets import load_dataset
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.jsonl"
    ds = load_dataset(hid, cfg, split=split) if cfg else load_dataset(hid, split=split)
    with p.open("w", encoding="utf-8") as f:
        for row in ds:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return p, len(ds)


def main():
    ap = argparse.ArgumentParser(description="벤치마크 데이터 내려받기 (GPU 0)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()

    if a.list:
        do_list()
        return 0
    if a.verify:
        return do_verify()
    if not (a.all or a.only):
        do_list()
        print("\n  ⚠️ 아무것도 받지 않았다. `--all` 또는 `--only <이름…>` 을 주세요.")
        return 2

    want = SPECS if a.all else [s for s in SPECS if s[0] in set(a.only)]
    banner(f"내려받기 {len(want)}종 — ★HF 게이트로 실패하면 **그것도 결과다. 지우지 않는다**", "#")
    good, bad = [], []
    for n, hid, cfg, sp, sz, _note in want:
        if (OUT / f"{n}.jsonl").exists():
            print(f"  [건너뜀] {n} — 이미 있다")
            good.append((n, "이미 있음"))
            continue
        try:
            p, cnt = fetch(n, hid, cfg, sp)
            flag = "✅" if (sz is None or cnt == sz) else "⚠️"
            print(f"  {flag} {n:<16} {cnt:>7}행 -> {p.name}"
                  + ("" if (sz is None or cnt == sz) else f"  (공식 {sz})"))
            good.append((n, cnt))
        except Exception as e:                                   # noqa: BLE001
            msg = str(e).splitlines()[0][:160]
            print(f"  🚫 {n:<16} 실패: {type(e).__name__}: {msg}")
            bad.append((n, f"{type(e).__name__}: {msg}"))

    banner("요약")
    print(f"  성공 {len(good)} / 실패 {len(bad)}")
    for n, why in bad:
        print(f"    🚫 {n}: {why}")
    if bad:
        print("\n  ⚠️★**실패 사유를 결과문서에 그대로 적는다.** 게이트·라이선스로 못 받은 것은 "
              "*'구현 안 함'* 이 아니라 *'접근 불가'* 다 — 둘은 다르다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
