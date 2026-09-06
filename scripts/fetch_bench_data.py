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

# ★★★2026-08-22 사고 — **이 한 줄이 없어서 15종이 전부 엉뚱한 곳에 받아졌다.**
#   `tinylm/paths.py` 는 import 부작용으로 HF_HOME·HF_HUB_CACHE·HF_DATASETS_CACHE 를
#   **작업폴더 `HF/` 로 강제**한다. 그런데 이 스크립트는 `sys.path` 만 건드리고
#   **`tinylm` 을 import 하지 않아서** 그 부작용이 한 번도 일어나지 않았다.
#   → `datasets` 가 사용자 환경의 `HF_HOME`(Z:\unsloth_files\cache)로 받았고
#      사용자가 손으로 옮겨야 했다.
#   ⚠️★**함정 37 의 다른 얼굴**이다: *"리다이렉트가 존재한다 != 그 경로가 실행된다."*
#   🚫**사용자 환경변수는 영구 수정하지 않는다** — 이 import 는 **이 프로세스 안에서만** 바꾼다.
import tinylm  # noqa: F401,E402  ★반드시 datasets/huggingface_hub 보다 먼저

OUT = ROOT / "datasets" / "bench"

# (이름, HF id, config, split, 공식 규모, 비고)
# ★규모는 **각 논문/데이터카드의 통용값**이다. ⚠️조회 상태는 `docs/methods/10_benchmarks.md` §6.
SPECS = [
    ("hellaswag",     "Rowan/hellaswag",              None,            "validation", 10042, "4지선다 문장완성"),
    # ⚠️2026-08-22 — `ybisk/piqa` 는 **로더 스크립트(piqa.py)** 라 최신 datasets 가 거절한다.
    #   HF 가 자동 변환해 두는 **parquet 브랜치**를 revision 으로 지정한다.
    ("piqa",          "ybisk/piqa",                   None,            "validation",  1838, "2지선다 물리상식"),
    ("winogrande",    "allenai/winogrande",           "winogrande_xl", "validation",  1267, "2지선다 대명사"),
    ("arc_easy",      "allenai/ai2_arc",              "ARC-Easy",      "test",        2376, "4지선다 과학"),
    ("arc_challenge", "allenai/ai2_arc",              "ARC-Challenge", "test",        1172, "4지선다 과학(난)"),
    # ★★2026-09-05 — arc_easy 를 **세 split 전부**로. 근거: McNemar 필요 n 2,451 vs test 2,376
    #   (결과 074 §11.4). 로컬 데이터카드 실사로 train 2,251 + test 2,376 + validation 570.
    #   ⚠️**별도 이름으로 둔다** — 기존 `arc_easy`(test 만)의 수치를 바꾸면 과거 비교가 깨진다.
    ("arc_easy_full", "allenai/ai2_arc",              "ARC-Easy",      "train+validation+test", 5197,
     "★arc_easy 세 split 전부. 정확도 검정력용"),
    # ★★2026-09-05 — KoBEST(arXiv:2204.04541). 한국어 축이 0 이었다.
    #   🚫**BoolQ·WiC·SentiNeg 는 안 받는다** — 논문 Table 4 에서 KoGPT3-39B zero-shot 이
    #   BoolQ 33.1 · WiC 34.7 로 **우연(50) 아래**다. 39B 가 못 하는 것을 81M 에 물리지 않는다.
    ("kobest_copa",   "skt/kobest_v1",                "copa",          "test",        1000, "★한국어 2지선다 인과"),
    ("kobest_hellaswag", "skt/kobest_v1",             "hellaswag",     "test",         500, "★한국어 4지선다 문장완성"),
    # ★★2026-09-06 — 우리 Stage1 held-out. 🚫**HF 가 아니라 로컬 파일**이다(SPECIAL 로 간다).
    #   v2.7 에서 D6(정답이 둘)이 0 이 되어 처음 채점에 쓸 수 있게 됐다.
    ("stage1_heldout", "(local)",                     None,            "(local)",      300, "★한국어 4지선다 관계추론(자체)"),
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


# ★2026-08-22 — 표준 `load_dataset` 로 안 되는 3종의 우회 경로. **왜 안 되는지 함께 적는다.**
SPECIAL = {}


def _fetch_piqa(split):
    """`ybisk/piqa` 는 **로더 스크립트**라 datasets 3.x 가 거절한다
    (`RuntimeError: Dataset scripts are no longer supported`).
    ★HF 가 모든 스크립트 데이터셋에 대해 자동 생성해 두는 **`refs/convert/parquet`** 브랜치를 쓴다."""
    from datasets import load_dataset
    return load_dataset("ybisk/piqa", revision="refs/convert/parquet", split=split)


def _fetch_mmlu_redux(split):
    """`edinburgh-dawg/mmlu-redux-2.0` 에는 **`all` config 가 없다** — 과목별로 나뉘어 있다.
    ★57개(실제로는 30개) 과목을 **전부 받아 이어붙인다.** 과목 이름을 `subject` 로 남긴다."""
    from datasets import load_dataset, get_dataset_config_names, concatenate_datasets
    names = get_dataset_config_names("edinburgh-dawg/mmlu-redux-2.0")
    parts = []
    for n in names:
        d = load_dataset("edinburgh-dawg/mmlu-redux-2.0", n, split=split)
        parts.append(d.add_column("subject", [n] * len(d)))
    return concatenate_datasets(parts)


def _fetch_bfcl(split):
    """BFCL 레포는 **표준 데이터 디렉터리 구조가 아니다**
    (`DataFilesNotFoundError: No (supported) data files found`).
    ★`.json`(jsonl 내용) 파일을 **직접 나열해 받는다**. 여러 카테고리가 있으므로
    ⚠️**`simple`·`multiple` 등 AST 채점 가능한 것만** 고른다 — 실행 채점이 필요한
    `exec_*` 는 우리가 어차피 못 돌린다(모델 생성 코드를 실행하지 않는다)."""
    from huggingface_hub import list_repo_files, hf_hub_download
    repo = "gorilla-llm/Berkeley-Function-Calling-Leaderboard"
    files = [f for f in list_repo_files(repo, repo_type="dataset")
             if f.endswith(".json") and "possible_answer" not in f
             and any(k in f for k in ("simple", "multiple", "parallel"))
             and "exec" not in f]
    rows = []
    for f in sorted(files):
        fp = hf_hub_download(repo, f, repo_type="dataset")
        for ln in open(fp, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                try:
                    r = json.loads(ln)
                    r["_src"] = f
                    rows.append(r)
                except json.JSONDecodeError:
                    pass
    if not rows:
        raise RuntimeError(f"{repo} 에서 읽을 수 있는 항목이 0개다 — 파일 목록 {files[:5]}")
    return rows


def _fetch_stage1_heldout(split):
    """★로컬 held-out 을 **가장 최신 판에서** 읽어 온다. HF 를 안 탄다.

    🚫★**결함이 있는 판은 내보내지 않는다.** `check_heldout_defects` 의 **D1**(오답이 정답과
    같아짐)과 **D6**(정답이 둘)은 **정확한 검사**이고 둘 중 하나라도 0 이 아니면
    그 판으로 채점한 점수는 **뜻이 없다**. 그래서 여기서 막는다 —
    ⚠️게이트를 사람이 따로 돌기를 기대하지 않는다(함정 38: 인쇄와 판정이 갈라진다).

    ★**어느 판을 썼는지 반드시 인쇄한다.** 판이 바뀌면 점수가 바뀌는데 태그에는 안 남는다.
    """
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from check_heldout_defects import BASE, load, scan, d6_two_answers   # noqa: PLC0415

    cands = sorted(p for p in BASE.glob("held-out_v2.*") if p.is_dir())
    if not cands:
        raise RuntimeError(f"{BASE} 아래에 held-out_v2.* 폴더가 없다")
    folder = cands[-1]
    _, recs = load(folder)
    d1 = scan(folder)[0] or []
    d6 = d6_two_answers(recs)
    print(f"  ★정본 판 = {folder.name}  ·  문항 {len(recs)}개  ·  D1 {len(d1)}건 · D6 {len(d6)}건")
    if d1 or d6:
        raise RuntimeError(
            f"🚫{folder.name} 은 D1 {len(d1)}건 · D6 {len(d6)}건이다 — "
            f"정답이 없거나 둘인 문항이 있는 판으로는 채점하지 않는다. "
            f"`python scripts/check_heldout_defects.py` 로 확인할 것")
    return recs


SPECIAL.update(piqa=_fetch_piqa, mmlu_redux=_fetch_mmlu_redux, bfcl_v3=_fetch_bfcl,
               stage1_heldout=_fetch_stage1_heldout)


def fetch(name, hid, cfg, split):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.jsonl"
    if name in SPECIAL:
        ds = SPECIAL[name](split)
    else:
        from datasets import load_dataset
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
    import os
    banner(f"내려받기 {len(want)}종 — ★HF 게이트로 실패하면 **그것도 결과다. 지우지 않는다**", "#")
    # ★★2026-08-22 — **어디로 받는지를 먼저 인쇄한다.** 지난번엔 조용히 사용자 환경의
    #   HF_HOME 으로 갔고 사용자가 손으로 옮겨야 했다. 보이면 다시는 안 그런다.
    print(f"  HF_HOME          = {os.environ.get('HF_HOME')}")
    print(f"  HF_DATASETS_CACHE= {os.environ.get('HF_DATASETS_CACHE')}")
    print(f"  최종 저장 위치     = {OUT}")
    if str(ROOT) not in str(os.environ.get("HF_HOME", "")):
        print("  🚫★**HF_HOME 이 작업폴더 밖을 가리킨다** — `import tinylm` 이 안 먹었다. 중단.")
        return 3
    print()
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
